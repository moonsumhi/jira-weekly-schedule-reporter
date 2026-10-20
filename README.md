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

EoS 확정 날짜의 원본은 `app/data/lifecycle_audit.json`입니다. 모델·버전별 제조사
출처와 지원 기준을 확인한 항목만 사용하며, 미확인 항목은 `근거 확인 필요`로 표시합니다.
외부 수집값은 이 검증 결과를 덮어쓰지 않습니다. 제조사 공지를 재검토해 날짜를 변경할 때는
이 파일과 `frontend/optool/src/data/lifecycle_audit.json`을 함께 수정해야 합니다.
`npm run check:lifecycle`이 두 파일의 일치를 검사합니다.

이미 저장된 과거 자동 입력값은 아래 명령으로 점검합니다. 기본 동작은 조회만 하며,
`--apply`를 붙이면 `asset_lifecycle_audit` 컬렉션에 이전 값을 보관한 뒤 교정합니다.
기존 자동 입력값과 다른 수동 값은 변경하지 않으며, 동시 수정된 자산도 덮어쓰지 않습니다.

```bash
docker compose exec backend python -m app.scripts.audit_asset_eos
docker compose exec backend python -m app.scripts.audit_asset_eos --apply
```

GitHub Actions는 `dev`/`main` 변경 시와 매일 03:17 KST에 외부 후보를 수집하여
`lifecycle-candidates-브랜치명` 아티팩트로 남깁니다. 저장소 쓰기 권한, 자동 커밋 및 푸시를
제거했습니다. 후보 보고서는 공식 제조사 자료를 대조하기 위한 참고 자료이며 배포 데이터가 아닙니다.
이 보호는 변경된 워크플로가 해당 원격 브랜치에 반영된 이후 적용됩니다.

```bash
python app/scripts/update_eos_snapshot.py --candidate-report /tmp/lifecycle-candidates.json
```

검토한 원본을 수정한 뒤 아래 명령으로 배포 스냅샷을 생성합니다. 외부 후보는 검증 원본의
날짜나 VMware Technical Guidance를 덮어쓸 수 없습니다.

```bash
python app/scripts/update_eos_snapshot.py --render-reviewed
cd frontend/optool
npm run check:lifecycle
```

최신 소스를 내부망으로 반입한 뒤 평소와 같이 `docker compose build` 및
`docker compose up -d`를 실행합니다. 외부 API가 전부 실패하면 갱신 명령은 기존 파일을 유지하고 실패합니다.

## API 문서

http://localhost:8000/docs
