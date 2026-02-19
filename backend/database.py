
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"  # Use SQLite for simplicity
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Create tables
def init_db():
    from backend.models.user_model import User  # noqa: F401
    from backend.models.life_event_model import LifeEvent  # noqa: F401
    from backend.models.task_model import Task  # noqa: F401
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()

