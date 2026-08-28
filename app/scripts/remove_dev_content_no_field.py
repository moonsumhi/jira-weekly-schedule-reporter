"""
"작업계획서(서비스)" / "개발 내용" 섹션에 남아있는 중복 "No." 필드를 제거한다.

배경: "개발 내용" 섹션은 이미 모든 multiple 섹션 테이블에 자동으로 붙는
행 번호 컬럼(1, 2, 3...)이 있어서, 필드로 또 "No."를 넣으면 중복이었다.
로컬 시드 소스(app/db/startup.py)에서는 이미 빠졌지만, 예전에 운영/개발서버를
동기화하는 데 썼던 fix_prod_form_duplicates_and_pairing.py /
replace_dev_content_and_result_sections.py 두 스크립트에 "No."가 하드코딩되어
남아있었던 탓에, 그 스크립트로 이미 동기화된 서버(dopsbackofficedev 등)에는
"No." 필드가 여전히 남아있을 수 있다. 이 스크립트로 정리한다.

Usage (컨테이너 안에서 직접 실행할 수 있는 서버):
    cd /workspace
    python -m app.scripts.remove_dev_content_no_field

Usage (SSH로만 접근 가능하고 파일 전송이 번거로운 서버 — base64 stdin pipe):
    로컬 PowerShell에서:
        $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("app/scripts/remove_dev_content_no_field.py"))
        $b64 | Set-Clipboard   # 또는 그대로 복사

    대상 서버 SSH 세션에서 (jira-backend 컨테이너 이름은 서버마다 docker-compose.yml 기준으로 동일):
        echo '<위에서 복사한 base64 문자열>' | base64 -d | docker exec -i jira-backend python -
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
SECTION_TITLE = "개발 내용"
REMOVE_LABEL = "No."


async def run() -> None:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    col = db["form_templates"]

    docs = await col.find({"title": TEMPLATE_TITLE}).to_list(length=None)
    print(f"[info] {TEMPLATE_TITLE!r} 문서 개수: {len(docs)}")
    if len(docs) > 1:
        print(f"[warn] 문서가 {len(docs)}개 중복 존재 — 모두 동일하게 정리합니다")

    for doc in docs:
        sections = doc.get("sections", [])
        changed = False
        for sec in sections:
            if sec.get("title") != SECTION_TITLE:
                continue
            fields = sec.get("fields", [])
            new_fields = [f for f in fields if f.get("label") != REMOVE_LABEL]
            if len(new_fields) != len(fields):
                sec["fields"] = new_fields
                changed = True
                print(f"[ok]   {doc['_id']}: {REMOVE_LABEL!r} 필드 제거 "
                      f"({[f.get('label') for f in fields]} -> {[f.get('label') for f in new_fields]})")
            else:
                print(f"[noop] {doc['_id']}: {REMOVE_LABEL!r} 필드 없음, 변경 불필요")

        if changed:
            result = await col.update_one({"_id": doc["_id"]}, {"$set": {"sections": sections}})
            print(f"[ok]   updated {doc['_id']} (modified_count={result.modified_count})")

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(run())
