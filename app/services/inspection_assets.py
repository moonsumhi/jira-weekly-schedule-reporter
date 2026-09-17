"""Inspection task targets across the registered asset categories."""
import asyncio
import re

from fastapi import HTTPException

from app.db.mongo import MongoClientManager as M
from app.utils.mongo import oid


def asset_snapshot(doc, category='서버'):
    fields = doc.get('fields') or {}
    name = next((fields[key] for key in ('자산명', '서버명', '장비명', '시스템명', '제품명', '랙명')
                 if fields.get(key)), None)
    return {'id': str(doc['_id']), 'category': category, 'name': doc.get('name') or str(name or doc.get('asset_no') or ''),
            'ip': doc.get('ip') or '', 'asset_name': str(name or doc.get('asset_no') or ''),
            'status': str(fields.get('상태') or ''), 'is_deleted': bool(doc.get('is_deleted'))}


async def asset_documents(query, category=None, limit=None):
    if category is not None and category not in M.CATEGORY_COLLECTIONS:
        raise HTTPException(422, '자산 유형을 확인해 주세요.')

    async def read(cat):
        cursor = M.get_asset_collection(cat).find(query).sort([('name', 1), ('_id', 1)])
        if limit is not None:
            cursor = cursor.limit(limit)
        return [(cat, doc) for doc in await cursor.to_list(limit)]

    groups = await asyncio.gather(*(read(cat) for cat in ([category] if category else M.CATEGORY_COLLECTIONS)))
    return [item for group in groups for item in group]


async def asset_map(ids, *, include_deleted=True, category=None):
    if not ids:
        return {}
    query = {'_id': {'$in': [oid(value) for value in ids]}}
    if not include_deleted:
        query['is_deleted'] = {'$ne': True}
    result = {}
    for cat, doc in await asset_documents(query, category):
        identifier = str(doc['_id'])
        if identifier in result:
            raise HTTPException(422, '여러 자산 유형에 중복된 자산 ID가 있습니다. 자산 정보를 확인해 주세요.')
        result[identifier] = asset_snapshot(doc, cat)
    return result


async def search_assets(search='', ids=(), category=None):
    if ids:
        found = await asset_map(ids, include_deleted=False, category=category)
        return [found[value] for value in ids if value in found]
    query = {'is_deleted': {'$ne': True}}
    if search.strip():
        pattern = {'$regex': re.escape(search.strip()), '$options': 'i'}
        query['$or'] = [{field: pattern} for field in (
            'name', 'ip', 'asset_no', 'asset_id', 'fields.자산명', 'fields.서버명', 'fields.장비명',
            'fields.시스템명', 'fields.제품명', 'fields.랙명')]
    rows = [asset_snapshot(doc, cat) for cat, doc in await asset_documents(query, category, limit=100)]
    return sorted(rows, key=lambda row: (row['name'], row['category'], row['id']))[:100]
