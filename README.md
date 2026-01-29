# Jira Schedule Reporter

Jira 업무 조회/보고, 서버 자산 관리(감사 추적 포함), 당직 일정 관리를 위한 풀스택 애플리케이션입니다.

## 기술 스택

- **Backend:** FastAPI (Python 3.12, async), MongoDB (motor), JWT 인증
- **Frontend:** Vue 3 + TypeScript, Quasar 2, Pinia, FullCalendar
- **Deployment:** Docker Compose

## Project 구조

```
project/
├─ app/
│   ├─ main.py
│   ├─ core/
│   │    ├─ config.py
│   │    └─ security.py          # JWT, bcrypt, OAuth2
│   ├─ models/                   # Pydantic schemas
│   ├─ utils/
│   │    └─ time.py              # TimeProvider, TimeUtil (KST/UTC helpers)
│   ├─ jira/
│   │    ├─ jql_builder.py       # JqlBuilder (immutable, chainable)
│   │    └─ client.py            # JiraClient (REST/search/pagination)
│   ├─ services/                 # Business logic layer
│   ├─ routers/                  # FastAPI route handlers
│   └─ db/
│        └─ mongo.py             # MongoClientManager singleton
├─ frontend/optool/              # Vue 3 + Quasar frontend
└─ docker-compose.yml
```

## 설치 및 실행

### Backend
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend/optool
npm install
npm run dev
```

### Docker
```bash
docker-compose up
```

## API 문서

http://localhost:8000/docs