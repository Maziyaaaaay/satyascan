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
  Sightengine).
- Reply format: `Verdict: TRUE/FALSE/LIKELY TRUE/LIKELY FALSE/MISLEADING/
  UNVERIFIABLE/SATIRE`, `Confidence: XX/100`, `Summary:` — not raw LLM
  prose. Image messages also get an `Image check:` line (AI-generated vs
  real photo).
- Auto language detection (English/Malayalam) from the inbound WhatsApp
  message — replies come back in the same language. (Only en/ml
  supported — see `app/models/enums.py` `Language` enum.)
- **Live web search** (Serper.dev) as evidence for claims with no
  existing fact-check article, or where the Fact Check API's results are
  topically-adjacent-but-irrelevant (see "Key architecture notes" below).
  This is what fixed a real bug where a recent, real event (a change of
  Chief Minister) was confidently reported as false because the
  reasoning LLM's training data predates the event.

## Known gaps / deferred

- **Audio/voice-note transcription is built but non-functional.** Code is
  deployed (OpenAI Whisper integration, `app/providers/speech_to_text/`),
  but the `OPENAI_API_KEY` has an `insufficient_quota` billing issue —
  confirmed live, not fixed. Voice notes currently fall through with "no
  claim found" until OpenAI billing is set up (Google AI Studio-style: add
  a payment method at platform.openai.com/settings/organization/billing).
  User explicitly deferred this ("not now") as of this session.
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
- **Local pipeline test** (bypasses WhatsApp/Railway entirely, useful for
  fast iteration on agent/prompt changes): see the inline Python snippets
  used throughout this session — `build_providers()` +
  `reset_providers_for_tests()` + `run_pipeline(PipelineState(...), providers)`.
- **Full test suite**: `pytest` from repo root (91 tests, all mock-based,
  no external accounts needed, runs in ~1.5s).
