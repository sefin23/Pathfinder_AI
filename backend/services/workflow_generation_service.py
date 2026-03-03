"""
Layer 3.3 — Workflow Generation Service.

Pipeline:
  1. For each life_event_type in the request, call retrieve() to get top-k
     knowledge-base entries.
  2. Merge and de-duplicate chunks from all types.
  3. Build a grounded prompt containing ONLY the retrieved content.
  4. Call Gemini with response_mime_type="application/json" to enforce
     strict JSON output matching the required schema.
  5. Parse and validate with Pydantic before returning.

Rules enforced:
  - The LLM is given ONLY retrieved knowledge; no outside facts allowed.
  - No DB writes.
  - No scheduler interaction.
  - No task auto-creation.
  - If retrieved content is insufficient, return an error dict which the
    route maps to a graceful response (not a 5xx).
"""

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from google import genai
from google.genai import types

from backend.config import settings
from backend.schemas.nlp_schema import LifeEventType
from backend.schemas.rag_schema import RetrievedChunk
from backend.schemas.workflow_schema import (
    ProposedSubtask,
    ProposedTask,
    WorkflowProposalResponse,
)
from backend.services.rag_service import retrieve

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GENERATION_MODEL = "gemini-2.5-flash-lite"

_WORKFLOW_SYSTEM_PROMPT = """\
You are Pathfinder AI, a life-event workflow planner.

You will receive:
1. One or more life-event types the user is going through.
2. Optional location and timeline context.
3. A numbered list of retrieved knowledge-base entries — these are the ONLY
   facts you may use.

Your job is to generate a practical, ordered task workflow to help the user
complete this life event.

STRICT RULES:
- Base EVERY task and subtask EXCLUSIVELY on the retrieved entries.
- Do NOT invent documents, steps, deadlines, or requirements not present in
  the entries.
- Do NOT use outside knowledge, legal advice, or general assumptions.
- If the retrieved entries do not contain enough information to generate a
  meaningful workflow, respond ONLY with:
  {"error": "Insufficient knowledge to generate workflow."}
- Assign priority 1 (most urgent) to 5 (least urgent).
- suggested_due_offset_days must be 0 or a positive integer.
- If a timeline is given, derive offsets logically from it.
- If no timeline, use sensible relative ordering (earlier steps get lower
  offsets than later steps).
- Output ONLY valid JSON matching this exact structure:
  {
    "tasks": [
      {
        "title": string,
        "description": string,
        "priority": integer 1-5,
        "suggested_due_offset_days": integer >= 0,
        "subtasks": [
          {
            "title": string,
            "priority": integer 1-5,
            "suggested_due_offset_days": integer >= 0
          }
        ]
      }
    ]
  }
- Do not include markdown, code fences, or any text outside the JSON.
"""

# ---------------------------------------------------------------------------
# Gemini client (shared lazy singleton via rag_service would cause circular
# import — keep a local one here)
# ---------------------------------------------------------------------------

_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


# ---------------------------------------------------------------------------
# Retrieval aggregation
# ---------------------------------------------------------------------------

def _gather_chunks(
    db: Session,
    life_event_types: list[LifeEventType],
    top_k: int,
) -> list[RetrievedChunk]:
    """
    Run RAG retrieval for each life-event type and merge results.

    De-duplicates by chunk ID so the same entry is never sent twice even
    when multiple life-event types share knowledge.

    Args:
        db:               Active SQLAlchemy session (read-only).
        life_event_types: Life event categories to retrieve for.
        top_k:            Number of chunks per category.

    Returns:
        Deduplicated list of :class:`RetrievedChunk` sorted by similarity.
    """
    seen_ids: set[int] = set()
    merged: list[RetrievedChunk] = []

    for event_type in life_event_types:
        # Build a rich query string so the embedding captures context
        query = f"requirements and documents for {event_type.value.replace('_', ' ').lower()}"
        try:
            chunks = retrieve(db, query, life_event_type=event_type, top_k=top_k)
        except ValueError:
            # No entries for this type — skip gracefully
            logger.warning("No KB entries found for life_event_type=%s", event_type.value)
            continue
        except RuntimeError as exc:
            raise RuntimeError(f"Retrieval failed for {event_type.value}: {exc}") from exc

        for chunk in chunks:
            if chunk.id not in seen_ids:
                seen_ids.add(chunk.id)
                merged.append(chunk)

    # Re-sort by similarity descending so the most relevant content leads
    merged.sort(key=lambda c: c.similarity_score, reverse=True)
    return merged


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(
    life_event_types: list[LifeEventType],
    location: Optional[str],
    timeline: Optional[str],
    chunks: list[RetrievedChunk],
) -> str:
    """Assemble the grounded user message for the LLM."""
    types_str = ", ".join(t.value.replace("_", " ") for t in life_event_types)

    context_lines = [f"Life event(s): {types_str}"]
    if location:
        context_lines.append(f"Location: {location}")
    if timeline:
        context_lines.append(f"Timeline: {timeline}")

    context_lines.append("\nRetrieved knowledge-base entries:\n")
    for i, chunk in enumerate(chunks, start=1):
        context_lines.append(
            f"Entry {i} [ID={chunk.id}, Category={chunk.life_event_type.value}]\n"
            f"Title: {chunk.title}\n"
            f"Content: {chunk.content}"
        )

    context_lines.append(
        "\nGenerate a step-by-step task workflow using ONLY the entries above."
    )
    return "\n\n".join(context_lines)


