import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient('mongodb://jira_user:nccrekr1!@mongo:27017/?authSource=backoffice')
    db = client['backoffice']
    templates = await db['form_templates'].find({'is_deleted': {'$ne': True}}).to_list(100)
    for t in templates:
        print('ID:', t['_id'], '| Title:', t.get('title'))
        for sec in t.get('sections', []):
            fields = [(f.get('label') or '') + '(' + (f.get('type') or '') + ')' for f in sec.get('fields', [])]
            print('  section:', sec.get('title'), '| multiple:', sec.get('multiple'), '| fields:', fields)

asyncio.run(main())
