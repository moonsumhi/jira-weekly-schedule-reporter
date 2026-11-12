import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/utils/dashboardLayout.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
})
const { resolveDashboardLayout } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
const base = ['pm', 'weeklyReport', 'calendar', 'favorites']

test('new dashboard shows my work and weekly report above calendar and favorites', () => {
  assert.deepEqual(resolveDashboardLayout([], {}, base), { order: base, sizes: {} })
})

test('retiring D-Day introduces the requested arrangement without changing custom sizes', () => {
  const savedOrder = ['resource', 'pm', 'dday', 'watch', 'eos', 'calendar']
  const savedSizes = { pm: { w: 2, h: 1 }, calendar: { w: 3, h: 3 }, dday: { w: 3, h: 2 } }
  const original = structuredClone({ savedOrder, savedSizes })
  assert.deepEqual(resolveDashboardLayout(savedOrder, savedSizes, base), { order: base, sizes: savedSizes })
  assert.deepEqual({ savedOrder, savedSizes }, original)
})

test('older preferences without a calendar also receive only currently available cards', () => {
  const layout = resolveDashboardLayout(['watch', 'pm', 'dday'], {}, base)
  assert.deepEqual(layout.order, base)
  assert.equal(layout.order.includes('dday'), false)
})

test('all four cards retain later custom positions and sizes on reload', () => {
  const order = ['favorites', 'calendar', 'weeklyReport', 'pm']
  const sizes = { favorites: { w: 3, h: 1 }, weeklyReport: { w: 2, h: 3 }, calendar: { w: 1, h: 2 } }
  assert.deepEqual(resolveDashboardLayout(order, sizes, base), { order, sizes })
})

test('PM-only shortcuts are never introduced for users without PM access', () => {
  assert.deepEqual(resolveDashboardLayout(['watch', 'dday', 'calendar', 'pm'], {}, ['pm', 'calendar']).order, ['pm', 'calendar'])
  assert.deepEqual(resolveDashboardLayout(base, {}, ['calendar']).order, ['calendar'])
})

test('newly granted PM access introduces the requested shortcut arrangement', () => {
  const sizes = { calendar: { w: 3, h: 2 } }
  assert.deepEqual(resolveDashboardLayout(['calendar', 'pm'], sizes, base), { order: base, sizes })
})

test('retired, hidden and duplicate cards are filtered and newly available cards appended', () => {
  const sizes = { favorites: { w: 1, h: 1 } }
  const layout = resolveDashboardLayout(['favorites', 'watch', 'calendar', 'resource', 'eos', 'favorites'], sizes, base)
  assert.deepEqual(layout, { order: ['favorites', 'calendar', 'pm', 'weeklyReport'], sizes })
})
