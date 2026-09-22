"""앱 시작 시 수행하는 DB 인덱스 생성, 시드 데이터 삽입, 마이그레이션."""
from __future__ import annotations

import logging
import re
from copy import deepcopy
from datetime import datetime, timezone

from app.db.mongo import MongoClientManager

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 시스템 메뉴 초기값 (slug가 없으면 자동 생성)
# ──────────────────────────────────────────────
_SYSTEM_MENUS = [
    {"slug": "job",      "title": "작업 관리",   "icon": "fa-solid fa-briefcase",  "sort_order": 2},
    {"slug": "asset",    "title": "자산",        "icon": "fa-solid fa-computer",   "sort_order": 3},
    {"slug": "watch",    "title": "당직 시간표", "icon": "fa-solid fa-clock",      "sort_order": 4},
    {"slug": "board",    "title": "게시판",      "icon": "fa-solid fa-clipboard-list", "sort_order": 5},
    {"slug": "calendar", "title": "팀캘린더",    "icon": "fa-solid fa-calendar",   "sort_order": 6},
    {"slug": "pm",           "title": "스케줄 관리",  "icon": "fa-solid fa-diagram-project",  "sort_order": 7},
    {"slug": "sr",           "title": "SR",           "icon": "fa-solid fa-paper-plane",      "sort_order": 8},
    {"slug": "server_check", "title": "서버 점검",    "icon": "fa-solid fa-server",           "sort_order": 10},
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
    await form_entries_col.create_index([("asset_ids", 1), ("created_at", -1)])

    asset_notes = MongoClientManager.get_asset_notes_collection()
    await asset_notes.create_index([('asset_id', 1), ('created_at', -1), ('_id', -1)])
    await asset_notes.create_index([('asset_id', 1), ('client_id', 1)], unique=True)
    await MongoClientManager.get_pm_issues_collection().create_index([('asset_ids', 1), ('created_at', -1)])

    menus_col = MongoClientManager.get_menus_collection()
    await menus_col.create_index("sort_order")
    await menus_col.create_index("slug", unique=True, sparse=True)

    board_posts_col = MongoClientManager.get_board_posts_collection()
    await board_posts_col.create_index("board_id")
    await board_posts_col.create_index("created_at")

    notices_col = MongoClientManager.get_notices_collection()
    await notices_col.create_index("start_date")
    await notices_col.create_index("end_date")

    env_categories_col = MongoClientManager.get_env_categories_collection()
    await env_categories_col.create_index("key", unique=True)

    logger.info("DB 인덱스 생성 완료")


async def seed_system_menus() -> None:
    """시스템 메뉴가 없으면 초기 데이터를 삽입한다."""
    menus_col = MongoClientManager.get_menus_collection()
    for sm in _SYSTEM_MENUS:
        existing = await menus_col.find_one({"slug": sm["slug"]})
        if not existing and sm["slug"] == "board":
            # 과거에는 게시판 상위 메뉴도 관리자가 직접 생성했다. 같은 이름의
            # 레거시 메뉴를 시스템 메뉴로 승격해 하위 게시판·게시글 연결을 보존한다.
            legacy = await menus_col.find_one({
                "title": "게시판",
                "$or": [{"slug": {"$exists": False}}, {"slug": None}],
            })
            if legacy:
                await menus_col.update_one(
                    {"_id": legacy["_id"]},
                    {"$set": {"slug": "board", "is_system": True}},
                )
                existing = legacy
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
        {"label": "작업 기간 (시작)", "type": "datetime", "required": True},
        {"label": "작업 기간 (종료)", "type": "datetime", "required": True},
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
        {"label": "서명",     "type": "image",    "required": False},
    ],
}
_PLAN_DEV_CONTENT = {
    "title": "개발 내용",
    "multiple": True,
    "fields": [
        {"label": "제목",        "type": "text",     "required": False},
        {"label": "리스크",      "type": "select",   "required": False, "options": ["상", "중", "하"]},
        {"label": "세부 작업 내용", "type": "textarea", "required": False},
    ],
}
_PLAN_STEPS = {
    "title": "세부 작업 내용",
    "multiple": True,
    "fields": [
        {"label": "제목",        "type": "text",     "required": False},
        {"label": "리스크",      "type": "select",   "required": False, "options": ["상", "중", "하"]},
        {"label": "세부 작업 내용", "type": "textarea", "required": False},
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

# NCDC포털_작업결과서_260604.hwp 실제 양식에서 추출한 섹션 구조.
# 작업 대상/작업자 정보/검토·서명은 작업계획서와 동일해 위 _PLAN_* 섹션을 그대로 재사용.
_RESULT_BASIC_INFO = {
    "title": "기본 정보",
    "fields": [
        {"label": "작업명",           "type": "text",     "required": True,  "placeholder": "작업명을 입력하세요"},
        {"label": "작업 일시",        "type": "text",     "required": True,  "placeholder": "YYYY.MM.DD HH:MM-HH:MM"},
        {"label": "서비스 명",        "type": "text",     "required": True},
        {"label": "회사명/성함/직책", "type": "text",     "required": True},
        {"label": "구분",             "type": "select",   "required": True,  "options": ["서버", "네트워크", "보안", "개발"]},
        {"label": "서비스 영향도",    "type": "select",   "required": True,  "options": ["유", "무"]},
        {"label": "목적",             "type": "textarea", "required": True},
    ],
}
_RESULT_WORK_CONTENT = {
    "title": "작업 내용",
    "multiple": True,
    "fields": [
        {"label": "작업 내용", "type": "textarea", "required": False},
        {"label": "비고",     "type": "text",     "required": False},
    ],
}
_RESULT_BEFORE_AFTER = {
    "title": "작업 결과",
    "multiple": True,
    "fields": [
        {"label": "작업 전",     "type": "textarea", "required": False, "paired_image": "작업 전 사진"},
        {"label": "작업 후",     "type": "textarea", "required": False, "paired_image": "작업 후 사진"},
        {"label": "작업 전 사진", "type": "image",    "required": False},
        {"label": "작업 후 사진", "type": "image",    "required": False},
    ],
}
_RESULT_TEST_SUCCESS = {
    "title": "테스트 케이스",
    "multiple": True,
    "fields": [
        {"label": "테스트 케이스 ID", "type": "text", "required": False},
        {"label": "결과",            "type": "select", "required": False, "options": ["성공", "실패"]},
        {"label": "시간",            "type": "text", "required": False},
        {"label": "발견된 이슈",     "type": "text", "required": False},
        {"label": "담당자",          "type": "text", "required": False},
    ],
}
_RESULT_EXTRA_INFO = {
    "title": "추가 정보",
    "fields": [
        {"label": "특이사항", "type": "textarea", "required": False},
        {"label": "완료 여부", "type": "boolean", "required": False},
    ],
}

# 반입신청서_한국보건의료정보원 (2).hwp 실제 양식에서 추출한 섹션 구조.
_INTAKE_APPLICANT_INFO = {
    "title": "신청자 정보",
    "fields": [
        {"label": "기관명",                        "type": "text",     "required": True},
        {"label": "사업자등록번호 또는 법인등록번호", "type": "text",     "required": False},
        {"label": "주소",                          "type": "text",     "required": False},
        {"label": "대표자명",                      "type": "text",     "required": False},
        {"label": "신청자/연락처",                  "type": "text",     "required": True},
        {"label": "신청일자",                      "type": "text",     "required": True,  "placeholder": "YYYY.MM.DD"},
        {"label": "유형",                          "type": "select",   "required": True,  "options": ["개인", "공공기관", "비영리법인", "민간기관"]},
    ],
}
_INTAKE_FILE_INFO = {
    "title": "반입 파일 정보",
    "fields": [
        {"label": "파일 개수",                      "type": "text",     "required": False},
        {"label": "파일명 (파일형식, 파일용량 포함)", "type": "text",     "required": False},
        {"label": "처리 목적",                      "type": "text",     "required": True,  "full_width": True},
        {"label": "내용 요약",                      "type": "textarea", "required": False},
    ],
}
_INTAKE_REVIEW = {
    "title": "적정성 검토",
    "multiple": True,
    "fields": [
        {"label": "소속",     "type": "text",     "required": False},
        {"label": "성함",     "type": "text",     "required": False},
        {"label": "검토의견", "type": "textarea", "required": False},
        {"label": "서명",     "type": "image",    "required": False},
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
            _PLAN_DEV_CONTENT,
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
        "title": "작업결과서",
        "jira_issue_key": "JOB-RESULT",
        "menu": "Job",
        "sort_order": 3,
        "sections": [
            _RESULT_BASIC_INFO,
            _PLAN_TARGETS,
            _RESULT_WORK_CONTENT,
            _PLAN_WORKERS,
            _PLAN_REVIEW,
            _RESULT_BEFORE_AFTER,
            _RESULT_TEST_SUCCESS,
            _RESULT_EXTRA_INFO,
        ],
    },
    {
        "title": "반입신청서",
        "jira_issue_key": "JOB-INTAKE-REQUEST",
        "menu": "Job",
        "sort_order": 4,
        "sections": [
            _INTAKE_APPLICANT_INFO,
            _INTAKE_FILE_INFO,
            _INTAKE_REVIEW,
        ],
    },
]


# 시스템 메뉴별 하위 메뉴 및 leaf link 초기값
# job: form templates에서 동적으로 로드 → 여기서 정의 안 함
# account: 하단 유저 카드 표시 → 여기서 정의 안 함
_SYSTEM_MENU_EXTRAS: dict[str, dict] = {
    "asset": {
        "submenus": [
            {"title": "전체",          "icon": "fa-solid fa-layer-group",   "link": "/asset/list"},
            {"title": "서버",          "icon": "fa-solid fa-server",        "link": "/asset/list?category=서버"},
            {"title": "네트워크",      "icon": "fa-solid fa-network-wired", "link": "/asset/list?category=네트워크"},
            {"title": "정보보호시스템", "icon": "fa-solid fa-shield-halved", "link": "/asset/list?category=정보보호시스템"},
            {"title": "DBMS",         "icon": "fa-solid fa-database",      "link": "/asset/list?category=DBMS"},
            {"title": "VMware",       "icon": "fa-brands fa-vuejs",        "link": "/asset/list?category=VMware"},
            {"title": "랙",           "icon": "fa-solid fa-boxes-stacked", "link": "/asset/list?category=랙"},
        ],
    },
    "watch":      {"link": "/watch/timetable"},
    "calendar":   {"link": "/calendar"},
    "pm": {
        "submenus": [
            {"title": "대시보드", "icon": "fa-solid fa-gauge",            "link": "/pm/dashboard"},
            {"title": "업무 현황","icon": "fa-solid fa-chart-bar",        "link": "/pm/work-status"},
            {"title": "프로젝트", "icon": "fa-solid fa-diagram-project",  "link": "/pm/projects"},
            {"title": "조직",    "icon": "fa-solid fa-building",         "link": "/pm/organizations"},
            {"title": "주간 보고","icon": "fa-solid fa-calendar-week",    "link": "/pm/weekly-report"},
            {"title": "월간 보고","icon": "fa-solid fa-calendar-days",    "link": "/pm/monthly-report"},
            {"title": "반복 업무","icon": "fa-solid fa-repeat",           "link": "/pm/recurring-issues"},
            {"title": "사용 가이드","icon": "fa-solid fa-circle-question","link": "/pm/schedule/guide"},
        ],
    },
    "sr": {
        "submenus": [
            {"title": "SR 접수",    "icon": "fa-solid fa-paper-plane",    "link": "/pm/sr/new"},
            {"title": "내 SR 목록", "icon": "fa-solid fa-list-check",     "link": "/pm/sr/my"},
            {"title": "SR 관리",   "icon": "fa-solid fa-tasks",          "link": "/pm/sr/manage"},
            {"title": "사용 가이드","icon": "fa-solid fa-circle-question","link": "/pm/sr/guide"},
        ],
    },
    "server_check": {
        "submenus": [
            {"title": "자원 점검", "icon": "fa-solid fa-server",       "link": "/inspection/health-servers"},
        ],
    },
    "admin": {
        "submenus": [
            {"title": "회원가입 승인", "icon": "fa-regular fa-thumbs-up",     "link": "/admin/approvals"},
            {"title": "회원 목록",    "icon": "fa-solid fa-users",           "link": "/admin/users"},
            {"title": "메뉴 관리",   "icon": "fa-solid fa-bars",            "link": "/admin/menus"},
            {"title": "공지사항",    "icon": "fa-solid fa-bullhorn",        "link": "/admin/notices"},
            {"title": "Audit Log",  "icon": "fa-solid fa-clipboard-list",  "link": "/admin/audit-log"},
            {"title": "세션 설정",   "icon": "fa-solid fa-clock",           "link": "/admin/settings"},
            {"title": "스킨 설정",   "icon": "fa-solid fa-palette",         "link": "/admin/theme"},
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


async def migrate_pm_report_submenu_access() -> None:
    """주간/월간 보고 서브메뉴의 require_admin을 False로 해제한다 (멱등)."""
    menus_col = MongoClientManager.get_menus_collection()
    doc = await menus_col.find_one({"slug": "pm"})
    if not doc:
        return
    submenus = doc.get("submenus", [])
    target_links = {"/pm/weekly-report", "/pm/monthly-report"}
    updated = []
    changed = False
    for s in submenus:
        if s.get("link") in target_links and s.get("require_admin"):
            s = {**s, "require_admin": False}
            changed = True
        updated.append(s)
    if changed:
        await menus_col.update_one({"slug": "pm"}, {"$set": {"submenus": updated}})
        logger.info("주간/월간 보고 서브메뉴 require_admin 해제 완료")


async def migrate_guide_submenus() -> None:
    """pm·sr 메뉴에 사용 가이드 서브메뉴가 없으면 추가한다 (멱등)."""
    menus_col = MongoClientManager.get_menus_collection()
    guide_items = {
        "pm": {"title": "사용 가이드", "icon": "fa-solid fa-circle-question", "link": "/pm/schedule/guide"},
        "sr": {"title": "사용 가이드", "icon": "fa-solid fa-circle-question", "link": "/pm/sr/guide"},
    }
    for slug, item in guide_items.items():
        doc = await menus_col.find_one({"slug": slug})
        if not doc:
            continue
        existing_links = [s.get("link") for s in doc.get("submenus", [])]
        if item["link"] not in existing_links:
            await menus_col.update_one({"slug": slug}, {"$push": {"submenus": item}})
            logger.info("가이드 서브메뉴 추가: %s → %s", slug, item["link"])


async def migrate_recurring_issue_submenu() -> None:
    """pm 메뉴에 반복 업무 서브메뉴가 없으면 추가한다 (멱등)."""
    menus_col = MongoClientManager.get_menus_collection()
    item = {"title": "반복 업무", "icon": "fa-solid fa-repeat", "link": "/pm/recurring-issues"}
    doc = await menus_col.find_one({"slug": "pm"})
    if not doc:
        return
    existing_links = [s.get("link") for s in doc.get("submenus", [])]
    if item["link"] not in existing_links:
        await menus_col.update_one({"slug": "pm"}, {"$push": {"submenus": item}})
        logger.info("반복 업무 서브메뉴 추가")


async def migrate_remove_deprecated_features() -> None:
    """제거된 기능(ISMS-P·서버실 점검·문서 관리·Jira)의 메뉴·데이터를 정리한다 (멱등).

    코드가 삭제된 기능들. 기존 배포 DB에 남아있는 메뉴 문서와 고아 컬렉션·죽은 권한을
    제거한다. server_check(서버 점검)는 유지 대상이라 제외.
    """
    db = MongoClientManager.get_db()

    # 1) 삭제된 메뉴 문서 (server_check는 건드리지 않음)
    dead_slugs = ["isms-p", "inspection", "documents", "jira"]
    r = await MongoClientManager.get_menus_collection().delete_many({"slug": {"$in": dead_slugs}})
    if r.deleted_count:
        logger.info("제거된 기능 메뉴 %d개 삭제: %s", r.deleted_count, dead_slugs)

    # 2) 고아 컬렉션 drop
    dead_collections = [
        "isms_vulnerabilities", "isms_import_logs",
        "inspection_checklists", "inspection_history",
        "document_folders", "document_files",
    ]
    existing = set(await db.list_collection_names())
    for c in dead_collections:
        if c in existing:
            await db.drop_collection(c)
            logger.info("고아 컬렉션 drop: %s", c)

    # 3) 유저 권한에서 죽은 문자열 제거
    dead_perms = ["isms-p", "inspection", "documents", "document_manage", "jira"]
    r2 = await MongoClientManager.get_users_collection().update_many(
        {"permissions": {"$in": dead_perms}},
        {"$pull": {"permissions": {"$in": dead_perms}}},
    )
    if r2.modified_count:
        logger.info("제거된 기능 권한 정리: %d명", r2.modified_count)


async def migrate_rack_submenu() -> None:
    """asset 메뉴에 '랙' 서브메뉴가 없으면 추가한다 (멱등)."""
    menus_col = MongoClientManager.get_menus_collection()
    item = {"title": "랙", "icon": "fa-solid fa-boxes-stacked", "link": "/asset/list?category=랙"}
    doc = await menus_col.find_one({"slug": "asset"})
    if not doc:
        return
    existing_links = [s.get("link") for s in doc.get("submenus", [])]
    if item["link"] not in existing_links:
        await menus_col.update_one({"slug": "asset"}, {"$push": {"submenus": item}})
        logger.info("랙 서브메뉴 추가")


async def migrate_notice_submenu() -> None:
    """admin 메뉴에 공지사항 서브메뉴가 없으면 추가한다 (멱등)."""
    menus_col = MongoClientManager.get_menus_collection()
    item = {"title": "공지사항", "icon": "fa-solid fa-bullhorn", "link": "/admin/notices"}
    doc = await menus_col.find_one({"slug": "admin"})
    if not doc:
        return
    existing_links = [s.get("link") for s in doc.get("submenus", [])]
    if item["link"] not in existing_links:
        await menus_col.update_one({"slug": "admin"}, {"$push": {"submenus": item}})
        logger.info("공지사항 서브메뉴 추가")


async def seed_env_categories() -> None:
    """관리자가 화면에서 관리하는 동적 설정(카테고리) 초기값을 없으면 삽입한다 (멱등)."""
    col = MongoClientManager.get_env_categories_collection()
    if not await col.find_one({"key": "target_system"}):
        await col.insert_one({
            "key": "target_system",
            "label": "대상 시스템",
            "is_system": True,
            "items": [],
            "created_at": datetime.now(timezone.utc),
        })
        logger.info("env_categories 초기값 삽입: target_system")
    if not await col.find_one({"key": "firewall_notify_emails"}):
        await col.insert_one({
            "key": "firewall_notify_emails",
            "label": "방화벽 담당자 메일",
            "is_system": True,
            "items": [],
            "created_at": datetime.now(timezone.utc),
        })
        logger.info("env_categories 초기값 삽입: firewall_notify_emails")
    if not await col.find_one({"key": "incident_notify_emails"}):
        await col.insert_one({
            "key": "incident_notify_emails",
            "label": "장애 알림 서비스 메일 대상자",
            "is_system": True,
            "items": [],
            "created_at": datetime.now(timezone.utc),
        })
        logger.info("env_categories 초기값 삽입: incident_notify_emails")
    if not await col.find_one({"key": "board_post_categories"}):
        await col.insert_one({
            "key": "board_post_categories",
            "label": "게시판 카테고리",
            "is_system": True,
            "items": [],
            "created_at": datetime.now(timezone.utc),
        })
        logger.info("env_categories 초기값 삽입: board_post_categories")
    if not await col.find_one({"key": "asset_location"}):
        from uuid import uuid4
        _locs = ["암빅데이터센터", "정보화팀", "정보보호팀"]
        await col.insert_one({
            "key": "asset_location",
            "label": "자산 위치 / 랙 서버실",
            "is_system": True,
            "items": [
                {"id": str(uuid4()), "label": v, "value": v, "sort_order": i, "is_active": True}
                for i, v in enumerate(_locs)
            ],
            "created_at": datetime.now(timezone.utc),
        })
        logger.info("env_categories 초기값 삽입: asset_location")


async def migrate_env_submenu() -> None:
    """admin 메뉴에 환경설정 서브메뉴가 없으면 추가한다 (멱등)."""
    menus_col = MongoClientManager.get_menus_collection()
    item = {"title": "환경설정", "icon": "fa-solid fa-sliders", "link": "/admin/env"}
    doc = await menus_col.find_one({"slug": "admin"})
    if not doc:
        return
    existing_links = [s.get("link") for s in doc.get("submenus", [])]
    if item["link"] not in existing_links:
        await menus_col.update_one({"slug": "admin"}, {"$push": {"submenus": item}})
        logger.info("환경설정 서브메뉴 추가")


async def seed_job_form_templates() -> None:
    """Job 폼 템플릿이 없으면 초기 데이터를 삽입한다."""
    col = MongoClientManager.get_form_templates_collection()
    for tmpl in _JOB_FORM_TEMPLATES:
        existing = await col.find_one({
            "$or": [
                {"jira_issue_key": tmpl["jira_issue_key"]},
                {"title": tmpl["title"]},
            ]
        })
        if not existing:
            await col.insert_one({
                **tmpl,
                "is_deleted": False,
                "created_at": datetime.now(timezone.utc),
            })
        elif not existing.get("jira_issue_key"):
            await col.update_one(
                {"_id": existing["_id"]},
                {"$set": {"jira_issue_key": tmpl["jira_issue_key"]}},
            )


def _job_section_key(value: object) -> str:
    return re.sub(r"[\s()]+", "", str(value or "")).lower()


async def migrate_job_test_case_sections() -> None:
    """작업결과서의 성공/실패 테스트 섹션을 하나의 테스트 케이스로 통합한다.

    기존 템플릿은 구조만 바꾸고, 기존 결과 데이터의 성공 행은 새 섹션명으로
    옮긴다. 실패 데이터는 삭제하지 않고 DB에 남겨 두어 원본 보존을 유지한다.
    """
    templates = MongoClientManager.get_form_templates_collection()
    entries = MongoClientManager.get_form_entries_collection()
    async for template in templates.find({"is_deleted": {"$ne": True}}):
        if template.get("menu") not in ("Job", "job", None) or "작업" not in str(template.get("title", "")):
            continue
        sections = template.get("sections", [])
        if not isinstance(sections, list):
            continue

        normalized: list[dict] = []
        test_section: dict | None = None
        changed = False
        for raw_section in sections:
            if not isinstance(raw_section, dict):
                normalized.append(raw_section)
                continue
            key = _job_section_key(raw_section.get("title"))
            if key in {"테스트케이스", "테스트케이스성공"}:
                section = deepcopy(raw_section)
                if section.get("title") != "테스트 케이스":
                    section["title"] = "테스트 케이스"
                    changed = True
                if test_section is None:
                    test_section = section
                    normalized.append(test_section)
                else:
                    existing_labels = {str(field.get("label")) for field in test_section.get("fields", [])}
                    for field in section.get("fields", []):
                        if str(field.get("label")) not in existing_labels:
                            test_section.setdefault("fields", []).append(field)
                            existing_labels.add(str(field.get("label")))
                            changed = True
                continue
            if key == "테스트케이스실패":
                changed = True
                continue
            normalized.append(raw_section)

        if changed:
            await templates.update_one({"_id": template["_id"]}, {"$set": {"sections": normalized}})
            logger.info("작업 템플릿 테스트 케이스 섹션 통합: %s", template.get("title"))

        # 성공 섹션의 기존 데이터는 새 이름으로 옮겨 기존 결과서가 계속 보이게 한다.
        template_id = str(template["_id"])
        async for entry in entries.find({"template_id": template_id}):
            data = entry.get("data")
            if not isinstance(data, dict) or "테스트 케이스(성공)" not in data:
                continue
            legacy = data.pop("테스트 케이스(성공)")
            current = data.get("테스트 케이스")
            if current is None:
                data["테스트 케이스"] = legacy
            elif isinstance(current, list) and isinstance(legacy, list):
                data["테스트 케이스"] = current + legacy
            elif isinstance(current, dict) and isinstance(legacy, dict):
                data["테스트 케이스"] = {**legacy, **current}
            await entries.update_one({"_id": entry["_id"]}, {"$set": {"data": data}})
            logger.info("작업 결과서 테스트 케이스 데이터 이관: %s", entry["_id"])


async def migrate_result_completion_field() -> None:
    """작업결과서의 추가 정보에 완료 여부 선택 필드를 보장한다.

    기존 설치본에는 실제 HWP 양식으로 재구성되는 과정에서 이 필드가 빠진
    템플릿이 있어, 새 템플릿과 기존 템플릿 모두에서 같은 편집 UI를 사용할 수
    있도록 멱등적으로 보완한다.
    """
    templates = MongoClientManager.get_form_templates_collection()
    async for template in templates.find({"is_deleted": {"$ne": True}}):
        if template.get("jira_issue_key") != "JOB-RESULT":
            continue
        sections = template.get("sections", [])
        if not isinstance(sections, list):
            continue
        normalized = deepcopy(sections)
        extra = next(
            (
                section for section in normalized
                if _job_section_key(section.get("title")) == "추가정보"
            ),
            None,
        )
        changed = False
        if extra is None:
            normalized.append(deepcopy(_RESULT_EXTRA_INFO))
            changed = True
        else:
            fields = extra.setdefault("fields", [])
            ordered_fields: list[dict] = []
            known_labels = {_job_section_key(field["label"]) for field in _RESULT_EXTRA_INFO["fields"]}
            for field in _RESULT_EXTRA_INFO["fields"]:
                label_key = _job_section_key(field["label"])
                existing = next(
                    (item for item in fields if isinstance(item, dict) and _job_section_key(item.get("label")) == label_key),
                    None,
                )
                ordered_fields.append(deepcopy(existing) if existing is not None else deepcopy(field))
            ordered_fields.extend(
                deepcopy(field)
                for field in fields
                if isinstance(field, dict) and _job_section_key(field.get("label")) not in known_labels
            )
            if fields != ordered_fields:
                extra["fields"] = ordered_fields
                changed = True
        if changed:
            await templates.update_one(
                {"_id": template["_id"]},
                {"$set": {"sections": normalized}},
            )
            logger.info("작업결과서 완료 여부 필드 보완: %s", template.get("title"))


def _split_result_work_period(value: object) -> tuple[str, str]:
    """기존 작업 일시 문자열을 작업결과서 시작/종료 datetime으로 분리한다."""
    source = ' '.join(str(value or '').split())
    times = list(re.finditer(r'(\d{1,2}):(\d{2})', source))
    if not times:
        return '', ''
    date = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', source)
    prefix = ''
    if date:
        year, month, day = date.groups()
        prefix = f'{year}-{month.zfill(2)}-{day.zfill(2)}T'
    start = f'{prefix}{times[0].group(1).zfill(2)}:{times[0].group(2)}'
    if len(times) < 2:
        return start, ''
    end = f'{prefix}{times[1].group(1).zfill(2)}:{times[1].group(2)}'
    return start, end


async def migrate_result_work_period_fields() -> None:
    """작업결과서의 구 작업 일시를 시작/종료 필드로 바꾼다 (멱등).

    Import 대상 양식과 저장된 결과서를 함께 갱신해 원본의 한 칸짜리 작업 일시가
    작업 기간 (시작)·작업 기간 (종료)로 일관되게 저장되도록 한다.
    """
    templates = MongoClientManager.get_form_templates_collection()
    entries = MongoClientManager.get_form_entries_collection()
    start_label, end_label, legacy_label = '작업 기간 (시작)', '작업 기간 (종료)', '작업 일시'
    desired_fields = [
        {"label": start_label, "type": "datetime", "required": True},
        {"label": end_label, "type": "datetime", "required": True},
    ]

    async for template in templates.find({"is_deleted": {"$ne": True}, "title": "작업결과서"}):
        sections = deepcopy(template.get('sections', []))
        basic = next((section for section in sections if _job_section_key(section.get('title')) in {'기본정보', '작업개요'}), None)
        if not basic:
            continue
        fields = basic.get('fields', [])
        labels = [str(field.get('label', '')) for field in fields]
        changed = False
        if start_label not in labels or end_label not in labels:
            legacy_index = next((index for index, field in enumerate(fields) if field.get('label') == legacy_label), None)
            if legacy_index is not None:
                fields[legacy_index:legacy_index + 1] = deepcopy(desired_fields)
                changed = True
        if changed:
            await templates.update_one({"_id": template["_id"]}, {"$set": {"sections": sections}})
            logger.info("작업결과서 작업 기간 필드 이관: %s", template["_id"])

        section_title = basic.get('title', '기본 정보')
        async for entry in entries.find({"template_id": str(template["_id"])}):
            data = entry.get('data')
            if not isinstance(data, dict):
                continue
            values = data.get(section_title)
            if not isinstance(values, dict) or not values.get(legacy_label):
                continue
            start, end = _split_result_work_period(values[legacy_label])
            if not start and not end:
                continue
            if start and not values.get(start_label):
                values[start_label] = start
            if end and not values.get(end_label):
                values[end_label] = end
            if values.get(start_label) and values.get(end_label):
                values.pop(legacy_label, None)
            await entries.update_one({"_id": entry["_id"]}, {"$set": {"data": data}})
            logger.info("작업결과서 작업 기간 데이터 이관: %s", entry["_id"])


async def migrate_remove_development_image_field() -> None:
    """개발 내용의 별도 개발 이미지 컬럼을 제거한다 (멱등).

    이미 생성된 템플릿에도 해당 컬럼이 남아 있을 수 있으므로 템플릿 구조와
    기존 작업 문서의 레거시 데이터 키를 함께 정리한다. 세부 작업 내용에
    저장된 Markdown과 나머지 필드는 그대로 보존한다.
    """
    templates = MongoClientManager.get_form_templates_collection()
    entries = MongoClientManager.get_form_entries_collection()
    template_ids: list[str] = []

    async for template in templates.find({"is_deleted": {"$ne": True}}):
        if template.get("menu") not in ("Job", "job", None) or "작업" not in str(template.get("title", "")):
            continue
        sections = template.get("sections", [])
        if not isinstance(sections, list):
            continue
        normalized_sections: list[dict] = []
        changed = False
        for raw_section in sections:
            if not isinstance(raw_section, dict):
                normalized_sections.append(raw_section)
                continue
            section = deepcopy(raw_section)
            if _job_section_key(section.get("title")) == "개발내용":
                fields = section.get("fields", [])
                if isinstance(fields, list):
                    filtered_fields: list[dict] = []
                    for raw_field in fields:
                        if not isinstance(raw_field, dict):
                            filtered_fields.append(raw_field)
                            continue
                        field = deepcopy(raw_field)
                        field_label = _job_section_key(field.get("label"))
                        paired_label = _job_section_key(field.get("paired_image") or field.get("pairedImage"))
                        if field_label == "개발이미지":
                            changed = True
                            continue
                        if paired_label == "개발이미지":
                            field.pop("paired_image", None)
                            field.pop("pairedImage", None)
                            changed = True
                        filtered_fields.append(field)
                    section["fields"] = filtered_fields
            normalized_sections.append(section)
        template_ids.append(str(template["_id"]))
        if changed:
            await templates.update_one({"_id": template["_id"]}, {"$set": {"sections": normalized_sections}})
            logger.info("작업 템플릿 개발 이미지 컬럼 제거: %s", template.get("title"))

    # 기존 항목의 이미지 값은 더 이상 표시·내보내기 대상이 아니므로 제거한다.
    for template_id in template_ids:
        result = await entries.update_many(
            {"template_id": template_id, "data.개발 내용": {"$type": "array"}},
            {"$unset": {
                "data.개발 내용.$[].개발이미지": "",
                "data.개발 내용.$[].개발 이미지": "",
            }},
        )
        if result.modified_count:
            logger.info("작업 문서 개발 이미지 데이터 제거: template=%s count=%d", template_id, result.modified_count)
        result = await entries.update_many(
            {"template_id": template_id, "data.개발 내용": {"$type": "object"}},
            {"$unset": {
                "data.개발 내용.개발이미지": "",
                "data.개발 내용.개발 이미지": "",
            }},
        )
        if result.modified_count:
            logger.info("작업 문서 개발 이미지 데이터 제거(단일 행): template=%s count=%d", template_id, result.modified_count)


async def migrate_remove_result_work_image_field() -> None:
    """작업결과서의 작업 내용에서 별도 작업 이미지 컬럼을 제거한다 (멱등).

    과거 결과서 템플릿에는 ``작업 내용`` 표에 ``작업 이미지`` 컬럼이
    추가된 적이 있다. 현재 결과서는 작업 내용 본문만 사용하므로 템플릿의
    필드와 이미 저장된 레거시 값까지 함께 정리한다.
    """
    templates = MongoClientManager.get_form_templates_collection()
    entries = MongoClientManager.get_form_entries_collection()

    async for template in templates.find({"is_deleted": {"$ne": True}}):
        title = str(template.get("title", ""))
        if template.get("menu") not in ("Job", "job", None) or "작업" not in title:
            continue
        sections = template.get("sections", [])
        if not isinstance(sections, list):
            continue

        changed = False
        section_titles: list[str] = []
        normalized_sections: list[dict] = []
        for raw_section in sections:
            if not isinstance(raw_section, dict):
                normalized_sections.append(raw_section)
                continue
            section = deepcopy(raw_section)
            if _job_section_key(section.get("title")) != "작업내용":
                normalized_sections.append(section)
                continue
            section_title = str(section.get("title") or "작업 내용")
            section_titles.append(section_title)
            fields = section.get("fields", [])
            if isinstance(fields, list):
                filtered_fields: list[dict] = []
                for raw_field in fields:
                    if not isinstance(raw_field, dict):
                        filtered_fields.append(raw_field)
                        continue
                    field = deepcopy(raw_field)
                    label_key = _job_section_key(field.get("label"))
                    paired_key = _job_section_key(field.get("paired_image") or field.get("pairedImage"))
                    if label_key == "작업이미지":
                        changed = True
                        continue
                    if paired_key == "작업이미지":
                        field.pop("paired_image", None)
                        field.pop("pairedImage", None)
                        changed = True
                    filtered_fields.append(field)
                section["fields"] = filtered_fields
            normalized_sections.append(section)

        template_id = str(template["_id"])
        if changed:
            await templates.update_one(
                {"_id": template["_id"]},
                {"$set": {"sections": normalized_sections}},
            )
            logger.info("작업결과서 작업 이미지 컬럼 제거: %s", template.get("title"))

        # 템플릿의 실제 섹션 제목(공백 포함)을 사용해 레거시 데이터도 정리한다.
        for section_title in section_titles:
            for label in ("작업 이미지", "작업이미지"):
                result = await entries.update_many(
                    {"template_id": template_id, f"data.{section_title}": {"$type": "array"}},
                    {"$unset": {f"data.{section_title}.$[].{label}": ""}},
                )
                if result.modified_count:
                    logger.info(
                        "작업결과서 작업 이미지 데이터 제거: template=%s count=%d",
                        template_id,
                        result.modified_count,
                    )
                result = await entries.update_many(
                    {"template_id": template_id, f"data.{section_title}": {"$type": "object"}},
                    {"$unset": {f"data.{section_title}.{label}": ""}},
                )
                if result.modified_count:
                    logger.info(
                        "작업결과서 작업 이미지 데이터 제거(단일 행): template=%s count=%d",
                        template_id,
                        result.modified_count,
                    )


async def migrate_remove_work_steps_image_field() -> None:
    """세부 작업 내용/절차 표의 별도 작업 이미지 컬럼을 제거한다 (멱등).

    작업 본문은 Markdown 편집기에서 이미지와 함께 작성하므로, 별도 이미지
    컬럼이나 ``paired_image`` 연결을 남기지 않는다. 기존 템플릿과 저장된
    작업 문서의 레거시 키도 함께 정리한다.
    """
    templates = MongoClientManager.get_form_templates_collection()
    entries = MongoClientManager.get_form_entries_collection()
    target_titles = {"세부작업내용", "세부작업절차", "작업시간표"}

    async for template in templates.find({"is_deleted": {"$ne": True}}):
        sections = template.get("sections", [])
        if not isinstance(sections, list):
            continue

        changed = False
        section_titles: list[str] = []
        normalized_sections: list[dict] = []
        for raw_section in sections:
            if not isinstance(raw_section, dict):
                normalized_sections.append(raw_section)
                continue
            section = deepcopy(raw_section)
            if _job_section_key(section.get("title")) not in target_titles:
                normalized_sections.append(section)
                continue

            section_titles.append(str(section.get("title") or "세부 작업 내용"))
            fields = section.get("fields", [])
            if isinstance(fields, list):
                filtered_fields: list[dict] = []
                for raw_field in fields:
                    if not isinstance(raw_field, dict):
                        filtered_fields.append(raw_field)
                        continue
                    field = deepcopy(raw_field)
                    label_key = _job_section_key(field.get("label"))
                    paired_key = _job_section_key(field.get("paired_image") or field.get("pairedImage"))
                    if label_key == "작업이미지":
                        changed = True
                        continue
                    if paired_key == "작업이미지":
                        field.pop("paired_image", None)
                        field.pop("pairedImage", None)
                        changed = True
                    filtered_fields.append(field)
                section["fields"] = filtered_fields
            normalized_sections.append(section)

        template_id = str(template["_id"])
        if changed:
            await templates.update_one(
                {"_id": template["_id"]},
                {"$set": {"sections": normalized_sections}},
            )
            logger.info("세부 작업 내용 작업 이미지 컬럼 제거: %s", template.get("title"))

        for section_title in section_titles:
            for label in ("작업 이미지", "작업이미지"):
                result = await entries.update_many(
                    {"template_id": template_id, f"data.{section_title}": {"$type": "array"}},
                    {"$unset": {f"data.{section_title}.$[].{label}": ""}},
                )
                if result.modified_count:
                    logger.info(
                        "세부 작업 내용 작업 이미지 데이터 제거: template=%s count=%d",
                        template_id,
                        result.modified_count,
                    )
                result = await entries.update_many(
                    {"template_id": template_id, f"data.{section_title}": {"$type": "object"}},
                    {"$unset": {f"data.{section_title}.{label}": ""}},
                )
                if result.modified_count:
                    logger.info(
                        "세부 작업 내용 작업 이미지 데이터 제거(단일 행): template=%s count=%d",
                        template_id,
                        result.modified_count,
                    )


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


async def migrate_asset_status_default() -> None:
    """상태 필드가 없는 자산에 기본값 '운영'을 채운다 (멱등). 랙 카테고리 제외."""
    db = MongoClientManager.get_db()
    total = 0
    for cat, (col_name, _hist) in MongoClientManager.CATEGORY_COLLECTIONS.items():
        if cat == "랙":
            continue
        r = await db[col_name].update_many(
            {"fields.상태": {"$in": [None, ""]}},  # 없음/null/빈값 모두 포함
            {"$set": {"fields.상태": "운영"}},
        )
        total += r.modified_count
    if total:
        logger.info("자산 상태 기본값 backfill: %d건", total)


async def migrate_rack_asset_type() -> None:
    """기존 랙 문서의 자산유형을 '랙'으로 보정한다 (멱등)."""
    col = MongoClientManager.get_asset_collection("랙")
    result = await col.update_many(
        {"fields.자산유형": {"$ne": "랙"}},
        {"$set": {"fields.자산유형": "랙"}},
    )
    if result.modified_count:
        logger.info("랙 자산유형 보정 완료: %d건", result.modified_count)


async def migrate_disposal_to_status() -> None:
    """기존 disposal_status='O' 자산을 상태='폐기'로 이관하고 disposal_status 필드를 제거한다.
    (멱등, 랙 제외) — migrate_asset_status_default(운영 기본값) 이후에 실행해 폐기가 우선되게 한다.
    """
    db = MongoClientManager.get_db()
    total = 0
    for cat, (col_name, _hist) in MongoClientManager.CATEGORY_COLLECTIONS.items():
        if cat == "랙":
            continue
        r = await db[col_name].update_many(
            {"fields.disposal_status": "O"},
            {"$set": {"fields.상태": "폐기"}, "$unset": {"fields.disposal_status": ""}},
        )
        total += r.modified_count
    if total:
        logger.info("폐기 상태 이관(disposal_status→상태='폐기'): %d건", total)


async def migrate_firewall_contact_names() -> None:
    """방화벽 담당자 메일 항목 중 value 없이 label에 이메일을 그대로 저장해둔
    과거 데이터를, users 컬렉션에서 이메일로 조회해 label=이름/value=이메일로
    분리해준다. 일치하는 회원이 없으면 건드리지 않는다(멱등).
    """
    col = MongoClientManager.get_env_categories_collection()
    doc = await col.find_one({"key": "firewall_notify_emails"})
    if not doc:
        return
    items = doc.get("items", [])
    users_col = MongoClientManager.get_users_collection()
    changed = False
    for item in items:
        if item.get("value"):
            continue
        email = (item.get("label") or "").strip()
        if not email:
            continue
        user = await users_col.find_one({"email": email})
        if user and user.get("full_name"):
            item["label"] = user["full_name"]
            item["value"] = email
            changed = True
    if changed:
        await col.update_one({"_id": doc["_id"]}, {"$set": {"items": items}})
        logger.info("방화벽 담당자 항목 이름/이메일 분리 마이그레이션 완료")


async def migrate_full_rack_placements_to_front() -> None:
    """기존 전·후면 전체 배치를 전면 배치로 변환한다."""
    col = MongoClientManager.get_rack_placements_collection()
    migrated = 0
    async for placement in col.find({"mount_side": "FULL"}, {"start_u": 1, "height_u": 1}):
        start_u = int(placement.get("start_u") or 0)
        height_u = int(placement.get("height_u") or 0)
        occupied_slots = [f"F:{u}" for u in range(start_u, start_u + height_u)]
        await col.update_one(
            {"_id": placement["_id"], "mount_side": "FULL"},
            {
                "$set": {"mount_side": "FRONT", "occupied_slots": occupied_slots},
                "$inc": {"version": 1},
            },
        )
        migrated += 1
    if migrated:
        logger.info("랙 전체 배치 %d건을 전면 배치로 마이그레이션 완료", migrated)


async def run_startup() -> None:
    """lifespan startup에서 호출하는 진입점."""
    await create_indexes()
    await seed_system_menus()
    await seed_system_menu_extras()
    await migrate_inspection_tasks()
    from app.services.monthly_inspection_reports import indexes as report_indexes
    await report_indexes()
    await migrate_pm_report_submenu_access()
    await migrate_guide_submenus()
    await migrate_recurring_issue_submenu()
    await migrate_rack_submenu()
    await migrate_notice_submenu()
    await migrate_remove_deprecated_features()
    await seed_env_categories()
    await migrate_firewall_contact_names()
    await migrate_env_submenu()
    await seed_job_form_templates()
    await migrate_job_test_case_sections()
    await migrate_result_completion_field()
    await migrate_result_work_period_fields()
    await migrate_remove_development_image_field()
    await migrate_remove_result_work_image_field()
    await migrate_remove_work_steps_image_field()
    await migrate_assets()
    await migrate_rack_asset_type()
    await migrate_asset_status_default()
    await migrate_disposal_to_status()
    await migrate_full_rack_placements_to_front()

    from app.db.rack_indexes import create_rack_indexes
    await create_rack_indexes()

    from app.db.pm_indexes import create_pm_indexes
    await create_pm_indexes()
    logger.info("PM 인덱스 생성 완료")

    from app.db.sr_indexes import create_sr_indexes
    await create_sr_indexes()
    logger.info("SR 인덱스 생성 완료")

    from app.db.notification_indexes import create_notification_indexes
    await create_notification_indexes()
    logger.info("알림 인덱스 생성 완료")


async def migrate_inspection_tasks():
    col = MongoClientManager.get_db()['inspection_tasks']
    await col.create_index('project_id')
    await col.create_index('occurrences.month')
    await col.create_index('occurrences.assets.id')
    await col.create_index('occurrences.work_plans.id')
    await col.create_index('work_plan_id', sparse=True)
    menus = MongoClientManager.get_menus_collection()
    # Uploaded measurements and monthly comparisons now live inside resource inspections.
    await menus.update_one(
        {'slug': 'server_check'},
        {'$pull': {'submenus': {'link': {'$in': [
            '/inspection/health-summary', '/inspection/health-compare',
        ]}}}},
    )
    await menus.update_one(
        {'slug': 'server_check', 'submenus.link': {'$ne': '/inspection/health-servers'}},
        {'$push': {'submenus': {'title': '자원 점검', 'icon': 'fa-solid fa-server',
                               'link': '/inspection/health-servers'}}},
    )
    await menus.update_one(
        {'slug': 'server_check', 'submenus.link': '/inspection/health-servers'},
        {'$set': {'submenus.$.title': '자원 점검'}},
    )
    await menus.update_one(
        {'slug': 'server_check', 'submenus': {'$elemMatch': {'link': '/inspection/tasks', 'title': '월별 작업'}}},
        {'$set': {'submenus.$.title': '월간 작업'}},
    )
    await menus.update_one(
        {'slug': 'server_check', 'submenus.link': {'$ne': '/inspection/tasks'}},
        {'$push': {'submenus': {'$each': [{'title': '월간 작업', 'icon': 'fa-solid fa-list-check',
                                          'link': '/inspection/tasks'}], '$position': 0}}},
    )
    await menus.update_one(
        {'slug': 'server_check', 'submenus.link': {'$ne': '/inspection/monthly-reports'}},
        {'$push': {'submenus': {'$each': [{'title': '점검 보고서', 'icon': 'fa-solid fa-file-lines',
                                          'link': '/inspection/monthly-reports'}], '$position': 1}}},
    )

    await menus.update_one(
        {'slug': 'server_check', 'submenus.link': '/inspection/monthly-reports'},
        {'$set': {'submenus.$.title': '점검 보고서'}},
    )
