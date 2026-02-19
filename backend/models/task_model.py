from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Date
from sqlalchemy.orm import relationship
from backend.database import Base
from datetime import datetime, timezone
import enum


class TaskStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    skipped = "skipped"


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.pending, nullable=False)
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.medium, nullable=False)
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Foreign key — every task belongs to a life event
    life_event_id = Column(Integer, ForeignKey("life_events.id"), nullable=False)

    # Relationships
    life_event = relationship("LifeEvent", back_populates="tasks")
