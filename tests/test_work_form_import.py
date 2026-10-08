import unittest
from app.services.work_form_import import map_document, EXTRA


class OriginalFormImportTests(unittest.TestCase):
    def test_plan_test_case_id_maps_from_operational_section(self):
        sections = [{
            'title': '테스트 케이스', 'multiple': True,
            'fields': [
                {'label': '테스트케이스 ID', 'type': 'text'},
                {'label': '설명', 'type': 'text'},
                {'label': '예상 결과', 'type': 'textarea'},
            ],
        }]
        markdown = '''## 테스트 계획

| 테스트케이스 ID | 설명 | 예상 결과 |
| --- | --- | --- |
| TC-01 | 웹 로그인 | 로그인 성공 |'''
        data, warnings = map_document(markdown, sections)
        self.assertEqual(data['테스트 케이스'][0]['테스트케이스 ID'], 'TC-01')
        self.assertEqual(data['테스트 케이스'][0]['예상 결과'], '로그인 성공')
        self.assertFalse(warnings)

    def test_fields_images_order_and_unmatched_content(self):
        sections = [
            {'title': '기본 정보', 'fields': [{'label': '작업명', 'type': 'text'}, {'label': '구분', 'type': 'select', 'options': ['서버', '개발']}]},
            {'title': '개발 내용', 'multiple': True, 'fields': [{'label': '제목', 'type': 'text'}, {'label': '세부 작업 내용', 'type': 'textarea'}]},
        ]
        markdown = '# 작업계획서\n\n## 작업 개요\n\n### 작 업 명\n\n점검\n\n### 구분\n\n□ 서버 ■ 개발\n\n## 개발 내용\n\n### 1번째 항목\n\n| 제목 |\n| --- |\n| 개선 |\n\n#### 세부 작업 내용\n\n작업 전\n\n![사진](/api/uploads/a.png)\n\n| 테스트 | 결과 |\n| --- | --- |\n| 점검 | 정상 |\n\n작업 후\n\n## 별도 참고\n\n누락하면 안 되는 내용'
        data, warnings = map_document(markdown, sections)
        self.assertNotIn('문서 본문', data)
        self.assertEqual(data['기본 정보']['작업명'], '점검')
        self.assertEqual(data['기본 정보']['구분'], '개발')
        row = data['개발 내용'][0]
        self.assertEqual(row['제목'], '개선')
        self.assertEqual(row['세부 작업 내용__format'], 'markdown')
        body = row['세부 작업 내용']
        self.assertLess(body.index('작업 전'), body.index('![사진]'))
        self.assertLess(body.index('![사진]'), body.index('| 테스트'))
        self.assertLess(body.index('| 테스트'), body.index('작업 후'))
        self.assertIn('누락하면 안 되는 내용', data[EXTRA][0]['내용'])
        self.assertTrue(warnings)

    def test_repeated_tables_and_unrecognized_field_survive(self):
        sections = [{'title': '작업 대상', 'multiple': True, 'fields': [{'label': 'IP', 'type': 'text'}]}]
        markdown = '## 작업 대상\n\n| IP |\n| --- |\n| 첫번째 |\n\n| IP |\n| --- |\n| 두번째 |\n\n#### 별도 메모\n\n보존'
        data, _ = map_document(markdown, sections)
        self.assertEqual([r['IP'] for r in data['작업 대상']], ['첫번째', '두번째'])
        self.assertIn('보존', data[EXTRA][0]['내용'])

    def test_unmapped_locations_are_reported_and_original_content_is_preserved(self):
        sections = [{'title': '작업 대상', 'multiple': True, 'fields': [{'label': 'IP', 'type': 'text'}]}]
        markdown = '''## 작업 대상

| IP | HOSTNAME |
| --- | --- |
| 10.0.0.1 | web01 |'''
        data, warnings = map_document(markdown, sections)
        content = data[EXTRA][0]['내용']
        self.assertIn('## 원본 내용', content)
        self.assertIn('### 작업 대상 / HOSTNAME', content)
        self.assertIn('web01', content)
        self.assertEqual(warnings[1]['field'], 'HOSTNAME')
        self.assertEqual(warnings[1]['source_preview'], 'web01')

    def test_test_plan_extra_column_does_not_fill_another_sections_note(self):
        sections = [
            {'title': '작업 대상', 'multiple': True, 'fields': [{'label': '비고', 'type': 'text'}]},
            {'title': '테스트 케이스', 'multiple': True, 'fields': [{'label': '설명', 'type': 'text'}]},
        ]
        markdown = '''## 테스트 계획

| 설명 | 비고 |
| --- | --- |
| 로그인 | 테스트 계획의 메모 |'''
        data, warnings = map_document(markdown, sections)
        self.assertEqual(data['테스트 케이스'][0]['설명'], '로그인')
        self.assertEqual(data['작업 대상'], [])
        self.assertIn('테스트 계획의 메모', data[EXTRA][0]['내용'])
        self.assertEqual(warnings[1]['field'], '비고')

    def test_unknown_section_is_not_guessed_from_shared_column(self):
        sections = [
            {'title': '작업 대상', 'multiple': True, 'fields': [{'label': '비고', 'type': 'text'}]},
            {'title': '테스트 케이스', 'multiple': True, 'fields': [{'label': '설명', 'type': 'text'}]},
        ]
        markdown = '''## 테스트 계획 상세

| 비고 |
| --- |
| 연결되지 않은 메모 |'''
        data, warnings = map_document(markdown, sections)
        self.assertEqual(data['작업 대상'], [])
        self.assertEqual(data['테스트 케이스'], [])
        self.assertIn('연결되지 않은 메모', data[EXTRA][0]['내용'])
        self.assertEqual(warnings[1]['section'], '테스트 계획 상세')

    def test_legacy_review_and_test_titles_map_to_current_sections(self):
        sections = [
            {'title': '검토의견', 'fields': [{'label': '성함/직책', 'type': 'text'}]},
            {'title': '테스트 케이스', 'fields': [{'label': '테스트 결과', 'type': 'textarea'}]},
        ]
        markdown = '''## 검토/서명

### 성함/직책

검토 담당자

## 테스트 결과

### 테스트 결과

정상 처리'''
        data, warnings = map_document(markdown, sections)
        self.assertEqual(data['검토의견']['성함/직책'], '검토 담당자')
        self.assertEqual(data['테스트 케이스']['테스트 결과'], '정상 처리')
        self.assertFalse(warnings)

    def test_old_success_and_failure_sections_map_to_one_test_section(self):
        sections = [
            {'title': '테스트 케이스', 'multiple': True, 'fields': [{'label': '테스트 결과', 'type': 'textarea'}]},
        ]
        markdown = '''## 테스트 케이스(성공)

### 테스트 결과

정상 처리

## 테스트 케이스(실패)

### 테스트 결과

실패 재현'''
        data, warnings = map_document(markdown, sections)
        self.assertEqual([row['테스트 결과'] for row in data['테스트 케이스']], ['정상 처리', '실패 재현'])
        self.assertFalse(warnings)

    def test_schedule_title_alias_maps_to_detail_procedure_section(self):
        sections = [{
            'title': '세부 작업 절차', 'multiple': True,
            'fields': [{'label': '시작 시간', 'type': 'text'}, {'label': '종료 시간', 'type': 'text'}],
        }]
        markdown = '''## 작업 시간표

| 시작 시간 | 종료 시간 |
| --- | --- |
| 17:00 | 18:00 |'''
        data, warnings = map_document(markdown, sections)
        self.assertEqual(data['세부 작업 절차'][0]['시작 시간'], '17:00')
        self.assertEqual(data['세부 작업 절차'][0]['종료 시간'], '18:00')
        self.assertFalse(warnings)

    def test_schedule_time_labels_with_reordered_words_map_to_canonical_fields(self):
        sections = [{
            'title': '세부 작업 절차', 'multiple': True,
            'fields': [
                {'label': '작업 시작 시간', 'type': 'text'},
                {'label': '작업 종료 시간', 'type': 'text'},
            ],
        }]
        markdown = '''## 세부 작업 절차

| 작업 시간 시작 | 작업 시간 종료 |
| --- | --- |
| 17:00 | 18:00 |'''
        data, warnings = map_document(markdown, sections)
        self.assertEqual(data['세부 작업 절차'][0]['작업 시작 시간'], '17:00')
        self.assertEqual(data['세부 작업 절차'][0]['작업 종료 시간'], '18:00')
        self.assertFalse(warnings)

    def test_assignee_title_maps_to_review_section_instead_of_extra_content(self):
        sections = [
            {
                'title': '작업자 정보', 'multiple': True,
                'fields': [{'label': '회사명', 'type': 'text'}, {'label': '역할', 'type': 'text'}],
            },
            {
                'title': '검토/서명', 'multiple': True,
                'fields': [
                    {'label': '소속', 'type': 'text'}, {'label': '성함', 'type': 'text'},
                    {'label': '검토의견', 'type': 'textarea'}, {'label': '서명', 'type': 'image'},
                ],
            },
        ]
        markdown = '''## 담당자

| No. | 소속 | 성함 | 검토의견 | 서명 |
| --- | --- | --- | --- | --- |
| 1 | 데이터활용팀 | 홍길동 | 확인 |  |'''
        data, warnings = map_document(markdown, sections)
        self.assertEqual(data['검토/서명'][0]['소속'], '데이터활용팀')
        self.assertEqual(data['검토/서명'][0]['성함'], '홍길동')
        self.assertNotIn(EXTRA, data)
        self.assertFalse(warnings)

    def test_result_time_and_work_period_map_to_current_result_template_fields(self):
        sections = [
            {
                'title': '기본 정보',
                'fields': [
                    {'label': '작업명', 'type': 'text'},
                    {'label': '작업 기간 (시작)', 'type': 'datetime'},
                    {'label': '작업 기간 (종료)', 'type': 'datetime'},
                ],
            },
            {
                'title': '테스트 케이스', 'multiple': True,
                'fields': [
                    {'label': '테스트 케이스 ID', 'type': 'text'},
                    {'label': '시간', 'type': 'text'},
                ],
            },
        ]
        markdown = '''## 작업 개요

| 항목 | 내용 |
| --- | --- |
| 작업명 | 결과서 점검 |
| 작업 일시 | 2026.09.16 17:30-18:00 |

## 테스트 결과

| 테스트 케이스 ID | 테스트 결과 / 시간 |
| --- | --- |
| TC-01 | 17:42 |'''
        data, warnings = map_document(markdown, sections)
        self.assertEqual(data['기본 정보']['작업명'], '결과서 점검')
        self.assertEqual(data['기본 정보']['작업 기간 (시작)'], '2026-09-16T17:30')
        self.assertEqual(data['기본 정보']['작업 기간 (종료)'], '2026-09-16T18:00')
        self.assertEqual(data['테스트 케이스'][0]['테스트 케이스 ID'], 'TC-01')
        self.assertEqual(data['테스트 케이스'][0]['시간'], '17:42')
        self.assertFalse(warnings)

    def test_operational_assignee_compound_name_and_role_maps_to_separate_fields(self):
        sections = [
            {
                'title': '검토/서명', 'multiple': True,
                'fields': [
                    {'label': '소속', 'type': 'text'},
                    {'label': '성함', 'type': 'text'},
                    {'label': '직책', 'type': 'text'},
                    {'label': '검토의견', 'type': 'textarea'},
                ],
            },
        ]
        markdown = '''## 담당자

| No. | 소속 | 성함 / 직책 | 검토의견 |
| --- | --- | --- | --- |
| 1 | 데이터운영팀 | 홍길동 / 선임 | 확인 완료 |'''
        data, warnings = map_document(markdown, sections)
        row = data['검토/서명'][0]
        self.assertEqual(row['소속'], '데이터운영팀')
        self.assertEqual(row['성함'], '홍길동')
        self.assertEqual(row['직책'], '선임')
        self.assertEqual(row['검토의견'], '확인 완료')
        self.assertFalse(warnings)

    def test_operational_assignee_title_with_name_and_role_maps_to_worker_info(self):
        sections = [
            {
                'title': '작업자 정보', 'multiple': True,
                'fields': [
                    {'label': '회사명', 'type': 'text'},
                    {'label': '성함/직책', 'type': 'text'},
                    {'label': '역할', 'type': 'text'},
                    {'label': '연락처', 'type': 'text'},
                ],
            },
            {
                'title': '검토/서명', 'multiple': True,
                'fields': [{'label': '소속', 'type': 'text'}, {'label': '성함', 'type': 'text'}],
            },
        ]
        markdown = '''## 담당자

| No. | 회사명 | 성함 / 직책 |
| --- | --- | --- |
| 1 | 데이터운영팀 | 홍길동 / 선임 |'''
        data, warnings = map_document(markdown, sections)
        self.assertEqual(data['작업자 정보'][0]['회사명'], '데이터운영팀')
        self.assertEqual(data['작업자 정보'][0]['성함/직책'], '홍길동 / 선임')
        self.assertFalse(warnings)

    def test_operational_assignee_separate_name_and_role_columns_are_combined(self):
        sections = [{
            'title': '작업자 정보', 'multiple': True,
            'fields': [
                {'label': '회사명', 'type': 'text'},
                {'label': '성함/직책', 'type': 'text'},
                {'label': '역할', 'type': 'text'},
            ],
        }]
        markdown = '''## 담당자

| No. | 회사명 | 성함 | 직책 | 역할 |
| --- | --- | --- | --- | --- |
| 1 | 데이터운영팀 | 홍길동 | 선임 | 서비스 배포 |'''
        data, warnings = map_document(markdown, sections)
        row = data['작업자 정보'][0]
        self.assertEqual(row['회사명'], '데이터운영팀')
        self.assertEqual(row['성함/직책'], '홍길동 / 선임')
        self.assertEqual(row['역할'], '서비스 배포')
        self.assertFalse(warnings)

    def test_operational_result_time_maps_to_result_time_label(self):
        sections = [
            {
                'title': '테스트 결과', 'multiple': True,
                'fields': [
                    {'label': '테스트 케이스 ID', 'type': 'text'},
                    {'label': '결과 시간', 'type': 'text'},
                ],
            },
        ]
        markdown = '''## 테스트 결과

| 테스트 케이스 ID | 테스트 결과 / 시간 |
| --- | --- |
| TC-02 | 18:05 |'''
        data, warnings = map_document(markdown, sections)
        self.assertEqual(data['테스트 결과'][0]['테스트 케이스 ID'], 'TC-02')
        self.assertEqual(data['테스트 결과'][0]['결과 시간'], '18:05')
        self.assertFalse(warnings)


