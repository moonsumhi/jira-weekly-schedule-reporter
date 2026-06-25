"""
세부 작업 절차 섹션에 '작업 이미지' (image 타입) 필드 추가.
multiple=True 인 세부 작업 절차 섹션에만 적용.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

IMAGE_FIELD = {"label": "작업 이미지", "type": "image", "required": False}
TARGET_SECTION = "세부 작업 절차"


async def main():
    client = AsyncIOMotorClient('mongodb://jira_user:nccrekr1!@mongo:27017/?authSource=backoffice')
    db = client['backoffice']
    templates = await db['form_templates'].find({'is_deleted': {'$ne': True}}).to_list(100)

    updated = 0
    for t in templates:
        sections = t.get('sections', [])
        changed = False
        for sec in sections:
            if sec.get('title') == TARGET_SECTION and sec.get('multiple'):
                fields = sec.get('fields', [])
                labels = [f.get('label') for f in fields]
                if IMAGE_FIELD['label'] not in labels:
                    fields.append(IMAGE_FIELD)
                    sec['fields'] = fields
                    changed = True
                    print(f"  [{t.get('title')}] '{TARGET_SECTION}' 섹션에 필드 추가")

        if changed:
            await db['form_templates'].update_one(
                {'_id': t['_id']},
                {'$set': {'sections': sections}}
            )
            updated += 1

    print(f"\n완료: {updated}개 템플릿 업데이트")


asyncio.run(main())
