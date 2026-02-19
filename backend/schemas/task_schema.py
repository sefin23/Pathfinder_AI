from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from backend.models.task_model import TaskStatus, TaskPriority


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.medium
    due_date: Optional[date] = None
    life_event_id: int


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[date]
    created_at: datetime
    updated_at: datetime
    life_event_id: int

    class Config:
        from_attributes = True


class TaskStatusUpdate(BaseModel):
    """Used by PATCH /tasks/{id}/status to update only the status field."""
    status: TaskStatus
