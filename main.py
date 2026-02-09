"""
Artworks API - A simple FastAPI application for managing artwork listings.

Run with: uvicorn main:app --reload
Docs available at: http://localhost:8000/docs
"""

from fastapi import FastAPI, Query, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from typing import Optional
from pymongo import MongoClient
from dotenv import load_dotenv
import json
import uuid
import os
from pathlib import Path

load_dotenv()

API_KEY = os.getenv("API_KEY")

# Initialize FastAPI app
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

app = FastAPI(
    title="Artworks API",
    description="API for browsing and filtering artwork listings",
    version="1.0.0",
    dependencies=[Depends(api_key_header)] if API_KEY else [],
)

# Allow cross-origin requests (useful if you want to call this from your portfolio site)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your actual domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API key middleware — require X-API-Key header on all endpoints except /
class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not API_KEY:
            return await call_next(request)
        exempt = {"/", "/docs", "/redoc", "/openapi.json"}
        if request.url.path in exempt or request.method == "OPTIONS":
            return await call_next(request)
        provided_key = request.headers.get("X-API-Key")
        if provided_key != API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
        return await call_next(request)


app.add_middleware(APIKeyMiddleware)

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
client = MongoClient(MONGODB_URI)
db = client["artworks_db"]
collection = db["artworks"]

# Path to seed data file
DATA_PATH = Path(__file__).parent / "data" / "artworks.json"


# --- Data Models ---

class Artwork(BaseModel):
    """Represents a single artwork item."""
    id: str
    title: str
    description: str
    types: list[str]
    price: float
    dimensions: str
    year: int
    available: bool
    image_url: str


class ArtworkCreate(BaseModel):
    """Model for creating a new artwork (no ID required)."""
    title: str
    description: str
    types: list[str]
    price: float
    dimensions: str
    year: int
    available: bool = True
    image_url: str = ""


class ArtworkUpdate(BaseModel):
    """Model for updating an artwork (all fields optional)."""
    title: Optional[str] = None
    description: Optional[str] = None
    types: Optional[list[str]] = None
    price: Optional[float] = None
    dimensions: Optional[str] = None
    year: Optional[int] = None
    available: Optional[bool] = None
    image_url: Optional[str] = None


class ArtworksResponse(BaseModel):
    """Response model for artwork listings."""
    total: int
    filtered_count: int
    artworks: list[Artwork]


# --- Startup: Seed database if empty ---

@app.on_event("startup")
def seed_database():
    """Seed the database with initial data if the collection is empty."""
    if collection.count_documents({}) == 0:
        with open(DATA_PATH, "r") as f:
            data = json.load(f)
        if data["artworks"]:
            collection.insert_many(data["artworks"])
            print(f"Seeded database with {len(data['artworks'])} artworks")


# --- Helper Functions ---

def generate_id() -> str:
    """Generate a unique ID for new artworks."""
    return str(uuid.uuid4())[:8]


def artwork_from_doc(doc: dict) -> dict:
    """Convert a MongoDB document to an artwork dict (remove _id)."""
    doc.pop("_id", None)
    return doc


# --- API Endpoints ---

@app.get("/", tags=["General"])
def root():
    """Welcome endpoint with API information."""
    return {
        "message": "Welcome to the Artworks API",
        "docs": "/docs",
        "endpoints": {
            "list_artworks": "GET /artworks",
            "get_artwork": "GET /artworks/{artwork_id}",
            "create_artwork": "POST /artworks",
            "update_artwork": "PUT /artworks/{artwork_id}",
            "delete_artwork": "DELETE /artworks/{artwork_id}",
            "get_types": "GET /types",
        },
    }


@app.get("/artworks", response_model=ArtworksResponse, tags=["Artworks"])
def list_artworks(
    type: Optional[str] = Query(
        None,
        description="Filter by artwork type (e.g., watercolor, mixed-media, large-canvas, featured)",
    ),
    available: Optional[bool] = Query(
        None,
        description="Filter by availability (true/false)",
    ),
    min_price: Optional[float] = Query(
        None,
        description="Minimum price filter",
        ge=0,
    ),
    max_price: Optional[float] = Query(
        None,
        description="Maximum price filter",
        ge=0,
    ),
    year: Optional[int] = Query(
        None,
        description="Filter by year created",
    ),
):
    """
    Get a list of artworks with optional filters.
    """
    total = collection.count_documents({})

    # Build MongoDB query
    query = {}

    if type:
        query["types"] = {"$regex": f"^{type}$", "$options": "i"}

    if available is not None:
        query["available"] = available

    price_filter = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price
    if price_filter:
        query["price"] = price_filter

    if year is not None:
        query["year"] = year

    results = [artwork_from_doc(doc) for doc in collection.find(query)]

    return ArtworksResponse(
        total=total,
        filtered_count=len(results),
        artworks=results,
    )


@app.get("/artworks/{artwork_id}", response_model=Artwork, tags=["Artworks"])
def get_artwork(artwork_id: str):
    """Get a single artwork by its ID."""
    doc = collection.find_one({"id": artwork_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Artwork with id '{artwork_id}' not found")
    return artwork_from_doc(doc)


@app.post("/artworks", response_model=Artwork, status_code=201, tags=["Artworks"])
def create_artwork(artwork: ArtworkCreate):
    """Create a new artwork."""
    new_artwork = {
        "id": generate_id(),
        **artwork.model_dump(),
    }
    collection.insert_one(new_artwork)
    return artwork_from_doc(new_artwork)


@app.put("/artworks/{artwork_id}", response_model=Artwork, tags=["Artworks"])
def update_artwork(artwork_id: str, artwork_update: ArtworkUpdate):
    """Update an existing artwork."""
    update_data = artwork_update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = collection.find_one_and_update(
        {"id": artwork_id},
        {"$set": update_data},
        return_document=True,
    )

    if not result:
        raise HTTPException(status_code=404, detail=f"Artwork with id '{artwork_id}' not found")

    return artwork_from_doc(result)


@app.delete("/artworks/{artwork_id}", tags=["Artworks"])
def delete_artwork(artwork_id: str):
    """Delete an artwork by its ID."""
    doc = collection.find_one_and_delete({"id": artwork_id})

    if not doc:
        raise HTTPException(status_code=404, detail=f"Artwork with id '{artwork_id}' not found")

    return {
        "message": f"Artwork '{doc['title']}' deleted successfully",
        "deleted_id": artwork_id,
    }


@app.get("/types", tags=["Artworks"])
def list_types():
    """Get all available artwork types."""
    types = sorted(collection.distinct("types"))
    return {
        "types": types,
        "count": len(types),
    }
