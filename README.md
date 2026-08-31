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

## 내부망 반입 전 EoS 스냅샷 갱신

서버 자산의 운영체제 및 제품 지원 종료일은 저장소의
`app/data/eos_map_snapshot.json`에 포함됩니다. 내부망 Docker 빌드와 실행 과정에서는
외부 API를 호출하지 않습니다.

GitHub Actions가 `dev` 또는 `main` 브랜치 변경 시와 매일 한 번 자동으로 최신 데이터를
확인합니다. 실제 데이터가 바뀐 경우에만 해당 브랜치에 snapshot 갱신 커밋을 추가하므로,
일반적인 반입 과정에서는 별도로 실행할 명령이 없습니다.

자동화를 기다리지 않고 즉시 갱신해야 할 때만 외부망에서 아래 명령을 실행하세요.

```bash
python app/scripts/update_eos_snapshot.py
```

명령이 성공하면 데이터가 변경된 경우 `app/data/eos_map_snapshot.json`이 교체됩니다.
이 파일을 포함한 최신 소스 전체를 내부망으로 반입한 뒤 평소와 같이 빌드하면 됩니다.

```bash
docker compose build
docker compose up -d
```

외부 API 조회가 모두 실패하면 기존 스냅샷을 덮어쓰지 않고 오류로 종료합니다.

## API 문서

http://localhost:8000/docs
