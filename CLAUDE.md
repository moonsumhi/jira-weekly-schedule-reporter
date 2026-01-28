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
