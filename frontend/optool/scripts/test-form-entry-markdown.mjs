import assert from 'node:assert/strict'
import { formEntryMarkdown, markdownFileName, hasOriginalForm, synchronizedDocument } from '../src/utils/formEntryMarkdown.ts'
import { comparisonMarkdown, comparisonFormatKey, workResultFieldGroups } from '../src/utils/workResultFields.ts'

const sections = [
  { title: '기본 정보', fields: [{ label: '내용', type: 'textarea' }, { label: '승인', type: 'boolean' }, { label: '횟수', type: 'number' }] },
  { title: '작업 절차', multiple: true, imagesBelow: true, fields: [
    { label: '설명', type: 'textarea', pairedImage: '사진' }, { label: '사진', type: 'image' },
  ] },
]
const markdown = formEntryMarkdown('점검 계획', sections, {
  '기본 정보': { '내용': '한글\r\n<script>alert(1)</script>', '승인': false, '횟수': 0 },
  '작업 절차': [{ '설명': 'A|B\n다음 줄', '사진': ['/api/uploads/점검 (1).png', 'https://example.com/after.png'] }],
}, 'http://localhost:9000')
assert.ok(markdown.startsWith('# 점검 계획\n'))
assert.ok(markdown.includes('| 항목 | 내용 |'))
assert.ok(markdown.includes('| 내용 | 한글<br>&lt;script&gt;alert\\(1\\)&lt;/script&gt; |'))
assert.ok(markdown.includes('| 승인 | false |'))
assert.ok(markdown.includes('| 횟수 | 0 |'))
assert.ok(markdown.includes('A\\|B<br>다음 줄'))
assert.ok(markdown.includes('![사진](<http://localhost:9000/api/uploads/'))
assert.ok(markdown.includes('![사진](<https://example.com/after.png>)'))
assert.equal((markdown.match(/!\[사진\]/g) || []).length, 2)
assert.ok(!markdown.includes('<script>'))
assert.ok(!formEntryMarkdown('빈 문서', sections, {}, 'http://localhost:9000').includes('undefined'))
assert.ok(formEntryMarkdown('구형 단일 행', [sections[1]], { '작업 절차': { '설명': '보존' } }, 'http://localhost:9000').includes('| No. | 설명 | 사진 |'))
assert.equal(markdownFileName('점검:/계획?\n', 'abc123'), '점검__계획___abc123.md')
console.log('Markdown export checks passed: Korean text, line breaks, tables, images, false/zero, empty and legacy data, filenames.')

const resultSection = { title: '작업 결과', multiple: true, fields: [
  { label: '작업 전', type: 'textarea', pairedImage: '작업 전 사진' },
  { label: '작업 후', type: 'textarea', pairedImage: '작업 후 사진' },
  { label: '작업 전 사진', type: 'image' }, { label: '작업 후 사진', type: 'image' },
] }
const groups = workResultFieldGroups(resultSection)
assert.deepEqual(groups.map(group => group.label), ['작업 전', '작업 후'])
const legacy = { '작업 전': '*그대로* <설정>', '작업 전 사진': ['/api/uploads/a.png', '/api/uploads/b.png'] }
const merged = comparisonMarkdown(legacy, groups[0].fields)
assert.ok(merged.startsWith('\\*그대로\\* &lt;설정&gt;'))
assert.equal((merged.match(/!\[/g) || []).length, 2)
const mixed = '작업 전 설명\n\n![사진](</api/uploads/pm/a.png>)\n\n![사진1](</api/uploads/pm/b.png>)\n\n이어서 설명'
const saved = { '작업 전': mixed, [comparisonFormatKey('작업 전')]: 'markdown', '작업 전 사진': [] }
assert.equal(comparisonMarkdown(saved, groups[0].fields), mixed)
const exported = formEntryMarkdown('결과서', [resultSection], { '작업 결과': [saved] }, 'http://localhost:9000')
assert.ok(exported.includes('![사진](<http://localhost:9000/api/uploads/pm/a.png>)'))
assert.ok(exported.indexOf('작업 전 설명') < exported.indexOf('![사진]'))
assert.ok(exported.indexOf('![사진1]') < exported.indexOf('이어서 설명'))
assert.ok(!exported.includes('__format'))
assert.ok(!exported.includes('#### 작업 전 사진'))
console.log('Mixed text/image checks passed: legacy merge, round-trip, photo ordering, export and hidden format metadata.')

const wholeDocument = { '문서 본문': [{ '제목': '원본 문서', '내용': mixed, '내용__format': 'markdown' }] }
const documentExport = formEntryMarkdown('양식', [], wholeDocument, 'http://localhost:9000')
assert.ok(documentExport.startsWith('작업 전 설명'))
assert.ok(documentExport.indexOf('![사진1]') < documentExport.indexOf('이어서 설명'))
assert.ok(!documentExport.includes('__format'))
assert.ok(documentExport.includes('http://localhost:9000/api/uploads/pm/a.png'))
assert.deepEqual(workResultFieldGroups({ title: '문서 본문', fields: [{ label: '제목', type: 'text' }, { label: '내용', type: 'textarea' }] }).map(group => group.label), ['', '내용'])
console.log('Whole Markdown document preservation checks passed.')

const originalForm = { '기본 정보': { '내용': '수정 전', '승인': false, '횟수': 0 }, '작업 절차': [{ '설명': '사진 앞', '사진': ['/api/uploads/a.png'] }] }
const firstSave = synchronizedDocument('계획서', sections, originalForm, 'http://localhost:9000')
assert.ok(hasOriginalForm(sections, firstSave))
assert.deepEqual(firstSave['기본 정보'], originalForm['기본 정보'])
const nextSave = synchronizedDocument('계획서', sections, { ...firstSave, '기본 정보': { ...firstSave['기본 정보'], '내용': '수정 후' } }, 'http://localhost:9000')
assert.ok(nextSave['문서 본문'][0]['내용'].includes('수정 후'))
assert.ok(!nextSave['문서 본문'][0]['내용'].includes('수정 전'))
assert.ok(nextSave['문서 본문'][0]['내용'].includes('![사진]'))
assert.equal(nextSave['기본 정보']['승인'], false)
assert.equal(nextSave['기본 정보']['횟수'], 0)
assert.ok(!hasOriginalForm(sections, wholeDocument))
assert.equal(originalForm['기본 정보']['내용'], '수정 전')
console.log('Original form and Markdown synchronization checks passed.')
