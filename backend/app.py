"""Vehicle Registry API — FastAPI + MongoDB (pymongo)."""

import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

app = FastAPI(title="Vehicle Registry API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("CORS_ORIGINS", "*")],
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/vehicles")


def get_db():
    client = MongoClient(MONGODB_URI)
    return client.get_default_database()


class VehicleCreate(BaseModel):
    brand: str
    model: str
    year: int
    color: str
    plate: str
    owner_name: str


class VehicleUpdate(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    plate: Optional[str] = None
    owner_name: Optional[str] = None


@app.get("/health")
async def health():
    try:
        db = get_db()
        db.command("ping")
        return {"status": "healthy", "database": "mongodb", "connected": True}
    except Exception as e:
        return {"status": "degraded", "database": "mongodb", "connected": False, "error": str(e)}


@app.post("/api/vehicles")
async def create_vehicle(vehicle: VehicleCreate):
    db = get_db()
    vehicle_id = str(uuid.uuid4())[:8]
    doc = {
        "_id": vehicle_id,
        "brand": vehicle.brand,
        "model": vehicle.model,
        "year": vehicle.year,
        "color": vehicle.color,
        "plate": vehicle.plate,
        "owner_name": vehicle.owner_name,
        "created_at": datetime.utcnow().isoformat(),
    }
    db.vehicles.insert_one(doc)
    return {"id": vehicle_id, "status": "created"}


@app.get("/api/vehicles")
async def list_vehicles():
    db = get_db()
    vehicles = list(db.vehicles.find().sort("created_at", -1))
    for v in vehicles:
        v["id"] = v.pop("_id")
    return {"vehicles": vehicles, "count": len(vehicles)}


@app.get("/api/vehicles/{vehicle_id}")
async def get_vehicle(vehicle_id: str):
    db = get_db()
    doc = db.vehicles.find_one({"_id": vehicle_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    doc["id"] = doc.pop("_id")
    return doc


@app.delete("/api/vehicles/{vehicle_id}")
async def delete_vehicle(vehicle_id: str):
    db = get_db()
    result = db.vehicles.delete_one({"_id": vehicle_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {"id": vehicle_id, "status": "deleted"}


@app.get("/api/stats")
async def stats():
    db = get_db()
    total = db.vehicles.count_documents({})
    return {"total_vehicles": total}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
