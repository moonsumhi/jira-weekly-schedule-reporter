import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/utils/assetTypeDetails.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } })
const { detailPayload, detailEditValue, detailList } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

test('storage fields survive save/edit with arrays, zero and separate units', () => {
  const first = detailPayload({ 총물리용량: '20.5', 총물리용량단위: 'TB', 사용가능용량: '0', 사용가능용량단위: 'GiB', 연결방식: '["NFS","SMB"]', 연결자산: '["a","b"]' }, '스토리지')
  const second = detailPayload(Object.fromEntries(Object.entries(first).map(([key, value]) => [key, detailEditValue(value)])), '스토리지')
  assert.deepEqual(second, first)
  assert.equal(second.사용가능용량, 0)
  assert.deepEqual(second.연결자산, ['a', 'b'])
})
test('software keeps identifier zeros and precise edition text', () => {
  const result = detailPayload({ 에디션: '1.10', 라이선스식별번호: '000123', 라이선스수량: '50', 라이선스기준: '사용자', 사용권형태: '구독', 사용권만료일: '2027-11-01' }, '소프트웨어')
  assert.equal(result.에디션, '1.10')
  assert.equal(result.라이선스식별번호, '000123')
  assert.equal(result.라이선스수량, 50)
  assert.equal(result.사용권만료일, '2027-11-01')
})
test('perpetual clears hidden expiry and other categories remain unaffected', () => {
  assert.equal(detailPayload({ 사용권형태: '영구', 사용권만료일: '2027-11-01' }, '소프트웨어').사용권만료일, null)
  assert.deepEqual(detailPayload({ 연결자산: '["a"]' }, '서버'), {})
})
test('Excel lists and empty selections serialize without losing values', () => {
  assert.deepEqual(detailList('NFS, SMB; FC'), ['NFS', 'SMB', 'FC'])
  assert.deepEqual(detailList('[]'), [])
  assert.equal(detailEditValue(0), '0')
  assert.deepEqual(detailPayload({ 연결자산: '[]' }, '소프트웨어').연결자산, [])
})
