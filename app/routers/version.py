from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["Version"])

@router.get("/version")
def get_version():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV
    }