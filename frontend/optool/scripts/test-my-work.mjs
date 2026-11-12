import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/utils/myWork.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } })
const { buildMyWork, workDeadline } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
const today = '2026-11-12'
const issue = (id, values = {}) => ({ id, projectKey: 'OPS', projectName: '운영', number: Number(id) || 1, title: `일감 ${id}`, assigneeId: 'me', reporterId: 'other', status: 'IN_PROGRESS', dueDate: null, ...values })
const sr = (id, values = {}) => ({ id, srNo: `SR-${id}`, title: `SR ${id}`, assigneeId: 'me', requesterId: 'other', status: 'ASSIGNED', plannedDueDate: null, desiredDueDate: null, ...values })

test('only my assigned unfinished work is shown, regardless of who reported or requested it', () => {
  const issues = [issue('mine'), issue('created', { reporterId: 'me', assigneeId: 'other' }), issue('unassigned', { assigneeId: null }), issue('done', { status: 'DONE' }), issue('legacy', { status: 'IMPLEMENTED' })]
  const srs = [sr('mine'), sr('requested', { requesterId: 'me', assigneeId: 'other' }), ...['DRAFT', 'COMPLETED', 'CONFIRMING', 'CLOSED', 'CANCELLED', 'REJECTED'].map(status => sr(status, { status }))]
  assert.deepEqual(buildMyWork(issues, srs, 'me', today).map(row => row.id).sort(), ['issue-mine', 'sr-mine'])
  assert.deepEqual(buildMyWork(issues, srs, undefined, today), [])
})

test('oldest overdue work appears first, followed by today, upcoming, paused and undated work', () => {
  const issues = [issue('undated'), issue('future', { dueDate: '2026-11-15' }), issue('recent', { dueDate: '2026-11-11' }), issue('today', { dueDate: today }), issue('old', { dueDate: '2026-11-01' })]
  const original = structuredClone(issues)
  const rows = buildMyWork(issues, [sr('paused', { status: 'ON_HOLD', plannedDueDate: '2026-10-01' }), sr('tomorrow', { plannedDueDate: '2026-11-13' })], 'me', today)
  assert.deepEqual(rows.map(row => row.id), ['issue-old', 'issue-recent', 'issue-today', 'sr-tomorrow', 'issue-future', 'sr-paused', 'issue-undated'])
  assert.deepEqual(rows.map(row => row.deadlineLabel), ['11일 지연', '1일 지연', '오늘 마감', '내일 마감', 'D-3', '보류 중', '마감일 없음'])
  assert.deepEqual(issues, original)
})

test('linked SR is shown once using its current planned deadline and status; PM-only users keep the issue', () => {
  const linked = issue('linked', { linkedSrId: 'request', dueDate: '2026-11-01' })
  const request = sr('request', { plannedDueDate: '2026-11-14T00:00:00', desiredDueDate: '2026-11-05' })
  const rows = buildMyWork([linked], [request], 'me', today)
  assert.equal(rows.length, 1)
  assert.equal(rows[0].id, 'sr-request')
  assert.equal(rows[0].dueDate, '2026-11-14')
  assert.equal(rows[0].deadlineLabel, 'D-2')
  assert.equal(buildMyWork([linked], [], 'me', today)[0].id, 'issue-linked')
})

test('SR desired deadline is used only when no planned deadline exists, and paused SR is not counted as delayed', () => {
  const rows = buildMyWork([], [sr('desired', { desiredDueDate: '2026-11-10T00:00:00Z' }), sr('held', { status: 'ON_HOLD', plannedDueDate: '2026-10-01' })], 'me', today)
  assert.equal(rows[0].deadlineLabel, '2일 지연')
  assert.equal(rows[1].urgency, 'paused')
  assert.equal(rows.filter(row => row.urgency === 'overdue').length, 1)
})

test('business dates advance only with the supplied Korean calendar day, including leap and year boundaries', () => {
  assert.equal(workDeadline('2026-11-12T00:00:00Z', '2026-11-12').deadlineLabel, '오늘 마감')
  assert.equal(workDeadline('2026-11-12T00:00:00Z', '2026-11-13').deadlineLabel, '1일 지연')
  assert.equal(workDeadline('2026-12-31', '2027-01-01').deadlineLabel, '1일 지연')
  assert.equal(workDeadline('2028-02-29', '2028-03-01').deadlineLabel, '1일 지연')
  for (const due of [null, '', 'invalid', '2026-02-29', '2026-13-01']) assert.equal(workDeadline(due, today).urgency, 'undated')
})

test('many recent issues cannot push an older overdue issue out of the list', () => {
  const rows = buildMyWork([...Array.from({ length: 60 }, (_, i) => issue(String(i))), issue('old', { dueDate: '2020-01-01' })], [], 'me', today)
  assert.equal(rows.length, 61)
  assert.equal(rows[0].id, 'issue-old')
})