class IncidentReportImportTests(unittest.TestCase):
    def test_hwp_blocks_keep_cause_solution_line_breaks_and_timeline_images(self):
        sections = [
            {
                'title': '장애 정보',
                'fields': [
                    {'label': '원인', 'type': 'textarea'},
                    {'label': '해결방안', 'type': 'textarea'},
                ],
            },
            {
                'title': '발생 경과 및 조치사항', 'multiple': True,
                'fields': [
                    {'label': '시간대', 'type': 'text'},
                    {'label': '상세내역', 'type': 'textarea'},
                ],
            },
        ]
        markdown = '''### 8번째 항목

| 1번째 내용 |
| --- |
| 원인 |

#### 2번째 내용

1.DB 서버 디스크 용량 초과

2.SSH 접속 무응답

### 9번째 항목

| 1번째 내용 | 2번째 내용 |
| --- | --- |
| 해결방안 | 1. 서버 재기동<br><br>2. 디스크 확장 |

### 10번째 항목

| 1번째 내용 |
| --- |
| 조치 |

#### 2번째 내용

| 시간대 | 상세내역 |
| --- | --- |
| 08:46 | 접속 불가 확인<br>![사진](/api/uploads/work_documents/images/sample.png) |
| 09:26 | 서비스 정상화 |'''

        data, warnings = map_document(markdown, sections)

        info = data['장애 정보']
        self.assertIn('1.DB 서버 디스크 용량 초과\n\n2.SSH 접속 무응답', info['원인'])
        self.assertIn('1. 서버 재기동\n\n2. 디스크 확장', info['해결방안'])
        self.assertEqual(info['원인__format'], 'markdown')
        self.assertEqual(info['해결방안__format'], 'markdown')
        timeline = data['발생 경과 및 조치사항']
        self.assertEqual([row['시간대'] for row in timeline], ['08:46', '09:26'])
        self.assertIn('![사진](', timeline[0]['상세내역'])
        self.assertIn('/api/uploads/work_documents/images/sample.png', timeline[0]['상세내역'])
        self.assertEqual(timeline[1]['상세내역'], '서비스 정상화')
        self.assertNotIn(EXTRA, data)
        self.assertFalse(warnings)
