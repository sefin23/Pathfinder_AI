from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.schemas.task_schema import TaskCreate, TaskResponse, TaskStatusUpdate
from backend.models.task_model import Task
from backend.models.life_event_model import LifeEvent
from backend.database import SessionLocal

router = APIRouter()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task under a life event. Pass parent_id to create a subtask."""
    # Verify the life event exists
    life_event = db.query(LifeEvent).filter(LifeEvent.id == task.life_event_id).first()
    if not life_event:
        raise HTTPException(status_code=404, detail="Life event not found")

    # If parent_id is given, verify the parent task exists and belongs to the same life event
    if task.parent_id is not None:
        parent_task = db.query(Task).filter(Task.id == task.parent_id).first()
        if not parent_task:
            raise HTTPException(status_code=404, detail="Parent task not found")
        if parent_task.life_event_id != task.life_event_id:
            raise HTTPException(
                status_code=400,
                detail="Parent task belongs to a different life event"
            )

    db_task = Task(
        title=task.title,
        description=task.description,
        priority=task.priority,
        due_date=task.due_date,
        life_event_id=task.life_event_id,
        parent_id=task.parent_id  # None = top-level task
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.get("/", response_model=List[TaskResponse])
def get_tasks(life_event_id: Optional[int] = None, db: Session = Depends(get_db)):
    """List all tasks. Optionally filter by life_event_id."""
    query = db.query(Task)
    if life_event_id is not None:
        query = query.filter(Task.life_event_id == life_event_id)
    return query.all()


@router.patch("/{task_id}/status", response_model=TaskResponse)
def update_task_status(task_id: int, update: TaskStatusUpdate, db: Session = Depends(get_db)):
    """Update only the status of a task (e.g., pending → in_progress → completed)."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = update.status
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task and all its subtasks (cascade handled by SQLAlchemy)."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()
    # 204 No Content — return nothing
