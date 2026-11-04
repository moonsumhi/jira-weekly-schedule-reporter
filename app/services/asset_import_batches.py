"""Persistent import batches and conservative per-asset rollback."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.db.mongo import MongoClientManager as M
from app.services.assets_service import _write_history, _check_asset_id, _ip_asset_type_query
from app.utils.mongo import to_out
from app.utils.time import TimeUtil

COLLECTION = 'asset_import_batches'
JOURNAL = '_import_journals'
SNAPSHOT_FIELDS = ('ip', 'name', 'asset_id', 'asset_no', 'fields', 'system_info')


def snapshot(doc: dict) -> dict:
    return {key: doc[key] for key in SNAPSHOT_FIELDS if key in doc}


def collection():
    return M.get_db()[COLLECTION]


async def start_batch(filename: str, actor: str, source: str = 'excel') -> dict:
    doc = {'filename': filename[:255], 'created_by': actor, 'created_at': TimeUtil.now_utc(),
           'status': 'RUNNING', 'active_requests': 0, 'write_count': 0, 'source': source}
    result = await collection().insert_one(doc)
    doc['_id'] = result.inserted_id
    return to_out(doc)


@asynccontextmanager
async def reserve(batch_id: str | None, actor: str):
    if not batch_id:
        yield None
        return
    if not ObjectId.is_valid(batch_id):
        raise HTTPException(400, '잘못된 Import 식별자입니다.')
    batch = await collection().find_one_and_update(
        {'_id': ObjectId(batch_id), 'created_by': actor, 'status': {'$in': ['RUNNING', 'FINISHED']}},
        {'$inc': {'active_requests': 1}}, return_document=ReturnDocument.AFTER,
    )
    if batch is None:
        raise HTTPException(409, '완료되었거나 사용할 수 없는 Import입니다.')
    try:
        yield str(ObjectId(batch_id))
    finally:
        await collection().update_one({'_id': ObjectId(batch_id)}, {'$inc': {'active_requests': -1}})


async def list_batches(skip: int, limit: int) -> list[dict]:
    cursor = collection().find({}).sort([('created_at', -1), ('_id', -1)]).skip(skip).limit(limit)
    return [to_out(doc) async for doc in cursor]


async def finish_batch(batch_id: str, actor: str) -> None:
    if not ObjectId.is_valid(batch_id):
        raise HTTPException(400, '잘못된 Import 식별자입니다.')
    await collection().update_one({'_id': ObjectId(batch_id), 'created_by': actor, 'status': 'RUNNING', 'active_requests': 0},
                                  {'$set': {'status': 'FINISHED', 'finished_at': TimeUtil.now_utc()}})


async def has_linked_work(asset_id: str) -> bool:
    from app.services import inspection_service
    checks = (
        (M.get_asset_notes_collection(), {'asset_id': asset_id, 'is_deleted': {'$ne': True}}),
        (M.get_form_entries_collection(), {'asset_ids': asset_id, 'is_deleted': {'$ne': True}}),
        (M.get_pm_issues_collection(), {'asset_ids': asset_id, 'is_deleted': {'$ne': True}}),
        (inspection_service.collection(), {'occurrences.assets.id': asset_id}),
    )
    for col, query in checks:
        if await col.find_one(query, {'_id': 1}):
            return True
    return False


async def rollback_batch(batch_id: str, actor: str) -> dict:
    if not ObjectId.is_valid(batch_id):
        raise HTTPException(400, '잘못된 Import 식별자입니다.')
    bid = ObjectId(batch_id)
    batch_id = str(bid)
    now = TimeUtil.now_utc()
    batch = await collection().find_one_and_update(
        {'_id': bid, 'status': {'$in': ['RUNNING', 'FINISHED', 'PARTIAL']}, 'active_requests': 0},
        {'$set': {'status': 'ROLLING_BACK', 'rollback_started_at': now, 'rollback_by': actor}},
        return_document=ReturnDocument.AFTER,
    )
    if batch is None:
        raise HTTPException(409, 'Import가 진행 중이거나 이미 롤백되었습니다.')
    restored = deleted = 0
    conflicts: list[dict[str, str]] = []
    try:
        for category, (col_name, history_name) in M.CATEGORY_COLLECTIONS.items():
            col = M.get_db()[col_name]
            path = f'{JOURNAL}.{batch_id}'
            async for doc in col.find({path: {'$exists': True}}):
                entry = doc[JOURNAL][batch_id]
                if entry.get('rolled_back'):
                    continue
                asset_id = str(doc['_id'])
                label = doc.get('name') or doc.get('ip') or asset_id
                if category == '랙':
                    conflicts.append({'category': category, 'asset_id': asset_id, 'name': label, 'reason': '랙 자산은 수동으로 확인해야 합니다.'})
                    continue
                if doc.get('is_deleted') or doc.get('version', 1) != entry['after_version'] or snapshot(doc) != entry['after']:
                    conflicts.append({'category': category, 'asset_id': asset_id, 'name': label, 'reason': 'Import 이후 자산이 변경되었거나 삭제되었습니다.'})
                    continue
                if entry['kind'] == 'created':
                    placement = await M.get_rack_placements_collection().find_one(
                        {'asset_category': category, 'asset_ref_id': doc['_id'], 'is_deleted': False})
                    if placement:
                        conflicts.append({'category': category, 'asset_id': asset_id, 'name': label, 'reason': '랙에 배치된 자산입니다.'})
                        continue
                    if await has_linked_work(asset_id):
                        conflicts.append({'category': category, 'asset_id': asset_id, 'name': label, 'reason': '연결된 운영 이력이 있는 자산입니다.'})
                        continue
                    set_fields: dict[str, Any] = {'is_deleted': True, 'delete_reason': 'Import 롤백', 'deleted_at': now, 'deleted_by': actor}
                    unset: dict[str, str] = {}
                    if doc.get('asset_id'):
                        set_fields['_rollback_asset_id'] = doc['asset_id']
                        unset['asset_id'] = ''
                    action = 'DELETE'
                else:
                    before = entry['before']
                    try:
                        await _check_asset_id(col, before.get('asset_id'), exclude_id=doc['_id'])
                        before_ip = before.get('ip')
                        if before_ip and before_ip != doc.get('ip'):
                            duplicate = await col.find_one({**_ip_asset_type_query(before_ip, category), '_id': {'$ne': doc['_id']}})
                            if duplicate:
                                raise ValueError('기존 IP가 다른 자산에서 사용 중입니다.')
                    except ValueError as error:
                        conflicts.append({'category': category, 'asset_id': asset_id, 'name': label, 'reason': str(error)})
                        continue
                    set_fields = dict(before)
                    unset = {key: '' for key in SNAPSHOT_FIELDS if key not in before}
                    action = 'UPDATE'
                set_fields.update({'updated_at': now, 'updated_by': actor, 'version': doc.get('version', 1) + 1,
                                   f'{path}.rolled_back': True, f'{path}.rolled_back_at': now})
                update: dict[str, Any] = {'$set': set_fields}
                if unset:
                    update['$unset'] = unset
                match = {'_id': doc['_id'], 'version': doc['version'] if 'version' in doc else {'$exists': False}, 'is_deleted': {'$ne': True},
                         f'{path}.after_version': entry['after_version']}
                for key in SNAPSHOT_FIELDS:
                    match[key] = doc[key] if key in doc else {'$exists': False}
                try:
                    result = await col.update_one(match, update)
                except DuplicateKeyError:
                    conflicts.append({'category': category, 'asset_id': asset_id, 'name': label, 'reason': '기존 자산 ID가 이미 사용 중입니다.'})
                    continue
                if not result.matched_count:
                    conflicts.append({'category': category, 'asset_id': asset_id, 'name': label, 'reason': '롤백 중 자산이 변경되었습니다.'})
                    continue
                after = await col.find_one({'_id': doc['_id']})
                await _write_history(asset_id, action, actor, to_out(doc), to_out(after),
                                     {'import_batch_id': batch_id, 'rollback': True}, history_col=M.get_db()[history_name], source='import_rollback')
                if action == 'DELETE':
                    deleted += 1
                else:
                    restored += 1
        result = {'restored': restored, 'deleted': deleted, 'conflicts': conflicts}
        await collection().update_one({'_id': bid}, {'$set': {
            'status': 'PARTIAL' if conflicts else 'ROLLED_BACK', 'rollback_at': TimeUtil.now_utc(),
            'rollback_by': actor, 'last_result': result,
        }})
        return result
    except Exception:
        await collection().update_one({'_id': bid}, {'$set': {'status': 'PARTIAL'}})
        raise
