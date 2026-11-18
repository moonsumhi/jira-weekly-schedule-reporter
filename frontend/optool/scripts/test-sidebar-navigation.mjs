import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/utils/sidebarNavigation.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } })
const { isSidebarLinkActive } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
const categories = ['서버', '네트워크', '스토리지', '소프트웨어', '정보보호시스템', 'DBMS', 'VMware', '랙']
const links = ['/asset/list', ...categories.map(category => '/asset/list?category=' + encodeURIComponent(category))]
const active = query => links.filter(link => isSidebarLinkActive(link, { path: '/asset/list', query }, links))

test('each asset category highlights only its own menu, including network and racks', () => {
  for (const category of categories) {
    assert.deepEqual(active({ category }), ['/asset/list?category=' + encodeURIComponent(category)])
  }
})

test('unfiltered assets highlight All even with search, pagination or a detail drawer', () => {
  for (const query of [{}, { search: 'web', page: '2' }, { assetId: 'asset-1', detailTab: 'system-info' }, { category: '' }]) {
    assert.deepEqual(active(query), ['/asset/list'])
  }
})

test('category selection survives additional filters and detail drawer parameters', () => {
  assert.deepEqual(active({ category: '네트워크', search: 'switch', page: '2', assetId: 'asset-1' }), [links[2]])
})

test('query variants on other menus also select the most specific match', () => {
  const peers = ['/reports', '/reports?kind=PLAN', '/reports?kind=RESULT']
  const route = { path: '/reports', query: { kind: 'RESULT', month: '2026-11' } }
  assert.deepEqual(peers.filter(link => isSidebarLinkActive(link, route, peers)), [peers[2]])
})

test('nested pages retain their parent selection and explicit menu aliases', () => {
  assert.equal(isSidebarLinkActive('/pm/projects', { path: '/pm/projects/123/backlog', query: {} }), true)
  assert.equal(isSidebarLinkActive('/pm/projects', { path: '/pm/projects-other', query: {} }), false)
  assert.equal(isSidebarLinkActive('/pm/monthly-report', { path: '/pm/monthly-report/123', query: {}, activeMenuLink: '/pm/monthly-report' }), true)
  assert.equal(isSidebarLinkActive('/spaces/rooms', { path: '/spaces/plans/123', query: {}, activeMenuLink: '/spaces/rooms' }), true)
})

test('unmatched paths, placeholders and external destinations are inactive', () => {
  const route = { path: '/asset/list', query: {} }
  for (const link of [undefined, '#', '', '/pm/projects', 'https://example.com/asset/list', '//example.com/asset/list']) {
    assert.equal(isSidebarLinkActive(link, route, links), false)
  }
})
