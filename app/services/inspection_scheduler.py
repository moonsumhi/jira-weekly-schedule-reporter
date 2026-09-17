"""점검 3일 전·당일 담당자별 미완료 작업 알림 (09:00 KST, 재실행 중복 방지)."""
import asyncio
import logging
import hashlib

from bson import ObjectId
from collections import defaultdict
from datetime import datetime, timezone

from app.services import inspection_service as svc
from app.utils.time import next_9am_kst

logger = logging.getLogger(__name__)


class InspectionScheduler:
    def __init__(self):
        self._task = None

    def start(self):
        self._task = asyncio.create_task(self._loop())

    def stop(self):
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while True:
            try:
                await self._run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('서버 점검 알림 생성 실패')
            now = datetime.now(timezone.utc)
            await asyncio.sleep(max(1, (next_9am_kst(now) - now).total_seconds()))

    async def _run_once(self):
        now = datetime.now(svc.KST)
        if now.hour < 9:
            return
        month = now.strftime('%Y-%m')
        day = await svc.inspection_date(month)
        remaining = (day - now.date()).days
        if remaining not in (0, 3):
            return
        docs = await svc.collection().find({'occurrences': {'$elemMatch': {'month': {'$lte': month}, 'state': 'ACTIVE'}}}).to_list(None)
        groups = defaultdict(set)
        rows = await svc.hydrate_tasks(docs, month)
        for task in rows:
            issue = task['issue']
            if task['state'] != 'ACTIVE' or task['issue_deleted'] or not issue.get('assignee_id') or issue['status'] == 'DONE':
                continue
            user = await svc.M.get_users_collection().find_one({'_id': ObjectId(issue['assignee_id'])})
            if not user or not (user.get('is_admin') or 'server_check' in user.get('permissions', [])):
                continue
            if not user.get('is_admin') and not svc.is_plan_task(task):
                member = await svc.M.get_pm_project_members_collection().find_one({
                    'user_id': user['_id'], 'project_id': ObjectId(issue['project_id'])})
                if not member:
                    continue
            groups[str(user['_id'])].add(task['issue_id'])
        for user_id, issues in groups.items():
            key = f'inspection:{day}:{remaining}:{user_id}'
            # 같은 시각 여러 worker가 실행되어도 알림 한 건만 생성한다.
            notification_id = ObjectId(hashlib.sha256(key.encode()).hexdigest()[:24])
            await svc.M.get_db()[svc.M.NOTIFICATIONS].update_one(
                {'_id': notification_id},
                {'$setOnInsert': {
                    'recipient_user_id': user_id, 'notification_type': 'SYSTEM',
                    'title': '서버 점검 작업 확인',
                    'message': f'{day.isoformat()} 서버 점검: 내 미완료 작업 {len(issues)}건을 확인해 주세요.',
                    'target_type': 'SYSTEM', 'target_id': month,
                    'target_url': f'/inspection/tasks?month={month}&mine=1',
                    'sender_user_id': None, 'sender_name': None,
                    'deduplication_key': key, 'is_read': False, 'read_at': None,
                    'is_archived': False, 'created_at': now, 'updated_at': now,
                }}, upsert=True,
            )
