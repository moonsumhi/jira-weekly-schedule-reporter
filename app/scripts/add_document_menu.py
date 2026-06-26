"""문서 관리 메뉴를 DB에 추가하는 스크립트."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
APP_DB_NAME = os.environ.get("APP_DB_NAME", "jira_reporter")


async def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[APP_DB_NAME]

    existing = await db["menus"].find_one({"slug": "document"})
    if existing:
        print("문서 관리 메뉴가 이미 존재합니다.")
        client.close()
        return

    # 기존 메뉴 중 최대 sortOrder 확인
    last = await db["menus"].find_one(sort=[("sortOrder", -1)])
    sort_order = (last.get("sortOrder", 0) + 1) if last else 10

    doc = {
        "title": "문서 관리",
        "slug": "document",
        "icon": "fa-solid fa-folder-open",
        "isVisible": True,
        "sortOrder": sort_order,
        "subOrder": None,
        "subIcons": {},
    }
    result = await db["menus"].insert_one(doc)
    print(f"문서 관리 메뉴 추가 완료: {result.inserted_id}")
    client.close()


asyncio.run(main())
