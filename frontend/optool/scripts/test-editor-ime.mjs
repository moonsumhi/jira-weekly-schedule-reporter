import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createEditorModelSync } from '../src/utils/editorModelSync.ts'

function fixture(t) {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  let text = ''
  const emitted = []
  const writes = []
  let settled = 0
  const sync = createEditorModelSync({
    read: () => text,
    write(value) {
      writes.push(value)
      text = value
      // Toast UI fires change synchronously for setMarkdown as well.
      sync.publish()
    },
    emit(value) { emitted.push(value) },
    onCompositionSettled() { settled += 1 },
  })
  return {
    sync, emitted, writes,
    setText(value) { text = value },
    get text() { return text },
    get settled() { return settled },
  }
}

test('Korean composition publishes the final syllable after editor microtasks', async t => {
  const f = fixture(t)
  f.sync.compositionStart()
  f.setText('ㄱ')
  f.sync.publish()
  f.sync.compositionEnd()
  assert.deepEqual(f.emitted, [])
  assert.equal(f.sync.composing, true)

  // The capture listener runs before the editor commits the final DOM change.
  await Promise.resolve().then(() => {
    f.setText('가')
    f.sync.publish()
    f.sync.applyExternal('ㄱ')
  })
  assert.deepEqual(f.writes, [])
  t.mock.timers.tick(1)
  assert.deepEqual(f.emitted, ['가'])
  f.sync.applyExternal(f.emitted.at(-1))
  assert.equal(f.text, '가')
  assert.deepEqual(f.writes, [])
})

test('a delayed Vue model echo cannot overwrite newer editor input', t => {
  const f = fixture(t)
  f.setText('가')
  f.sync.publish()
  f.setText('각')
  f.sync.applyExternal('가')
  assert.equal(f.text, '각')
  assert.deepEqual(f.writes, [])
})

test('consecutive syllables cancel the previous pending composition end', t => {
  const f = fixture(t)
  f.sync.compositionStart()
  f.setText('가')
  f.sync.compositionEnd()
  f.sync.compositionStart()
  f.setText('가ㄴ')
  t.mock.timers.tick(1)
  f.sync.publish()
  assert.equal(f.sync.composing, true)
  assert.deepEqual(f.emitted, [])
  f.setText('가나')
  f.sync.compositionEnd()
  t.mock.timers.tick(1)
  assert.deepEqual(f.emitted, ['가나'])
})

test('external loading and clearing work without emitting changes back', t => {
  const f = fixture(t)
  f.sync.applyExternal('불러온 문서')
  f.sync.applyExternal('')
  assert.deepEqual(f.writes, ['불러온 문서', ''])
  assert.deepEqual(f.emitted, [])
  f.setText('수정')
  f.sync.publish()
  f.sync.applyExternal('다른 문서')
  f.sync.applyExternal('수정')
  assert.equal(f.text, '수정')
})

test('unmount cancels pending publication and menu updates', t => {
  const f = fixture(t)
  f.sync.compositionStart()
  f.setText('가')
  f.sync.compositionEnd()
  f.sync.dispose()
  t.mock.timers.tick(1)
  f.sync.publish()
  assert.deepEqual(f.emitted, [])
  assert.equal(f.settled, 0)
})
