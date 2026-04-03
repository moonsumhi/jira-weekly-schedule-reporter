"""
Migration script: update Job form templates.

Changes applied:
  작업계획서(서비스) and 작업계획서(서비스 외):
    - "세부작업 절차" section → multiple=true
    - "사전 작업" section     → multiple=true

  작업결과서:
    - "작업 실적" section     → removed
    - "작업 대상" section     → inserted (multiple=true) if missing; made multiple if present
    - "작업 내용" section     → inserted (multiple=true) if missing; made multiple if present

Note: "항목 추가" section is removed by remove_item_section.py (TASK-NCDC-618).

Usage:
    cd /workspace
    python -m app.scripts.update_job_templates
"""
from __future__ import annotations

import asyncio

from motor.motor_asyncio import AsyncIOMotorClient

# ── load settings the same way the app does ──────────────────────────────────
try:
    from app.core.config import settings
    MONGO_URI = settings.MONGO_URI
    DB_NAME = settings.APP_DB_NAME
except Exception as exc:
    print(f"[warn] Could not load settings: {exc}")
    import os
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("APP_DB_NAME", "optool")


PLAN_TITLES = ["작업계획서(서비스)", "작업계획서(서비스 외)"]
PLAN_MULTIPLE_SECTIONS = {"세부작업 절차", "사전 작업"}

RESULT_TITLE = "작업결과서"
RESULT_REMOVE_SECTIONS = {"작업 실적"}
RESULT_MULTIPLE_SECTIONS = {"작업 대상", "작업 내용"}

# New sections to insert into 작업결과서 if missing.
# Each entry: (section_title, insert_after_title, section_definition)
# insert_after_title=None means append at end.
RESULT_NEW_SECTIONS = [
    (
        "작업 대상",
        "기본 정보",
        {
            "title": "작업 대상",
            "multiple": True,
            "fields": [
                {
                    "label": "작업 대상",
                    "type": "textarea",
                    "required": False,
                    "placeholder": "작업 대상을 입력하세요",
                },
            ],
        },
    ),
    (
        "작업 내용",
        "작업 대상",
        {
            "title": "작업 내용",
            "multiple": True,
            "fields": [
                {
                    "label": "작업 내용",
                    "type": "textarea",
                    "required": False,
                    "placeholder": "작업 내용을 입력하세요",
                },
            ],
        },
    ),
]


def _update_plan_sections(sections: list) -> list:
    """Mark 세부작업 절차 / 사전 작업 as multiple=true."""
    updated = []
    for section in sections:
        if not isinstance(section, dict):
            updated.append(section)
            continue
        if section.get("title") in PLAN_MULTIPLE_SECTIONS:
            section = {**section, "multiple": True}
        updated.append(section)
    return updated


def _update_result_sections(sections: list) -> list:
    """
    - Remove 작업 실적
    - Mark 작업 대상 / 작업 내용 as multiple=true (if present)
    - Insert 작업 대상 / 작업 내용 if they are missing
    """
    # First pass: remove deleted sections and update existing ones
    updated = []
    for section in sections:
        if not isinstance(section, dict):
            updated.append(section)
            continue

        title = section.get("title", "")

        if title in RESULT_REMOVE_SECTIONS:
            # Drop this section
            continue

        if title in RESULT_MULTIPLE_SECTIONS:
            section = {**section, "multiple": True}

        updated.append(section)

    # Second pass: insert missing sections at the right positions
    existing_titles = {s.get("title") for s in updated if isinstance(s, dict)}

    for section_title, insert_after, section_def in RESULT_NEW_SECTIONS:
        if section_title in existing_titles:
            continue  # already present

        # Find insertion position
        insert_idx = None
        if insert_after is not None:
            for i, s in enumerate(updated):
                if isinstance(s, dict) and s.get("title") == insert_after:
                    insert_idx = i + 1
                    break

        if insert_idx is not None:
            updated.insert(insert_idx, section_def)
        else:
            updated.append(section_def)

        existing_titles.add(section_title)

    return updated


async def run() -> None:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    col = db["form_templates"]

    # ── Work plan templates ───────────────────────────────────────────────
    for title in PLAN_TITLES:
        doc = await col.find_one({"title": title})
        if not doc:
            print(f"[skip] template not found: {title!r}")
            continue

        new_sections = _update_plan_sections(doc.get("sections", []))
        result = await col.update_one(
            {"_id": doc["_id"]},
            {"$set": {"sections": new_sections}},
        )
        if result.modified_count:
            print(f"[ok]   updated: {title!r}")
        else:
            print(f"[noop] no changes: {title!r}")

    # ── Work result template ──────────────────────────────────────────────
    doc = await col.find_one({"title": RESULT_TITLE})
    if not doc:
        print(f"[skip] template not found: {RESULT_TITLE!r}")
    else:
        new_sections = _update_result_sections(doc.get("sections", []))
        result = await col.update_one(
            {"_id": doc["_id"]},
            {"$set": {"sections": new_sections}},
        )
        if result.modified_count:
            print(f"[ok]   updated: {RESULT_TITLE!r}")
        else:
            print(f"[noop] no changes: {RESULT_TITLE!r}")

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(run())
