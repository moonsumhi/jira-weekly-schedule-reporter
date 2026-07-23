# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jira Schedule Reporter — a full-stack app for viewing/reporting Jira tasks, managing server assets with audit trails, and scheduling watch rotations. Korean-localized UI.

## Tech Stack

- **Backend:** FastAPI (Python 3.12, async), MongoDB (motor), JWT auth (python-jose + bcrypt), httpx
- **Frontend:** Vue 3 + TypeScript, Quasar 2, Pinia, FullCalendar, Axios, vue-i18n
- **Deployment:** Docker Compose (backend:8000, frontend/nginx:9000, MongoDB 7, Mongo Express:8081)

## Common Commands

### Backend
```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend/optool
npm install
npm run dev        # Dev server with hot reload
npm run build      # Production build → dist/spa/
npm run lint       # ESLint
npm run format     # Prettier
```

### Docker
```bash
docker-compose up          # All services
docker-compose up backend  # Backend only
```

## Architecture

### Backend (app/)
- **Routers** (`app/routers/`) — FastAPI route handlers, one file per domain (auth, admin, issues, assets, watch, health)
- **Services** (`app/services/`) — Business logic layer (JiraTaskService, WatchTimetableService)
- **Models** (`app/models/`) — Pydantic schemas for request/response validation, separate Create/Replace/Patch/Out variants per entity
- **Jira** (`app/jira/`) — JiraClient (async httpx wrapper) and JqlBuilder (frozen dataclass, immutable fluent interface)
- **DB** (`app/db/mongo.py`) — MongoClientManager singleton; collections accessed via `manager.db["collection_name"]`
- **Utils** (`app/utils/`) — TimeUtil/TimeProvider (KST timezone handling), MongoDB helpers (oid, to_out)
- **Security** (`app/core/security.py`) — JWT creation/verification, bcrypt hashing, OAuth2 password flow

All handlers and DB operations are async. The app uses a lifespan context manager in `app/main.py` for startup/shutdown.

### Frontend (frontend/optool/src/)
- **Pages** — Lazy-loaded route components organized by domain (auth/, jira/, asset/, watch/)
- **Services** — API client modules wrapping Axios calls
- **Stores** — Pinia stores (auth store manages JWT token + user state)
- **Boot** — Axios interceptor auto-injects JWT; i18n setup
- **Router** — Route guards via metadata: `requiresAuth`, `guestOnly`, `requireAdmin`

Nginx serves the SPA and proxies `/api/` to the backend container.

### Auth Flow
User registers → admin approves (pending_users → users) → login returns JWT → Axios interceptor attaches token. Admin routes require `is_admin` flag.

## Configuration

Backend loads settings from `app/secret/.env` via Pydantic BaseSettings (`app/core/config.py`). Key vars: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `MONGO_URI`, `JWT_SECRET_KEY`, `APP_DB_NAME`.

## MongoDB Collections

`users`, `pending_users`, `assets_servers`, `assets_server_history`, `watch_assignments`

## 프론트엔드 빌드 규칙 (절대 준수)

**커밋 전에 반드시 프론트엔드 빌드를 실행하고, 에러가 없는 상태에서만 커밋한다.**

```bash
cd frontend/optool && npm run lint && npm run build
```

- TypeScript 타입 에러, ESLint 에러가 발생하면 반드시 수정 후 커밋한다
- 빌드 성공 확인 없이 커밋하지 않는다
- 프론트엔드 파일을 하나라도 수정했다면 예외 없이 빌드 확인을 거친다

## 커밋 규칙 (절대 준수)

**Claude는 `git commit`을 Bash tool로 직접 실행하지 않는다. 반드시 `/commit` 스킬을 사용한다.**

- 커밋이 필요한 시점이 오면 `/commit` 스킬을 호출한다
- 티켓 번호가 없으면 커밋 전에 반드시 사용자에게 먼저 물어본다
- 이전 대화의 티켓 번호를 그대로 재사용하지 않는다 — 작업마다 티켓이 다를 수 있음
- 티켓 형식: `SR-N`, `SR-YYYY-NNNN`, `BACKOFFICE-N` 등 프로젝트마다 다름
- 스킬 위치: `.claude/commands/commit.md`
