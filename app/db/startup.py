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
    {"slug": "account",  "title": "계정 설정",   "icon": "fa-solid fa-user-gear",  "sort_order": 5},
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

    # 구 SR 개별 메뉴 제거 (sr 상위 메뉴로 통합)
    for old_slug in ("sr-new", "sr-my", "sr-manage"):
        await menus_col.delete_one({"slug": old_slug})



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
    await migrate_assets()

    from app.db.pm_indexes import create_pm_indexes
    await create_pm_indexes()
    logger.info("PM 인덱스 생성 완료")

    from app.db.sr_indexes import create_sr_indexes
    await create_sr_indexes()
    logger.info("SR 인덱스 생성 완료")
