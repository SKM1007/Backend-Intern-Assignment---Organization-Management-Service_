from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.db import connect_to_mongo, close_mongo_connection
from app.api.v1.org import router as org_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Events
    await connect_to_mongo()
    yield
    # Shutdown Events
    await close_mongo_connection()

# Initialize the FastAPI application
app = FastAPI(
    title="Organization Management Service",
    version="1.0.0",
    lifespan=lifespan
)

# Include the main router
app.include_router(org_router, prefix="/api/v1")

# Optional root endpoint
@app.get("/")
async def root():
    return {"message": "Organization Management Service API is running."}