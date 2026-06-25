"""
작업결과서 템플릿의 '작업 결과', '작업 내용' 섹션에 '작업 이미지' (image 타입) 필드 추가.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

IMAGE_FIELD = {"label": "작업 이미지", "type": "image", "required": False}
TARGET_TEMPLATE = "작업결과서"
TARGET_SECTIONS = ["작업 결과", "작업 내용"]


async def main():
    client = AsyncIOMotorClient('mongodb://jira_user:nccrekr1!@mongo:27017/?authSource=backoffice')
    db = client['backoffice']
    templates = await db['form_templates'].find({'is_deleted': {'$ne': True}}).to_list(100)

    updated = 0
    for t in templates:
        if t.get('title') != TARGET_TEMPLATE:
            continue

        sections = t.get('sections', [])
        changed = False
        for sec in sections:
            if sec.get('title') in TARGET_SECTIONS and sec.get('multiple'):
                fields = sec.get('fields', [])
                labels = [f.get('label') for f in fields]
                if IMAGE_FIELD['label'] not in labels:
                    fields.append(IMAGE_FIELD)
                    sec['fields'] = fields
                    changed = True
                    print(f"  [{t.get('title')}] '{sec.get('title')}' 섹션에 필드 추가")

        if changed:
            await db['form_templates'].update_one(
                {'_id': t['_id']},
                {'$set': {'sections': sections}}
            )
            updated += 1

    print(f"\n완료: {updated}개 템플릿 업데이트")


asyncio.run(main())
