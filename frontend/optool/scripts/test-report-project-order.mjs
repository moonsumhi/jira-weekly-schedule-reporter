import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/utils/reportProjectOrder.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } })
const { sortWorkItemsByDate } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

function issue(number, startDate, dueDate) {
  return { issueId: String(number), issueNumber: number, startDate, dueDate }
}

test('sort project work chronologically without mutating the report snapshot', () => {
  const items = [issue(3, '2026-10-08', '2026-10-09'), issue(1, '2026-10-01', '2026-10-02'),
    issue(2, '2026-10-05', '2026-10-06'), issue(4, '2026-10-10', '2026-10-11')]
  assert.deepEqual(sortWorkItemsByDate(items).map(i => i.issueNumber), [1, 2, 3, 4])
  assert.deepEqual(items.map(i => i.issueNumber), [3, 1, 2, 4])
})

test('use due date when start is missing, place undated work last, and compare timestamps consistently', () => {
  const items = [issue(5, null, null), issue(3, null, '2026-10-04'), issue(4, 'bad-date', null),
    issue(2, '2026-10-03T15:00:00Z', '2026-10-05'), issue(1, '2026-10-04T00:00:00+09:00', '2026-10-04')]
  assert.deepEqual(sortWorkItemsByDate(items).map(i => i.issueNumber), [1, 2, 3, 4, 5])
})

test('sort each status group independently without mutating or removing overlapping work', () => {
  const shared = issue(9, '2026-10-09', null)
  const completed = [issue(3, '2026-10-08', null), issue(1, null, '2026-10-01')]
  const inProgress = [shared, issue(2, '2026-10-02', null)]
  const upcoming = [shared, issue(4, null, '2026-10-04'), issue(5, null, null)]
  assert.deepEqual([completed, inProgress, upcoming].map(group => sortWorkItemsByDate(group).map(i => i.issueNumber)), [
    [1, 3], [2, 9], [4, 9, 5],
  ])
  assert.deepEqual(completed.map(i => i.issueNumber), [3, 1])
  assert.deepEqual(inProgress.map(i => i.issueNumber), [9, 2])
})
