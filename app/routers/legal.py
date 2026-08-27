from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

_STATIC_DIR = Path(__file__).parent.parent / "static" / "legal"


@router.get("/privacy")
async def privacy_policy():
    return FileResponse(_STATIC_DIR / "privacy.html")


@router.get("/terms")
async def terms_of_service():
    return FileResponse(_STATIC_DIR / "terms.html")
