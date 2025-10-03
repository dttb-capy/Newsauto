"""Health check endpoints."""

from datetime import datetime

import psutil
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from newsauto.core.database import get_db
from newsauto.llm.ollama_client import OllamaClient

router = APIRouter()

start_time = datetime.utcnow()


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": (datetime.utcnow() - start_time).total_seconds(),
        "services": {},
    }

    # Check database
    try:
        db.execute(text("SELECT 1"))
        health_status["services"]["database"] = "connected"
    except Exception as e:
        health_status["services"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check Ollama
    try:
        ollama = OllamaClient()
        if ollama.verify_connection():
            health_status["services"]["ollama"] = "connected"
        else:
            health_status["services"]["ollama"] = "disconnected"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["ollama"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    return health_status


@router.get("/health/system")
async def system_stats():
    """System resource statistics."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    stats = {
        "cpu": {"percent": cpu_percent, "cores": psutil.cpu_count()},
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "percent": memory.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "percent": disk.percent,
        },
    }

    # GPU stats if available
    try:
        import torch

        if torch.cuda.is_available():
            stats["gpu"] = {
                "available": True,
                "device": torch.cuda.get_device_name(0),
                "memory_allocated_gb": round(
                    torch.cuda.memory_allocated() / (1024**3), 2
                ),
                "memory_reserved_gb": round(
                    torch.cuda.memory_reserved() / (1024**3), 2
                ),
            }
        else:
            stats["gpu"] = {"available": False}
    except ImportError:
        stats["gpu"] = {"available": False}

    return stats
