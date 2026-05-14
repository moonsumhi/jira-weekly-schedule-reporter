"""
서버/네트워크/DBMS 자산에 잘못 저장된 '수량' 필드를 제거하는 스크립트.
'정보보호시스템' 자산은 그대로 유지.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.APP_DB_NAME]
    col = db["assets_servers"]

    # 정보보호시스템이 아닌 자산 중 fields.수량이 존재하는 것
    query = {
        "fields.수량": {"$exists": True},
        "fields.자산유형": {"$nin": ["정보보호시스템"]},
    }

    # 먼저 대상 확인
    targets = await col.find(query, {"_id": 1, "name": 1, "fields.자산유형": 1, "fields.수량": 1}).to_list(None)
    if not targets:
        print("정리할 대상이 없습니다.")
        client.close()
        return

    print(f"정리 대상 {len(targets)}건:")
    for t in targets:
        asset_type = t.get("fields", {}).get("자산유형", "(서버)")
        qty = t.get("fields", {}).get("수량")
        print(f"  - {t.get('name')} [{asset_type}]  수량={qty}")

    confirm = input("\n위 항목에서 '수량' 필드를 삭제합니다. 계속할까요? (y/N): ").strip().lower()
    if confirm != "y":
        print("취소했습니다.")
        client.close()
        return

    result = await col.update_many(query, {"$unset": {"fields.수량": ""}})
    print(f"\n완료: {result.modified_count}건 수정.")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
