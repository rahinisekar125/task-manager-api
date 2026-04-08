from fastapi import FastAPI, HTTPException, Path, Query
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum
import uuid

# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Task Manager API",
    description="A simple in-memory Task Manager with full CRUD support.",
    version="1.0.0",
)

# ── Enums & Schemas ───────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    pending    = "pending"
    in_progress = "in_progress"
    completed  = "completed"


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, examples=["Buy groceries"])
    description: Optional[str] = Field(None, max_length=1000, examples=["Milk, eggs, bread"])
    status: TaskStatus = Field(TaskStatus.pending, examples=["pending"])

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be blank or whitespace")
        return v.strip()


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[TaskStatus] = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("title must not be blank or whitespace")
        return v.strip() if v else v


class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: TaskStatus

    model_config = {"from_attributes": True}


# ── In-Memory Storage ─────────────────────────────────────────────────────────

db: dict[str, dict] = {}


# ── Helper ────────────────────────────────────────────────────────────────────

def get_task_or_404(task_id: str) -> dict:
    task = db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return task


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=201,
    summary="Create a new task",
    tags=["Tasks"],
)
def create_task(payload: TaskCreate):
    """Create a new task and return it with a generated UUID."""
    task_id = str(uuid.uuid4())
    task = {
        "id": task_id,
        "title": payload.title,
        "description": payload.description,
        "status": payload.status,
    }
    db[task_id] = task
    return task


@app.get(
    "/tasks",
    response_model=list[TaskResponse],
    summary="List all tasks",
    tags=["Tasks"],
)
def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
):
    """Return all tasks, optionally filtered by status."""
    tasks = list(db.values())
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    return tasks


@app.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Get a single task",
    tags=["Tasks"],
)
def get_task(
    task_id: str = Path(..., description="UUID of the task"),
):
    """Fetch a task by its ID."""
    return get_task_or_404(task_id)


@app.put(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Fully replace a task",
    tags=["Tasks"],
)
def replace_task(
    payload: TaskCreate,
    task_id: str = Path(..., description="UUID of the task"),
):
    """Replace all fields of an existing task (PUT semantics)."""
    get_task_or_404(task_id)
    task = {
        "id": task_id,
        "title": payload.title,
        "description": payload.description,
        "status": payload.status,
    }
    db[task_id] = task
    return task


@app.patch(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Partially update a task",
    tags=["Tasks"],
)
def update_task(
    payload: TaskUpdate,
    task_id: str = Path(..., description="UUID of the task"),
):
    """Update only the provided fields of an existing task (PATCH semantics)."""
    task = get_task_or_404(task_id)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields provided for update.")
    task.update(updates)
    db[task_id] = task
    return task


@app.delete(
    "/tasks/{task_id}",
    status_code=204,
    summary="Delete a task",
    tags=["Tasks"],
)
def delete_task(
    task_id: str = Path(..., description="UUID of the task"),
):
    """Delete a task by ID. Returns 204 No Content on success."""
    get_task_or_404(task_id)
    del db[task_id]


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Meta"], summary="Health check")
def health():
    return {"status": "ok", "task_count": len(db)}


# ── Run directly ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


# added for CodeRabbit review demo
