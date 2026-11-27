const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const { test } = require('node:test')
const ts = require('typescript')
const source = fs.readFileSync(path.join(__dirname, '../src/utils/searchResultClick.ts'), 'utf8')
const exportsUnderTest = {}
vm.runInNewContext(ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText, { exports: exportsUnderTest })
const { preserveSearchResultClick } = exportsUnderTest

test('pressing a result keeps the composing search focused until its click', () => {
  const document = { activeElement: null }
  const input = { ownerDocument: document }
  document.activeElement = input
  let prevented = false
  preserveSearchResultClick({ button: 0, preventDefault() { prevented = true } }, input)
  assert.equal(prevented, true)
})

test('right click, unfocused search and absent input keep normal behavior', () => {
  const input = { ownerDocument: { activeElement: null } }
  const event = { button: 0, preventDefault() { throw new Error('unexpected prevention') } }
  preserveSearchResultClick(event, input)
  preserveSearchResultClick(event, null)
  input.ownerDocument.activeElement = input
  preserveSearchResultClick({ ...event, button: 2 }, input)
})
