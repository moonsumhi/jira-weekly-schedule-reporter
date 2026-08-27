"""
운영 DB의 "개발 내용"(작업계획서(서비스))/"작업 결과"(작업결과서) 섹션이
UI 편집 등으로 로컬/GitHub 소스와 다르게 진화한 상태를 로컬과 동일한 필드
구조로 강제 교체한다.

주의: 이 섹션에 기존에 제출된 데이터가 있다면, 필드명이 바뀌면서 화면에
안 보이게 될 수 있다 (DB에서 삭제되지는 않음).

변경 내용:
  작업계획서(서비스) / "개발 내용" 섹션 fields ->
    No., 제목, 리스크, 세부 작업 내용(paired_image=개발이미지), 개발이미지
  작업결과서 / "작업 결과" 섹션 fields ->
    작업 전(paired_image=작업 전 사진), 작업 후(paired_image=작업 후 사진),
    작업 전 사진, 작업 후 사진

Usage:
    cd /workspace
    python -m app.scripts.replace_dev_content_and_result_sections
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


# (template_title, section_title, new_fields)
REPLACEMENTS = [
    (
        "작업계획서(서비스)",
        "개발 내용",
        [
            {"label": "No.", "type": "text", "required": False},
            {"label": "제목", "type": "text", "required": False},
            {"label": "리스크", "type": "select", "required": False, "options": ["상", "중", "하"]},
            {"label": "세부 작업 내용", "type": "textarea", "required": False, "paired_image": "개발이미지"},
            {"label": "개발이미지", "type": "image", "required": False},
        ],
    ),
    (
        "작업결과서",
        "작업 결과",
        [
            {"label": "작업 전", "type": "textarea", "required": False, "paired_image": "작업 전 사진"},
            {"label": "작업 후", "type": "textarea", "required": False, "paired_image": "작업 후 사진"},
            {"label": "작업 전 사진", "type": "image", "required": False},
            {"label": "작업 후 사진", "type": "image", "required": False},
        ],
    ),
]


async def run() -> None:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    col = db["form_templates"]

    for template_title, section_title, new_fields in REPLACEMENTS:
        doc = await col.find_one({"title": template_title})
        if not doc:
            print(f"[skip] template not found: {template_title!r}")
            continue

        sections = doc.get("sections", [])
        found = False
        for sec in sections:
            if sec.get("title") == section_title:
                sec["fields"] = new_fields
                sec["multiple"] = True
                sec.pop("images_below", None)
                sec.pop("images_inline", None)
                found = True
                break

        if not found:
            print(f"[skip] section not found: {template_title!r} / {section_title!r}")
            continue

        result = await col.update_one({"_id": doc["_id"]}, {"$set": {"sections": sections}})
        print(f"[ok]   replaced fields on {template_title!r} / {section_title!r} (modified_count={result.modified_count})")

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(run())
