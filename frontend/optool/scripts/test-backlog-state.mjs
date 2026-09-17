import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

// Run the production TypeScript without requiring a browser or another test runner.
const source = await readFile(new URL('../src/utils/pm/backlogState.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
})
const {
  backlogDueDay, backlogFilterKey, defaultBacklogFilters, hasBacklogFilters,
  matchesBacklogIssue, normalizeBacklogFilters, readBacklogFilters, writeBacklogFilters,
} = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

const issue = {
  title: 'git migration', number: 23, projectKey: 'PRE', linkedSrNo: 'SR-2026-1234',
  status: 'TODO', type: 'TASK', priority: 'HIGH', assigneeId: 'alice', dueDate: '2026-09-16T00:00:00',
}
const filters = overrides => ({ ...defaultBacklogFilters(), ...overrides })
const memoryStorage = () => {
  const data = new Map()
  return { getItem: key => data.get(key) ?? null, setItem: (key, value) => data.set(key, value) }
}

test('end date includes the entire Korean calendar day, including naive UTC timestamps', () => {
  const range = filters({ dateFrom: '2026-09-16', dateTo: '2026-09-16' })
  for (const dueDate of ['2026-09-16', '2026-09-16T00:00:00', '2026-09-15T15:00:00Z', '2026-09-16T14:59:59.999Z', '2026-09-16T23:59:59+09:00']) {
    assert.equal(matchesBacklogIssue({ ...issue, dueDate }, range), true, dueDate)
  }
  for (const dueDate of [null, 'invalid', '2026-09-15T14:59:59Z', '2026-09-16T15:00:00Z']) {
    assert.equal(matchesBacklogIssue({ ...issue, dueDate }, range), false, String(dueDate))
  }
  assert.equal(matchesBacklogIssue({ ...issue, dueDate: null }, filters()), true)
  assert.equal(backlogDueDay('2026-02-30'), null)
})

test('one-sided date ranges remain inclusive', () => {
  assert.equal(matchesBacklogIssue(issue, filters({ dateTo: '2026-09-16' })), true)
  assert.equal(matchesBacklogIssue(issue, filters({ dateFrom: '2026-09-16' })), true)
  assert.equal(matchesBacklogIssue(issue, filters({ dateFrom: '2026-09-17' })), false)
})

test('invalid saved values cannot become invisible filtering conditions', () => {
  assert.deepEqual(normalizeBacklogFilters({
    search: 123, statusTabs: ['REMOVED', '!REMOVED', 'DONE', '!DONE', 'DONE', '!TODO'],
    priority: 'REMOVED', type: 'REMOVED', assigneeId: ' ', dateFrom: '2026-02-30', dateTo: 'invalid',
  }), filters({ statusTabs: ['!TODO', 'DONE'] }))
  assert.deepEqual(normalizeBacklogFilters({ dateFrom: '2026-09-30', dateTo: '2026-09-01' }), filters())
  assert.equal(matchesBacklogIssue(issue, filters({ dateFrom: '2026-09-30', dateTo: '2026-09-01' })), true)
  assert.deepEqual(normalizeBacklogFilters({ status: 'TODO' }).statusTabs, ['TODO'])
  for (const value of [null, 'TODO', [], 5]) assert.deepEqual(normalizeBacklogFilters(value), filters())
  assert.equal(hasBacklogFilters(filters({ search: '  ' })), false)
})

test('combined filters and status exclusion preserve matching issues', () => {
  const combined = filters({ search: 'PRE-23', statusTabs: ['TODO', 'IN_PROGRESS', '!DONE'], priority: 'HIGH', type: 'TASK', assigneeId: 'alice' })
  assert.equal(matchesBacklogIssue(issue, combined), true)
  for (const query of [' Git Migration ', 'sr-2026-1234', 'pre-23']) {
    assert.equal(matchesBacklogIssue(issue, { ...combined, search: query }), true)
  }
  assert.equal(matchesBacklogIssue({ ...issue, projectKey: undefined }, combined, 'PRE'), true)
  assert.equal(matchesBacklogIssue({ ...issue, status: 'DONE' }, combined), false)
  assert.equal(matchesBacklogIssue({ ...issue, assigneeId: 'bob' }, combined), false)
  assert.equal(matchesBacklogIssue(issue, filters({ statusTabs: ['!TODO'] })), false)
  assert.equal(matchesBacklogIssue(issue, filters({ statusTabs: ['!DONE'] })), true)
})

test('preferences restore independently by account and project, including clearing', () => {
  const storage = memoryStorage()
  writeBacklogFilters('alice', 'project-a', filters({ search: 'migration' }), storage)
  writeBacklogFilters('alice', 'project-b', filters({ statusTabs: ['!DONE'] }), storage)
  writeBacklogFilters('bob', 'project-a', filters({ type: 'BUG' }), storage)
  assert.equal(readBacklogFilters('alice', 'project-a', storage).filters.search, 'migration')
  assert.deepEqual(readBacklogFilters('alice', 'project-b', storage).filters.statusTabs, ['!DONE'])
  assert.equal(readBacklogFilters('bob', 'project-a', storage).filters.type, 'BUG')
  assert.deepEqual(readBacklogFilters('bob', 'project-b', storage).filters, filters())
  writeBacklogFilters('alice', 'project-a', filters(), storage)
  assert.deepEqual(readBacklogFilters('alice', 'project-a', storage).filters, filters())
  assert.equal(readBacklogFilters('bob', 'project-a', storage).filters.type, 'BUG')
  assert.notEqual(backlogFilterKey('a:b', 'c'), backlogFilterKey('a', 'b:c'))
})

test('legacy filters with no account owner are reset once without deleting the old data', () => {
  const storage = memoryStorage()
  storage.setItem('backlog_filter_project-a', JSON.stringify({ search: 'another user' }))
  const restored = readBacklogFilters('alice', 'project-a', storage)
  assert.equal(restored.resetLegacy, true)
  assert.deepEqual(restored.filters, filters())
  writeBacklogFilters('alice', 'project-a', restored.filters, storage)
  assert.equal(readBacklogFilters('alice', 'project-a', storage).resetLegacy, false)
  assert.ok(storage.getItem('backlog_filter_project-a'))
})

test('corrupt or unavailable storage does not prevent loading the backlog', () => {
  const storage = memoryStorage()
  storage.setItem(backlogFilterKey('alice', 'project-a'), '{corrupt')
  assert.deepEqual(readBacklogFilters('alice', 'project-a', storage).filters, filters())
  const blocked = { getItem() { throw Error('blocked') }, setItem() { throw Error('quota') } }
  assert.deepEqual(readBacklogFilters('alice', 'project-a', blocked).filters, filters())
  assert.doesNotThrow(() => writeBacklogFilters('alice', 'project-a', filters(), blocked))
})
