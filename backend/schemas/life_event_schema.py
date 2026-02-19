from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from backend.models.life_event_model import LifeEventStatus


class LifeEventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    user_id: int


class LifeEventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: LifeEventStatus
    created_at: datetime
    updated_at: datetime
    user_id: int

    class Config:
        from_attributes = True


class LifeEventWithTasksResponse(LifeEventResponse):
    """Returns a life event along with all its tasks."""
    tasks: List["TaskResponse"] = []

    class Config:
        from_attributes = True


# Avoid circular import — import TaskResponse after defining the class
from backend.schemas.task_schema import TaskResponse  # noqa: E402

LifeEventWithTasksResponse.model_rebuild()
