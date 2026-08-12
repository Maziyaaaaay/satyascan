import logging
from typing import Optional

import structlog

from app.config import get_settings

_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    settings = get_settings()
    level = logging.getLevelName(settings.log_level.upper())
    logging.basicConfig(format="%(message)s", level=level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # chromadb 0.4.x's bundled posthog telemetry client is incompatible with
    # newer posthog releases (capture() signature changed), so every attempt
    # logs a "Failed to send telemetry event" error. The send always fails
    # locally before any network call is attempted (harmless, just noisy) -
    # anonymized_telemetry=False is also set on the client itself, but this
    # silences the resulting error spam regardless.
    logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

    _configured = True


def get_logger(name: Optional[str] = None):
    configure_logging()
    return structlog.get_logger(name)
