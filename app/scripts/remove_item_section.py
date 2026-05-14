"""
Migration script: remove "항목 추가" section from 작업결과서 template.

Changes applied:
  작업결과서:
    - "항목 추가" section → removed

Usage:
    cd /workspace
    python -m app.scripts.remove_item_section
"""
from __future__ import annotations

import asyncio

from motor.motor_asyncio import AsyncIOMotorClient

try:
    from app.core.config import settings
    MONGO_URI = settings.MONGO_URI
    DB_NAME = settings.APP_DB_NAME
except Exception as exc:
    print(f"[warn] Could not load settings: {exc}")
    import os
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("APP_DB_NAME", "optool")


RESULT_TITLE = "작업결과서"
REMOVE_SECTION = "항목 추가"


async def run() -> None:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    col = db["form_templates"]

    doc = await col.find_one({"title": RESULT_TITLE})
    if not doc:
        print(f"[skip] template not found: {RESULT_TITLE!r}")
        client.close()
        return

    sections = doc.get("sections", [])
    new_sections = [
        s for s in sections
        if not (isinstance(s, dict) and s.get("title") == REMOVE_SECTION)
    ]

    if len(new_sections) == len(sections):
        print(f"[noop] section {REMOVE_SECTION!r} not found in {RESULT_TITLE!r}")
    else:
        result = await col.update_one(
            {"_id": doc["_id"]},
            {"$set": {"sections": new_sections}},
        )
        if result.modified_count:
            print(f"[ok]   removed {REMOVE_SECTION!r} from {RESULT_TITLE!r}")
        else:
            print(f"[noop] no changes: {RESULT_TITLE!r}")

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(run())
