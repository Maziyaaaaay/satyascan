# SatyaScan — Project Status (session handoff)

Last updated: 2026-08-25. This file exists so a new chat session (or a
future you) can pick up without re-deriving everything below.

## Live deployment

- **Production URL**: https://satyascan-production.up.railway.app
- **Simulator**: https://satyascan-production.up.railway.app/simulator
- **Railway project**: "lucky-vision", service "satyascan"
  - On the **Trial plan** — "~19 days or $4.71 left" as of this session.
    No payment method on file. **Deployment goes offline when the trial
    runs out** unless a card is added (Railway dashboard → Settings →
    Billing → add card, then subscribe to Hobby plan, ~$5/mo). This needs
    the account owner to do it — not something Claude can do.
  - Persistent volume `satyascan-volume` mounted at `/app/data` (holds
    SQLite DB + Chroma store) — survives redeploys.
  - Auto-deploys on every push to `main` on GitHub
    (github.com/Maziyaaaaay/satyascan, private repo).
- **WhatsApp number**: +91 90748 71768, phone_number_id `1269837569544861`,
  under the "SatyaScan" WhatsApp Business Account
  (waba_id `2079943089395665`), Meta app "SatyaScan" (app_id
  `1620583282955304`). Fully verified, registered, and **live** — you can
  message it directly and it replies. WhatsApp access token is a
  **permanent System User token** (never expires) — no more 24h-expiry
  issue.

## What's working end-to-end

- Text claim verification via WhatsApp — full 8-agent pipeline, real
  providers (Gemini, Google Fact Check, Google Vision, Google Translate,
  Sightengine, C2PA manifest checking via `c2pa-python`).
- Reply is a structured WhatsApp interactive message (native quick-reply
  buttons, "🔁 Check another" / "❔ How it works") whose body text shape
  depends on `Verification.source_media_type` (see
  `app/services/report_formatting.py`): a plain text claim leads with
  "Claim:"; a photo leads with the image findings themselves (C2PA +
  AI-detection) since there's often no caption; a video splits "From the
  video frame" (visual authenticity) from "What was said" (the audio
  transcript) instead of presenting it as a generic photo; audio leads
  with "What we heard" (the transcript) so a non-technical sender can
  confirm SatyaScan understood them correctly.
- Auto language detection (English/Malayalam/Hindi/Tamil) from the
  inbound WhatsApp message — replies come back in the same language (see
  `app/models/enums.py` `Language` enum). Hindi/Tamil translations are a
  first pass, not native-reviewed.
- **Live web search** (Serper.dev) as evidence for claims with no
  existing fact-check article, or where the Fact Check API's results are
  topically-adjacent-but-irrelevant (see "Key architecture notes" below).
  This is what fixed a real bug where a recent, real event (a change of
  Chief Minister) was confidently reported as false because the
  reasoning LLM's training data predates the event.
- **Duplicate-reply protection**: WhatsApp delivers webhooks at-least-once
  and retries on a slow response (our pipeline runs several LLM calls per
  message); a `webhook_events` table (see `app/models/webhook_event.py`)
  claims each inbound message id in its own immediately-committed
  transaction before the pipeline runs, so a retry is a no-op instead of
  a duplicate reply.
- **First-ever message gets a plain welcome reply**, no verdict — a
  brand-new WhatsApp user's very first message (regardless of content)
  gets the welcome text only; real verification starts from their next
  message. See `_handle_message` in `app/routers/webhook_whatsapp.py`.
- **Video messages**: downloads the video, extracts a representative
  frame via `ffmpeg` (fed into the same AI-generation-detection + C2PA
  pipeline as a photo) and the audio track (fed into speech-to-text, same
  as a voice note) — see `app/services/video_processing.py`. Best-effort:
  if `ffmpeg` can't decode it, falls back to just the message caption
  rather than dropping the message. Confirmed live end-to-end against a
  real synthesized video (frame + speech audio track) with real
  Gemini/Sightengine/Vision keys - not just mocked tests.
- **Audio/voice-note transcription** (including video audio tracks) is
  live via `GeminiSpeechToTextProvider` (`app/providers/speech_to_text/
  gemini_stt.py`) — Gemini's native audio understanding, not OpenAI
  Whisper (see "Known gaps" below for why). Confirmed live: transcribed a
  real spoken clip ("I heard that the minister has died, is that true?")
  accurately in ~2s and ran it through the full pipeline correctly.

## Known gaps / deferred

- **OpenAI Whisper is still wired up as a speech-to-text fallback**
  (`app/providers/speech_to_text/openai_whisper.py`) **but selected only
  if `GEMINI_API_KEY` is unset** (see `get_speech_to_text_provider` in
  `app/providers/factory.py`) - Gemini is preferred specifically because
  it reuses the key already required elsewhere instead of needing
  separate OpenAI billing (the `OPENAI_API_KEY` account has an
  `insufficient_quota` issue that was never resolved - this is why Gemini
  was chosen instead, not by fixing that billing).
- **WhatsApp number is reachable by anyone but not discoverable in
  WhatsApp's own in-app search** - confirmed via the Graph API
  (`GET /{phone_number_id}?fields=search_visibility` → `NON_VISIBLE`;
  `account_mode` is `LIVE`, not the old 5-tester sandbox, so this is not
  the earlier "only testers can message it" limitation). People need the
  number/wa.me link/QR code; making it search-visible is tied to the
  Meta Business Verification below.
