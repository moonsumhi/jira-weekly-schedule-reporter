"""연간 반복 규칙, 한국 날짜 경계 및 사전 생성 기간 회귀 테스트."""
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from pydantic import ValidationError

from app.models.pm.recurring_issue import (
    RecurrenceRule, RecurringIssueTemplateCreate, RecurringIssueTemplatePatch,
    RecurringIssueTemplateOut,
)
from app.services.pm import recurring_issue_service as recurring


def template(**rule):
    return {
        '_id': ObjectId(), 'project_id': str(ObjectId()), 'name': '연간 점검',
        'blueprint': {'title': '인증서 갱신'},
        'rule': {'freq': 'yearly', 'month': 1, 'days_of_month': [1], 'time': '09:00', **rule},
        'lead_days': 0,
    }


class YearlyRuleTests(unittest.TestCase):
    def test_month_is_required_and_bounded_on_create_and_patch(self):
        for month in (None, 0, 13):
            for model in (RecurringIssueTemplateCreate, RecurringIssueTemplatePatch):
                with self.subTest(month=month, model=model.__name__):
                    data = template(month=month)
                    with self.assertRaises(ValidationError):
                        model(**data)

    def test_yearly_rule_survives_create_patch_and_response(self):
        data = template(month=11, days_of_month=[19, 5, 19])
        created = RecurringIssueTemplateCreate(**data).model_dump()
        updated = RecurringIssueTemplatePatch(rule=created['rule']).model_dump()
        response = RecurringIssueTemplateOut(id=str(data['_id']), **created)
        self.assertEqual(response.rule.month, 11)
        self.assertEqual(updated['rule']['freq'], 'yearly')
        self.assertEqual(response.rule.days_of_month, [5, 19])

    def test_legacy_monthly_rule_keeps_defaults_and_ignores_yearly_month(self):
        rule = RecurrenceRule(days_of_month=[1]).model_dump()
        self.assertEqual(rule['freq'], 'monthly')
        for month in (1, 6, 12):
            data = template(**{**rule, 'month': 11})
            self.assertEqual(recurring.compute_occurrences(data, 2026, month)[0]['day'], 1)

    def test_only_selected_month_in_each_year_is_generated(self):
        data = template(month=11, days_of_month=[19, 5, 19])
        for year in (2026, 2027):
            for month in range(1, 13):
                with self.subTest(year=year, month=month):
                    occurrences = recurring.compute_occurrences(data, year, month)
                    expected = [f'{year}-11-05', f'{year}-11-19'] if month == 11 else []
                    self.assertEqual([o['occurrence_date'] for o in occurrences], expected)
        november = recurring.compute_occurrences(data, 2026, 11)
        self.assertEqual([o['title'] for o in november], ['인증서 갱신 - 11월 1차', '인증서 갱신 - 11월 2차'])

    def test_leap_day_skips_non_leap_years(self):
        data = template(month=2, days_of_month=[29])
        self.assertEqual(recurring.compute_occurrences(data, 2027, 2), [])
        self.assertEqual(recurring.compute_occurrences(data, 2028, 2)[0]['occurrence_date'], '2028-02-29')
        self.assertEqual(recurring.compute_occurrences(data, 2100, 2), [])

    def test_weekday_rule_supports_first_last_and_missing_fifth(self):
        data = template(month=2, mode='weekday', weekdays=[
            {'week': 1, 'weekday': 0}, {'week': -1, 'weekday': 4}, {'week': 5, 'weekday': 0},
        ])
        self.assertEqual([o['day'] for o in recurring.compute_occurrences(data, 2027, 2)], [1, 26])
        self.assertEqual(recurring.compute_occurrences(data, 2027, 3), [])

    def test_time_is_interpreted_in_korea(self):
        occurrence = recurring.compute_occurrences(template(time='00:30'), 2027, 1)[0]
        self.assertEqual(occurrence['occurrence_date'], '2027-01-01')
        self.assertEqual(occurrence['occurrence_dt'], datetime(2026, 12, 31, 15, 30, tzinfo=timezone.utc))


class YearlyAutomaticGenerationTests(unittest.IsolatedAsyncioTestCase):
    async def generate(self, data, now):
        with patch.object(recurring, '_existing_issue', new=AsyncMock(return_value=None)), \
                patch.object(recurring, '_create_issue_from_occurrence', new=AsyncMock(return_value={'_id': ObjectId()})):
            return await recurring.generate_due(data, now)

    async def test_full_sixty_day_window_crosses_year_and_two_month_boundaries(self):
        data = {**template(), 'lead_days': 60}
        self.assertEqual(await self.generate(data, datetime(2026, 11, 1)), [])
        result = await self.generate(data, datetime(2026, 11, 2))
        self.assertEqual([o['occurrence_date'] for o in result], ['2027-01-01'])

    async def test_sixty_day_window_can_span_four_calendar_months(self):
        data = {**template(month=4), 'lead_days': 60}
        result = await self.generate(data, datetime(2027, 1, 31))
        self.assertEqual([o['occurrence_date'] for o in result], ['2027-04-01'])

    async def test_korean_new_year_day_works_even_when_utc_is_previous_year(self):
        result = await self.generate(template(), datetime(2026, 12, 31, 15, tzinfo=timezone.utc))
        self.assertEqual([o['occurrence_date'] for o in result], ['2027-01-01'])

    async def test_past_annual_date_is_not_generated_retroactively(self):
        self.assertEqual(await self.generate(template(), datetime(2027, 1, 2)), [])

    async def test_monthly_generation_still_respects_lead_window(self):
        data = {**template(freq='monthly'), 'lead_days': 3}
        self.assertEqual(await self.generate(data, datetime(2026, 11, 27)), [])
        result = await self.generate(data, datetime(2026, 11, 28))
        self.assertEqual([o['occurrence_date'] for o in result], ['2026-12-01'])
