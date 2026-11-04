import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/utils/reportProjectOrder.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } })
const { projectTimeline } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

function issue(number, startDate, dueDate) {
  return { issueId: String(number), issueNumber: number, startDate, dueDate }
}

test('sort project work across completion and upcoming groups in chronological order', () => {
  const completed = [issue(3, '2026-10-08', '2026-10-09'), issue(1, '2026-10-01', '2026-10-02')]
  const inProgress = [issue(2, '2026-10-05', '2026-10-06')]
  const upcoming = [issue(4, '2026-10-10', '2026-10-11')]
  assert.deepEqual(projectTimeline({ completed, inProgress, upcoming }).map(i => i.issueNumber), [1, 2, 3, 4])
  assert.deepEqual(completed.map(i => i.issueNumber), [3, 1])
})

test('use due date when start is missing, place undated work last, and compare timestamps consistently', () => {
  const items = [issue(5, null, null), issue(3, null, '2026-10-04'), issue(4, 'bad-date', null),
    issue(2, '2026-10-03T15:00:00Z', '2026-10-05'), issue(1, '2026-10-04T00:00:00+09:00', '2026-10-04')]
  assert.deepEqual(projectTimeline({ completed: items, inProgress: [], upcoming: [] }).map(i => i.issueNumber), [1, 2, 3, 4, 5])
})
