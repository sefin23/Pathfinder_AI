# Plan: Layer 1.1 - Project Skeleton Setup

## Goal

Initialize a minimal FastAPI project structure for Pathfinder AI, focusing on a clean, scalable foundation without premature complexity.

## Proposed Structure

```text
backend/
├── main.py              # Application entry point
├── database.py          # Database connection (SQLite)
├── models.py            # database models (SQLAlchemy)
├── schemas.py           # Pydantic schemas (Request/Response)
└── routes/              # API Route definitions
    └── __init__.py
```

## Tasks

- [x] Create `backend` directory
- [x] Create `main.py` (FastAPI app instance)
- [x] Create `database.py` (SQLAlchemy setup)
- [x] Create `models.py` (Empty for now, just structure)
- [x] Create `schemas.py` (Empty for now)
- [x] Verify environment works (`uvicorn backend.main:app --reload`)

## Verification

- [x] `uvicorn backend.main:app` starts without errors.
- [x] `curl localhost:8000/docs` returns 200 OK.
