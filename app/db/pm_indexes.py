"""PM 컬렉션 MongoDB 인덱스 초기화."""
from app.db.mongo import MongoClientManager


async def create_pm_indexes() -> None:
    db = MongoClientManager.get_db()

    await db[MongoClientManager.PM_ORGANIZATIONS].create_index("slug", unique=True)

    await db[MongoClientManager.PM_ORG_MEMBERS].create_index(
        [("org_id", 1), ("user_id", 1)], unique=True
    )
    await db[MongoClientManager.PM_ORG_MEMBERS].create_index("user_id")

    await db[MongoClientManager.PM_PROJECTS].create_index(
        [("org_id", 1), ("key", 1)], unique=True
    )
    await db[MongoClientManager.PM_PROJECTS].create_index("org_id")

    await db[MongoClientManager.PM_PROJECT_MEMBERS].create_index(
        [("project_id", 1), ("user_id", 1)], unique=True
    )
    await db[MongoClientManager.PM_PROJECT_MEMBERS].create_index("user_id")

    await db[MongoClientManager.PM_ISSUES].create_index(
        [("project_id", 1), ("number", 1)], unique=True
    )
    await db[MongoClientManager.PM_ISSUES].create_index([("project_id", 1), ("status", 1)])
    await db[MongoClientManager.PM_ISSUES].create_index("assignee_id")
    await db[MongoClientManager.PM_ISSUES].create_index("sprint_id")

    await db[MongoClientManager.PM_SPRINTS].create_index("project_id")

    await db[MongoClientManager.PM_LABELS].create_index(
        [("project_id", 1), ("name", 1)], unique=True
    )

    await db[MongoClientManager.PM_ISSUE_COMMENTS].create_index("issue_id")
    await db[MongoClientManager.PM_ISSUE_HISTORY].create_index("issue_id")
