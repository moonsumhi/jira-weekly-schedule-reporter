import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'
const source = await readFile(new URL('../src/utils/storageAssetForm.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } })
const { storageErrors, storageTextFields, storageCapacityText, storageRecordName, storageFormIdentity } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
const basic = { 서버명: '백업 스토리지', 구분: 'NAS', 자산번호: 'ST-001', 운영체제: 'Storage Model', 설명: '운영 백업' }
test('asset name is required; hostname, IP, capacity and links are optional', () => {
  assert.deepEqual(storageErrors(basic), {})
  assert.equal(Object.keys(storageErrors({})).length, 5)
  assert.equal(storageTextFields(basic).서버명, '백업 스토리지')
  assert.equal(storageTextFields(basic).호스트명, null)
  assert.equal(storageRecordName(basic), '백업 스토리지')
  assert.ok(storageErrors({ ...basic, 서버명: '', __name__: 'nas-01' }).서버명)
})
test('capacity comparisons respect decimal and binary units and preserve zero', () => {
  assert.deepEqual(storageErrors({ ...basic, 총물리용량: '2', 총물리용량단위: 'TiB', 사용가능용량: '2048', 사용가능용량단위: 'GiB' }), {})
  assert.ok(storageErrors({ ...basic, 총물리용량: '2', 총물리용량단위: 'TB', 사용가능용량: '2048', 사용가능용량단위: 'GiB' }).사용가능용량)
  assert.equal(storageCapacityText({ 사용가능용량: '0', 사용가능용량단위: 'GB' }, '사용가능용량'), '0 GB')
  assert.equal(storageCapacityText({}, '사용가능용량'), '미등록')
})
test('negative capacities, unknown units and fractional disk counts are actionable', () => {
  assert.ok(storageErrors({ ...basic, 총물리용량: '-1' }).총물리용량)
  assert.ok(storageErrors({ ...basic, 총물리용량: '1', 총물리용량단위: '??' }).총물리용량단위)
  assert.ok(storageErrors({ ...basic, 디스크수량: '1.5' }).디스크수량)
})
test('legacy asset names, serials and firmware versions remain strings', () => {
  const fields = storageTextFields({ ...basic, 서버명: '기존 표시명', SN: '000123', version: '1.10', 유지보수연락처: '00123' })
  assert.equal(fields.서버명, '기존 표시명')
  assert.equal(fields.SN, '000123')
  assert.equal(fields.version, '1.10')
  assert.equal(fields.유지보수연락처, '00123')
  assert.ok(!('__name__' in fields))
})

test('optional hostnames stay separate from asset names when created, cleared and reopened', () => {
  const withoutHost = { name: storageRecordName(basic), fields: storageTextFields(basic) }
  assert.deepEqual(storageFormIdentity(withoutHost), { __name__: '', 서버명: '백업 스토리지' })
  const named = { ...basic, __name__: 'nas-01' }
  const withHost = { name: storageRecordName(named), fields: storageTextFields(named) }
  assert.deepEqual(storageFormIdentity(withHost), { __name__: 'nas-01', 서버명: '백업 스토리지' })
  const cleared = { ...storageFormIdentity(withHost), __name__: '', 서버명: '변경된 자산명' }
  assert.equal(storageRecordName(cleared), '변경된 자산명')
  assert.equal(storageTextFields(cleared).호스트명, null)
  assert.deepEqual(storageFormIdentity({ name: 'legacy-host', fields: { 서버명: '기존 자산명' } }), { __name__: 'legacy-host', 서버명: '기존 자산명' })
  assert.deepEqual(storageFormIdentity({ name: '이름만 있는 기존 장비' }), { __name__: '이름만 있는 기존 장비', 서버명: '이름만 있는 기존 장비' })
})
