#!/usr/bin/env python3
"""
Seed script: NCDC-515
당직시간표 - Ye Song Park, 2026-03-23 ~ 2026-03-27, 12:00~13:00 KST

Usage:
    python scripts/seed_watch_ncdc515.py

Requires MONGO_URI and APP_DB_NAME env vars (or app/secret/.env).
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.core.config import settings
    MONGO_URI = settings.MONGO_URI
    DB_NAME = settings.APP_DB_NAME
except Exception:
    MONGO_URI = os.environ["MONGO_URI"]
    DB_NAME = os.environ["APP_DB_NAME"]

from motor.motor_asyncio import AsyncIOMotorClient

ASSIGNEE = "Ye Song Park"
# KST = UTC+9 → 12:00 KST = 03:00 UTC, 13:00 KST = 04:00 UTC
KST_OFFSET = timedelta(hours=9)
START_HOUR_UTC = 3   # 12:00 KST
END_HOUR_UTC = 4     # 13:00 KST

DATES = [
    (2026, 3, 23),
    (2026, 3, 24),
    (2026, 3, 25),
    (2026, 3, 26),
    (2026, 3, 27),
]


async def main() -> None:
    client = AsyncIOMotorClient(MONGO_URI)
    col = client[DB_NAME]["watch_assignments"]
    now = datetime.now(timezone.utc)

    inserted = 0
    skipped = 0

    for y, m, d in DATES:
        start = datetime(y, m, d, START_HOUR_UTC, 0, 0, tzinfo=timezone.utc)
        end = datetime(y, m, d, END_HOUR_UTC, 0, 0, tzinfo=timezone.utc)

        # Skip if already exists (idempotent)
        existing = await col.find_one({
            "assignee": ASSIGNEE,
            "start": start,
            "end": end,
            "is_deleted": {"$ne": True},
        })
        if existing:
            print(f"  [skip] {start.date()} entry already exists")
            skipped += 1
            continue

        doc = {
            "assignee": ASSIGNEE,
            "start": start,
            "end": end,
            "fields": {},
            "created_at": now,
            "created_by": "seed/ncdc-515",
            "updated_at": now,
            "updated_by": "seed/ncdc-515",
            "version": 1,
            "is_deleted": False,
        }
        await col.insert_one(doc)
        print(f"  [ok]   {start.date()} {START_HOUR_UTC:02d}:00–{END_HOUR_UTC:02d}:00 UTC  ({ASSIGNEE})")
        inserted += 1

    client.close()
    print(f"\nDone: {inserted} inserted, {skipped} skipped.")


if __name__ == "__main__":
    asyncio.run(main())
