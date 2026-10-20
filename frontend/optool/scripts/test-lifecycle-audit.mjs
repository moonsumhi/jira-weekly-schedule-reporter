import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'
import ts from 'typescript'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const cache = new Map()
function load(name) {
  if (name === 'boot/axios') return { api: { get: async () => { throw new Error('offline test') } } }
  if (cache.has(name)) return cache.get(name)
  const file = path.join(root, name.endsWith('.json') ? name : name + '.ts')
  if (name.endsWith('.json')) return JSON.parse(fs.readFileSync(file, 'utf8'))
  const module = { exports: {} }
  cache.set(name, module.exports)
  const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true } }).outputText
  new Function('module', 'exports', 'require', code)(module, module.exports, load)
  return module.exports
}
const { getNetworkEos, getAutoEos } = load('src/services/eosDetection')
const { supportStatus, reviewedEosMap } = load('src/services/lifecycleAudit')
test('exact hardware and independent variants', () => {
  assert.equal(getNetworkEos('N9K-C9332C').date, '2029-01')
  for (const model of ['N9K-C9332C-GX','9372PX-E','ASR1001-HX','Palo Alto','Juniper','C9336C-FX2']) {
    assert.equal(getNetworkEos(model).status, 'REVIEW_REQUIRED', model)
    assert.equal(getNetworkEos(model).date, '', model)
  }
})
test('unverified versions and editions cannot inherit optimistic dates', () => {
  assert.equal(getAutoEos('Oracle','19.3').date, '2032-12')
  for (const [product, version] of [['Oracle','23c'],['SAP HANA','2.0'],['Windows 11','23H2'],['PostgreSQL','15.999']]) {
    assert.equal(getAutoEos(product, version).status, 'REVIEW_REQUIRED')
    assert.equal(getAutoEos(product, version).date, '')
  }
})
test('support remains valid through last day; month precision stays uncertain', () => {
  assert.equal(supportStatus('2029-01-31','2029-01-31'),'ACTIVE')
  assert.equal(supportStatus('2029-01-31','2029-02-01'),'EOS')
  assert.equal(supportStatus('2029-01','2029-01-05'),'REVIEW_REQUIRED')
})
test('offline and API results use same reviewed facts', () => {
  const map = reviewedEosMap({'Oracle|19c':'2027-04','SAP HANA|2.0':'2030-12'})
  assert.equal(map['Oracle|19c'],'2032-12')
  assert.equal(map['SAP HANA|2.0'],undefined)
  assert.equal(getAutoEos('VMware ESXi', '7.0 U3').date,'2025-10')
  assert.equal(getAutoEos('Rocky Linux','8.10').status,'MAINTENANCE')
})

const { getAutoEol } = load('src/services/eolData')
test('standard and extended support dates remain distinct and sourced', () => {
  assert.equal(getAutoEol('Oracle','19.3').date, '2029-12')
  assert.equal(getAutoEos('Oracle','19.3').date, '2032-12')
  assert.equal(getAutoEol('Amazon Linux','2023').date, '2027-06')
  assert.equal(getAutoEos('Amazon Linux','2023').date, '2029-06')
  assert.equal(getAutoEol('Ubuntu','22.04.3').date, '2027-05')
  assert.equal(getAutoEol('SAP HANA','SPS 08').status, 'REVIEW_REQUIRED')
})

test('unreviewed guidance cannot overwrite official dates or reappear', () => {
  const map = reviewedEosMap({'ESXi|7.0|technicalGuidance':'2099-01-01','ESXi|9.0|technicalGuidance':'2099-01-01'})
  assert.equal(map['ESXi|7.0|technicalGuidance'], '2027-04-02')
  assert.equal(map['ESXi|9.0|technicalGuidance'], undefined)
  assert.equal(getAutoEos('Windows 11', '23H2 Home/Pro').date, '2025-11')
  assert.equal(getAutoEos('Windows 11', '23H2 Enterprise/Education').date, '2026-11')
})
