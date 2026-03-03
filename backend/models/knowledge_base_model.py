"""
Layer 3.2 — Knowledge Base model.

Each row is one curated requirement (a document chunk) associated with a
specific life-event type. The embedding column stores a JSON-serialised
list of floats produced by Gemini gemini-embedding-001 (3072 dimensions).

Embeddings are stored in the DB so retrieval is entirely database-based —
no web scraping, no external vector stores at query time.
"""

import enum

from sqlalchemy import Column, Integer, String, Text, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from backend.database import Base
from backend.schemas.nlp_schema import LifeEventType  # reuse canonical enum


class KnowledgeBaseEntry(Base):
    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True, index=True)

    # Canonical life-event category this entry belongs to
    life_event_type = Column(
        SQLEnum(LifeEventType),
        nullable=False,
        index=True,
    )

    # Short human-readable label for the requirement
    title = Column(String(255), nullable=False)

    # Full requirement text — the content that gets retrieved and shown to the user
    content = Column(Text, nullable=False)

    # JSON-serialised list[float] — 3072 floats for gemini-embedding-001
    # Stored as TEXT because SQLite has no native vector type.
    # Format: "[0.123, -0.456, ...]"
    embedding = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
