#!/bin/sh
set -e

# Platforms like Railway inject their own PORT and route to whatever the
# container listens on; fall back to 8000 for plain `docker compose up`
# where nothing sets PORT.
PORT="${PORT:-8000}"

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
