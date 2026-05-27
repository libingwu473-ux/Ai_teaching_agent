# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

AI 教学助手 (AI Teaching Assistant) — a Dify-based conversational learning platform with automated student scoring. Students chat with a Dify-hosted LLM workflow; the backend logs conversations, tracks stage progression, and scores student performance for teacher review.

Two top-level subprojects: [backend/](backend/) (Django REST API) and [frontend/](frontend/) (Vue 3 SPA). They are developed and run separately.

Specs live in [技术规范文档.md](技术规范文档.md) and [可行性报告.md](可行性报告.md) (both in Chinese — the UI is also Chinese, `LANGUAGE_CODE = 'zh-hans'`).

## Common commands

### Backend (run from [backend/](backend/))

```bash
pip install -r requirements.txt              # install deps (no venv config — create your own)
python manage.py migrate                     # apply migrations
python manage.py seed_workflow               # create the default 3-stage workflow + a default teacher (admin123)
python manage.py createsuperuser             # create an admin
python manage.py runserver                   # serve on http://127.0.0.1:8000
python manage.py sync_dify_logs              # pull all active users' conversation history from Dify
python manage.py sync_dify_logs --user-id 5  # pull for a single user
```

Tests: none present yet — `manage.py test` would discover them once added under `apps/*/tests.py`.

### Frontend (run from [frontend/](frontend/))

```bash
npm install
npm run dev        # vite dev server on :5173, proxies /api → 127.0.0.1:8000
npm run build      # production build to dist/
npm run preview    # preview the build
```

Both servers must run together for normal development. Vite proxies `/api/*` to Django, **except** the SSE chat stream — see "SSE quirk" below.

## Gotchas (read before editing the chat path)

