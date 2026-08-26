"""
Migration script for 작업계획서(서비스) template:
  1. Revert the earlier mistaken "개발 이미지" field added inside "세부 작업 내용".
  2. Insert a new "개발 내용" section (No./제목/리스크/세부 작업 내용/개발이미지),
     positioned right after "검토/서명" and before "세부 작업 내용".

Usage:
    cd /workspace
    python -m app.scripts.add_dev_content_section
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


TEMPLATE_TITLE = "작업계획서(서비스)"
STEPS_SECTION = "세부 작업 내용"
REVERT_FIELD = "개발 이미지"
INSERT_AFTER_SECTION = "검토/서명"

NEW_SECTION = {
    "title": "개발 내용",
    "multiple": True,
    "fields": [
        {"label": "제목", "type": "text", "required": False},
        {"label": "리스크", "type": "select", "required": False, "options": ["상", "중", "하"]},
        {"label": "세부 작업 내용", "type": "textarea", "required": False},
        {"label": "개발이미지", "type": "image", "required": False},
    ],
}


async def run() -> None:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    col = db["form_templates"]

    doc = await col.find_one({"title": TEMPLATE_TITLE})
    if not doc:
        print(f"[skip] template not found: {TEMPLATE_TITLE!r}")
        client.close()
        return

    sections = doc.get("sections", [])
    changed = False

    # 1) 되돌리기: "세부 작업 내용" 섹션에서 "개발 이미지" 필드 제거
    for sec in sections:
        if sec.get("title") == STEPS_SECTION and sec.get("multiple"):
            fields = sec.get("fields", [])
            new_fields = [f for f in fields if f.get("label") != REVERT_FIELD]
            if len(new_fields) != len(fields):
                sec["fields"] = new_fields
                changed = True
                print(f"[ok]   removed {REVERT_FIELD!r} from {STEPS_SECTION!r}")
            break

    # 2) "개발 내용" 섹션 삽입 (없을 때만)
    if any(s.get("title") == NEW_SECTION["title"] for s in sections):
        print(f"[noop] section {NEW_SECTION['title']!r} already present")
    else:
        idx = next((i for i, s in enumerate(sections) if s.get("title") == INSERT_AFTER_SECTION), len(sections) - 1)
        sections.insert(idx + 1, NEW_SECTION)
        changed = True
        print(f"[ok]   inserted section {NEW_SECTION['title']!r} after {INSERT_AFTER_SECTION!r}")

    if changed:
        result = await col.update_one({"_id": doc["_id"]}, {"$set": {"sections": sections}})
        print(f"[ok]   updated {TEMPLATE_TITLE!r} (modified_count={result.modified_count})")
    else:
        print("[noop] no changes needed")

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(run())
