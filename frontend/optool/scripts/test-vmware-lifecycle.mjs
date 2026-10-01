import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'
import ts from 'typescript'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const cache = new Map()
const snapshot = JSON.parse(fs.readFileSync(path.join(root, '../../app/data/eos_map_snapshot.json'), 'utf8')).data
function load(name) {
  if (name === 'boot/axios') return { api: { get: async () => ({ data: snapshot }) } }
  if (cache.has(name)) return cache.get(name)
  const file = path.join(root, name.endsWith('.json') ? name : `${name}.ts`)
  if (file.endsWith('.json')) return JSON.parse(fs.readFileSync(file, 'utf8'))
  const compiled = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  }).outputText
  const module = { exports: {} }
  cache.set(name, module.exports)
  new Function('module', 'exports', 'require', compiled)(module, module.exports, load)
  return module.exports
}

const { OS_TREE } = load('src/constants/osVersions')
const { normalizeVmware, getVmwareGuidanceDate, getVmwareGeneralSupportDate } = load('src/services/vmwareLifecycle')
const { detectOsFamily, detectOsMajor, getAutoEos } = load('src/services/eosDetection')
const { getAutoEol } = load('src/services/eolData')
const { fetchEosMap } = load('src/services/eosData')

test('VMware 제품/버전 선택은 API 로드 전후 모두 일반 지원 종료일을 제공하고 EoL을 추정하지 않는다', async () => {
  for (const online of [false, true]) {
    if (online) await fetchEosMap()
    for (const [dist, versions] of Object.entries(OS_TREE.VMware)) {
      assert.equal(detectOsFamily(dist), 'VMware')
      for (const [major, minors] of Object.entries(versions)) {
        for (const version of minors) {
          const expected = snapshot[`${dist}|${version}`]
          assert.ok(expected)
          assert.equal(getAutoEos(dist, version)?.date, expected)
          assert.equal(getAutoEol(dist, version), null)
          assert.equal(detectOsMajor(dist, version), major)
        }
      }
    }
  }
})

test('기존 VMware 제품명과 업데이트 표기를 지원 주기로 인식한다', () => {
  for (const dist of ['ESXi', 'VMware ESXi', 'esxi', 'VMware ESX']) {
    for (const version of ['7.0', '7.0 U3', '7.0 Update 3w', '7.0.3']) {
      assert.deepEqual(normalizeVmware(dist, version), { dist: 'ESXi', version: '7.0' })
      assert.equal(getAutoEos(dist, version)?.date, '2025-10')
      assert.equal(getAutoEol(dist, version), null)
    }
  }
  assert.equal(getAutoEos('ESXi 7.0', '')?.date, '2025-10')
  assert.equal(getAutoEol('VMware vCenter Server 7.0', ''), null)
  assert.equal(detectOsMajor('VMware ESXi', '7.0 U3'), '7')
})

test('버전 누락/미지원 버전은 종료일을 추측하지 않는다', () => {
  for (const version of ['', '99.0', 'unknown', '7garbage']) {
    assert.equal(getAutoEos('ESXi', version), null)
    assert.equal(getAutoEol('ESXi', version), null)
  }
  assert.equal(normalizeVmware('Ubuntu', '22.04'), null)
  assert.equal(getAutoEol('Ubuntu', '22.04')?.date, '2027-04')
})

test('VMware 메이저 선택은 마이너를 임의로 지정하지 않는다', () => {
  for (const dist of ['ESXi', 'vCenter']) {
    for (const major of Object.keys(OS_TREE.VMware[dist])) {
      assert.deepEqual(normalizeVmware(dist, major), { dist, version: major })
      assert.equal(detectOsMajor(dist, major), major)
      assert.equal(getAutoEos(dist, major), null)
      assert.equal(getAutoEol(dist, major), null)
    }
    assert.equal(detectOsMajor(dist, '6.5'), '6')
    assert.equal(detectOsMajor(dist, '6.7'), '6')
    assert.deepEqual(normalizeVmware(dist, '6.x'), { dist, version: '6' })
  }
})

test('일반 지원 종료와 계약 조건부 기술 가이드를 구분한다', () => {
  for (const dist of ['ESXi', 'VMware vCenter Server']) {
    assert.equal(getVmwareGeneralSupportDate(dist, '7.0 U3'), '2025-10-02')
    assert.equal(getVmwareGuidanceDate(dist, '7.0 U3'), '2027-04-02')
    assert.equal(getVmwareGuidanceDate(dist, '6.5'), '2023-11-15')
    assert.equal(getVmwareGuidanceDate(dist, '8.0'), '2029-10-11')
    for (const version of ['', '7', 'unknown']) {
      assert.equal(getVmwareGuidanceDate(dist, version), null)
    }
  }
  assert.equal(getVmwareGuidanceDate('Ubuntu', '7.0'), null)
})

test('프런트엔드 오프라인 맵은 자동 생성된 서버 VMware 맵과 일치한다', () => {
  const fallback = load('src/data/vmware_lifecycle_snapshot.json')
  const vmware = Object.fromEntries(Object.entries(snapshot).filter(([key]) => /^(ESXi|vCenter)\|/.test(key)))
  assert.deepEqual(fallback, vmware)
  assert.equal(getVmwareGuidanceDate('ESXi', '9.0'), snapshot['ESXi|9.0|technicalGuidance'])
})
