# Next Steps — Taking SatyaScan From Mocked to Real

The app runs completely today with zero external accounts (everything mocked). This is your
checklist for turning on real services one at a time. Add **one** key, restart the server, and
test that one integration before moving to the next — don't configure everything at once.

Every setting below goes in your `.env` file (copy `.env.example` to `.env` if you haven't).

---

## 1. LLM — Gemini (primary) and/or OpenAI (fallback)

- **Gemini**: get a key at [Google AI Studio](https://aistudio.google.com/apikey) →
  `GEMINI_API_KEY=...`
- **OpenAI** (optional fallback): get a key at
  [platform.openai.com/api-keys](https://platform.openai.com/api-keys) → `OPENAI_API_KEY=...`

With just `GEMINI_API_KEY` set, every LLM-driven agent (intent, claim extraction, reasoning,
explanation) switches from mock to real Gemini calls automatically — no code changes.

## 2. Google Fact Check Tools API (Search Agent)

1. In [Google Cloud Console](https://console.cloud.google.com), create or pick a project.
2. **APIs & Services → Library** → search "Fact Check Tools API" → Enable.
3. **APIs & Services → Credentials** → Create Credentials → API key. Restrict it to the Fact
   Check Tools API.
4. `.env`: `GOOGLE_FACT_CHECK_API_KEY=...`

## 3. Google Cloud Vision (Image Verification Agent — OCR + reverse image search)

1. In the same Cloud Console project, enable "Cloud Vision API".
2. Create an API key as above, or (more typical for Vision) create a **service account** with
   a JSON key instead — Vision's web-detection features sometimes need full credentials rather
   than a bare API key. If a plain API key errors or comes back limited, that's the fallback:
   generate a service account key, set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`, and
   flag it here so the `GoogleVisionImageSearchProvider` in `app/providers/image_search/
   google_vision.py` can be adjusted to use it instead of `client_options={"api_key": ...}`.
3. `.env`: `GOOGLE_CLOUD_VISION_API_KEY=...`

## 4. Google Cloud Translation (Malayalam explanation fallback)

1. Enable "Cloud Translation API" in the same project.
2. Reuse or create an API key.
3. `.env`: `GOOGLE_TRANSLATE_API_KEY=...`

## 5. WhatsApp — Meta Cloud API (the actual bot)

1. Create a [Meta developer account](https://developers.facebook.com) and a new App.
2. Add the **WhatsApp** product to the app. This gives you a test phone number, a temporary
   access token, and a **Phone Number ID**.
3. For a token that doesn't expire in 24 hours, create a System User (Meta Business Suite →
   Business Settings → Users → System Users) and generate a permanent token with
   `whatsapp_business_messaging` permission.
4. Find your **App Secret** under App Settings → Basic.
5. Make up your own **Verify Token** — any string you choose, used only to prove to Meta that
   webhook requests are reaching your server. It must match in two places: your `.env` and the
   Meta webhook configuration screen (step 7 below).
6. `.env`:
   ```
   WHATSAPP_ACCESS_TOKEN=...
   WHATSAPP_PHONE_NUMBER_ID=...
   WHATSAPP_VERIFY_TOKEN=your-own-chosen-string
   WHATSAPP_APP_SECRET=...
   ```
7. Meta needs a **public HTTPS URL** to send webhooks to — `localhost` won't work. For local
   testing, install [ngrok](https://ngrok.com), run `ngrok http 8000`, and register
   `https://<your-ngrok-id>.ngrok.io/webhook/whatsapp` as the webhook URL in the Meta App
   dashboard (WhatsApp → Configuration), using the Verify Token from step 5. Subscribe to the
   `messages` webhook field.
8. Send a WhatsApp message to your test number — it should hit your running server and reply
   with a verdict.

## 6. Security / production settings

- Generate a real encryption key (the app runs on a throwaway dev key otherwise, which breaks
  on every restart):
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
  → `.env`: `FIELD_ENCRYPTION_KEY=...`
- Decide `MESSAGE_RETENTION_DAYS` if you want any message excerpt retained for consenting
  users (`0` = never, matches the privacy-first default).

## 7. Docker

Docker wasn't installed on the machine this was built on, so `docker compose up --build` was
never actually run end-to-end — only checked by inspection. Install
[Docker Desktop](https://www.docker.com/products/docker-desktop/), then:
```bash
docker compose -f docker/docker-compose.yml up --build
```
Please run this yourself and report back if it fails — the Dockerfile/compose config should
work but hasn't been build-tested on a real Docker install.

## 8. Deploying for real

No specific host was chosen as part of this build. Pick one that can run the Docker image and
give you a public HTTPS URL — Railway, Render, Fly.io, a VPS, or AWS/GCP all work. Once live:
- Point the Meta webhook at your real domain instead of the ngrok tunnel.
- If you outgrow SQLite, uncomment the Postgres + pgvector service block in
  `docker/docker-compose.yml` and point `DATABASE_URL` at it — the schema (see
  `app/db/base.py`'s `GUID` type) is already Postgres-compatible, no migration rewrite needed.

## 9. Verifying real calls are actually happening

Every external call is recorded in the `api_logs` table with an `is_mock` flag. After adding a
key and sending a test message, check:
```bash
python3 -c "
import sqlite3
con = sqlite3.connect('data/satyascan.db')
for row in con.execute('select provider, endpoint, is_mock from api_logs order by created_at desc limit 10'):
    print(row)
"
```
`is_mock = 0` confirms the real provider was used, not the mock.
