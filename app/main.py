from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.logging_conf import configure_logging
from app.routers import feedback, health, landing, legal, simulator, webhook_whatsapp

_STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="SatyaScan Verification Engine", version="0.1.0")

    app.include_router(health.router)
    app.include_router(webhook_whatsapp.router)
    app.include_router(simulator.router)
    app.include_router(feedback.router)
    app.include_router(legal.router)
    app.include_router(landing.router)

    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    return app


app = create_app()
