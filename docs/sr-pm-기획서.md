# SR / PM 기능 원페이지 기획서

> 작성일: 2026-07-01 | 대상 시스템: OPTOOL (데이터운영팀 내부 운영 도구)

---

## 1. 개요

| 구분 | SR (Service Request) | PM (Project Management) |
|------|----------------------|-------------------------|
| 목적 | 내·외부 요청자의 업무 요청을 접수·검토·처리하는 티켓 관리 | 프로젝트 단위 업무를 이슈로 분해하고 스프린트·칸반으로 추적 |
| 주요 사용자 | 데이터활용팀 등 요청 부서 + 데이터운영팀 처리 담당자 | 데이터운영팀 내부 개발/운영 인력 |
| 연계 | SR 담당자 배정 시 → PM 이슈 자동 생성 | SR에서 변환된 이슈 추적 (`linked_sr_id`) |

---

## 2. SR 기능

### 2-1. 상태 흐름

```
DRAFT(임시저장)
    └─▶ SUBMITTED(접수)
            └─▶ REVIEWING(검토 중)
                   ├─▶ PENDING_INFO(추가 확인 요청) ──▶ [요청자 보완] ──▶ SUBMITTED
                   ├─▶ REJECTED(반려) ─────────────────────────────────── 종료
                   ├─▶ ON_HOLD(보류)
                   └─▶ APPROVED(승인)
                               └─▶ ASSIGNED(담당자 배정)
                                           └─▶ IN_PROGRESS(처리 중)
                                                       └─▶ COMPLETED(처리 완료)
                                                                   └─▶ CONFIRMING(요청자 확인)
                                                                               └─▶ CLOSED(완료)

* CANCELLED: 요청자가 CLOSED / CANCELLED / REJECTED 이전 언제든 취소 가능
```

### 2-2. 권한 체계

| 역할 | 접근 범위 | 주요 액션 |
|------|----------|----------|
| `sr_requester` | 내 SR | 접수·임시저장·취소, 추가확인 요청 시 수정, 처리결과 확인(CONFIRMING) |
| `sr_operator` | 배정된 SR | 상태 변경(IN_PROGRESS→COMPLETED), 처리결과 입력, 배포일 기록 |
| `sr_manager` | 전체 SR | 검토(승인/반려/보류/추가확인), 담당자 배정, 통계·Excel 내보내기 |
| `is_admin` | 전체 | SR 기본 연결 프로젝트 설정 포함 |

### 2-3. 접수 폼 (4단계 스텝)

| 단계 | 내용 |
|------|------|
| Step 1 — 유형 선택 | IMPROVEMENT · BUG_FIX · DATA_REQUEST · PERMISSION · CONFIG_CHANGE · SERVER_INFRA · SECURITY · ETC |
| Step 2 — 기본 정보 | 제목, 요청 부서, 대상 시스템, 요청 배경(선택), 희망 완료일, 중요도(CRITICAL/HIGH/MEDIUM/LOW), 긴급 여부 |
| Step 3 — 유형별 상세 | 유형에 따라 동적 필드 렌더링 (textarea · select · date · checkbox 등), `type_detail` JSON 저장 |
| Step 4 — 최종 확인 | 첨부파일, 처리 완료 기준, 검토자 지정(선택), 임시저장 or 제출 |

### 2-4. 담당자 배정 입력 항목

계획 시작일 · 계획 완료일 · 예상 공수(h) · 배포 필요 여부 · 보안 검토 필요 여부

담당자 후보: **데이터운영팀** 소속 사용자만 선택 가능

### 2-5. 관리 화면 통계

전체 / 접수 / 검토중 / 처리중 / 처리완료 / **지연** / **긴급** 건수 카드  
+ 유형별 · 부서별 · 담당자별 집계, 평균 처리일, 기한 준수율

---

## 3. PM 기능

### 3-1. 데이터 계층

