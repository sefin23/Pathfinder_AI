from fastapi import FastAPI
from backend.routes import user_routes, life_event_routes, task_routes
from backend.database import init_db

app = FastAPI(title="Pathfinder AI - Backend")

# Initialize database tables
init_db()

# Include routers
app.include_router(user_routes.router, prefix="/users", tags=["Users"])
app.include_router(life_event_routes.router, prefix="/life-events", tags=["Life Events"])
app.include_router(task_routes.router, prefix="/tasks", tags=["Tasks"])


@app.get("/")
def root():
    return {"message": "Welcome to the Pathfinder AI Backend"}

