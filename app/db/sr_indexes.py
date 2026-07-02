"""SR 컬렉션 MongoDB 인덱스 초기화."""
from app.db.mongo import MongoClientManager


async def create_sr_indexes() -> None:
    db = MongoClientManager.get_db()

    sr = db[MongoClientManager.SERVICE_REQUESTS]
    await sr.create_index("sr_no", unique=True)
    await sr.create_index("requester_id")
    await sr.create_index("status")
    await sr.create_index("assignee_id")
    await sr.create_index("priority")
    await sr.create_index("is_urgent")
    await sr.create_index("created_at")
    await sr.create_index("desired_due_date")
    await sr.create_index("planned_due_date")
    await sr.create_index("deleted_at")
    await sr.create_index([("status", 1), ("deleted_at", 1)])
    await sr.create_index([("requester_id", 1), ("deleted_at", 1)])

    comments = db[MongoClientManager.SR_COMMENTS]
    await comments.create_index("sr_id")
    await comments.create_index([("sr_id", 1), ("created_at", 1)])

    histories = db[MongoClientManager.SR_HISTORIES]
    await histories.create_index("sr_id")
    await histories.create_index("changed_at")

    status_hist = db[MongoClientManager.SR_STATUS_HISTORIES]
    await status_hist.create_index("sr_id")
    await status_hist.create_index("changed_at")

    due_hist = db[MongoClientManager.SR_DUE_DATE_HISTORIES]
    await due_hist.create_index("sr_id")
    await due_hist.create_index("changed_at")

    # sr_counters의 _id는 MongoDB가 자동으로 unique 보장하므로 별도 인덱스 불필요
