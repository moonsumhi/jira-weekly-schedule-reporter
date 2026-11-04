"""Team leader feedback and next-month report contributions."""
import logging
from datetime import datetime, timezone
from typing import Literal

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.pm.weekly_reports import _require_pm
from app.services.monthly_report_scheduler import TEAM, ensure_monthly_report
from app.services.notification_service import create_notification

router = APIRouter()
logger = logging.getLogger(__name__)


class FeedbackCreate(BaseModel):
    source_report_id: str
    title: str = Field(min_length=1, max_length=300)
    comment: str = Field(min_length=1, max_length=10000)
    assignee_id: str
    due_date: str = Field(default='', max_length=30)


class FeedbackAction(BaseModel):
    action: Literal['save', 'submit', 'return', 'apply', 'cancel']
    content: str = Field(default='', max_length=10000)
    review_note: str = Field(default='', max_length=2000)


def _team(user):
    _require_pm(user)
    if not user.is_admin and user.team != TEAM:
        raise HTTPException(403, '데이터운영팀 권한이 필요합니다.')


def _id(value):
    if not ObjectId.is_valid(value):
        raise HTTPException(400, '올바르지 않은 식별자입니다.')
    return ObjectId(value)


def _out(doc):
    return {**doc, 'id': str(doc['_id']), '_id': str(doc['_id'])}


async def _notify(recipient, user, title, message, report_id, feedback_id, *, notification_type='REVIEW_REQUESTED'):
    if recipient == user.id:
        return
    try:
        await create_notification(recipient, notification_type, title, message,
            sender_user_id=user.id, sender_name=user.full_name or user.email,
            target_type='SYSTEM', target_id=str(feedback_id),
            target_url=f'/pm/monthly-report/{report_id}?feedback={feedback_id}')
    except Exception:
        logger.exception('월간보고 피드백 알림 생성 실패: %s', feedback_id)


@router.get('')
async def list_feedback(report_id: str, user: UserPublic = Depends(get_current_user)):
    _team(user)
    _id(report_id)
    docs = await M.get_db()['pm_monthly_feedback'].find({
        '$or': [{'source_report_id': report_id}, {'target_report_id': report_id}],
    }).sort('created_at', -1).to_list(None)
    return [_out(d) for d in docs]


@router.get('/mine')
async def my_feedback(user: UserPublic = Depends(get_current_user)):
    _team(user)
    docs = await M.get_db()['pm_monthly_feedback'].find({
        'assignee_id': user.id, 'status': {'$in': ['REQUESTED', 'WRITING', 'SUBMITTED', 'APPLYING']},
    }).sort('created_at', -1).to_list(None)
    return [_out(d) for d in docs]


@router.get('/assignees')
async def feedback_assignees(user: UserPublic = Depends(get_current_user)):
    _team(user)
    docs = await M.get_users_collection().find({
        'team': TEAM, 'is_blocked': {'$ne': True},
        '$or': [{'is_admin': True}, {'permissions': 'pm'}],
    }, {'full_name': 1, 'email': 1}).sort('full_name', 1).to_list(None)
    return [{'id': str(d['_id']), 'name': d.get('full_name') or d.get('email', '')} for d in docs]


