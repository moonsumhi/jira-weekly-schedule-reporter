import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import { pathToFileURL } from 'node:url'
import test from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/utils/time/kst.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
})
const luxonUrl = pathToFileURL(createRequire(import.meta.url).resolve('luxon')).href
const code = outputText.replace(/from ['"]luxon['"]/, `from '${luxonUrl}'`)
const { getIsoWeekKst, getIsoWeekPeriodKst, getCalendarMonthKst } = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`)

test('weekly report switches at Monday midnight in Korea', () => {
  assert.deepEqual(getIsoWeekKst(new Date('2026-11-08T14:59:59Z')), { year: 2026, week: 45 })
  assert.deepEqual(getIsoWeekKst(new Date('2026-11-08T15:00:00Z')), { year: 2026, week: 46 })
})

test('weekly report uses ISO week year across calendar year boundaries', () => {
  assert.deepEqual(getIsoWeekKst(new Date('2027-01-01T12:00:00+09:00')), { year: 2026, week: 53 })
  assert.deepEqual(getIsoWeekKst(new Date('2027-01-04T00:00:00+09:00')), { year: 2027, week: 1 })
  assert.deepEqual(getIsoWeekKst(new Date('2025-12-29T00:00:00+09:00')), { year: 2026, week: 1 })
})

test('displayed report period follows Korean Monday boundaries and spans year end', () => {
  assert.deepEqual(getIsoWeekPeriodKst(new Date('2026-11-08T14:59:59Z')), {
    year: 2026, week: 45, startDate: '2026-11-02', endDate: '2026-11-08',
  })
  assert.deepEqual(getIsoWeekPeriodKst(new Date('2026-11-08T15:00:00Z')), {
    year: 2026, week: 46, startDate: '2026-11-09', endDate: '2026-11-15',
  })
  assert.deepEqual(getIsoWeekPeriodKst(new Date('2027-01-01T12:00:00+09:00')), {
    year: 2026, week: 53, startDate: '2026-12-28', endDate: '2027-01-03',
  })
})

test('monthly shortcuts follow Korean midnight and use calendar year, not ISO week year', () => {
  assert.deepEqual(getCalendarMonthKst(new Date('2026-11-30T14:59:59Z')), { year: 2026, month: 11 })
  assert.deepEqual(getCalendarMonthKst(new Date('2026-11-30T15:00:00Z')), { year: 2026, month: 12 })
  assert.deepEqual(getCalendarMonthKst(new Date('2026-12-31T15:00:00Z')), { year: 2027, month: 1 })
  assert.deepEqual(getCalendarMonthKst(new Date('2025-12-29T00:00:00+09:00')), { year: 2025, month: 12 })
})