# ---------------------------------------------------------------------------
# LLM call + parse
# ---------------------------------------------------------------------------

def _generate_workflow(prompt: str) -> dict:
    """
    Call Gemini with strict JSON output and return the parsed dict.

    Raises:
        RuntimeError: If the API call or JSON parsing fails.
    """
    client = _get_client()
    try:
        response = client.models.generate_content(
            model=_GENERATION_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_WORKFLOW_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.2,           # low temp for deterministic structure
                max_output_tokens=4096,
            ),
        )
        raw = response.text.strip()
    except Exception as exc:
        err_str = str(exc)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            raise RuntimeError("Gemini rate limit hit. Try again in ~60s.") from exc
        raise RuntimeError(f"Workflow LLM call failed: {exc}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON: %s", raw[:300])
        raise RuntimeError(f"LLM returned non-JSON output: {exc}") from exc


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def _parse_tasks(data: dict) -> tuple[list[ProposedTask], Optional[str]]:
    """
    Validate and coerce the LLM output dict into Pydantic models.

    Returns:
        (tasks, error) — either tasks is populated or error is set.
    """
    # LLM signalled insufficient knowledge
    if "error" in data:
        return [], data["error"]

    raw_tasks = data.get("tasks", [])
    if not raw_tasks:
        return [], "Insufficient knowledge to generate workflow."

    tasks: list[ProposedTask] = []
    for raw_task in raw_tasks:
        # Guard against LLM omitting title
        task_title = raw_task.get("title")
        if not task_title:
            continue

        raw_subtasks = raw_task.get("subtasks", [])
        subtasks: list[ProposedSubtask] = []
        for s in raw_subtasks:
            sub_title = s.get("title")
            if not sub_title:
                continue
            subtasks.append(
                ProposedSubtask(
                    title=sub_title,
                    priority=max(1, min(5, int(s.get("priority", 3)))),
                    suggested_due_offset_days=max(0, int(s.get("suggested_due_offset_days", 0))),
                )
            )

        tasks.append(
            ProposedTask(
                title=task_title,
                description=raw_task.get("description", ""),
                priority=max(1, min(5, int(raw_task.get("priority", 3)))),
                suggested_due_offset_days=max(
                    0, int(raw_task.get("suggested_due_offset_days", 0))
                ),
                subtasks=subtasks,
            )
        )

    return tasks, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def propose_workflow(
    db: Session,
    life_event_types: list[LifeEventType],
    location: Optional[str],
    timeline: Optional[str],
    top_k: int = 5,
) -> WorkflowProposalResponse:
    """
    Full Layer 3.3 pipeline: retrieve → prompt → generate → validate.

    Args:
        db:               Read-only SQLAlchemy session.
        life_event_types: Life event categories.
        location:         Optional location string.
        timeline:         Optional timeline hint.
        top_k:            KB entries to retrieve per event type.

    Returns:
        :class:`WorkflowProposalResponse` — either tasks or an error message.

    Raises:
        RuntimeError: If retrieval or LLM generation fails at the infrastructure level.
        ValueError:   If the KB is empty for all requested event types.
    """
    logger.info(
        "Workflow proposal | types=%s | location=%s | timeline=%s",
        [t.value for t in life_event_types],
        location,
        timeline,
    )

    # 1. Retrieve grounded knowledge
    chunks = _gather_chunks(db, life_event_types, top_k)

    if not chunks:
        raise ValueError(
            "No knowledge-base entries found for the requested life event type(s). "
            "Run the seed script first: python -m backend.scripts.seed_knowledge_base"
        )

    # 2. Build grounded prompt
    prompt = _build_prompt(life_event_types, location, timeline, chunks)

    # 3. Call LLM
    raw_data = _generate_workflow(prompt)

    # 4. Validate with Pydantic
    tasks, error = _parse_tasks(raw_data)

    return WorkflowProposalResponse(
        success=error is None,
        life_event_types=life_event_types,
        location=location,
        timeline=timeline,
        tasks=tasks,
        retrieved_chunk_ids=[c.id for c in chunks],
        error=error,
    )
