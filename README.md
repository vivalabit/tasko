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
selects `openai/gpt-5.6-terra`, disables reasoning, caps answers at 1,200
tokens, and disables all external skills and tools. Tasko conversations and
memory are therefore kept separate from the personal assistant.

GPT-5.6 Terra requires OpenClaw 2026.7.1 or newer.
It runs through OpenClaw's native Codex harness while retaining the isolated
Tasko workspace, memory, token cap, and disabled tool policy.

Assistant responses use resumable SSE through `POST /assistant/chat/stream`.
Clients reconnect with the same `requestId` and last received `offset`; active
generation can be cancelled with `DELETE /assistant/chat/stream/{requestId}`.

Assistant requests have a bounded 32,000-character prompt and a 6,000-character
user-message limit. PostgreSQL keeps the complete conversation, while the model
receives a compact summary of older turns plus the latest 12 messages. Each
generation uses a fresh isolated OpenClaw session so hidden provider context
cannot grow without a bound. Temporary timeouts, rate limits, and network
failures are retried once with exponential backoff. Every run writes a
structured JSON log containing latency, model, token counts (provider-reported
when available, otherwise explicitly marked estimates), prompt size, and retry
count. Vacancy/profile/application text is passed through an untrusted-data
boundary that removes common prompt-injection instructions before generation.

The reliability budget can be adjusted with these API environment variables:

- `OPENCLAW_ASSISTANT_TIMEOUT_SECONDS`
- `OPENCLAW_ASSISTANT_MAX_ATTEMPTS`
- `OPENCLAW_ASSISTANT_RETRY_BACKOFF_SECONDS`
- `OPENCLAW_ASSISTANT_MAX_PROMPT_CHARS`
- `OPENCLAW_ASSISTANT_MAX_USER_MESSAGE_CHARS`
- `OPENCLAW_ASSISTANT_MAX_HISTORY_MESSAGES`
- `OPENCLAW_ASSISTANT_MAX_HISTORY_CHARS`

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

OpenClaw can propose a small allowlist of Tasko actions: application notes and
next steps, interview events, documents, and individual profile fields. These
proposals are stored with the assistant message and rendered as previews. No
mutation runs during generation; FastAPI executes an idempotent action only
after the user clicks Apply.
