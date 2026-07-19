# tasko

Personal AI assistant for job search workflows: profile setup, vacancy search, matching, document generation, application tracking, and future auto-apply automation.

## Database migrations

The API applies all pending Alembic migrations before it starts accepting
requests. A migration or database connection failure aborts startup.

Run migrations manually from the repository root with:

```bash
cd apps/api
alembic upgrade head
```

```bash
cd apps/api
alembic stamp 20260718_0001
alembic upgrade head
```

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

Docker Compose keeps OpenClaw's mutable SQLite plugin state in the dedicated
`openclaw-tasko-state` volume. On its first start, the API seeds that volume
from the host OpenClaw state and rebuilds the plugin-state index. This avoids
sharing a WAL database between macOS and the Linux container while preserving
the host configuration, Codex plugin registration, and provider credentials.

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
`GET /documents/{id}/download` returns the stored rendered `.docx` for the
current or a selected historical version. If that rendered artifact is no
longer available, the API returns `410 Gone`; it never reconstructs a DOCX from
the stored generation payload.

### Document storage and AI disclosure

DOCX templates are deduplicated per document type by the SHA-256 digest of the
uploaded bytes. Before storage, Tasko rejects unsafe ZIP paths, encrypted or
symlinked entries, malformed XML, DTDs/entities, and packages that exceed the
entry-count, uncompressed-size, XML-size, or XML-element limits.

Source templates and generated files have independent retention. Deleting a
source template removes its original bytes and extracted text but keeps any
already-generated DOCX files downloadable. Deleting a document removes all of
its versions, attachments, validation/provenance records, and generated DOCX
files. Neither source templates nor generated documents expire automatically.

Before the first document-generation request, the application identifies the
data sent through OpenClaw to the configured AI provider and requires explicit
acknowledgement. Provider-side processing and retention remain governed by the
provider configured for the deployment.

OpenClaw can propose a small allowlist of Tasko actions: application notes and
next steps, interview events, documents, and individual profile fields. These
proposals are stored with the assistant message and rendered as previews. No
mutation runs during generation; FastAPI executes an idempotent action only
after the user clicks Apply.
