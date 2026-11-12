import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/utils/dialogHistory.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
})
const { createDialogHistory } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

function mockBrowser() {
  const initial = { position: 4, current: '/pm/projects?filter=mine', back: '/dashboard' }
  const entries = [{ state: {}, url: '/dashboard' }, { state: initial, url: '/pm/projects?filter=mine' }]
  let index = 1
  const listeners = new Set()
  let queued
  let stopped = false
  const browser = {
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
  return { browser, initial, flush() { const fn = queued; queued = undefined; fn?.() },
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
