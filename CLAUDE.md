# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Snapshot

Personal finance assistant reached over WhatsApp. Users send text/voice notes; a multi-agent LangGraph pipeline (orchestrator + sub-agents for expenses, income, goals, reports) interprets intent and acts on a PostgreSQL store. See `AGENTS.md` for the full agent architecture, data model, and WhatsApp output rules — treat it as the source of truth for product behavior.

**Python ≥ 3.11, FastAPI, LangGraph, Postgres, Redis, Gemini, WhatsApp Cloud API.** Dependency management via `uv` (lockfile: `uv.lock`); do not hand-edit `pyproject.toml` to add packages.

---

## Build, Run, Test

```bash
# Install / sync deps
uv sync

# Dev server (auto-reload, port 8000)
uv run uvicorn main:app --reload --port 8000

# Local Redis
docker run -d -p 6379:6379 redis:alpine

# All tests
uv run pytest tests/

# Single test file / single test
uv run pytest tests/test_webhook.py -v
uv run pytest tests/test_webhook.py::test_name -v

# With coverage
uv run pytest --cov=. tests/
```

There is no formal linter/formatter configured in `pyproject.toml` — match the existing style (PEP 8, type hints, Google-style docstrings) when editing.

---

## Code Architecture (as it exists today)

```
main.py                        # FastAPI app factory; mounts routers; /health
core/
  config.py                    # pydantic-settings Settings — single source of env config
api/
  whatsapp/
    router.py                  # /webhook GET (challenge) + POST (inbound msgs) + /test
    dependencies.py            # FastAPI deps: verify_webhook_token, get_whatsapp_client
services/
  whatsapp.py                  # WhatsAppClient (httpx.AsyncClient) + dataclass payloads
  transcription.py             # STT pipeline stub (audio URL → text) — NOT YET BUILT
core/graph/                    # LangGraph nodes + state + builder — placeholders, not built
core/memory/                   # Redis session + LangGraph checkpointer — placeholders
core/tools/                    # Shared DB / chart tools — placeholders
core/models/                   # Pydantic schemas for all entities — placeholders
db/connection.py               # Async DB connection — placeholder
tests/                         # Empty stubs: test_nodes.py, test_tools.py, test_webhook.py
```

### What is real right now

The only fully implemented code paths are:
1. **Webhook entry** — `api/whatsapp/router.py` receives `POST /webhook`, parses the Meta payload, marks the message read, and currently **echoes the text back** (see `AGENTS.md` "Open Items": this is the connection point for the orchestrator).
2. **WhatsApp client** — `services/whatsapp.py`: `send_text`, `mark_as_read`, `subscribe_app`, `get_media_url`, `download_media`. Always uses `httpx.AsyncClient`, base URL `https://graph.facebook.com/{api_version}`, Bearer auth from `settings.whatsapp_token`.
3. **Config** — `core/config.py` is the only place that should read env vars. Import `settings` from there, never `os.getenv(...)` directly.

Everything under `core/graph/`, `core/memory/`, `core/tools/`, `core/models/`, `db/`, and the three test files is scaffold-only. New work will be filling these in per `AGENTS.md`.

### Wiring rules to respect

- `core/tools/` is a shared layer. Nodes (once built) call tools — they must not contain raw SQL or direct DB calls, and tools must not be placed inside `core/graph/nodes/`.
- Sub-agents are **tools of the orchestrator**, not conversation peers. They never see the user; the orchestrator routes and the user only ever talks to the orchestrator.
- Session state lives in Redis; conversation history in the LangGraph checkpointer. `thread_id` for the checkpointer = the WhatsApp sender phone number (per session, not per message).
- All DB and WhatsApp calls are async.
- WhatsApp-bound text responses must be **plain text only** (no Markdown — no `**`, no `_`, no headers, no bullets, no code fences). Emojis are fine. This is enforced at the response layer, not the agent layer.

### Adding a dependency

```bash
uv add <package>          # runtime
uv add --dev <package>    # dev only (tests, linters, etc.)
```

Never edit `pyproject.toml` by hand. Commit `uv.lock` alongside.

---

## Environment Setup

```bash
cp .env.example .env
# Fill in: WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_WABA_ID,
#          WHATSAPP_WEBHOOK_VERIFY_TOKEN, DATABASE_URL, REDIS_URL, GEMINI_API_KEY, STT_MODEL
```

See `AGENTS.md` "Environment Variables" for the full list and meanings. Never commit `.env`; never hardcode secrets.

---

## Reference

- **AGENTS.md** — full agent architecture, data model, WhatsApp output constraints, known gotchas, open items. Read it before touching the agent graph, DB layer, or anything user-facing on WhatsApp.
- **Postman collection** (referenced in `services/whatsapp.py` and `api/whatsapp/router.py` docstrings) — https://go.postman.co/collection/13382743-84d01ff8-4253-4720-b454-af661f36acc2 — official Meta reference for the WhatsApp Cloud API payload shapes used throughout the client and router.
