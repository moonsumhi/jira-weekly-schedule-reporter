const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const ts = require('typescript')
const { parse, compileScript } = require('@vue/compiler-sfc')
const { createRenderer, defineComponent, h, ref, nextTick } = require('vue')

test('live Korean search does not rerender the composing input', async () => {
  const filename = path.join(__dirname, '../src/pages/pm/components/ProjectSearchInput.vue')
  const { descriptor } = parse(fs.readFileSync(filename, 'utf8'))
  const compiled = compileScript(descriptor, { id: 'ime-test', inlineTemplate: true })
  const exports = {}
  vm.runInNewContext(ts.transpileModule(compiled.content, {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText, { exports, require })
  const native = { value: '' }
  let renders = 0
  const QInput = defineComponent({
    props: ['modelValue'],
    setup(props, { expose, slots }) {
      expose({ nativeEl: native })
      return () => {
        renders++
        native.value = props.modelValue
        return h('input', {}, slots.append?.())
      }
    },
  })
  const node = type => ({ type, children: [], props: {}, style: {} })
  const renderer = createRenderer({
    createElement: node, createText: node, createComment: node,
    insert(child, parent) { parent.children.push(child) }, remove() {},
    setText() {}, setElementText() {}, parentNode() { return null }, nextSibling() { return null },
    patchProp(el, key, old, value) { el.props[key] = value },
  })
  const query = ref('')
  const onSearch = value => { query.value = value }
  const app = renderer.createApp({ render: () => h('main', [
    h(exports.default, { onSearch }), h('results', { query: query.value }),
  ]) })
  app.component('q-input', QInput)
  app.component('q-icon', { render: () => h('icon') })
  const root = node('root')
  app.mount(root)
  const wrapper = root.children[0].children[0]
  for (const value of ['ㄱ', '가', '간', '관리', '']) {
    native.value = value
    wrapper.props.onInputCapture({ target: native })
    await nextTick()
    assert.equal(query.value, value)
    assert.equal(native.value, value)
    assert.equal(renders, 1, 'search results must not rerender QInput during composition')
  }
  app.unmount()
})
