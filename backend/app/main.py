from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.init_db import init_database
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="HotelIQ Revenue Management API",
    description="AI-powered revenue management platform for hotels",
    version="1.0.0"
)

# CORS middleware (for frontend later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on app startup"""
    init_database()

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "🏨 HotelIQ Revenue Management API",
        "status": "active",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected"
    }

# We'll add API routes here in next steps

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)