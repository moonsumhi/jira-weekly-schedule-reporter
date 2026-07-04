"""앱 시작 시 수행하는 DB 인덱스 생성, 시드 데이터 삽입, 마이그레이션."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.db.mongo import MongoClientManager

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 시스템 메뉴 초기값 (slug가 없으면 자동 생성)
# ──────────────────────────────────────────────
_SYSTEM_MENUS = [
    {"slug": "jira",     "title": "Jira",       "icon": "fa-brands fa-jira",      "sort_order": 1},
    {"slug": "job",      "title": "작업 관리",   "icon": "fa-solid fa-briefcase",  "sort_order": 2},
    {"slug": "asset",    "title": "자산",        "icon": "fa-solid fa-computer",   "sort_order": 3},
    {"slug": "watch",    "title": "당직 시간표", "icon": "fa-solid fa-clock",      "sort_order": 4},
    {"slug": "calendar", "title": "팀캘린더",    "icon": "fa-solid fa-calendar",   "sort_order": 6},
    {"slug": "pm",           "title": "스케줄 관리",  "icon": "fa-solid fa-diagram-project",  "sort_order": 7},
    {"slug": "sr",           "title": "SR",           "icon": "fa-solid fa-paper-plane",      "sort_order": 8},
    {"slug": "inspection",   "title": "점검",         "icon": "fa-solid fa-clipboard-check",  "sort_order": 9},
    {"slug": "server_check", "title": "서버 점검",    "icon": "fa-solid fa-server",           "sort_order": 10},
    {"slug": "documents",    "title": "문서 관리",    "icon": "fa-solid fa-folder-open",      "sort_order": 11},
    {"slug": "isms-p",       "title": "ISMS-P",       "icon": "fa-solid fa-shield-halved",    "sort_order": 12},
    {"slug": "admin",        "title": "관리자",       "icon": "fa-solid fa-user-shield",      "sort_order": 99},
]


async def create_indexes() -> None:
    """컬렉션별 인덱스를 생성한다. 이미 존재하면 무시된다."""
    db = MongoClientManager.get_db()

    users = MongoClientManager.get_users_collection()
    await users.create_index("email", unique=True)

    watch = MongoClientManager.get_watch_assignments_collection()
    await watch.create_index("start")
    await watch.create_index("end")
    await watch.create_index("assignee")

    for _cat, (col_name, hist_name) in MongoClientManager.CATEGORY_COLLECTIONS.items():
        col = db[col_name]
        await col.create_index("ip")
        for idx_name in ("asset_no_1", "name_1", "asset_id_1"):
            try:
                await col.drop_index(idx_name)
            except Exception:
                pass
        await col.create_index(
            "asset_id", unique=True,
            partialFilterExpression={"asset_id": {"$type": "string"}},
        )
        await col.create_index("asset_no")
        hist = db[hist_name]
        await hist.create_index("asset_id")
        await hist.create_index("changed_at")

    inspection_checklists = MongoClientManager.get_inspection_checklists_collection()
    await inspection_checklists.create_index("inspection_month", unique=True)
    await inspection_checklists.create_index("person_in_charge")

    inspection_history = MongoClientManager.get_inspection_history_collection()
    await inspection_history.create_index("checklist_id")
    await inspection_history.create_index("changed_at")

    job_plans = MongoClientManager.get_job_plans_collection()
    await job_plans.create_index("work_date")
    await job_plans.create_index("worker")
    await job_plans.create_index("status")

    job_plans_history = MongoClientManager.get_job_plans_history_collection()
    await job_plans_history.create_index("plan_id")
    await job_plans_history.create_index("changed_at")

    form_entries_col = MongoClientManager.get_form_entries_collection()
    await form_entries_col.create_index("template_id")
    await form_entries_col.create_index("created_at")

    menus_col = MongoClientManager.get_menus_collection()
    await menus_col.create_index("sort_order")
    await menus_col.create_index("slug", unique=True, sparse=True)

    board_posts_col = MongoClientManager.get_board_posts_collection()
    await board_posts_col.create_index("board_id")
    await board_posts_col.create_index("created_at")

    logger.info("DB 인덱스 생성 완료")


async def seed_system_menus() -> None:
    """시스템 메뉴가 없으면 초기 데이터를 삽입한다."""
    menus_col = MongoClientManager.get_menus_collection()
    for sm in _SYSTEM_MENUS:
        existing = await menus_col.find_one({"slug": sm["slug"]})
        if not existing:
            await menus_col.insert_one({
                **sm,
                "is_visible": True,
                "is_system": True,
                "created_at": datetime.now(timezone.utc),
            })
        elif sm["slug"] == "calendar" and existing.get("link"):
            await menus_col.update_one({"slug": "calendar"}, {"$unset": {"link": ""}})
        elif sm["slug"] == "pm" and existing.get("title") == "PM":
            await menus_col.update_one({"slug": "pm"}, {"$set": {"title": "스케줄 관리"}})

    # account 메뉴는 하단 유저 카드로 대체 — DB에서 제거
    await menus_col.delete_one({"slug": "account"})

    # 구 SR 개별 메뉴 제거 (sr 상위 메뉴로 통합)
    for old_slug in ("sr-new", "sr-my", "sr-manage"):
        await menus_col.delete_one({"slug": old_slug})



# NCDC포털_작업계획서_260604.hwp 실제 양식에서 추출한 섹션 구조 (서비스/서비스 외 공통).
_PLAN_BASIC_INFO = {
    "title": "기본 정보",
    "fields": [
        {"label": "작업명",           "type": "text",     "required": True,  "placeholder": "작업명을 입력하세요"},
        {"label": "작업 일시",        "type": "text",     "required": True,  "placeholder": "YYYY.MM.DD HH:MM-HH:MM"},
        {"label": "서비스 명",        "type": "text",     "required": True},
        {"label": "회사명/성함/직책", "type": "text",     "required": True},
        {"label": "중요도",           "type": "select",   "required": True,  "options": ["상", "중", "하"]},
        {"label": "목적",             "type": "textarea", "required": True},
    ],
}
_PLAN_TARGETS = {
    "title": "작업 대상",
    "multiple": True,
    "fields": [
        {"label": "작업 대상", "type": "text", "required": False},
        {"label": "IP",       "type": "text", "required": False},
        {"label": "HOSTNAME", "type": "text", "required": False},
        {"label": "비고",     "type": "text", "required": False},
    ],
}
_PLAN_BACKUP = {
    "title": "백업 및 복구 방법",
    "multiple": True,
    "fields": [
        {"label": "백업 및 복구 방법 및 절차", "type": "textarea", "required": False},
        {"label": "비고",                    "type": "text",     "required": False},
    ],
}
_PLAN_WORKERS = {
    "title": "작업자 정보",
    "multiple": True,
    "fields": [
        {"label": "회사명",       "type": "text", "required": False},
        {"label": "성함/직책",   "type": "text", "required": False},
        {"label": "역할",        "type": "text", "required": False},
        {"label": "연락처",      "type": "text", "required": False},
        {"label": "비고",        "type": "text", "required": False},
    ],
}
_PLAN_REVIEW = {
    "title": "검토/서명",
    "multiple": True,
    "fields": [
        {"label": "소속",     "type": "text",     "required": False},
        {"label": "성함",     "type": "text",     "required": False},
        {"label": "검토의견", "type": "textarea", "required": False},
        {"label": "서명",     "type": "text",     "required": False},
    ],
}
_PLAN_STEPS = {
    "title": "세부 작업 내용",
    "multiple": True,
    "fields": [
        {"label": "제목",        "type": "text",     "required": False},
        {"label": "리스크",      "type": "select",   "required": False, "options": ["상", "중", "하"]},
        {"label": "세부 작업 내용", "type": "textarea", "required": False},
        {"label": "작업 이미지", "type": "image",    "required": False},
    ],
}
_PLAN_SCHEDULE = {
    "title": "작업 시간표",
    "multiple": True,
    "fields": [
        {"label": "시작 시간",     "type": "text",     "required": False},
        {"label": "종료 시간",     "type": "text",     "required": False},
        {"label": "세부 작업 내용", "type": "textarea", "required": False},
        {"label": "비고",         "type": "text",     "required": False},
    ],
}
_PLAN_PRECHECK = {
    "title": "사전 점검",
    "multiple": True,
    "fields": [
        {"label": "사전 점검 사항", "type": "textarea", "required": False},
        {"label": "점검 결과",     "type": "text",     "required": False},
        {"label": "비고",         "type": "text",     "required": False},
    ],
}
_PLAN_TEST_CASES = {
    "title": "테스트 케이스",
    "multiple": True,
    "fields": [
        {"label": "설명",       "type": "text",     "required": False},
        {"label": "전제 조건",  "type": "text",     "required": False},
        {"label": "테스트 데이터","type": "text",     "required": False},
        {"label": "예상 결과",  "type": "textarea", "required": False},
    ],
}

_JOB_FORM_TEMPLATES = [
    {
        "title": "작업계획서(서비스)",
        "jira_issue_key": "JOB-PLAN-SERVICE",
        "menu": "Job",
        "sort_order": 1,
        "sections": [
            _PLAN_BASIC_INFO,
            _PLAN_TARGETS,
            _PLAN_BACKUP,
            _PLAN_WORKERS,
            _PLAN_REVIEW,
            _PLAN_STEPS,
            _PLAN_SCHEDULE,
            _PLAN_PRECHECK,
            _PLAN_TEST_CASES,
        ],
    },
    {
        "title": "작업계획서(서비스 외)",
        "jira_issue_key": "JOB-PLAN-NONSERVICE",
        "menu": "Job",
        "sort_order": 2,
        "sections": [
            _PLAN_BASIC_INFO,
            _PLAN_TARGETS,
            _PLAN_BACKUP,
            _PLAN_WORKERS,
            _PLAN_REVIEW,
            _PLAN_STEPS,
            _PLAN_SCHEDULE,
            _PLAN_PRECHECK,
            _PLAN_TEST_CASES,
        ],
    },
    {
        # ServiceWorkResultBase 필드와 1:1로 맞춤
        "title": "작업결과서",
        "jira_issue_key": "JOB-RESULT",
        "menu": "Job",
        "sort_order": 3,
        "sections": [
            {
                "title": "기본 정보",
                "fields": [
                    {"label": "작업명",   "type": "text",   "required": True,  "placeholder": "작업명을 입력하세요"},
                    {"label": "작업 일시","type": "text",   "required": True,  "placeholder": "YYYY-MM-DD HH:MM"},
                    {"label": "작업자",   "type": "text",   "required": True},
                    {"label": "신청자",   "type": "text",   "required": True},
                    {"label": "시스템명", "type": "text",   "required": True},
                    {"label": "작업 구분","type": "select", "required": True,  "options": ["정기", "긴급", "임시"]},
                ],
            },
            {
                # result / actual_start_time / actual_end_time / summary — 단일 필드 (반복 아님)
                "title": "작업 결과",
                "fields": [
                    {"label": "결과",         "type": "select",   "required": True,  "options": ["성공", "부분성공", "실패"]},
                    {"label": "실제 시작 시간","type": "text",     "required": False},
                    {"label": "실제 종료 시간","type": "text",     "required": False},
                    {"label": "작업 요약",     "type": "textarea", "required": True},
                ],
            },
            {
                # service_affected / actual_downtime
                "title": "서비스 영향",
                "fields": [
                    {"label": "서비스 영향 여부", "type": "checkbox", "required": False},
                    {"label": "실제 중단 시간",   "type": "text",     "required": False},
                ],
            },
            {
                # step_results: List[JobWorkStepResult] (order, task, person, completed, notes)
                "title": "작업 절차 결과",
                "multiple": True,
                "fields": [
                    {"label": "작업 내용", "type": "textarea", "required": False},
                    {"label": "담당자",   "type": "text",     "required": False},
                    {"label": "완료 여부", "type": "checkbox", "required": False},
                    {"label": "비고",     "type": "textarea", "required": False},
                ],
            },
            {
                # issues_occurred / issue_details / action_taken
                "title": "문제 및 조치",
                "fields": [
                    {"label": "문제 발생 여부", "type": "checkbox", "required": False},
                    {"label": "문제 내용",      "type": "textarea", "required": False},
                    {"label": "조치 내용",      "type": "textarea", "required": False},
                ],
            },
            {
                # post_check_done / post_check_details
                "title": "사후 점검",
                "fields": [
                    {"label": "사후 점검 여부", "type": "checkbox", "required": False},
                    {"label": "사후 점검 내용", "type": "textarea", "required": False},
                ],
            },
            {
                # plan_id / notes
                "title": "비고",
                "fields": [
                    {"label": "연관 작업계획서 ID", "type": "text",     "required": False},
                    {"label": "비고",              "type": "textarea", "required": False},
                ],
            },
        ],
    },
]


# 시스템 메뉴별 하위 메뉴 및 leaf link 초기값
# job: form templates에서 동적으로 로드 → 여기서 정의 안 함
# account: 하단 유저 카드 표시 → 여기서 정의 안 함
_SYSTEM_MENU_EXTRAS: dict[str, dict] = {
    "jira": {
        "submenus": [
            {"title": "검색",    "icon": "fa-solid fa-list",          "link": "/jira/search"},
            {"title": "주간보고", "icon": "fa-solid fa-calendar-week", "link": "/report/weekly"},
        ],
    },
    "asset": {
        "submenus": [
            {"title": "전체",          "icon": "fa-solid fa-layer-group",   "link": "/asset/list"},
            {"title": "서버",          "icon": "fa-solid fa-server",        "link": "/asset/list?category=서버"},
            {"title": "네트워크",      "icon": "fa-solid fa-network-wired", "link": "/asset/list?category=네트워크"},
            {"title": "정보보호시스템", "icon": "fa-solid fa-shield-halved", "link": "/asset/list?category=정보보호시스템"},
            {"title": "DBMS",         "icon": "fa-solid fa-database",      "link": "/asset/list?category=DBMS"},
            {"title": "VMware",       "icon": "fa-brands fa-vuejs",        "link": "/asset/list?category=VMware"},
        ],
    },
    "watch":      {"link": "/watch/timetable"},
    "inspection": {"link": "/inspection/checklist"},
    "calendar":   {"link": "/calendar"},
    "documents":  {"link": "/documents"},
    "pm": {
        "submenus": [
            {"title": "대시보드", "icon": "fa-solid fa-gauge",            "link": "/pm/dashboard"},
            {"title": "업무 현황","icon": "fa-solid fa-chart-bar",        "link": "/pm/work-status"},
            {"title": "프로젝트", "icon": "fa-solid fa-diagram-project",  "link": "/pm/projects"},
            {"title": "조직",    "icon": "fa-solid fa-building",         "link": "/pm/organizations"},
            {"title": "주간 보고","icon": "fa-solid fa-calendar-week",    "link": "/pm/weekly-report",  "require_admin": True},
            {"title": "월간 보고","icon": "fa-solid fa-calendar-days",    "link": "/pm/monthly-report", "require_admin": True},
        ],
    },
    "sr": {
        "submenus": [
            {"title": "SR 접수",    "icon": "fa-solid fa-paper-plane", "link": "/pm/sr/new"},
            {"title": "내 SR 목록", "icon": "fa-solid fa-list-check",  "link": "/pm/sr/my"},
            {"title": "SR 관리",   "icon": "fa-solid fa-tasks",       "link": "/pm/sr/manage"},
        ],
    },
    "server_check": {
        "submenus": [
            {"title": "요약",      "icon": "fa-solid fa-table-list",   "link": "/inspection/health-summary"},
            {"title": "서버리스트", "icon": "fa-solid fa-server",       "link": "/inspection/health-servers"},
            {"title": "월별 비교", "icon": "fa-solid fa-code-compare", "link": "/inspection/health-compare"},
        ],
    },
    "isms-p": {
        "submenus": [
            {"title": "단계별 산출물", "icon": "fa-solid fa-folder-open", "link": "/isms-p/01. ISMS-P_단계별산출물"},
        ],
    },
    "admin": {
        "submenus": [
            {"title": "회원가입 승인", "icon": "fa-regular fa-thumbs-up",     "link": "/admin/approvals"},
            {"title": "회원 목록",    "icon": "fa-solid fa-users",           "link": "/admin/users"},
            {"title": "메뉴 관리",   "icon": "fa-solid fa-bars",            "link": "/admin/menus"},
            {"title": "Audit Log",  "icon": "fa-solid fa-clipboard-list",  "link": "/admin/audit-log"},
        ],
    },
}


async def seed_system_menu_extras() -> None:
    """시스템 메뉴에 link / submenus 초기값을 설정한다 (필드가 없을 때만)."""
    menus_col = MongoClientManager.get_menus_collection()
    for slug, extras in _SYSTEM_MENU_EXTRAS.items():
        doc = await menus_col.find_one({"slug": slug})
        if not doc:
            continue
        update: dict = {}
        if "link" in extras and not doc.get("link"):
            update["link"] = extras["link"]
        if "submenus" in extras and not doc.get("submenus"):
            update["submenus"] = extras["submenus"]
        if update:
            await menus_col.update_one({"slug": slug}, {"$set": update})


async def seed_job_form_templates() -> None:
    """Job 폼 템플릿이 없으면 초기 데이터를 삽입한다."""
    col = MongoClientManager.get_form_templates_collection()
    for tmpl in _JOB_FORM_TEMPLATES:
        existing = await col.find_one({"jira_issue_key": tmpl["jira_issue_key"]})
        if not existing:
            await col.insert_one({
                **tmpl,
                "is_deleted": False,
                "created_at": datetime.now(timezone.utc),
            })


async def migrate_assets() -> None:
    """assets_servers 컬렉션의 비서버 자산을 유형별 컬렉션으로 이동한다.

    이미 이동된 데이터는 건너뛰므로 멱등하게 실행 가능하다.
    """
    db = MongoClientManager.get_db()
    src = MongoClientManager.get_assets_servers_collection()
    col_map = {
        "네트워크":      db[MongoClientManager.ASSETS_NETWORK],
        "정보보호시스템": db[MongoClientManager.ASSETS_SECURITY],
        "DBMS":          db[MongoClientManager.ASSETS_DBMS],
        "VMware":        db[MongoClientManager.ASSETS_VMWARE],
    }
    migrated = 0
    async for doc in src.find({"fields.자산유형": {"$in": list(col_map.keys())}}):
        asset_type = doc["fields"]["자산유형"]
        target = col_map[asset_type]
        if not await target.find_one({"_id": doc["_id"]}):
            await target.insert_one(doc)
            migrated += 1
        await src.delete_one({"_id": doc["_id"]})
    if migrated:
        logger.info("assets 마이그레이션 완료: %d건 이동", migrated)


async def run_startup() -> None:
    """lifespan startup에서 호출하는 진입점."""
    await create_indexes()
    await seed_system_menus()
    await seed_system_menu_extras()
    await seed_job_form_templates()
    await migrate_assets()

    from app.db.pm_indexes import create_pm_indexes
    await create_pm_indexes()
    logger.info("PM 인덱스 생성 완료")

    from app.db.sr_indexes import create_sr_indexes
    await create_sr_indexes()
    logger.info("SR 인덱스 생성 완료")