- **No WhatsApp Business profile picture set** - confirmed via
  `GET /{phone_number_id}/whatsapp_business_profile` (no
  `profile_picture_url` in the response). User is providing an image to
  set one via the Graph API's `whatsapp_business_profile` endpoint
  (resumable-upload → `profile_picture_handle`).
- **Full WhatsApp "production" tier not complete**: payment method for
  business-initiated messages, and Meta Business Verification, are both
  still outstanding. Currently running on the free tier (1,000
  user-initiated conversations/month), which is sufficient for testing
  and moderate real usage but not for the business proactively messaging
  users first. User explicitly deferred this earlier in the project
  ("stick with the free test number" / later migrated the personal number
  instead of doing formal business verification — no registered business
  exists to verify against).
- `SECRET_KEY` is set in Railway (real random value) — not a gap, just
  noting it's handled.

## Key architecture notes (read before touching the pipeline again)

1. **The Fact Check Tools API does keyword search, not claim matching.**
   It can return non-empty results that are topically related but
   substantively irrelevant (e.g. old fact-checks debunking a fake video
   "of CM Vijay" — these mention the subject's title only in passing, but
   get pulled in and mis-scored). Don't assume "fact_checks is non-empty"
   means "we have real evidence for this specific claim."
2. **Live search (Serper) always runs now**, not just as a fallback when
   fact_checks is empty — see `app/agents/search_agent.py`. This was a
   two-stage bug fix:
   - Stage 1: added Serper as a fallback only when `fact_checks` was
     empty. Insufficient — the Fact Check API often returns *something*
     (see point 1), so the fallback never fired.
   - Stage 2: made it unconditional, and added a stance-classification
     LLM call (`_classify_stance` in `search_agent.py`) so the live
     search result gets tagged supports/contradicts/neutral instead of
     always defaulting to neutral.
3. **Confidence scoring is a separate, deterministic formula**
   (`app/agents/confidence_scoring.py`), not an LLM call. It does a raw
   stance-count ratio, which means a single correct, on-topic piece of
   evidence can get mathematically drowned out by many irrelevant
   "contradicts"-tagged items even when the reasoning LLM correctly
   ignores that noise for the verdict itself. Fixed with
   `RankedEvidence.is_live_search` + `LIVE_SEARCH_CONFIRMED_FLOOR`: a
   live-search confirmation matching the verdict direction sets a
   confidence floor (0.85) regardless of how much older/tangential
   evidence exists.
4. **Gemini's own "Google Search grounding" tool is NOT reliable** for
   current events — tested live, it called a real, months-old event
   "speculative or fictional." Don't use `LLMProvider`-level grounding for
   this; use the independent `WebSearchProvider` (Serper) instead. (This
   capability was added, tested, found wanting, and removed from
   `GeminiProvider` in the same session — if you see references to
   `search_grounded` in old commits, that's why it's gone now.)
5. **`mark_as_read` in `meta_cloud_api.py` is now best-effort** (wrapped
   in try/except) — it used to be able to silently kill the entire reply
   if it failed for any reason (e.g. Meta's own webhook test payloads use
   fake message IDs that 400).

## Environment variables reference

All real values live in Railway's Variables tab (18 vars) and locally in
`.env` (gitignored). Notable ones added this session: `SERPER_API_KEY`,
`SECRET_KEY`, `WHATSAPP_ACCESS_TOKEN` (permanent token, replaced the old
24h one), `WHATSAPP_PHONE_NUMBER_ID` (real number, not the old test
number `1306817919170611`).

## How to test

- **WhatsApp**: message +91 90748 71768 directly.
- **Simulator**: `curl -X POST https://satyascan-production.up.railway.app/simulator/message -H "Content-Type: application/json" -d '{"session_id": "test-1", "text": "your claim here"}'`
- **Local pipeline test against real providers** (bypasses WhatsApp/
  Railway entirely, useful for fast iteration on agent/prompt changes, or
  for reproducing a bug seen in production): `build_providers()` +
  `reset_providers_for_tests()` + call `_handle_message(msg, db, providers)`
  directly (see `app/routers/webhook_whatsapp.py`) - **always overwrite
  `providers.whatsapp` with a fresh `MockWhatsAppClient()` first** unless
  you genuinely intend to send a real WhatsApp message, since
  `build_providers()` picks the real Meta client whenever
  `WHATSAPP_ACCESS_TOKEN`/`WHATSAPP_PHONE_NUMBER_ID` are set (as they are
  in this repo's `.env`) - confirmed the hard way: an early version of this
  pattern without the mock override sent two real (rejected, 400) API
  calls to a fake test number.
  Note: this repo's local dev venv is Python 3.9, which can't import
  `c2pa-python` (needs 3.10+) - use `uv python install 3.11` +
  `uv venv --python 3.11 /tmp/some-venv` + `uv pip install ".[real,dev]"`
  to reproduce anything C2PA-related against a real environment.
- **Full test suite**: `pytest` from repo root (129 tests, all mock-based,
  no external accounts needed, runs in ~2s).
