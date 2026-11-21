"""
EMS AI Service  Main entry point.
Starts the FastAPI workflow API server.

Usage:
    python main.py                    # dev mode with auto-reload
    uvicorn main:app --host 0.0.0.0   # production
"""
import uvicorn
from app.orchestration.workflow_api import app  # noqa: F401

if __name__ == "__main__":
    from app.config.settings import settings
    uvicorn.run(
        "app.orchestration.workflow_api:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
