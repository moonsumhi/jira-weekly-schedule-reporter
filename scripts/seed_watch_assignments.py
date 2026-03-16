"""
Seed script: 당직 스케줄 등록
오늘(2026-03-16)부터 금요일(2026-03-20)까지 12:00~13:00 KST, 당직자: 문현진
"""
from datetime import datetime, timezone, timedelta
import pymongo

MONGO_URI = "mongodb://jira_user:nccrekr1!@mongo:27017/?authSource=backoffice"
DB_NAME = "backoffice"
COLLECTION = "watch_assignments"

KST_OFFSET = timedelta(hours=9)

# Today is 2026-03-16 (Monday), Friday is 2026-03-20
dates = [
    (2026, 3, 16),  # Mon
    (2026, 3, 17),  # Tue
    (2026, 3, 18),  # Wed
    (2026, 3, 19),  # Thu
    (2026, 3, 20),  # Fri
]

now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

client = pymongo.MongoClient(MONGO_URI)
col = client[DB_NAME][COLLECTION]

for year, month, day in dates:
    # KST 12:00 → UTC 03:00
    start_utc = datetime(year, month, day, 3, 0, 0)   # 12:00 KST
    end_utc   = datetime(year, month, day, 4, 0, 0)   # 13:00 KST

    # Check for existing (non-deleted) overlapping assignment for same assignee
    existing = col.find_one({
        "assignee": "문현진",
        "is_deleted": {"$ne": True},
        "start": {"$lt": end_utc},
        "end": {"$gt": start_utc},
    })
    if existing:
        print(f"SKIP {year}-{month:02d}-{day:02d}: overlap exists ({existing['_id']})")
        continue

    doc = {
        "assignee": "문현진",
        "start": start_utc,
        "end": end_utc,
        "fields": {},
        "created_at": now_utc,
        "created_by": "pilot@system",
        "updated_at": now_utc,
        "updated_by": "pilot@system",
        "version": 1,
        "is_deleted": False,
    }
    result = col.insert_one(doc)
    print(f"INSERT {year}-{month:02d}-{day:02d} 12:00~13:00 KST → _id={result.inserted_id}")

client.close()
print("Done.")
