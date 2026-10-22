import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/utils/rackPlacement.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
})
const { placementRangeError } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
const racks = [{ rackId: 'large', totalU: 42 }, { rackId: 'small', totalU: 12 }]
const form = { rackId: 'large', startU: 40, heightU: 3, mountSide: 'FRONT' }

test('placement can occupy the last U but cannot extend beyond the rack', () => {
  assert.equal(placementRangeError(form, racks), '')
  assert.match(placementRangeError({ ...form, heightU: 4 }, racks), /42U/)
  assert.equal(placementRangeError({ ...form, startU: 42, heightU: 1 }, racks), '')
})
test('changing to a smaller rack immediately validates its capacity', () => {
  assert.match(placementRangeError({ ...form, rackId: 'small' }, racks), /12U/)
  assert.equal(placementRangeError({ ...form, rackId: 'small', startU: 10 }, racks), '')
  assert.match(placementRangeError({ ...form, rackId: 'missing' }, racks), /랙을 선택/)
})
test('blank, fractional, negative and nonfinite coordinates cannot be saved', () => {
  for (const field of ['startU', 'heightU']) {
    for (const value of ['', null, NaN, Infinity, 0, -1, 1.5]) {
      assert.match(placementRangeError({ ...form, [field]: value }, racks), /정수/)
    }
  }
})
test('both mounting sides are accepted while an unspecified side is rejected', () => {
  assert.equal(placementRangeError({ ...form, mountSide: 'REAR' }, racks), '')
  assert.match(placementRangeError({ ...form, mountSide: '' }, racks), /장착면/)
})
