#!/bin/sh
set -e

# Platforms like Railway inject their own PORT and route to whatever the
# container listens on; fall back to 8000 for plain `docker compose up`
# where nothing sets PORT.
PORT="${PORT:-8000}"

# Chroma collections here are entirely transient by design (see
# app/agents/evidence_ranking.py: one collection per verification, written
# and queried once, then deleted immediately after in the same request) -
# nothing is meant to survive a restart. A leak in that cleanup (fixed
# separately) let this directory grow unbounded and was confirmed live as
# the actual cause of a "database or disk is full" production outage on a
# small persistent volume - clearing it unconditionally on every boot means
# a stray future leak can never again fill the disk badly enough to stop
# the app from even starting. This is a deletion, not a write, so it's safe
# to run even when the volume is already completely full.
rm -rf "${CHROMA_PERSIST_DIR:-/app/data/chroma}"/*

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
