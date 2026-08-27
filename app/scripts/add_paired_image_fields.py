"""
Migration script: apply paired_image (text+image same-cell display) to
작업계획서(서비스)/작업계획서(서비스 외)/작업결과서 templates.

Changes applied:
  작업계획서(서비스):
    - "개발 내용" 섹션의 "세부 작업 내용" 필드 -> paired_image = "개발이미지"
    - "세부 작업 내용" 섹션의 "세부 작업 내용" 필드 -> paired_image = "작업 이미지"
  작업계획서(서비스 외):
    - "세부 작업 내용" 섹션의 "세부 작업 내용" 필드 -> paired_image = "작업 이미지"
  작업결과서:
    - "작업 결과" 섹션의 images_below 플래그 제거
    - "작업 전" 필드 -> paired_image = "작업 전 사진"
    - "작업 후" 필드 -> paired_image = "작업 후 사진"

Usage:
    cd /workspace
    python -m app.scripts.add_paired_image_fields
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


# (template_title, section_title, text_field_label, image_field_label)
PAIRS = [
    ("작업계획서(서비스)", "개발 내용", "세부 작업 내용", "개발이미지"),
    ("작업계획서(서비스)", "세부 작업 내용", "세부 작업 내용", "작업 이미지"),
    ("작업계획서(서비스 외)", "세부 작업 내용", "세부 작업 내용", "작업 이미지"),
    ("작업결과서", "작업 결과", "작업 전", "작업 전 사진"),
    ("작업결과서", "작업 결과", "작업 후", "작업 후 사진"),
]


async def run() -> None:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    col = db["form_templates"]

    docs: dict[str, dict] = {}
    for template_title, section_title, text_label, image_label in PAIRS:
        doc = docs.get(template_title)
        if doc is None:
            doc = await col.find_one({"title": template_title})
            if not doc:
                print(f"[skip] template not found: {template_title!r}")
                continue
            docs[template_title] = doc

        for sec in doc.get("sections", []):
            if sec.get("title") != section_title:
                continue
            if sec.get("images_below"):
                del sec["images_below"]
                print(f"[ok]   removed images_below on {template_title!r} / {section_title!r}")
            if sec.get("images_inline"):
                del sec["images_inline"]
            for f in sec.get("fields", []):
                if f.get("label") == text_label and f.get("paired_image") != image_label:
                    f["paired_image"] = image_label
                    print(f"[ok]   set paired_image on {template_title!r} / {section_title!r} / {text_label!r} -> {image_label!r}")
            break

    for template_title, doc in docs.items():
        result = await col.update_one({"_id": doc["_id"]}, {"$set": {"sections": doc["sections"]}})
        print(f"[ok]   updated {template_title!r} (modified_count={result.modified_count})")

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(run())
