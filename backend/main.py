from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.database import init_db
from backend.routes import life_event_routes, nlp_routes, rag_routes, task_routes, user_routes, workflow_routes
from backend.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB + start scheduler. Shutdown: stop scheduler cleanly."""
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Pathfinder AI - Backend", lifespan=lifespan)

# Add CORS middleware
# Note: allow_origins=["*"] is restricted when allow_credentials=True
# In production, Replace with explicit frontend URLs (e.g. ["http://localhost:5173"])
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex="http://localhost:.*",  # Allow any local port for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(user_routes.router, prefix="/users", tags=["Users"])
app.include_router(life_event_routes.router, prefix="/life-events", tags=["Life Events"])
app.include_router(task_routes.router, prefix="/tasks", tags=["Tasks"])
app.include_router(nlp_routes.router, prefix="/life-events", tags=["NLP"])
app.include_router(rag_routes.router, prefix="/rag", tags=["RAG"])
app.include_router(workflow_routes.router, prefix="/life-events", tags=["Workflow"])


@app.get("/")
def root():
    return {"message": "Welcome to the Pathfinder AI Backend"}
