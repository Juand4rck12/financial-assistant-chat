# AGENTS.md - Financial Assistant

## Project Overview

Personal finance management system that processes user messages via WhatsApp
(text and voice/audio) using a multi-agent AI architecture. The system routes
requests through an orchestrator agent that delegates to specialized sub-agents
for expenses, income, goals, and reporting.

Built as a real-world portfolio project targeting Data Science and AI
Engineering competencies.

---

## Tech Stack

| Layer            | Technology                     |
| ---------------- | ------------------------------ |
| Orchestration    | LangGraph                      |
| Backend          | Python 3.11+, FastAPI          |
| Session State    | Redis + LangGraph Checkpointer |
| Primary DB       | PostgreSQL                     |
| LLM              | Google Gemini                  |
| Messaging        | WhatsApp (official API)        |
| Visualization    | Plotly (charts), Streamlit      |
| Audio            | Whisper or equivalent STT      |

---

## Architecture

### Agent Roles

- **Orchestrator**: Routes intent to sub-agents. Never writes directly to DB.
- **Query Agent**: Reads and answers questions about financial data.
- **Report Agent**: Generates summaries, charts (Plotly), and period-based reports.
- **Expenses Agent**: Handles expense creation and categorization.
- **Incomes Agent**: Handles income registration (projected and historical).

### Critical Rules

1. Sub-agents are tools, not conversation partners.
2. One question at a time.
3. Collect before writing.
4. Stateful by design.

---

## WhatsApp Output Constraints

- Plain text only. No Markdown.
- Structured data as simple numbered lists or inline text.
- Keep responses concise.
- Emojis encouraged for UX clarity.

---

## Coding Conventions

- Python type hints mandatory.
- Pydantic models for all data.
- Agent system prompts as module-level constants.
- All DB operations async (SQLAlchemy async).
- Structured logging (structlog).
- Conventional Commits.
