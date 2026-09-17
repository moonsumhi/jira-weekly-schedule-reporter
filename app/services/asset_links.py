"""Shared server asset selection and minimal snapshots for work documents and issues."""
import re

from fastapi import HTTPException

from app.db.mongo import MongoClientManager as M
from app.utils.mongo import oid


def asset_info(doc):
    return {'id': str(doc['_id']), 'name': doc.get('name', ''), 'ip': doc.get('ip', ''),
            'asset_name': str((doc.get('fields') or {}).get('서버명') or ''), 'is_deleted': bool(doc.get('is_deleted'))}


async def selected_assets(asset_ids, previous=None):
    old = {a['id']: a for a in (previous or {}).get('linked_assets', [])}
    docs = await M.get_assets_servers_collection().find({'_id': {'$in': [oid(i) for i in asset_ids]}}).to_list(100)
    by_id = {str(doc['_id']): doc for doc in docs}
    result = []
    for asset_id in asset_ids:
        doc = by_id.get(asset_id)
        if not doc or doc.get('is_deleted'):
            # 기존 삭제된 자산 연결은 유지할 수 있지만 새로 연결하지는 않는다.
            if asset_id not in old:
                raise HTTPException(422, '선택한 서버가 삭제되었거나 존재하지 않습니다. 다시 선택해 주세요.')
            result.append({**old[asset_id], 'is_deleted': True})
        else:
            if ((doc.get('fields') or {}).get('자산유형') or '서버') != '서버':
                raise HTTPException(422, '서버 자산만 연결할 수 있습니다.')
            result.append(asset_info(doc))
    return result


async def hydrate(entries):
    ids = {a['id'] for entry in entries for a in entry.get('linked_assets', [])}
    if not ids:
        return
    docs = await M.get_assets_servers_collection().find({'_id': {'$in': [oid(i) for i in ids]}}).to_list(None)
    current = {str(doc['_id']): asset_info(doc) for doc in docs}
    for entry in entries:
        entry['linked_assets'] = [current.get(a['id'], {**a, 'is_deleted': True}) for a in entry.get('linked_assets', [])]


async def search_assets(search):
    query = {'is_deleted': {'$ne': True}, 'fields.자산유형': {'$in': ['서버', None, '']}}
    if search.strip():
        pattern = {'$regex': re.escape(search.strip()), '$options': 'i'}
        query['$or'] = [{field: pattern} for field in ('name', 'ip', 'asset_no', 'fields.서버명')]
    docs = await M.get_assets_servers_collection().find(query).sort([('name', 1), ('_id', 1)]).limit(50).to_list(50)
    return [asset_info(doc) for doc in docs]
