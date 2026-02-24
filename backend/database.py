
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"  # Use SQLite for simplicity
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Create all tables and seed the default demo user."""
    from backend.models.user_model import User       # noqa: F401
    from backend.models.life_event_model import LifeEvent  # noqa: F401
    from backend.models.task_model import Task       # noqa: F401
    Base.metadata.create_all(bind=engine)
    _seed_default_user()


def _seed_default_user():
    """Ensure user id=1 ('Demo User') exists.
    Layer 1.4 has no authentication — all events are created under this user.
    This will be replaced with real auth in a future layer.
    """
    from backend.models.user_model import User
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.id == 1).first():
            db.add(User(name="Demo User", email="demo@pathfinder.ai"))
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
