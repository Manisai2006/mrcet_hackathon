import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine, Base
from app.routes import auth, chat, voice, documents, rag, exams, analytics

# Create tables if not exists
Base.metadata.create_all(bind=engine)

# Safe SQLite schema migration for new columns
with engine.connect() as conn:
    try:
        from sqlalchemy import text
        conn.execute(text("ALTER TABLE documents ADD COLUMN extraction_method VARCHAR DEFAULT 'text'"))
        conn.commit()
    except Exception:
        pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI Regional-Language Personal Tutor Backend API"
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local hackathon development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Router Modules
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(voice.router)
app.include_router(documents.router)
app.include_router(rag.router)
app.include_router(exams.router)
app.include_router(analytics.router)








@app.get("/", tags=["Health Check"])
def root_healthcheck():
    return {
        "status": "online",
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "connected",
        "configured_gemini_keys": len(settings.GEMINI_API_KEYS)
    }

@app.get("/api/health", tags=["Health Check"])
def api_healthcheck():
    return {
        "status": "healthy",
        "message": "AI Regional Tutor API is running smoothly."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
