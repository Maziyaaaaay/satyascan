FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# build-essential: chromadb's native deps (e.g. hnswlib) occasionally have no
# prebuilt wheel for a given platform/Python combo and fall back to compiling
# from source. ffmpeg: extracts a frame + audio track from forwarded WhatsApp
# videos (see app/services/video_processing.py) - no Python package needed,
# invoked as a subprocess.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml alembic.ini ./
COPY app ./app
COPY migrations ./migrations

# Includes the [real] extras (Gemini/OpenAI/Vision/Translate SDKs) so the
# deployed container can use real providers as soon as API keys are set via
# environment variables - no rebuild needed to switch a service from mock to
# live. Confirmed live on Railway: without this, real provider calls fail
# with "google-generativeai is not installed."
RUN pip install --upgrade pip && pip install ".[real]"

RUN mkdir -p /app/data

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
