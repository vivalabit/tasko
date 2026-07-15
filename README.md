# tasko

Personal AI assistant for job search workflows: profile setup, vacancy search, matching, document generation, application tracking, and future auto-apply automation.

## Stack

- Frontend: Next.js, TypeScript, Tailwind CSS, shadcn/ui style components
- Backend: Python FastAPI
- Data: PostgreSQL, SQLAlchemy, pgvector later
- Queues: Celery, Redis
- AI: OpenAI API, LangChain, LangGraph later
- Automation: Playwright Python
- Storage: S3-compatible storage later

## Tasko OpenClaw agent

The AI Assistant uses its own isolated `tasko-assistant` agent instead of the
personal `main` agent. Set it up once before starting the API:

```bash
pnpm openclaw:setup
```

The setup is idempotent. It creates a separate workspace and agent state,
selects `openai/gpt-5.4-mini`, disables reasoning, caps answers at 1,200
tokens, and disables all skills and tools. Tasko conversations and memory are
therefore kept separate from the personal assistant.
