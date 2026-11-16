import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

async function moduleUrl(file, imports = {}) {
  let source = await readFile(new URL(file, import.meta.url), 'utf8')
  for (const [specifier, url] of Object.entries(imports)) source = source.replace(`'${specifier}'`, `'${url}'`)
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  })
  return `data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`
}
const scrollUrl = await moduleUrl('../src/utils/dialogScroll.ts')
const { createDialogHistory } = await import(await moduleUrl('../src/utils/dialogHistory.ts', { './dialogScroll': scrollUrl }))
const { routeScrollBehavior } = await import(await moduleUrl('../src/utils/routeScroll.ts'))

function mockBrowser() {
  const initial = { position: 4, current: '/pm/projects?filter=mine', back: '/dashboard' }
  const entries = [{ state: {}, url: '/dashboard' }, { state: initial, url: '/pm/projects?filter=mine' }]
  let index = 1
  const listeners = new Set()
  let queued
  let stopped = false
  let nextFrame = 0
  const frames = new Map()
  const list = { scrollLeft: 120, scrollTop: 360, isConnected: true,
    scrollTo({ left, top }) { this.scrollLeft = left; this.scrollTop = top } }
  const browser = {
    scrollX: 24, scrollY: 840,
    scrollTo({ left, top }) { this.scrollX = left; this.scrollY = top },
    document: { querySelectorAll() { return [list] } },
    requestAnimationFrame(fn) { frames.set(++nextFrame, fn); return nextFrame },
    cancelAnimationFrame(id) { frames.delete(id) },
    location: { href: entries[index].url },
    history: {
      get state() { return entries[index].state },
      pushState(state, _, url) { entries.splice(++index, Infinity, { state, url }); browser.location.href = url },
      replaceState(state, _, url) { entries[index] = { state, url } },
      back() { queued = () => {
        index--
        browser.location.href = entries[index].url
        stopped = false
        const event = { state: entries[index].state, stopImmediatePropagation() { stopped = true } }
        for (const listener of [...listeners]) {
          listener(event)
          if (stopped) break
        }
      } },
    },
    addEventListener(_, handler) { listeners.add(handler) },
    removeEventListener(_, handler) { listeners.delete(handler) },
  }
  return { browser, initial, list,
    flushFrames() { const tasks = [...frames.values()]; frames.clear(); tasks.forEach(fn => fn()) },
    flush() { const fn = queued; queued = undefined; fn?.() },
    get index() { return index }, get stopped() { return stopped } }
}

test('Back closes the dialog without changing the URL or router state; next Back navigates', async () => {
  const m = mockBrowser()
  let closed = 0
  const dialog = createDialogHistory(m.browser, () => closed++)
  await dialog.setOpen(true)
  await dialog.setOpen(true)
  assert.equal(m.index, 2)
  assert.equal(m.browser.history.state.position, 4)
  m.browser.history.back(); m.flush()
  assert.equal(closed, 1)
  assert.equal(m.browser.location.href, '/pm/projects?filter=mine')
  assert.deepEqual(m.browser.history.state, m.initial)
  assert.equal(m.stopped, true)
  m.browser.history.back(); m.flush()
  assert.equal(m.browser.location.href, '/dashboard')
  assert.equal(closed, 1)
})

test('manual close waits for history cleanup before intentional navigation', async () => {
  const m = mockBrowser()
  const dialog = createDialogHistory(m.browser, () => assert.fail('manual close must not notify Back'))
  await dialog.setOpen(true)
  let completed = false
  const closing = dialog.close().then(() => { completed = true })
  await Promise.resolve()
  assert.equal(completed, false)
  m.flush(); await closing
  assert.equal(m.index, 1)
  m.browser.history.back(); m.flush()
  assert.equal(m.browser.location.href, '/dashboard')
})

test('rapid reopen and dispose consume only their own temporary entries', async () => {
  const m = mockBrowser()
  const dialog = createDialogHistory(m.browser, () => assert.fail('unexpected close'))
  await dialog.setOpen(true)
  const closing = dialog.setOpen(false)
  const opening = dialog.setOpen(true)
  m.flush(); await closing; await opening
  assert.equal(m.index, 2)
  dialog.dispose(); m.flush()
  assert.equal(m.index, 1)
})

test('nested details close one at a time and preserve the underlying dialog', async () => {
  const m = mockBrowser()
  let parentClosed = 0, childClosed = 0
  const parent = createDialogHistory(m.browser, () => parentClosed++)
  const child = createDialogHistory(m.browser, () => childClosed++)
  await parent.setOpen(true)
  await child.setOpen(true)
  assert.equal(m.index, 3)
  m.browser.history.back(); m.flush()
  assert.equal(childClosed, 1)
  assert.equal(parentClosed, 0)
  m.browser.history.back(); m.flush()
  assert.equal(parentClosed, 1)
})

