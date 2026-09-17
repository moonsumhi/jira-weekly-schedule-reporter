"""작업 관리 문서와 등록 서버 자산의 연결. 본문·내보내기 데이터와 분리한다."""

from fastapi import HTTPException

from app.db.mongo import MongoClientManager as M
from app.utils.mongo import oid, fmt_dt
from app.services import asset_links
from app.services.asset_links import asset_info, hydrate, search_assets


def require_job(user):
    if not user.is_admin and 'job' not in user.permissions:
        raise HTTPException(403, '작업 관리 메뉴 권한이 필요합니다.')


def is_work_document(template):
    return str(template.get('menu', '')).lower() == 'job'


async def selected_assets(template_id, asset_ids, previous=None):
    template = await M.get_form_templates_collection().find_one({'_id': oid(template_id), 'is_deleted': {'$ne': True}})
    if not template or not is_work_document(template):
        raise HTTPException(422, '서버 자산은 작업 관리 문서에 연결할 수 있습니다.')
    return await asset_links.selected_assets(asset_ids, previous)


def summary(doc, template):
    fields = {}
    for value in doc.get('data', {}).values():
        if isinstance(value, dict):
            fields.update(value)
    title = next((str(fields[k]) for k in ('작업명', '작업 명', '작업 제목', '제목', '문서명', '신청명', '처리 목적') if fields.get(k)), '')
    body = doc.get('data', {}).get('문서 본문', [])
    if not title and isinstance(body, list) and body and isinstance(body[0], dict):
        title = str(body[0].get('제목', ''))
    date_field = next((k for k in ('작업 기간 (시작)', '작업 일시', '작업일', '신청일자', '신청일', '작성일') if fields.get(k)), '')
    work_date = str(fields[date_field]) if date_field else ''
    date_label = '신청일' if date_field.startswith('신청') else '작성일' if date_field == '작성일' else '작업일'
    return {'id': str(doc['_id']), 'template_id': doc['template_id'], 'template_title': template['title'],
            'title': title or template['title'], 'work_date': work_date, 'date_label': date_label,
            'created_at': fmt_dt(doc.get('created_at')), 'created_by': doc.get('created_by'),
            'asset_count': len(doc.get('asset_ids', []))}


async def history_query(asset_id):
    asset_id = str(oid(asset_id))
    templates = await M.get_form_templates_collection().find({'is_deleted': {'$ne': True}}).to_list(None)
    work_templates = {str(t['_id']): t for t in templates if is_work_document(t)}
    query = {'asset_ids': asset_id, 'is_deleted': {'$ne': True}, 'template_id': {'$in': list(work_templates)}}
    return work_templates, query


async def asset_history(asset_id, offset, limit):
    work_templates, query = await history_query(asset_id)
    col = M.get_form_entries_collection()
    total = await col.count_documents(query)
    docs = await col.find(query).sort([('created_at', -1), ('_id', -1)]).skip(offset).limit(limit).to_list(limit)
    return {'total': total, 'items': [summary(doc, work_templates[doc['template_id']]) for doc in docs]}
