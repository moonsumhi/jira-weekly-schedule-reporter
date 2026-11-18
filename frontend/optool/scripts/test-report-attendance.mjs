import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/utils/reportAttendance.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } })
const { attendanceRemaining, validAttendanceDays } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

test('remaining days preserve decimal precision without floating point artifacts', () => {
  for (const [accrued, used, expected] of [
    ['15.123', '10', '5.123'], ['0.3', '0.1', '0.2'],
    ['12.3456', '7.222', '5.1236'], ['15.000', '15', '0'],
    [0, 0, '0'], ['0', '1.125', '-1.125'], ['1e-3', '.0001', '0.0009'],
    ['100000000000000000000', '.001', '99999999999999999999.999'],
  ]) assert.equal(attendanceRemaining(accrued, used), expected)
})

test('clearing either input removes the calculated balance', () => {
  for (const empty of ['', ' ', null, undefined]) {
    assert.equal(attendanceRemaining(empty, '1'), null)
    assert.equal(attendanceRemaining('15', empty), null)
    assert.equal(validAttendanceDays(empty), true)
  }
})

test('invalid or negative input is rejected but a negative balance is allowed', () => {
  for (const invalid of ['-1', 'NaN', 'Infinity', 'abc', '1,5', '1e999']) {
    assert.equal(validAttendanceDays(invalid), false)
    assert.equal(attendanceRemaining(invalid, '0'), null)
  }
  assert.equal(validAttendanceDays('5.123'), true)
  assert.equal(attendanceRemaining('1', '2'), '-1')
})
