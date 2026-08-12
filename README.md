# SatyaScan Verification Engine (SVE) — MVP

An AI verification engine that lets a user forward a suspicious message or image on WhatsApp
and get back a verdict, confidence score, sources, and a plain-language explanation
(English or Malayalam). WhatsApp is the first client of a centralized verification engine
built around an 8-agent pipeline.

This is the MVP scope only: the WhatsApp-first flow, the full backend and database, and a
local browser-based chat simulator for testing without a live WhatsApp number. See
`docs/` (none yet) — for now, architecture decisions are described inline below and in code
docstrings/comments where non-obvious.

## Quickstart (local, no external accounts needed)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Then open http://localhost:8000/simulator in a browser and send a message.

Everything runs on deterministic mock providers by default — no API keys required. Add real
keys to `.env` later (see `.env.example`) to switch individual services (Gemini, OpenAI,
Google Fact Check, Google Cloud Vision, Google Translate, WhatsApp) from mock to live; no
code changes needed.

## Tests

```bash
pytest
```

## Docker

```bash
docker compose -f docker/docker-compose.yml up --build
```

Runs migrations automatically on container start, then serves on http://localhost:8000
(simulator at `/simulator`). Data persists in the `satyascan_data` named volume. To use real
provider keys, uncomment and fill in the relevant `environment:` entries in
`docker/docker-compose.yml` (see `.env.example` for the full list). To move off SQLite onto
Postgres + pgvector later, uncomment the `db` service in the same file and point
`DATABASE_URL` at it — the schema is already Postgres-compatible.

## Scope

Built: WhatsApp webhook (Meta Cloud API) + local simulator, 8-agent verification pipeline,
full database, privacy-first storage (no permanent message content by default).

Not built (roadmap only): browser extension, Telegram/Instagram/Facebook clients, mobile
apps, enterprise SDK, public API beyond the WhatsApp webhook, billing/business model,
speech-to-text.
