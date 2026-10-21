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
  assert.equal(getAutoEos('Oracle','19.3').date, '')
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
  assert.equal(map['Oracle|19c'],undefined)
  assert.equal(map['SAP HANA|2.0'],undefined)
  assert.equal(getAutoEos('VMware ESXi', '7.0 U3').date,'')
  assert.equal(getAutoEos('Rocky Linux','8.10').status,'MAINTENANCE')
})

const { getAutoEol } = load('src/services/eolData')
test('intermediate support phases are not service end or life end', () => {
  assert.equal(getAutoEol('Oracle','19.3').date, '')
  assert.equal(getAutoEos('Oracle','19.3').date, '')
  assert.equal(getAutoEol('Amazon Linux','2023').date, '')
  assert.equal(getAutoEos('Amazon Linux','2023').date, '2029-06')
  assert.equal(getAutoEol('Ubuntu','22.04.3').date, '')
  assert.equal(getAutoEol('SAP HANA','SPS 08').status, 'REVIEW_REQUIRED')
})

test('unreviewed guidance cannot overwrite official dates or reappear', () => {
  const map = reviewedEosMap({'ESXi|7.0|technicalGuidance':'2099-01-01','ESXi|9.0|technicalGuidance':'2099-01-01'})
  assert.equal(map['ESXi|7.0|technicalGuidance'], '2027-04-02')
  assert.equal(map['ESXi|9.0|technicalGuidance'], undefined)
  assert.equal(getAutoEos('Windows 11', '23H2 Home/Pro').date, '2025-11')
  assert.equal(getAutoEos('Windows 11', '23H2 Enterprise/Education').date, '2026-11')
})

test('all intermediate service milestones stay visible but cannot drive EoS', () => {
  for (const [product, version] of [['Oracle','19c'],['MySQL','8.0'],['RHEL','8'],['Ubuntu','22.04'],['ESXi','7.0'],['SAP HANA','1.0']]) {
    const result = getAutoEos(product, version)
    assert.equal(result.date, '')
    assert.equal(result.status, 'REVIEW_REQUIRED')
    assert.ok(result.milestone.date)
    assert.ok(result.note)
  }
  assert.ok(getAutoEol('PostgreSQL','15').date)
  assert.equal(getAutoEol('Windows Server','2022').date, '')
})

test('APIC bundles, servers and software retain independent service dates', () => {
  for (const [gen, end] of [[1,'2021-10'],[2,'2024-06'],[3,'2028-10'],[4,'2031-06']]) {
    for (const prefix of ['', 'SERVER-', 'CLUSTER-']) for (const size of ['M','L']) {
      const pid = `Cisco APIC-${prefix}${size}${gen}`
      assert.equal(getNetworkEos(pid).date, end)
      assert.equal(getAutoEos(pid, '').date, end)
    }
  }
  assert.equal(getNetworkEos('APIC-SERVER-M3=').date, '2028-10')
  assert.equal(getAutoEol('APIC-CLUSTER-M3', '').date, '')
  assert.equal(getAutoEol('APIC-CLUSTER-M3', '').status, 'REVIEW_REQUIRED')
  for (const pid of ['APIC-CLUSTER-M30','APIC-M3-EX','APIC-M2-240G','APIC-SERVER-G5']) assert.equal(getNetworkEos(pid).date, '')
  assert.equal(getAutoEos('APIC','5.2(8g)').date, '2026-12')
  assert.equal(getAutoEos('Cisco ACI Switch','15.3(2b)').date, '2026-12')
  assert.equal(getAutoEol('Cisco APIC','5.2(8g)').date, '')
  for (const version of ['5','5.20','6.0','5.2-invalid']) assert.equal(getAutoEos('Cisco APIC',version).date, '')
  assert.equal(getNetworkEos('SE-NODE-G2').date, '2028-10')
  assert.equal(getNetworkEos('ND-NODE-L4').date, '2031-06')
})

const { localLifecycleDocument, lifecycleDocumentNotice, assetLifecycleEvidence } = load('src/services/lifecycleReferences')
test('all vendor evidence resolves to bundled PDFs without falling back to external URLs', () => {
  const audit = load('src/data/lifecycle_audit.json')
  const sources = new Set()
  const collect = value => {
    if (!value || typeof value !== 'object') return
    for (const [key, child] of Object.entries(value)) {
      if (key === 'source' && typeof child === 'string' && child.startsWith('https://')) sources.add(child)
      else collect(child)
    }
  }
  collect(audit)
  for (const source of sources) {
    const doc = localLifecycleDocument(source)
    assert.ok(doc || lifecycleDocumentNotice(source), source)
    if (doc) {
      assert.match(doc.path, /^\/reference\/[^.]+\.pdf$/)
      assert.ok(fs.readFileSync(path.join(root, 'public', doc.path)).subarray(0, 5).equals(Buffer.from('%PDF-')))
    }
  }
  for (const source of ['https://unregistered.example/doc.pdf', '//outside.example/file.pdf', 'javascript:alert(1)', undefined]) {
    assert.equal(localLifecycleDocument(source), null)
  }
})
test('status icons use the same normalized product evidence as lifecycle calculations', () => {
  for (const fields of [
    {'운영체제':'Cisco APIC','version':'5.2(8g)'},
    {'운영체제':'APIC-CLUSTER-M3'},
    {'운영체제':'PostgreSQL','version':'15.2'},
    {'운영체제':'Windows Server','version':2022},
    {'운영체제':'VMware ESXi','version':'7.0 U3'},
  ]) {
    assert.ok(localLifecycleDocument(assetLifecycleEvidence(fields, 'eos')?.source), JSON.stringify(fields))
  }
  assert.ok(localLifecycleDocument(assetLifecycleEvidence({'운영체제':'PostgreSQL','version':'15.2'}, 'eol')?.source))
  assert.equal(assetLifecycleEvidence(undefined, 'eos'), null)
  assert.equal(assetLifecycleEvidence({'운영체제':'VMware ESXi','version':'7.0 U3'}, 'eol'), null)
})
