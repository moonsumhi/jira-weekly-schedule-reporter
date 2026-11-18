import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'
async function load(path) {
  const source = await readFile(new URL(path, import.meta.url), 'utf8')
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } })
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
}
const { softwareErrors, softwareTextFields } = await load('../src/utils/softwareAssetForm.ts')
const { detailPayload } = await load('../src/utils/assetTypeDetails.ts')
const basic = { 운영체제: 'Nginx', 구분: 'WEB', 자산번호: '000123', 설명: 'ATOM 웹 요청 처리', version: '1.10' }
test('a first registration needs no duplicate name, IP, license or server', () => {
  assert.deepEqual(softwareErrors(basic), {})
  const fields = { ...softwareTextFields(basic), ...detailPayload(basic, '소프트웨어') }
  assert.equal(fields.서버명, 'Nginx')
  assert.equal(fields.version, '1.10')
  assert.deepEqual(fields.연결자산, [])
  assert.ok(!('__name__' in fields))
})
test('a distinct management name and identifier survive text serialization', () => {
  const values = { ...basic, __name__: '운영 웹 서버', 라이선스식별번호: '000124', 사용권형태: '구독', 라이선스기준: '사용자', 라이선스수량: '50' }
  const fields = { ...softwareTextFields(values), ...detailPayload(values, '소프트웨어') }
  assert.equal(fields.서버명, '운영 웹 서버')
  assert.equal(fields.운영체제, 'Nginx')
  assert.equal(fields.라이선스식별번호, '000124')
  assert.equal(fields.라이선스수량, 50)
})
test('invalid dates, reversed periods and license quantities are caught before save', () => {
  assert.ok(softwareErrors({ ...basic, 사용시작일: '2026-02-30' }).사용시작일)
  assert.ok(softwareErrors({ ...basic, 사용시작일: '2026-11-20', 사용권만료일: '2026-11-10' }).사용권만료일)
  assert.ok(softwareErrors({ ...basic, 라이선스수량: '-2' }).라이선스수량)
  assert.ok(softwareErrors({ ...basic, 라이선스수량: '50' }).라이선스기준)
  assert.deepEqual(softwareErrors({ ...basic, 라이선스수량: '0', 라이선스기준: '서버' }), {})
})
test('required fields reject whitespace and old classifications remain editable', () => {
  assert.ok(softwareErrors({ ...basic, 운영체제: '  ' }).운영체제)
  assert.deepEqual(softwareErrors({ ...basic, 구분: '기존 조직별 분류' }), {})
})

test('editing keeps a separate legacy asset name instead of overwriting it', () => {
  const fields = softwareTextFields({ ...basic, __name__: '새 관리명', 서버명: '기존 자산 표시명' })
  assert.equal(fields.서버명, '기존 자산 표시명')
})