test('a declined close can restore the entry for another Back attempt', async () => {
  const m = mockBrowser()
  let attempts = 0
  const dialog = createDialogHistory(m.browser, () => {
    attempts++
    void dialog.setOpen(true)
  })
  await dialog.setOpen(true)
  m.browser.history.back(); m.flush()
  assert.equal(attempts, 1)
  assert.equal(m.index, 2)
  m.browser.history.back(); m.flush()
  assert.equal(attempts, 2)
  dialog.dispose(); m.flush()
})

test('Back restores page and nested list scroll after the dialog unlocks the page', async () => {
  const m = mockBrowser()
  const dialog = createDialogHistory(m.browser, () => {})
  await dialog.setOpen(true)
  m.browser.history.back(); m.flush()
  // Simulate scroll changes during dialog focus/scroll-lock cleanup.
  m.browser.scrollX = 0; m.browser.scrollY = 0
  m.list.scrollLeft = 0; m.list.scrollTop = 0
  m.flushFrames()
  assert.equal(m.browser.scrollX, 24)
  assert.equal(m.browser.scrollY, 840)
  assert.equal(m.list.scrollLeft, 120)
  assert.equal(m.list.scrollTop, 360)
  // QDialog's hide event follows the closing animation.
  m.browser.scrollY = 0
  dialog.restoreScroll()
  assert.equal(m.browser.scrollY, 840)
})

test('manual close restores scroll and does not add a navigation', async () => {
  const m = mockBrowser()
  const dialog = createDialogHistory(m.browser, () => assert.fail('unexpected Back notification'))
  await dialog.setOpen(true)
  const closing = dialog.close()
  m.flush(); await closing
  m.browser.scrollY = 0
  m.flushFrames()
  assert.equal(m.index, 1)
  assert.equal(m.browser.scrollY, 840)
})

test('intentional navigation cancels restoration of the previous page', async () => {
  const m = mockBrowser()
  const dialog = createDialogHistory(m.browser, () => {})
  await dialog.setOpen(true)
  const closing = dialog.close()
  m.flush(); await closing
  m.browser.location.href = '/pm/sr/linked-sr'
  m.browser.scrollY = 0
  m.flushFrames(); dialog.restoreScroll()
  assert.equal(m.browser.scrollY, 0)
})

test('a child dialog restores its parent list position independently', async () => {
  const m = mockBrowser()
  const parent = createDialogHistory(m.browser, () => {})
  const child = createDialogHistory(m.browser, () => {})
  await parent.setOpen(true)
  m.list.scrollTop = 640
  await child.setOpen(true)
  m.browser.history.back(); m.flush()
  m.list.scrollTop = 0
  m.flushFrames()
  assert.equal(m.list.scrollTop, 640)
  m.browser.history.back(); m.flush(); m.flushFrames()
  assert.equal(m.list.scrollTop, 360)
})

test('late close restoration leaves a reopened dialog and removed elements alone', async () => {
  const m = mockBrowser()
  const dialog = createDialogHistory(m.browser, () => {})
  await dialog.setOpen(true)
  const closing = dialog.close()
  m.flush(); await closing
  await dialog.setOpen(true)
  m.browser.scrollY = 123
  m.flushFrames(); dialog.restoreScroll()
  assert.equal(m.browser.scrollY, 123)
  m.browser.history.back(); m.flush()
  m.list.isConnected = false; m.list.scrollTop = 0
  m.flushFrames()
  assert.equal(m.list.scrollTop, 0)
})

test('router keeps dialog and query-only updates in place but restores real Back navigation', () => {
  const page = { path: '/pm/projects', hash: '', fullPath: '/pm/projects?issueId=123', query: { issueId: '123' }, matched: [{}] }
  assert.equal(routeScrollBehavior(page, page, { left: 0, top: 0 }), false)
  assert.equal(routeScrollBehavior({ ...page, fullPath: '/pm/projects', query: {} }, page, null), false)
  const other = { path: '/dashboard', hash: '', fullPath: '/dashboard', query: {}, matched: [{}] }
  assert.deepEqual(routeScrollBehavior(other, page, { left: 20, top: 700 }), { left: 20, top: 700 })
  assert.deepEqual(routeScrollBehavior(other, page, null), { left: 0, top: 0 })
  const filtered = { ...page, fullPath: '/pm/projects?search=ops', query: { search: 'ops' } }
  assert.deepEqual(routeScrollBehavior(filtered, page, null), { left: 0, top: 0 })
  assert.deepEqual(routeScrollBehavior(filtered, page, { left: 0, top: 320 }), { left: 0, top: 320 })
  assert.deepEqual(routeScrollBehavior(page, { ...page, matched: [] }, { left: 0, top: 400 }), { left: 0, top: 400 })
})
