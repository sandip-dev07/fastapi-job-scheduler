import logging

import redis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.utils.configs import settings
from src.utils.db import get_db

logger = logging.getLogger(__name__)

health_router = APIRouter(tags=["Health"])


@health_router.get("/health/live")
def liveness():
    return {"message": "Service is healthy"}


@health_router.get("/health/ready")
def readiness(db: Session = Depends(get_db)):
    checks = {"database": "ok", "redis": "ok"}
    healthy = True

    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database readiness check failed")
        checks["database"] = "error"
        healthy = False

    client = None
    try:
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
    except Exception:
        logger.exception("Redis readiness check failed")
        checks["redis"] = "error"
        healthy = False
    finally:
        if client is not None:
            client.close()

    if not healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=checks,
        )

    return {
        "message": "Service is healthy",
        "data": checks,
    }
