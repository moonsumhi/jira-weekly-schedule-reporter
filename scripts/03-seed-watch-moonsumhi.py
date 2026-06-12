"""
Seed script: Add watch assignments for 문수미
Period: 2026-03-16 ~ 2026-03-27 (오늘부터 다음주 금요일까지)
Time:   11:00 ~ 12:00 KST (02:00 ~ 03:00 UTC)
"""

import sys
from datetime import datetime, timezone, timedelta

try:
    import pymongo
except ImportError:
    print("pymongo not found, trying motor...")
    sys.exit(1)

MONGO_URI = "mongodb://jira_user:nccrekr1!@mongo:27017/?authSource=backoffice"
DB_NAME = "backoffice"
COLLECTION = "watch_assignments"

ASSIGNEE = "문수미"
CREATED_BY = "system"

# KST is UTC+9, so 11:00 KST = 02:00 UTC
START_HOUR_UTC = 2   # 11:00 KST
END_HOUR_UTC = 3     # 12:00 KST

# Date range: 2026-03-16 to 2026-03-27 inclusive
start_date = datetime(2026, 3, 16, tzinfo=timezone.utc)
end_date = datetime(2026, 3, 27, tzinfo=timezone.utc)


def generate_dates():
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def main():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    col = db[COLLECTION]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    inserted = 0
    skipped = 0

    for date in generate_dates():
        slot_start = date.replace(hour=START_HOUR_UTC, minute=0, second=0, microsecond=0, tzinfo=None)
        slot_end = date.replace(hour=END_HOUR_UTC, minute=0, second=0, microsecond=0, tzinfo=None)

        # Check for existing assignment (avoid duplicates)
        existing = col.find_one({
            "assignee": ASSIGNEE,
            "start": slot_start,
            "end": slot_end,
            "is_deleted": {"$ne": True},
        })
        if existing:
            print(f"  SKIP {date.strftime('%Y-%m-%d')} — already exists")
            skipped += 1
            continue

        doc = {
            "assignee": ASSIGNEE,
            "start": slot_start,
            "end": slot_end,
            "fields": {},
            "created_at": now,
            "created_by": CREATED_BY,
            "updated_at": now,
            "updated_by": CREATED_BY,
            "version": 1,
            "is_deleted": False,
        }
        col.insert_one(doc)
        print(f"  INSERT {date.strftime('%Y-%m-%d')} 11:00-12:00 KST → {slot_start} - {slot_end} UTC")
        inserted += 1

    client.close()
    print(f"\nDone. Inserted: {inserted}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
