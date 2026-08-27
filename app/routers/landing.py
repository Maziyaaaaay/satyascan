from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

_STATIC_DIR = Path(__file__).parent.parent / "static" / "landing"


@router.get("/")
async def landing_page():
    return FileResponse(_STATIC_DIR / "index.html")
