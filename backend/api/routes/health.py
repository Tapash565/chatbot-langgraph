"""Health check API routes."""
from fastapi import APIRouter, Request
from datetime import datetime

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(request: Request):
    """Readiness check endpoint."""
    try:
        # Check database connection
        from backend.db.session import db_session
        with db_session.cursor() as cursor:
            cursor.execute("SELECT 1")

        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
