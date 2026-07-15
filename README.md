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

Assistant responses use resumable SSE through `POST /assistant/chat/stream`.
Clients reconnect with the same `requestId` and last received `offset`; active
generation can be cancelled with `DELETE /assistant/chat/stream/{requestId}`.

Assistant history is stored in PostgreSQL in normalized `conversations` and
`messages` tables. `GET /assistant/conversations` returns active conversations;
pass `archived=true` for the archive. Conversation context, title, timestamps,
messages, and the isolated OpenClaw session key are persisted across browsers.
The frontend imports the legacy `localStorage` history once, without
overwriting conversations that already exist on the server.

Assistant responses can be saved as editable cover letters or tailored
resumes. Documents, vacancy-specific variants, immutable content versions, and
application attachments are stored in PostgreSQL through `/documents`.
`GET /documents/{id}/download` produces a styled `.docx` for the current or a
selected historical version.
