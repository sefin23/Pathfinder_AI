from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.schemas.life_event_schema import LifeEventCreate, LifeEventResponse, LifeEventWithTasksResponse
from backend.models.life_event_model import LifeEvent
from backend.models.user_model import User
from backend.database import SessionLocal

router = APIRouter()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=LifeEventResponse)
def create_life_event(life_event: LifeEventCreate, db: Session = Depends(get_db)):
    """Create a new life event for a user."""
    # Verify the user exists
    user = db.query(User).filter(User.id == life_event.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_life_event = LifeEvent(
        title=life_event.title,
        description=life_event.description,
        user_id=life_event.user_id
    )
    db.add(db_life_event)
    db.commit()
    db.refresh(db_life_event)
    return db_life_event


@router.get("/", response_model=List[LifeEventResponse])
def get_life_events(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """List all life events. Optionally filter by user_id."""
    query = db.query(LifeEvent)
    if user_id is not None:
        query = query.filter(LifeEvent.user_id == user_id)
    return query.all()


@router.get("/{life_event_id}", response_model=LifeEventWithTasksResponse)
def get_life_event(life_event_id: int, db: Session = Depends(get_db)):
    """Get a specific life event with all its tasks."""
    life_event = db.query(LifeEvent).filter(LifeEvent.id == life_event_id).first()
    if not life_event:
        raise HTTPException(status_code=404, detail="Life event not found")
    return life_event
