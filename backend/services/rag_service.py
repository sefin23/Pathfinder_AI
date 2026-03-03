"""
Layer 3.2 — Requirement Retrieval Service (RAG).

Pipeline:
  1. embed_text()          — generate a 3072-dim vector via Gemini embedding API
  2. retrieve()            — cosine similarity search over the knowledge_base table
  3. explain_with_llm()    — Gemini explains retrieved chunks; no guessing beyond them
  4. rag_query()           — orchestrates the full RAG pipeline

Rules enforced:
  - All retrieval is database-based; no web scraping.
  - The LLM is only given retrieved content — it may not use outside knowledge.
  - No task creation. No DB writes (other than embedding cache writes via
    embed_and_store in the seed script).
"""

import json
import logging
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from google import genai
from google.genai import types

from backend.config import settings
from backend.models.knowledge_base_model import KnowledgeBaseEntry
from backend.schemas.nlp_schema import LifeEventType
from backend.schemas.rag_schema import (
    RAGExplanation,
    RAGQueryResponse,
    RetrievedChunk,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EMBEDDING_MODEL = "gemini-embedding-001"     # 3072-dim, multilingual
_EXPLANATION_MODEL = "gemini-2.5-flash-lite"  # separate quota from 2.0-flash
_DEFAULT_TOP_K = 3

_GROUNDED_SYSTEM_PROMPT = """\
You are a Pathfinder AI requirement advisor.

You will be given:
1. A user query.
2. A numbered list of retrieved knowledge-base entries (title + content).

Your ONLY job is to explain the retrieved requirements clearly and concisely
in the context of the user's query.

STRICT RULES:
- Base your explanation EXCLUSIVELY on the provided entries.
- Do NOT add advice, steps, or facts not present in the entries.
- Do NOT guess, hallucinate, or use outside knowledge.
- If the retrieved entries do not contain enough information, say so explicitly.
- Write in plain English. Use bullet points where helpful.
- Cite entries by their numbers (e.g. "Entry 1 states…").
"""


# ---------------------------------------------------------------------------
# Gemini client — embeddings + explanations
# ---------------------------------------------------------------------------

_gemini_client: Optional[genai.Client] = None


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    return _gemini_client


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def embed_text(text: str) -> list[float]:
    """
    Generate a 3072-dimensional embedding for *text* using Gemini.

    Args:
        text: The string to embed.

    Returns:
        A list of 3072 floats.

    Raises:
        RuntimeError: If the embedding API call fails.
    """
    client = _get_gemini_client()
    try:
        response = client.models.embed_content(
            model=_EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return response.embeddings[0].values
    except Exception as exc:
        logger.exception("Embedding generation failed.")
        raise RuntimeError(f"Embedding call failed: {exc}") from exc


def embed_text_for_document(text: str) -> list[float]:
    """
    Same as embed_text but uses RETRIEVAL_DOCUMENT task type.
    Use this when embedding knowledge-base entries during seeding.
    Produces a 3072-dimensional vector.
    """
    client = _get_gemini_client()
    try:
        response = client.models.embed_content(
            model=_EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        return response.embeddings[0].values
    except Exception as exc:
        logger.exception("Document embedding generation failed.")
        raise RuntimeError(f"Document embedding call failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return cosine similarity in [0, 1] between two float vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve(
    db: Session,
    query: str,
    life_event_type: Optional[LifeEventType] = None,
    top_k: int = _DEFAULT_TOP_K,
) -> list[RetrievedChunk]:
    """
    Embed *query* and return the top-k most similar knowledge-base entries.

    Args:
        db:               Active SQLAlchemy session.
        query:            User's natural-language question.
        life_event_type:  Optional filter; restricts candidates to one category.
        top_k:            Number of results to return.

    Returns:
        List of :class:`RetrievedChunk` sorted by similarity descending.

    Raises:
        ValueError:    If no embedded entries are found in the DB.
        RuntimeError:  If the embedding call fails.
    """
    # 1. Embed the query
    query_vector = embed_text(query)

    # 2. Load candidate entries (filter by life_event_type if provided)
    q = db.query(KnowledgeBaseEntry).filter(
        KnowledgeBaseEntry.embedding.isnot(None)  # skip unembedded rows
    )
    if life_event_type is not None:
        q = q.filter(KnowledgeBaseEntry.life_event_type == life_event_type)

    candidates = q.all()

    if not candidates:
        raise ValueError(
            "No embedded knowledge-base entries found"
            + (f" for life_event_type={life_event_type.value}" if life_event_type else "")
            + ". Run the seed script first: python -m backend.scripts.seed_knowledge_base"
        )

    # 3. Score every candidate
    scored: list[tuple[float, KnowledgeBaseEntry]] = []
    for entry in candidates:
        try:
            doc_vector = json.loads(entry.embedding)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Skipping entry id=%s — invalid embedding JSON.", entry.id)
            continue
        score = _cosine_similarity(query_vector, doc_vector)
        scored.append((score, entry))

    # 4. Sort descending, take top_k
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:top_k]

    return [
        RetrievedChunk(
            id=entry.id,
            life_event_type=entry.life_event_type,
            title=entry.title,
            content=entry.content,
            similarity_score=round(score, 4),
        )
        for score, entry in top
    ]


# ---------------------------------------------------------------------------
# Grounded LLM explanation — powered by Gemini
# ---------------------------------------------------------------------------

def explain_with_llm(
    query: str,
    chunks: list[RetrievedChunk],
) -> RAGExplanation:
    """
    Use Gemini (2.5 Flash Lite) to explain retrieved chunks.

    The model is given ONLY the retrieved content via a strict system prompt
    — it may not use outside knowledge.

    Args:
        query:  The original user query.
        chunks: Retrieved knowledge-base chunks.

    Returns:
        :class:`RAGExplanation` with explanation text and source IDs.

    Raises:
        RuntimeError: If the Gemini API call fails.
    """
    if not chunks:
        return RAGExplanation(
            explanation="No relevant requirements were found for your query.",
            source_ids=[],
        )

    # Build the grounded context block
    context_lines = []
    for i, chunk in enumerate(chunks, start=1):
        context_lines.append(
            f"Entry {i} [ID={chunk.id}, Category={chunk.life_event_type.value}]\n"
            f"Title: {chunk.title}\n"
            f"Content: {chunk.content}"
        )
    context_block = "\n\n---\n\n".join(context_lines)

    user_message = (
        f"User query: {query}\n\n"
        f"Retrieved entries:\n\n{context_block}\n\n"
        f"Explain the requirements relevant to the user's query, "
        f"drawing only from the entries above."
    )

    client = _get_gemini_client()
    try:
        response = client.models.generate_content(
            model=_EXPLANATION_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=_GROUNDED_SYSTEM_PROMPT,
                temperature=0.1,
                max_output_tokens=1024,
            ),
        )
        text = response.text.strip()
    except Exception as exc:
        err_str = str(exc)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            logger.warning("Gemini rate limited on explanation: %s", err_str[:200])
            raise RuntimeError(
                "Gemini rate limit hit. Try again in ~60s."
            ) from exc
        logger.exception("Gemini explanation call failed.")
        raise RuntimeError(f"LLM explanation failed: {exc}") from exc

    return RAGExplanation(
        explanation=text,
        source_ids=[chunk.id for chunk in chunks],
    )


# ---------------------------------------------------------------------------
# Full RAG pipeline
# ---------------------------------------------------------------------------

def rag_query(
    db: Session,
    query: str,
    life_event_type: Optional[LifeEventType] = None,
    top_k: int = _DEFAULT_TOP_K,
) -> RAGQueryResponse:
    """
    Full RAG pipeline: embed → retrieve → explain.

    Args:
        db:               Active SQLAlchemy session (read-only usage).
        query:            User's natural-language question.
        life_event_type:  Optional category filter.
        top_k:            Number of chunks to retrieve.

    Returns:
        :class:`RAGQueryResponse` with chunks + grounded explanation.
    """
    logger.info(
        "RAG query | top_k=%d | filter=%s | query=%.80s",
        top_k,
        life_event_type.value if life_event_type else "none",
        query,
    )

    chunks = retrieve(db, query, life_event_type, top_k)

    # Attempt LLM explanation — degrade gracefully if rate-limited or unavailable
    explanation: Optional[RAGExplanation] = None
    explanation_available = True
    explanation_error: Optional[str] = None

    try:
        explanation = explain_with_llm(query, chunks)
    except RuntimeError as exc:
        explanation_available = False
        explanation_error = (
            "LLM explanation unavailable (rate limited or API error). "
            "Retrieved chunks are still accurate and usable."
        )
        logger.warning("Explanation skipped — returning chunks only. Error: %s", exc)

    return RAGQueryResponse(
        success=True,
        query=query,
        life_event_type_filter=life_event_type,
        retrieved_chunks=chunks,
        explanation=explanation,
        explanation_available=explanation_available,
        explanation_error=explanation_error,
    )
