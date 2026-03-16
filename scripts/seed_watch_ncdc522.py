"""
Seed script: TASK-NCDC-522
당직시간표에 다음주 월~금 (2026-03-23~27) 12:00~13:00 KST 당직자 박예송 추가
"""
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

MONGO_URI = "mongodb://jira_user:nccrekr1!@mongo:27017/?authSource=backoffice"
DB_NAME = "backoffice"
COLLECTION = "watch_assignments"

# KST is UTC+9, so 12:00 KST = 03:00 UTC
DATES = [
    (2026, 3, 23),  # Monday
    (2026, 3, 24),  # Tuesday
    (2026, 3, 25),  # Wednesday
    (2026, 3, 26),  # Thursday
    (2026, 3, 27),  # Friday
]

ASSIGNEE = "박예송"
ACTOR_EMAIL = "seed@system"

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
col = client[DB_NAME][COLLECTION]

now = datetime.now(timezone.utc)

inserted = 0
skipped = 0

for year, month, day in DATES:
    start_utc = datetime(year, month, day, 3, 0, 0, tzinfo=timezone.utc)   # 12:00 KST
    end_utc   = datetime(year, month, day, 4, 0, 0, tzinfo=timezone.utc)   # 13:00 KST

    # Check for existing (non-deleted) overlap for this assignee
    existing = col.find_one({
        "is_deleted": {"$ne": True},
        "assignee": ASSIGNEE,
        "start": {"$lt": end_utc},
        "end":   {"$gt": start_utc},
    })

    if existing:
        print(f"[SKIP] {year}-{month:02d}-{day:02d}: overlap exists ({existing['_id']})")
        skipped += 1
        continue

    doc = {
        "assignee": ASSIGNEE,
        "start": start_utc.replace(tzinfo=None),   # MongoDB stores naive UTC
        "end":   end_utc.replace(tzinfo=None),
        "fields": {},
        "created_at": now.replace(tzinfo=None),
        "created_by": ACTOR_EMAIL,
        "updated_at": now.replace(tzinfo=None),
        "updated_by": ACTOR_EMAIL,
        "version": 1,
        "is_deleted": False,
    }

    res = col.insert_one(doc)
    print(f"[OK]   {year}-{month:02d}-{day:02d} 12:00-13:00 KST → inserted {res.inserted_id}")
    inserted += 1

client.close()
print(f"\nDone: {inserted} inserted, {skipped} skipped.")