@router.post('', status_code=201)
async def create_feedback(body: FeedbackCreate, user: UserPublic = Depends(get_current_user)):
    _team(user)
    if not body.title.strip() or not body.comment.strip():
        raise HTTPException(400, '제목과 팀장님 코멘트를 입력해 주세요.')
    if len(body.comment.strip()) > 5000:
        raise HTTPException(400, '팀장님 코멘트는 5,000자 이내로 입력해 주세요.')
    source = await M.get_pm_monthly_reports_collection().find_one({'_id': _id(body.source_report_id), 'deleted_at': None})
    if not source:
        raise HTTPException(404, '원본 보고서를 찾을 수 없습니다.')
    if source.get('department') not in (None, '', TEAM):
        raise HTTPException(400, '데이터운영팀 보고서에서 요청해 주세요.')
    assignee = await M.get_users_collection().find_one({'_id': _id(body.assignee_id), 'team': TEAM, 'is_blocked': {'$ne': True}})
    if not assignee or (not assignee.get('is_admin') and 'pm' not in (assignee.get('permissions') or [])):
        raise HTTPException(400, '스케줄 관리 권한이 있는 데이터운영팀 담당자를 선택해 주세요.')
    year, month = source['report_year'], source['report_month']
    year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    try:
        target = await ensure_monthly_report(year, month)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if not target or target.get('status') == 'CONFIRMED':
        raise HTTPException(409, '다음 달 보고서가 확정되어 요청을 추가할 수 없습니다.')
    now = datetime.now(timezone.utc)
    doc = {'source_report_id': body.source_report_id, 'target_report_id': str(target['_id']),
           'title': body.title.strip(), 'comment': body.comment.strip(), 'assignee_id': body.assignee_id,
           'assignee_name': assignee.get('full_name') or assignee.get('email'),
           'requester_id': user.id, 'requester_name': user.full_name or user.email,
           'due_date': body.due_date, 'status': 'REQUESTED', 'content': '', 'review_note': '',
           'created_at': now, 'updated_at': now}
    result = await M.get_db()['pm_monthly_feedback'].insert_one(doc)
    doc['_id'] = result.inserted_id
    await _notify(body.assignee_id, user, '월간보고 작성 요청', body.title.strip(), str(target['_id']), result.inserted_id)
    return _out(doc)


@router.post('/{feedback_id}/action')
async def act(feedback_id: str, body: FeedbackAction, user: UserPublic = Depends(get_current_user)):
    _team(user)
    col = M.get_db()['pm_monthly_feedback']
    fid = _id(feedback_id)
    doc = await col.find_one({'_id': fid})
    if not doc:
        raise HTTPException(404, '피드백 요청을 찾을 수 없습니다.')
    if body.action in ('save', 'submit'):
        if doc['assignee_id'] != user.id and not user.is_admin:
            raise HTTPException(403, '담당자만 작성할 수 있습니다.')
        if body.action == 'submit' and doc['status'] == 'APPLIED':
            return _out(doc)
        allowed = ('REQUESTED', 'WRITING', 'SUBMITTED', 'APPLYING') if body.action == 'submit' else ('REQUESTED', 'WRITING', 'SUBMITTED')
        if doc['status'] not in allowed:
            raise HTTPException(409, '작성 가능한 요청이 아닙니다.')
        if body.action == 'submit' and doc['status'] != 'APPLYING' and not body.content.strip():
            raise HTTPException(400, '보고 내용을 입력해 주세요.')
        if body.action == 'submit':
            return await _complete_feedback(doc, user, body.content, legacy=False)
        changes = {'content': body.content, 'status': 'WRITING'}
    elif body.action == 'cancel':
        if doc['requester_id'] != user.id and not user.is_admin:
            raise HTTPException(403, '요청자만 취소할 수 있습니다.')
        if doc['status'] not in ('REQUESTED', 'WRITING', 'SUBMITTED'):
            raise HTTPException(409, '취소할 수 없는 요청입니다.')
        changes = {'status': 'CANCELLED'}
    else:
        if doc['requester_id'] != user.id and not user.is_admin:
            raise HTTPException(403, '요청자만 검토할 수 있습니다.')
        if doc['status'] not in (('SUBMITTED', 'APPLYING') if body.action == 'apply' else ('SUBMITTED',)):
            raise HTTPException(409, '검토 대기 중인 요청이 아닙니다.')
        changes = {'status': 'WRITING' if body.action == 'return' else 'APPLIED', 'review_note': body.review_note}
        if body.action == 'apply':
            # Compatibility for older clients and already-submitted requests.
            return await _complete_feedback(doc, user, doc['content'], legacy=True)
    changes['updated_at'] = datetime.now(timezone.utc)
    updated = await col.find_one_and_update({'_id': fid, 'status': doc['status'], 'updated_at': doc['updated_at']}, {'$set': changes}, return_document=True)
    if not updated:
        raise HTTPException(409, '다른 사용자가 요청을 변경했습니다. 다시 확인해 주세요.')
    if body.action == 'return':
        await _notify(doc['assignee_id'], user, '월간보고 보완 요청', doc['title'], doc['target_report_id'], fid)
    elif body.action == 'cancel':
        await _notify(doc['assignee_id'], user, '월간보고 작성 요청 취소', doc['title'], doc['target_report_id'], fid)
    return _out(updated)


