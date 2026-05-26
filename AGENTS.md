# AGENTS.md — Financial Assistant

## Project Overview

Personal finance management system that processes user messages via WhatsApp (text and voice/audio) using a multi-agent AI architecture. The system routes requests through an orchestrator agent that delegates to specialized sub-agents for expenses, income, goals, and reporting.

Built as a real-world portfolio project targeting Data Science and AI Engineering competencies.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph |
| Backend | Python 3.11+, FastAPI |
| Session State | Redis + LangGraph Checkpointer |
| Primary DB | PostgreSQL |
| LLM | Google Gemini |
| Messaging | WhatsApp (official API) |
| Visualization | Plotly (charts), Streamlit (dashboard) |
| Audio | Whisper or equivalent STT (transcription layer) |

---

## Architecture

```
WhatsApp Webhook (FastAPI)
        │
        ▼
[Audio/Voice? → STT Transcription]
        │
        ▼
  Orchestrator Agent   ←── Redis session state + LangGraph checkpointer
        │
   Intent routing
   ┌────┼────┬────┐
   ▼    ▼    ▼    ▼
Query Report Expenses Incomes
 Agent  Agent  Agent   Agent
        │
        ▼
    PostgreSQL
```

### Agent Roles

- **Orchestrator**: The sole user-facing component. Routes intent to sub-agents. Never writes directly to DB.
- **Query Agent**: Reads and answers questions about financial data.
- **Report Agent**: Generates summaries, charts (Plotly), and period-based reports.
- **Expenses Agent**: Handles expense creation and categorization. Always collects full structured data before any write.
- **Incomes Agent**: Handles income registration (projected and historical).

### Critical Architectural Rules

1. **Sub-agents are tools, not conversation partners.** They are invoked by the Orchestrator and return structured results. They never interact directly with the user.
2. **One question at a time.** The Orchestrator follows a single-question interaction pattern per turn — never ask multiple things at once.
3. **Collect before writing.** No sub-agent executes a DB write until all required fields are confirmed by the user.
4. **Stateful by design.** Session state (Redis) and conversation history (LangGraph checkpointer) must persist across turns. Never treat conversation as stateless.

---

## WhatsApp Output Constraints

These rules are non-negotiable for any text returned to the user:

- **Plain text only.** No Markdown: no `**bold**`, no `_italic_`, no headers, no bullet symbols, no code blocks.
- Structured data must be presented as simple numbered lists or inline text.
- Keep responses concise. WhatsApp is a messaging interface, not a dashboard.
- Emojis are acceptable and encouraged for UX clarity.

---

## Data Model (Conceptual)

### Expenses
- `id`, `amount`, `category`, `description`, `date`, `type` (fixed | variable), `user_id`

### Income
- `id`, `source`, `amount`, `date`, `type` (projected | actual), `user_id`

### Savings Goals
- `id`, `name`, `target_amount`, `current_amount`, `deadline`, `user_id`

---

## Project Structure

```
financial-assistant-chat/
├── AGENTS.md
├── README.md
├── .env.example
├── requirements.txt
├── main.py                        # FastAPI app entrypoint
│
├── api/
│   └── whatsapp/
│       ├── router.py              # Webhook routes & handlers
│       └── dependencies.py        # FastAPI dependencies (auth, validation)
│
├── core/
│   ├── graph/
│   │   ├── builder.py             # LangGraph graph compilation & config
│   │   ├── state.py               # Shared graph state (TypedDict)
│   │   └── nodes/
│   │       ├── orchestrator.py    # Orchestrator node — intent routing
│   │       ├── expense_node.py
│   │       ├── income_node.py
│   │       └── report_node.py
│   │
│   ├── tools/                     # Shared tool layer — used by all nodes
│   │   ├── db_tool.py             # All PostgreSQL operations (read/write)
│   │   └── chart_tool.py          # Plotly chart generation
│   │
│   ├── memory/
│   │   ├── redis_state.py         # Session state manager (WhatsApp thread)
│   │   └── checkpointer.py        # LangGraph checkpointer config
│   │
│   └── models/
│       └── schemas.py             # Pydantic models for all data entities
│
├── db/
│   ├── connection.py              # Async DB connection (SQLAlchemy / asyncpg)
│   └── migrations/                # Alembic migrations
│
├── services/
│   ├── whatsapp.py                # WhatsApp API client (send messages, media)
│   └── transcription.py           # STT pipeline: WhatsApp audio URL → text
│
└── tests/
    ├── test_nodes.py
    ├── test_tools.py
    └── test_webhook.py
```

> ⚠️ `core/tools/` is a shared layer. Nodes invoke tools — they never contain raw SQL or direct DB calls. Tools must not be placed inside `nodes/`.

---

## Dev Environment Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# Fill in: DATABASE_URL, REDIS_URL, GEMINI_API_KEY, WHATSAPP_TOKEN, etc.

# Run database migrations
alembic upgrade head

# Start Redis (local dev)
docker run -d -p 6379:6379 redis:alpine

# Start FastAPI server
uvicorn main:app --reload --port 8000
```

---

## Running Tests

```bash
# All tests
pytest tests/

# Specific module
pytest tests/test_agents.py -v

# With coverage
pytest --cov=agents --cov=tools tests/
```

All tests must pass before merging any branch.

---

## Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `GEMINI_API_KEY` | Google Gemini API key |
| `WHATSAPP_TOKEN` | WhatsApp API bearer token |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verification token |
| `STT_MODEL` | Speech-to-text model identifier |
| `ENV` | `development` \| `production` |

> 🔒 Never commit `.env` files. Never hardcode secrets anywhere in the codebase.

---

## Coding Conventions

- Python type hints are mandatory in all function signatures.
- Use `Pydantic` models for all data flowing between agents and tools.
- Agent system prompts live in `agents/<agent_name>.py` as module-level constants, not inline strings.
- All DB operations are async (`asyncpg` or `SQLAlchemy async`).
- Log agent decisions and tool calls using structured logging (`structlog` or `logging` with JSON format).
- Commit messages follow Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`.

---

## Known Gotchas

- **LangGraph checkpointer config**: Must be initialized with the correct `thread_id` per WhatsApp session, not per message. The `thread_id` is the WhatsApp sender phone number.
- **WhatsApp audio messages**: Arrive as an audio URL + media_id. Must be downloaded, then passed to the STT pipeline before reaching the Orchestrator. This is handled in `audio/transcription.py` before any agent is invoked.
- **Sub-agent tool descriptions**: Tool descriptions in the Orchestrator's tool registry must be specific and unambiguous. Vague descriptions cause mis-routing (learned from N8N prototype).
- **No Markdown in responses**: LLM responses must be post-processed to strip any Markdown formatting before sending to WhatsApp.
- **PostgreSQL only**: Excel/OneDrive was the previous data store and introduced date serial errors and column misalignment. Do not reintroduce file-based storage for any financial data.

---

## Open Items (Pending Implementation)

- [ ] Voice/audio handling pipeline (`audio/transcription.py`) — architecture defined, not yet built
- [ ] Streamlit dashboard (`dashboard/app.py`) — planned for V2
- [ ] Full test suite for all agents and tools
- [ ] Deployment pipeline (Docker + cloud target TBD)