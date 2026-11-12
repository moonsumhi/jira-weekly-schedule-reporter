import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/utils/dutyPeriods.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } })
const { groupDutyPeriods, nextDutyPeriod, dutyPeriodStatus, loadDashboardDuties } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
const ms = iso => Date.parse(iso)
const duty = (id, date, start = '11:00', end = '12:00', assignee = 'me') => ({ id, assignee, start: `${date}T${start}:00+09:00`, end: `${date}T${end}:00+09:00` })

test('same-day shifts and adjacent dates form one period; a date without duty splits it', () => {
  const rows = [duty('later', '2026-11-19'), duty('b', '2026-11-16', '12:00', '13:00'), duty('first', '2026-11-15'), duty('a', '2026-11-16'), duty('third', '2026-11-17')]
  const original = structuredClone(rows)
  const groups = groupDutyPeriods([...rows, rows[0]])
  assert.deepEqual(groups.map(g => [g.days, g.shifts.map(s => s.id)]), [[3, ['first', 'a', 'b', 'third']], [1, ['later']]])
  assert.deepEqual(rows, original)
})

test('Korean dates are stable for UTC, naive UTC, and explicit offset timestamps across year end', () => {
  const groups = groupDutyPeriods([
    { id: 'dec', assignee: 'me', start: '2026-12-30T15:30:00', end: '2026-12-30T16:15:00Z' },
    duty('jan', '2027-01-01'),
  ])
  assert.equal(groups.length, 1)
  assert.equal(groups[0].days, 2)
  assert.equal(new Date(groups[0].startDay).toISOString().slice(0, 10), '2026-12-31')
  assert.equal(new Date(groups[0].endDay).toISOString().slice(0, 10), '2027-01-01')
})

test('overnight duty covers its actual days, while midnight end is exclusive', () => {
  const overnight = { id: 'night', assignee: 'me', start: '2026-11-15T23:00:00+09:00', end: '2026-11-16T01:00:00+09:00' }
  assert.equal(groupDutyPeriods([overnight, duty('next', '2026-11-17')])[0].days, 3)
  const midnight = { ...overnight, end: '2026-11-16T00:00:00+09:00' }
  assert.deepEqual(groupDutyPeriods([midnight, duty('next', '2026-11-17')]).map(g => g.days), [1, 1])
})

test('a period keeps its original dates between shifts and switches at its last end time', () => {
  const groups = groupDutyPeriods([duty('first', '2026-11-15'), duty('last', '2026-11-16'), duty('next', '2026-11-18')])
  assert.equal(dutyPeriodStatus(groups[0], ms('2026-11-12T10:00:00+09:00')), 'D-3')
  assert.equal(dutyPeriodStatus(groups[0], ms('2026-11-15T10:00:00+09:00')), 'D-Day')
  for (const time of ['2026-11-15T11:00:00+09:00', '2026-11-15T18:00:00+09:00', '2026-11-16T11:59:59+09:00']) {
    const group = nextDutyPeriod(groups, ms(time))
    assert.equal(group.id, 'first')
    assert.equal(group.days, 2)
    assert.equal(dutyPeriodStatus(group, ms(time)), '당직 중')
  }
  assert.equal(nextDutyPeriod(groups, ms('2026-11-16T12:00:00+09:00')).id, 'next')
  assert.equal(dutyPeriodStatus(groups[0], ms('2026-11-16T12:00:00+09:00')), '종료')
  assert.equal(nextDutyPeriod(groups, ms('2026-11-18T12:00:00+09:00')), undefined)
})

test('invalid ranges are ignored and only periods within the next 30 Korean days are selected', () => {
  const groups = groupDutyPeriods([
    duty('outside', '2026-12-13'), duty('boundary', '2026-12-12'),
    { ...duty('invalid', '2026-11-13'), start: 'not a date' },
    duty('reversed', '2026-11-13', '13:00', '12:00'), duty('empty', '2026-11-13', '12:00', '12:00'),
  ])
  assert.equal(groups[0].shifts.length, 2)
  assert.equal(nextDutyPeriod(groups, ms('2026-11-12T00:00:00+09:00')).id, 'boundary')
  assert.equal(nextDutyPeriod(groupDutyPeriods([duty('outside', '2026-12-13')]), ms('2026-11-12T00:00:00+09:00')), undefined)
})

function windowFetcher(rows, calls) {
  return async params => {
    calls.push(params)
    return rows.filter(row => ms(row.end) >= ms(params.start) && ms(row.start) <= ms(params.end))
  }
}

test('window loading recovers the entire current period across both boundaries and deduplicates overlaps', async () => {
  const rows = Array.from({ length: 70 }, (_, i) => duty(`d-${i}`, new Date(Date.UTC(2026, 9, 10 + i)).toISOString().slice(0, 10)))
  const calls = []
  const now = ms('2026-11-12T10:00:00+09:00')
  const loaded = await loadDashboardDuties(windowFetcher(rows, calls), a => a === 'me', now)
  const group = nextDutyPeriod(groupDutyPeriods(loaded), now)
  assert.equal(group.days, 70)
  assert.equal(group.shifts.length, 70)
  assert.equal(calls.length, 3)
  assert.equal(calls[0].start, '2026-10-12T15:00:00.000Z')
  assert.equal(calls[0].end, '2026-12-12T14:59:59.999Z')
})

test('ordinary schedules use one bounded request; other people cannot bridge a gap or extend it', async () => {
  const rows = [duty('mine', '2026-11-15'), duty('next', '2026-11-17'), duty('other', '2026-11-16', '11:00', '12:00', 'other'), duty('edge', '2026-12-12', '11:00', '12:00', 'other')]
  const calls = []
  const loaded = await loadDashboardDuties(windowFetcher(rows, calls), a => a === 'me', ms('2026-11-12T10:00:00+09:00'))
  assert.equal(calls.length, 1)
  assert.equal(groupDutyPeriods(loaded.filter(row => row.assignee === 'me')).length, 2)
  assert.deepEqual(await loadDashboardDuties(async () => [], () => true, Date.now()), [])
  await assert.rejects(loadDashboardDuties(async () => { throw new Error('offline') }, () => true, Date.now()), /offline/)
})
