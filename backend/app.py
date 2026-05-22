"""Task Manager API — FastAPI + MongoDB (pymongo)."""

import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

app = FastAPI(title="Task Manager API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("CORS_ORIGINS", "*")],
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/taskmanager")


def get_db():
    client = MongoClient(MONGODB_URI)
    return client.get_default_database()


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    done: Optional[bool] = None


@app.get("/health")
async def health():
    try:
        db = get_db()
        db.command("ping")
        return {"status": "healthy", "database": "mongodb", "connected": True}
    except Exception as e:
        return {"status": "degraded", "database": "mongodb", "connected": False, "error": str(e)}


@app.post("/api/tasks")
async def create_task(task: TaskCreate):
    db = get_db()
    task_id = str(uuid.uuid4())[:8]
    doc = {
        "_id": task_id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "done": False,
        "created_at": datetime.utcnow().isoformat(),
    }
    db.tasks.insert_one(doc)
    return {"id": task_id, "status": "created"}


@app.get("/api/tasks")
async def list_tasks(done: Optional[bool] = None):
    db = get_db()
    query = {}
    if done is not None:
        query["done"] = done
    tasks = list(db.tasks.find(query).sort("created_at", -1))
    for t in tasks:
        t["id"] = t.pop("_id")
    return {"tasks": tasks, "count": len(tasks)}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    db = get_db()
    doc = db.tasks.find_one({"_id": task_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Task not found")
    doc["id"] = doc.pop("_id")
    return doc


@app.put("/api/tasks/{task_id}")
async def update_task(task_id: str, task: TaskUpdate):
    db = get_db()
    updates = {k: v for k, v in task.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = db.tasks.update_one({"_id": task_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task_id, "status": "updated"}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    db = get_db()
    result = db.tasks.delete_one({"_id": task_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task_id, "status": "deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
