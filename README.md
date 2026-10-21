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

### 기관의 EoS/EoL 정의 (2026-10-21)

- EoS는 **End of Service**이며, 명시된 제조사/프로젝트가 제공하는 해당 제품·버전의 서비스 종료일입니다. 기관이 체결한 별도 유지보수 계약의 만료일이 아닙니다. 커뮤니티 제품은 공식 프로젝트 지원 범위를 표시합니다.
- EoL은 제조사가 명시한 제품·버전 수명 종료일만 사용합니다. 발표일, 판매 종료일, 일반 지원 종료일로 추정하지 않습니다.
- `dateKind=service_end`/`life_end`로 검증된 날짜만 각 판정에 사용합니다. 원래 중간 지원 단계의 날짜·출처는 `milestone`에 보관하며 화면의 지원 근거에서 확인할 수 있습니다.
- Oracle의 Sustaining Support, VMware 계약별 Technical Guidance, Ubuntu ESM/Legacy, RHEL 연장 서비스처럼 후속 서비스 범위가 불명확하면 서비스 종료일을 단정하지 않습니다. 미확정은 지원 중 또는 무기한 패치 제공을 뜻하지 않습니다.
- Windows ESU는 일반 기술지원 연장과 다르므로 ESU 날짜로 서비스 종료일을 일괄 연장하지 않습니다.
- 저장 자산 교정 도구는 EoS/EoL 각각의 과거 자동 입력값(`legacyDates`)을 비교합니다. 수동 날짜는 검토 대상으로 남기며, 변경 전 백업과 동시 수정 검사를 수행합니다. 먼저 dry-run으로 범위를 확인합니다.

### Cisco APIC / ACI 수명주기

- APIC M1~M4/L1~L4의 본체·SERVER·CLUSTER PID, SE-NODE-G2/SE-CL-L3, ND-NODE-L4/ND-CLUSTER-L4를 개별 PID로 판정합니다. SSD 등 비슷한 모델명에는 날짜를 상속하지 않습니다.
- 하드웨어 EoS는 공식 공지의 Last Date of Support입니다. 판매·유지보수·보안 지원 종료일은 별도 단계로 보관하며, EoL은 발표일이나 판매 종료일로 대체하지 않습니다.
- 자산의 `Cisco 소프트웨어`, `Cisco 소프트웨어 버전` 필드로 설치 소프트웨어를 하드웨어와 별도로 관리합니다. APIC 4.2/5.2/5.3, ACI Switch 14.2/15.2/15.3을 지원하며 `5.2(8g)` 등은 해당 릴리스로 판정합니다. 미확인 릴리스에는 다른 버전의 날짜를 적용하지 않습니다.
- 추가 항목과 공식 출처: `reports/cisco-apic-additions-2026-10-21.csv`.

### 내부망용 EoS / EoL 근거 PDF

- 자산 목록·등록·수정·상세의 EoS/EoL 정보 아이콘에서 근거 설명과 로컬 PDF를 확인합니다. VMware EoTG도 기존 로컬 PDF를 사용합니다. 외부 사이트로 자동 이동하지 않습니다.
- `frontend/optool/public/reference/lifecycle/`에는 공식 PDF 원본과 공식 웹 자료의 본문·표를 PDF로 보관한 파일이 있습니다. `src/data/lifecycle_references.json`은 기존 출처 URL과 PDF 경로, 실제 보관 출처, 보관 시각, SHA-256을 연결합니다. 종료일 원본 데이터는 수정하지 않습니다.
- 2026-10-21 기준 118개 출처 중 117개를 연결했습니다. SAP HANA 1.0 공지는 제조사 접근 제한으로 원문 PDF 미확보 상태를 명시했습니다. Broadcom 로그인형 수명주기 표는 공개된 조회 안내, 이전 Cisco N9504 지원 페이지와 Fujitsu 데이터시트는 현재 공식 자료를 보관하고 대체 사유를 표시합니다. 이 안내 자료로 제품별 종료일을 확정하지 않습니다.
- 프론트 빌드는 `public/reference` 전체를 배포 이미지에 포함합니다. 인터넷 연결 없이 열람할 수 있으며, 자동 EoS 후보 갱신 작업은 PDF와 매핑을 수정하지 않습니다.
- 근거를 추가·교체할 때 공식 원문 확인 후 PDF와 매핑을 함께 갱신합니다. 웹 보관본에는 출처·보관일을 표시하고 로그인/차단/오류 페이지를 PDF로 등록하지 않습니다. 미확보 항목은 사유와 확인일을 명시합니다. `npm run check:lifecycle`이 출처별 등록 여부, 로컬 PDF 경로, 파일 형식과 SHA-256을 검증합니다.