- **SSE bypasses the Vite proxy.** Vite buffers proxied responses, which kills streaming. `getChatURL()` returns the absolute Django URL so the browser connects to `http://127.0.0.1:8000/api/chat/send/` directly. CORS on Django is set up for `localhost:5173`. See "SSE quirk" below.
- **The chat send endpoint is not a DRF view** — it's `@csrf_exempt` with manual JWT auth and returns `StreamingHttpResponse`. DRF rejects `Accept: text/event-stream` with HTTP 406, so don't convert it to `@api_view`. See [dify_integration/views.py:21](backend/apps/dify_integration/views.py#L21).
- **Scoring is silently zero without `stage_key`.** `ChatLog.stage_key` is populated from Dify's `current_stage` output (live via SSE events, or via sync). If the Dify workflow doesn't emit it, every dimension of the score is zero — no error, no warning. See "Stage tracking contract" below.

## Architecture

### High-level data flow

```
Student (Vue)  ──SSE──▶  Django /api/chat/send/  ──HTTP stream──▶  Dify API
                              │                                       │
                              ▼                                       │
                       ConversationSession + ChatLog   ◀──periodic────┘
                              │                          sync (sync_dify_logs)
                              ▼
                       ScoringEngine ──▶ StudentScore + ScoreDetail
                              │
                              ▼
                       Teacher dashboard (Vue)
```

### Backend layout ([backend/](backend/))

Django 4.2 + DRF + SimpleJWT, SQLite by default. Four apps under [backend/apps/](backend/apps/), all settings in [backend/config/settings.py](backend/config/settings.py).

- **[apps/users/](backend/apps/users/)** — custom `User` model with `role ∈ {student, teacher, admin}` ([users/models.py](backend/apps/users/models.py)). JWT auth at `/api/auth/{register,login,profile}/`. A `post_save` signal in [users/signals.py](backend/apps/users/signals.py) auto-creates a `DifyUserMapping` (random `dify_edu_<uuid>` ID) for every new user — this ID is what gets sent to Dify as the `user` field.

- **[apps/dify_integration/](backend/apps/dify_integration/)** — Dify API wrapper plus workflow/stage definitions.
  - [services/dify_client.py](backend/apps/dify_integration/services/dify_client.py): thin httpx client for Dify's chat/conversations/messages/files endpoints. **SSL verification is off by default** (`VERIFY_SSL=False`) to dodge intermittent Windows SSL errors — change cautiously.
  - [services/chat_service.py](backend/apps/dify_integration/services/chat_service.py): `DifyChatService.stream_chat_message()` consumes Dify's SSE stream, re-emits events to the frontend, detects stage transitions from `node_finished`/`workflow_finished` events (looks for `outputs.current_stage`), and persists the full exchange as `ConversationSession` + `ChatLog` on stream end.
  - [sync_service.py](backend/apps/dify_integration/sync_service.py): pulls historical conversations from Dify into the local DB. Triggered manually via `/api/chat/sync/` (teacher/admin only) or the `sync_dify_logs` command. No scheduler is wired up — `SYNC_CONFIG['INTERVAL_MINUTES']` exists but is unused.
  - [models.py](backend/apps/dify_integration/models.py): `DifyUserMapping`, `LearningWorkflow`, `WorkflowStage`. A workflow is an ordered list of stages with `stage_key`, `expected_min_messages`, `expected_min_minutes`, and `weight`.

- **[apps/chat_logs/](backend/apps/chat_logs/)** — `ConversationSession` (one per Dify conversation) and `ChatLog` (one per Q&A turn). `stage_key` on each log is what the scorer keys off.

- **[apps/scoring/](backend/apps/scoring/)** — automatic scoring + teacher review.
  - [scoring_engine.py](backend/apps/scoring/scoring_engine.py): four weighted dimensions (defaults in `SCORING_CONFIG`): stage completion 40%, sequence adherence 25%, time investment 15%, engagement 20%. `make_score_details()` produces per-stage breakdowns.
  - `StudentScore.status` flows `pending_review → reviewed → finalized`; teachers add `teacher_score` + `teacher_comment` via PUT `/api/teacher/scores/<id>/`.

URL roots (see [config/urls.py](backend/config/urls.py)):
- `/api/auth/` → users
- `/api/chat/` → dify_integration (student chat + sync trigger)
- `/api/logs/` → chat_logs
- `/api/teacher/` → scoring (teacher-only, role checked in each view)

### Frontend layout ([frontend/src/](frontend/src/))

Vue 3 + Vite + Pinia + vue-router 4. No TypeScript. No linter configured.

- [api/client.js](frontend/src/api/client.js) — axios instance with JWT injection and a 401 → `/login` interceptor.
- [api/chat.js](frontend/src/api/chat.js) — REST helpers, plus `getChatURL()` returning the **absolute** Django URL for SSE.
- [router/index.js](frontend/src/router/index.js) — auth guard reads `localStorage.access_token`; role guard restricts `meta.role: 'teacher'` routes to teacher/admin.
- [stores/](frontend/src/stores/) — `user`, `chat` (Pinia).
- [views/](frontend/src/views/) — `Login`, `Register`, `MainLayout`, `ChatView` (student), `teacher/{Dashboard,StudentDetail,ScoreReview}`. `views/admin/` exists but is empty (placeholder for future admin UI).
- [components/chat/](frontend/src/components/chat/) — `DifyChat.vue` (main chat UI, uses `@microsoft/fetch-event-source` to consume the SSE stream), `MessageBubble.vue`, `FileUploader.vue`, `StageProgress.vue`.

### SSE quirk (important)

The Vite dev proxy buffers responses, which breaks live streaming. `getChatURL()` therefore hits Django **directly** at `http://127.0.0.1:8000/api/chat/send/`, bypassing the proxy. Django CORS is configured to allow `localhost:5173` with credentials.

The chat endpoint ([dify_integration/views.py:21](backend/apps/dify_integration/views.py#L21)) is **not** a DRF view — it's a plain `@csrf_exempt` function that does manual JWT auth and returns a `StreamingHttpResponse` with `Content-Type: text/event-stream`. This is deliberate: DRF's content negotiation rejects `Accept: text/event-stream` with HTTP 406. Don't convert it to `@api_view`.

### Stage tracking contract

The scoring engine depends on `ChatLog.stage_key` being populated. Two sources fill it:
1. **Live**: `DifyChatService._collect_event()` reads `outputs.current_stage` from `node_finished`/`workflow_finished` SSE events.
2. **Sync**: `DifySyncService._sync_session_messages()` reads `msg['inputs']['current_stage']`.

If the Dify workflow doesn't output `current_stage`, all scoring will be zero. The default seeded workflow expects three stages: `stage_concept`, `stage_practice`, `stage_summary`.

## Configuration

Backend reads from [backend/.env](backend/.env) via `python-decouple`. Keys: `SECRET_KEY`, `DEBUG`, `DIFY_API_BASE_URL`, `DIFY_API_KEY`, `DIFY_APP_ID`, `DIFY_VERIFY_SSL`. The committed `.env` contains a working Dify API key for the dev instance — rotate before any non-local deployment.

Tunables live as dicts in [settings.py](backend/config/settings.py): `DIFY_CONFIG`, `SCORING_CONFIG`, `SYNC_CONFIG`.
