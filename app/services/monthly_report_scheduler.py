"""Prepare the data operations team's monthly report, including after downtime."""
import asyncio
import hashlib
import logging
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.db.mongo import MongoClientManager as M
from app.utils.time import next_9am_kst

logger = logging.getLogger(__name__)
TEAM = '데이터운영팀'
SYSTEM_USER = ObjectId('000000000000000000000000')


async def ensure_monthly_report(year: int, month: int):
    # Import locally to avoid a router/service import cycle.
    from app.routers.pm.monthly_reports import _month_range, _next_month_range
    from app.routers.pm.report_agg import aggregate_period
    from app.services.monthly_report_context import capture_context, AGGREGATION_VERSION

    col = M.get_pm_monthly_reports_collection()
    candidates = await col.find({'report_year': year, 'report_month': month, 'deleted_at': None}).to_list(None)
    team_reports = [r for r in candidates if r.get('department') == TEAM]
    if len(team_reports) == 1:
        return team_reports[0]
    if len(team_reports) > 1:
        raise ValueError(f'{year}-{month:02d} 데이터운영팀 보고서가 여러 개입니다.')
    if len(candidates) == 1 and not candidates[0].get('department'):
        return candidates[0]
    if any(not r.get('department') for r in candidates):
        raise ValueError(f'{year}-{month:02d} 부서 미지정 보고서가 여러 개이거나 다른 보고서와 혼재합니다.')

    report_id = ObjectId(hashlib.sha256(f'monthly-report:{TEAM}:{year:04d}-{month:02d}'.encode()).hexdigest()[:24])
    old = await col.find_one({'_id': report_id})
    if old:
        if old.get('deleted_at') is not None:
            raise ValueError(f'{year}-{month:02d} 자동 생성 보고서가 삭제되었습니다.')
        return old
    start, end = _month_range(year, month)
    next_start, next_end = _next_month_range(year, month)
    items, upcoming, projects, people, stats = await aggregate_period(start, end, next_start, next_end, monthly_actuals=True)
    comparison, operational = await capture_context(year, month, TEAM, start, end)
    now = datetime.now(timezone.utc)
    doc = {
        '_id': report_id, 'report_year': year, 'report_month': month,
        'title': f'{year}년 {month}월 월간 보고', 'department': TEAM, 'status': 'DRAFT',
        'by_project': [p.model_dump() for p in projects], 'by_person': [p.model_dump() for p in people],
        'all_items': [i.model_dump() for i in items], 'upcoming_items': [i.model_dump() for i in upcoming],
        'stats': stats.model_dump(), 'aggregation_version': AGGREGATION_VERSION,
        'comparison': comparison, 'operational_summary': operational,
        'created_by': SYSTEM_USER, 'created_at': now, 'updated_at': now,
        'aggregated_at': now, 'aggregated_by': SYSTEM_USER, 'deleted_at': None,
        'edit_history': [{'editor_id': SYSTEM_USER, 'editor_name': '시스템', 'action': '자동 생성', 'edited_at': now}],
    }
    try:
        await col.insert_one(doc)
        return doc
    except DuplicateKeyError:
        return await col.find_one({'_id': report_id, 'deleted_at': None})


class MonthlyReportScheduler:
    def __init__(self):
        self.task = None

    def start(self):
        self.task = asyncio.create_task(self._loop())

    def stop(self):
        if self.task:
            self.task.cancel()

    async def _run_once(self, now):
        state = M.get_db()['pm_scheduler_state']
        checkpoint = await state.find_one({'_id': 'monthly-report-data-operations'})
        current = now.year * 100 + now.month
        last = checkpoint.get('last_month') if checkpoint else None
        if not last or last >= current:
            months = [(now.year, now.month)]
        else:
            year, month = divmod(last, 100)
            months = []
            while year * 100 + month < current:
                year, month = (year + 1, 1) if month == 12 else (year, month + 1)
                months.append((year, month))
        for year, month in months:
            await ensure_monthly_report(year, month)
            await state.update_one({'_id': 'monthly-report-data-operations'},
                                   {'$max': {'last_month': year * 100 + month}}, upsert=True)

    async def _loop(self):
        from datetime import timedelta
        kst = timezone(timedelta(hours=9))
        while True:
            try:
                now = datetime.now(kst)
                await self._run_once(now)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('월간 보고 자동 생성 실패')
            await asyncio.sleep(max(1, (next_9am_kst(datetime.now(timezone.utc)) - datetime.now(timezone.utc)).total_seconds()))
