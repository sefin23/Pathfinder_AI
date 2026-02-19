# Plan: Layer 1.2 - Core Domain Models (Life Events & Tasks)

## Goal

Build the core domain models that represent the heart of Pathfinder AI:
**Life Events** and **Tasks**. These models bring the "life-event first" philosophy
to life — every task belongs to a life event, and every life event belongs to a user.

## Why This Matters

Layer 1.1 gave us a working skeleton with a `User` model.
But Pathfinder AI is about helping users manage _life situations_ — moving cities,
starting a job, graduating, etc. We need models that capture:

- A **LifeEvent** (e.g., "Moving to Bangalore for first job")
- **Tasks** within that event (e.g., "Find accommodation", "Open bank account")
- Relationships: User → LifeEvents → Tasks

## What We'll Build

### Database Models (SQLAlchemy)

1. **LifeEvent** model (`backend/models/life_event_model.py`)
   - `id` — Primary key
   - `title` — Short description ("Moving to Bangalore")
   - `description` — Detailed context (optional)
   - `status` — Enum: `active`, `paused`, `completed`
   - `created_at` — Timestamp
   - `updated_at` — Timestamp
   - `user_id` — Foreign key → User

2. **Task** model (`backend/models/task_model.py`)
   - `id` — Primary key
   - `title` — Short description ("Find PG accommodation")
   - `description` — Details / notes (optional)
   - `status` — Enum: `pending`, `in_progress`, `completed`, `skipped`
   - `priority` — Enum: `low`, `medium`, `high`
   - `due_date` — Optional deadline
   - `created_at` — Timestamp
   - `updated_at` — Timestamp
   - `life_event_id` — Foreign key → LifeEvent

### Pydantic Schemas (Request/Response)

3. **LifeEvent schemas** (`backend/schemas/life_event_schema.py`)
   - `LifeEventCreate` — For creating a new life event
   - `LifeEventResponse` — For returning life event data

4. **Task schemas** (`backend/schemas/task_schema.py`)
   - `TaskCreate` — For creating a new task
   - `TaskResponse` — For returning task data

### API Routes

5. **LifeEvent routes** (`backend/routes/life_event_routes.py`)
   - `POST /life-events/` — Create a life event for a user
   - `GET /life-events/` — List all life events (filterable by user)
   - `GET /life-events/{id}` — Get a specific life event with its tasks

6. **Task routes** (`backend/routes/task_routes.py`)
   - `POST /tasks/` — Create a task under a life event
   - `GET /tasks/` — List tasks (filterable by life event)
   - `PATCH /tasks/{id}/status` — Update task status

### Wiring

7. **Update `database.py`** — Register new models in `init_db()`
8. **Update `main.py`** — Include new routers

## Tasks (Step-by-step)

- [x] 1. Create `LifeEvent` model
- [x] 2. Create `Task` model
- [x] 3. Create LifeEvent schemas
- [x] 4. Create Task schemas
- [x] 5. Create LifeEvent routes
- [x] 6. Create Task routes
- [x] 7. Wire everything into `database.py` and `main.py`
- [x] 8. Delete old `test.db` and verify fresh start
- [x] 9. Test all endpoints via `/docs`

## Verification

- [ ] Server starts without errors
- [ ] Can create a user, then a life event for that user
- [ ] Can create tasks under a life event
- [ ] Can update task status
- [ ] All data persists in SQLite
