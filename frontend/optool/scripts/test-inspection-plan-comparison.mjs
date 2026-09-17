import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/utils/inspectionPlanComparison.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
})
const { inspectionPlanComparison } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
const task = (id, values = {}) => ({
  issueId: id, month: '2026-09', state: 'ACTIVE', common: false,
  assets: [{ id: 'asset-1', name: 'server' }], plannedStart: '2026-09-17', plannedEnd: '2026-09-17',
  issue: { title: '예정 작업', assigneeId: 'person-1', assigneeName: '담당자', status: 'TODO' },
  ...values,
})

test('legacy results without a submitted plan do not invent a baseline', () => {
  assert.equal(inspectionPlanComparison({ tasks: [task('one')] }), null)
  assert.equal(inspectionPlanComparison({ tasks: [], plan: null }), null)
})

test('identifies completion, missing, cancelled, rolled and added work by occurrence', () => {
  const planned = ['done', 'pending', 'missing', 'cancelled', 'rolled'].map(id => task(id))
  const actual = [
    task('done', { issue: { ...planned[0].issue, status: 'DONE' } }),
    task('pending'), task('cancelled', { state: 'EXCLUDED' }), task('rolled', { state: 'ROLLED' }),
    task('extra'), task('excluded-extra', { state: 'EXCLUDED' }),
  ]
  const snapshot = { tasks: actual, plan: { tasks: planned } }
  const before = structuredClone(snapshot)
  const result = inspectionPlanComparison(snapshot)
  assert.deepEqual([result.planned, result.completed, result.pending, result.omitted, result.rolled, result.added], [5, 1, 1, 2, 1, 1])
  assert.deepEqual(result.changes.map(row => row.task.issueId), ['missing', 'cancelled', 'rolled', 'extra'])
  assert.deepEqual(snapshot, before)
})

test('task renames are changes, while server renames and asset ordering are not', () => {
  const planned = task('one', { assets: [{ id: 'a', name: 'old-a' }, { id: 'b', name: 'old-b' }] })
  const actual = { ...planned, assets: [{ id: 'b', name: 'new-b' }, { id: 'a', name: 'new-a' }] }
  assert.equal(inspectionPlanComparison({ plan: { tasks: [planned] }, tasks: [actual] }).changes.length, 0)
  actual.issue = { ...actual.issue, title: '변경된 작업', assigneeId: 'person-2' }
  actual.plannedEnd = '2026-09-18'
  actual.assets = [{ id: 'c', name: 'new-server' }]
  const result = inspectionPlanComparison({ plan: { tasks: [planned] }, tasks: [actual] })
  assert.equal(result.added, 0)
  assert.deepEqual(result.changes[0].changes, ['작업명 변경', '담당자 변경', '대상 자산 변경', '일정 변경'])
})

test('same task in another month cannot count as execution of the submitted occurrence', () => {
  const result = inspectionPlanComparison({ plan: { tasks: [task('one')] }, tasks: [task('one', { month: '2026-10' })] })
  assert.equal(result.omitted, 1)
  assert.equal(result.added, 1)
})
