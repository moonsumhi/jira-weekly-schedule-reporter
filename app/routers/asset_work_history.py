"""Combined asset history for documents, issues, inspections and local notes."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.db.mongo import MongoClientManager as M
from app.models.asset_note import AssetNoteCreate, AssetNotePatch, AssetNoteDelete
from app.models.user import UserPublic
from app.routers.permissions import require_asset_access
from app.services import inspection_service, work_document_assets
from app.utils.mongo import oid, fmt_dt

router = APIRouter()


async def server_asset(asset_id, *, writing=False):
    asset = await M.get_assets_servers_collection().find_one({'_id': oid(asset_id)})
    if not asset or ((asset.get('fields') or {}).get('자산유형') or '서버') != '서버':
        raise HTTPException(404, '서버 자산을 찾을 수 없습니다.')
    if writing and asset.get('is_deleted'):
        raise HTTPException(409, '삭제된 자산에는 운영 메모를 추가하거나 변경할 수 없습니다.')
    return asset


def note_out(note, user, asset):
    return {'id': str(note['_id']), 'asset_id': note['asset_id'], 'type': 'note',
            'content': note['content'], 'occurred_on': note['occurred_on'], 'version': note['version'],
            'created_by': note['created_by'], 'created_at': fmt_dt(note['created_at']),
            'updated_by': note['updated_by'], 'updated_at': fmt_dt(note['updated_at']),
            'can_edit': not asset.get('is_deleted') and (user.is_admin or note['created_by_id'] == user.id)}


async def existing_note(asset_id, note_id, user, *, writing=False):
    asset = await server_asset(asset_id, writing=writing)
    note = await M.get_asset_notes_collection().find_one({
        '_id': oid(note_id), 'asset_id': str(asset['_id']), 'is_deleted': {'$ne': True}})
    if not note:
        raise HTTPException(404, '운영 메모를 찾을 수 없습니다.')
    if writing and not (user.is_admin or note['created_by_id'] == user.id):
        raise HTTPException(403, '작성자 또는 관리자만 운영 메모를 변경할 수 있습니다.')
    return asset, note


@router.get('/{asset_id}/work-history')
async def work_history(asset_id: str, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
                       user: UserPublic = Depends(require_asset_access)):
    asset = await server_asset(asset_id)
    pipeline = [
        {'$match': {'asset_id': str(asset['_id']), 'is_deleted': {'$ne': True}}},
        {'$set': {'entry_type': 'note'}},
    ]
    templates = {}
    projects = await inspection_service.accessible_projects(user) if user.is_admin or any(
        permission in user.permissions for permission in ('pm', 'server_check')) else []
    can_inspect = user.is_admin or 'server_check' in user.permissions
    if user.is_admin or 'job' in user.permissions:
        templates, query = await work_document_assets.history_query(asset_id)
        pipeline.append({'$unionWith': {'coll': M.get_form_entries_collection().name, 'pipeline': [
            {'$match': query}, {'$set': {'entry_type': 'document'}},
        ]}})
    if user.is_admin or 'pm' in user.permissions:
        query = {'asset_ids': str(asset['_id'])}
        if projects is not None:
            query['project_id'] = {'$in': projects}
        issue_pipeline = [{'$match': query}]
        if can_inspect:
            # A live inspection occurrence replaces a duplicate issue row.
            # Archived/completed snapshots must not hide a reopened issue.
            issue_pipeline.extend([
                {'$lookup': {'from': inspection_service.collection().name, 'let': {'issue_id': '$_id'}, 'pipeline': [
                    {'$match': {'$expr': {'$eq': ['$_id', '$$issue_id']}, 'occurrences': {'$elemMatch': {
                        'assets.id': str(asset['_id']), 'state': 'ACTIVE', '$or': [
                            {'month': {'$gte': inspection_service.current_month()}},
                            {'completed_snapshot': {'$exists': False}},
                        ]}}}},
                    {'$project': {'_id': 1}}, {'$limit': 1},
                ], 'as': 'inspection_links'}},
                {'$match': {'inspection_links.0': {'$exists': False}}},
                {'$unset': 'inspection_links'},
            ])
        issue_pipeline.append({'$set': {'entry_type': 'issue'}})
        pipeline.append({'$unionWith': {'coll': M.get_pm_issues_collection().name, 'pipeline': issue_pipeline}})
    if can_inspect:
        query = {'occurrences.assets.id': str(asset['_id']), **inspection_service.project_scope(projects)}
        pipeline.append({'$unionWith': {'coll': inspection_service.collection().name, 'pipeline': [
            {'$match': query},
            {'$unwind': '$occurrences'},
            # A server may be targeted in only one of an issue's monthly occurrences.
            {'$match': {'occurrences.assets.id': str(asset['_id'])}},
            {'$set': {'entry_type': 'inspection', 'created_at': '$occurrences.created_at'}},
        ]}})
    pipeline.extend([
        {'$sort': {'created_at': -1, '_id': -1, 'entry_type': 1, 'occurrences.month': -1}},
        {'$facet': {'items': [{'$skip': offset}, {'$limit': limit}], 'count': [{'$count': 'total'}]}},
    ])
    result = (await M.get_asset_notes_collection().aggregate(pipeline).to_list(1))[0]
    tasks = await inspection_service.hydrate_tasks(
        [{**item, 'occurrences': [item['occurrences']]} for item in result['items'] if item['entry_type'] == 'inspection'],
        inspection_service.current_month(), all_months=True)
    task_map = {(task['issue_id'], task['month']): task for task in tasks}
    items = []
    for item in result['items']:
        if item['entry_type'] == 'note':
            items.append(note_out(item, user, asset))
        elif item['entry_type'] == 'inspection':
            task = task_map[(str(item['_id']), item['occurrences']['month'])]
            items.append({**task, 'type': 'inspection', 'id': f"{task['issue_id']}:{task['month']}"})
        elif item['entry_type'] == 'issue':
            items.append({'type': 'issue', 'id': str(item['_id']), 'issue': await inspection_service.issue_snapshot(item),
                          'created_at': fmt_dt(item.get('created_at')), 'start_date': fmt_dt(item.get('start_date')),
                          'due_date': fmt_dt(item.get('due_date'))})
        else:
            items.append({'type': 'document', **work_document_assets.summary(item, templates[item['template_id']])})
    return {'total': result['count'][0]['total'] if result['count'] else 0, 'items': items}


@router.post('/{asset_id}/notes', status_code=201)
async def create_note(asset_id: str, body: AssetNoteCreate, user: UserPublic = Depends(require_asset_access)):
    asset = await server_asset(asset_id, writing=True)
    now = datetime.now(timezone.utc)
    actor = user.full_name or user.email
    values = {'asset_id': str(asset['_id']), 'content': body.content, 'occurred_on': body.occurred_on.isoformat(),
              'client_id': body.client_id, 'version': 1, 'is_deleted': False,
              'created_by_id': user.id, 'created_by': actor, 'created_at': now,
              'updated_by': actor, 'updated_at': now}
    col = M.get_asset_notes_collection()
    query = {'asset_id': values['asset_id'], 'client_id': body.client_id}
    try:
        note = await col.find_one_and_update(query, {'$setOnInsert': values}, upsert=True, return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:
        note = await col.find_one(query)
    if not note or note['created_by_id'] != user.id or note.get('is_deleted') or any(
            note[key] != values[key] for key in ('content', 'occurred_on')):
        raise HTTPException(409, '이미 처리된 등록 요청입니다. 이력을 새로고침해 확인해 주세요.')
    return note_out(note, user, asset)


@router.get('/{asset_id}/notes/{note_id}')
async def get_note(asset_id: str, note_id: str, user: UserPublic = Depends(require_asset_access)):
    asset, note = await existing_note(asset_id, note_id, user)
    return note_out(note, user, asset)


@router.patch('/{asset_id}/notes/{note_id}')
async def update_note(asset_id: str, note_id: str, body: AssetNotePatch, user: UserPublic = Depends(require_asset_access)):
    asset, previous = await existing_note(asset_id, note_id, user, writing=True)
    note = await M.get_asset_notes_collection().find_one_and_update(
        {'_id': previous['_id'], 'asset_id': str(asset['_id']), 'version': body.version, 'is_deleted': {'$ne': True}},
        {'$set': {'content': body.content, 'occurred_on': body.occurred_on.isoformat(),
                  'updated_by': user.full_name or user.email, 'updated_at': datetime.now(timezone.utc)}, '$inc': {'version': 1}},
        return_document=ReturnDocument.AFTER)
    if not note:
        raise HTTPException(409, '다른 사용자가 변경한 운영 메모입니다. 다시 열어 최신 내용을 확인해 주세요.')
    return note_out(note, user, asset)


@router.delete('/{asset_id}/notes/{note_id}', status_code=204)
async def delete_note(asset_id: str, note_id: str, body: AssetNoteDelete, user: UserPublic = Depends(require_asset_access)):
    asset, previous = await existing_note(asset_id, note_id, user, writing=True)
    result = await M.get_asset_notes_collection().update_one(
        {'_id': previous['_id'], 'asset_id': str(asset['_id']), 'version': body.version, 'is_deleted': {'$ne': True}},
        {'$set': {'is_deleted': True, 'updated_by': user.full_name or user.email, 'updated_at': datetime.now(timezone.utc)},
         '$inc': {'version': 1}})
    if not result.modified_count:
        raise HTTPException(409, '다른 사용자가 변경한 운영 메모입니다. 다시 열어 최신 내용을 확인해 주세요.')
    return Response(status_code=204)
