"""
운영 DB 전용 정리 스크립트.

1. "작업계획서(서비스)" 제목으로 된 문서가 중복 존재하는 상태를 감안해,
   해당 제목의 모든 문서에 대해 "개발 내용" 섹션 fields를 로컬과 동일하게 맞춘다.
2. "작업계획서(서비스)"/"작업계획서(서비스 외)" 두 템플릿 모두, 실제 섹션명이
   "세부 작업 내용"이 아니라 "세부 작업 절차"인 상태이므로, 그 섹션 안의
   "세부 작업 내용" 필드와 "작업 이미지" 필드를 페어링한다.
   "작업 이미지" 필드가 없으면 새로 추가한다.

중복 문서 자체는 삭제하지 않는다 (어느 쪽이 실제 서비스 중인지 불확실하므로
둘 다 동일하게 맞춰서 어느 쪽이 열려도 같은 결과가 나오게만 한다).

Usage:
    cd /workspace
    python -m app.scripts.fix_prod_form_duplicates_and_pairing
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


DEV_CONTENT_FIELDS = [
    {"label": "No.", "type": "text", "required": False},
    {"label": "제목", "type": "text", "required": False},
    {"label": "리스크", "type": "select", "required": False, "options": ["상", "중", "하"]},
    {"label": "세부 작업 내용", "type": "textarea", "required": False, "paired_image": "개발이미지"},
    {"label": "개발이미지", "type": "image", "required": False},
]

STEPS_SECTION_TITLE = "세부 작업 절차"
STEPS_TEXT_LABEL = "세부 작업 내용"
STEPS_IMAGE_LABEL = "작업 이미지"

TEMPLATE_TITLES = ["작업계획서(서비스)", "작업계획서(서비스 외)"]


def fix_steps_section(sec: dict) -> bool:
    """세부 작업 절차 섹션에 작업 이미지 필드를 보장하고 paired_image를 연결한다."""
    fields = sec.get("fields", [])
    changed = False

    if not any(f.get("label") == STEPS_IMAGE_LABEL for f in fields):
        fields.append({"label": STEPS_IMAGE_LABEL, "type": "image", "required": False})
        changed = True

    for f in fields:
        if f.get("label") == STEPS_TEXT_LABEL and f.get("paired_image") != STEPS_IMAGE_LABEL:
            f["paired_image"] = STEPS_IMAGE_LABEL
            changed = True

    if changed:
        sec["fields"] = fields
    return changed


async def run() -> None:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    col = db["form_templates"]

    for template_title in TEMPLATE_TITLES:
        docs = await col.find({"title": template_title}).to_list(length=None)
        if not docs:
            print(f"[skip] template not found: {template_title!r}")
            continue
        if len(docs) > 1:
            print(f"[warn] {template_title!r} 문서가 {len(docs)}개 중복 존재 (id: {[str(d['_id']) for d in docs]}) — 모두 동일하게 업데이트합니다")

        for doc in docs:
            sections = doc.get("sections", [])
            changed = False

            for sec in sections:
                title = sec.get("title")
                if title == "개발 내용" and template_title == "작업계획서(서비스)":
                    if sec.get("fields") != DEV_CONTENT_FIELDS:
                        sec["fields"] = DEV_CONTENT_FIELDS
                        sec["multiple"] = True
                        changed = True
                        print(f"[ok]   {doc['_id']} / '개발 내용' fields 교체")
                elif title == STEPS_SECTION_TITLE:
                    if fix_steps_section(sec):
                        changed = True
                        print(f"[ok]   {doc['_id']} / '{STEPS_SECTION_TITLE}' paired_image 적용")

            if changed:
                result = await col.update_one({"_id": doc["_id"]}, {"$set": {"sections": sections}})
                print(f"[ok]   updated {doc['_id']} (modified_count={result.modified_count})")
            else:
                print(f"[noop] {doc['_id']} 변경 없음")

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(run())