async def _complete_feedback(doc, user, content, *, legacy):
    """Save the submitted text and add it once to the linked next-month report."""
    col = M.get_db()['pm_monthly_feedback']
    fid = doc['_id']
    if doc['status'] != 'APPLYING':
        claimed = await col.find_one_and_update(
            {'_id': fid, 'status': doc['status'], 'updated_at': doc['updated_at']},
            {'$set': {'status': 'APPLYING', 'content': content, 'updated_at': datetime.now(timezone.utc)}}, return_document=True)
        if not claimed:
            raise HTTPException(409, '다른 사용자가 요청을 변경했습니다. 다시 확인해 주세요.')
        doc = claimed
    # An interrupted submission is retried with its saved text, never replaced
    # by a different request body while the report write may already exist.
    insight_id = f'feedback-{fid}'
    item = {'id': insight_id, 'kind': 'MAIN_AGENDA', 'title': doc['title'], 'content': doc['content'],
            'owner': doc['assignee_name'], 'impact': '', 'action_plan': '', 'due_date': doc['due_date'],
            'planned_date': '', 'expected_date': '', 'status': '',
            'source_report_id': None, 'source_item_id': None, 'source_label': None}
    reports = M.get_pm_monthly_reports_collection()
    report = await reports.find_one_and_update(
        {'_id': _id(doc['target_report_id']), 'deleted_at': None, 'status': {'$ne': 'CONFIRMED'}, 'insights.id': {'$ne': insight_id}},
        {'$push': {'insights': item}, '$set': {'updated_at': datetime.now(timezone.utc), 'updated_by': _id(user.id)}}, return_document=True)
    if not report:
        existing = await reports.find_one({'_id': _id(doc['target_report_id']), 'deleted_at': None, 'insights.id': insight_id})
        if not existing:
            # A definite rejection keeps the text as a draft. For an uncertain
            # database error keep APPLYING, so retrying cannot duplicate an item.
            await col.update_one({'_id': fid, 'status': 'APPLYING', 'updated_at': doc['updated_at']},
                                 {'$set': {'status': 'SUBMITTED' if legacy else 'WRITING', 'updated_at': datetime.now(timezone.utc)}})
            raise HTTPException(409, '다음 달 보고서가 확정되었거나 삭제되어 반영하지 못했습니다. 작성 내용은 보관했습니다.')
    updated = await col.find_one_and_update(
        {'_id': fid, 'status': 'APPLYING', 'updated_at': doc['updated_at']},
        {'$set': {'status': 'APPLIED', 'updated_at': datetime.now(timezone.utc)}}, return_document=True)
    if not updated:
        finished = await col.find_one({'_id': fid, 'status': 'APPLIED'})
        if finished:
            return _out(finished)
        raise HTTPException(409, '반영 상태를 다시 확인해 주세요.')
    recipient = doc['assignee_id'] if legacy else doc['requester_id']
    await _notify(recipient, user, '월간보고 반영 완료',
                  f"{doc['title']} — 다음 달 주요 안건에 추가되었습니다.", doc['target_report_id'], fid,
                  notification_type='STATUS_CHANGED')
    return _out(updated)