```
조직 (Organization)
  └─ 프로젝트 (Project)  [키: 영문 대문자 2~10자, 예: PROJ]
       ├─ 이슈 (Issue)
       │    ├─ EPIC  ←  STORY / TASK / BUG / SUB_TASK 포함
       │    └─ SUB_TASK  [parent_issue_id 참조]
       ├─ 스프린트 (Sprint)  [PLANNED → ACTIVE → COMPLETED]
       ├─ 레이블 (Label)
       └─ 멤버 (ProjectMember)  [ADMIN / PROJECT_MANAGER / DEVELOPER / VIEWER]
```

### 3-2. 이슈 속성

| 항목 | 값 |
|------|----|
| 타입 | EPIC · STORY · TASK · BUG · SUB_TASK |
| 상태 | BACKLOG → TODO → IN_PROGRESS → IN_REVIEW → DONE |
| 우선순위 | LOWEST · LOW · MEDIUM · HIGH · HIGHEST |
| 주요 필드 | 제목, 설명(리치텍스트), 담당자, 스프린트, 에픽, 레이블, 시작일·마감일, 스토리포인트, 첨부파일 |
| SR 연계 | `linked_sr_id` — SR에서 자동 생성된 이슈 추적 |

### 3-3. 화면 목록

| 화면 | 경로 | 주요 기능 |
|------|------|----------|
| 대시보드 | /pm/dashboard | 내가 담당한 이슈 · 내가 보고한 이슈, 상태·우선순위 필터 |
| 업무 현황 | /pm/work-status | 전체 이슈 통계·현황 |
| 프로젝트 목록 | /pm/projects | 조직별 프로젝트 카드 뷰 |
| 프로젝트 상세 | /pm/projects/:id | 개요·멤버·설정 탭, 보드·백로그·스프린트 링크 |
| 칸반 보드 | /pm/projects/:id/board | 상태 컬럼별 드래그 앤 드롭 |
| 백로그 | /pm/projects/:id/backlog | 스프린트별 이슈 + 미할당 백로그, 담당자·에픽 필터 |
| 스프린트 관리 | /pm/projects/:id/sprints | 스프린트 생성·ACTIVE 전환·완료 |
| 조직 목록 | /pm/organizations | 조직 카드 목록 |
| 조직 상세 | /pm/organizations/:id | 소속 프로젝트 + 멤버(ADMIN/MEMBER) 관리 |
| 주간 보고 | /pm/weekly-report | 관리자 전용 |
| 월간 보고 | /pm/monthly-report | 관리자 전용 |

### 3-4. 역할 체계

| 레벨 | 역할 | 주요 권한 |
|------|------|----------|
| 조직 | ADMIN | 조직 내 모든 프로젝트·멤버 관리 |
| 조직 | MEMBER | 소속 프로젝트 접근 |
| 프로젝트 | ADMIN | 프로젝트 설정·삭제, 멤버 관리 |
| 프로젝트 | PROJECT_MANAGER | 스프린트 생성·종료, 이슈 전체 관리 |
| 프로젝트 | DEVELOPER | 이슈 작성·수정·상태 변경 |
| 프로젝트 | VIEWER | 읽기 전용 |

---

## 4. SR ↔ PM 연계 흐름

```
SR 접수 (sr_requester)
    ↓ 검토·승인 (sr_manager)
    ↓ 담당자 배정 (sr_manager)  ──▶  PM 이슈 자동 생성 (SR 기본 프로젝트)
    ↓ 처리 (sr_operator)             이슈 상태 변경: TODO → IN_PROGRESS → DONE
    ↓ 처리 완료 보고
    ↓ 요청자 확인 (CONFIRMING)
    ↓ CLOSED
```

- SR 관리 화면 > 프로젝트 설정에서 `is_sr_default` 프로젝트 지정
- 이슈 생성 시 `linked_sr_id` 기록 → SR 상세에서 연결된 이슈 조회 가능

---

## 5. 메뉴 접근 권한 요약

| 메뉴 | 필요 권한 | 비고 |
|------|----------|------|
| SR 접수 · 내 SR 목록 | `sr` + `sr_requester` | 외부 팀도 접근 가능 |
| SR 관리 (전체 목록) | `sr` + `sr_manager` | 통계·Excel·담당자 배정 |
| PM 전체 메뉴 | `pm` | 내부 데이터운영팀 중심 |
| 주간·월간 보고 | `is_admin` | 관리자 전용 |
