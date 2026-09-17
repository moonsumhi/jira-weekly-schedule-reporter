import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

const source = await readFile(
  new URL('../src/utils/inspectionMeasurements.ts', import.meta.url),
  'utf8',
);
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
const { importedMeasurement, measurementBasis, networkMeasurement } = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`
);

test('single readings in either legacy slot stay a single measurement', () => {
  assert.deepEqual(importedMeasurement({ beforeVal: '16 GB', beforePct: '62%' }), {
    value: '16 GB',
    pct: 62,
  });
  assert.deepEqual(importedMeasurement({ afterVal: '16 GB', afterPct: '58%' }), {
    value: '16 GB',
    pct: 58,
  });
});
test('keep the existing representative value, with zero as a valid reading', () => {
  const data = { beforeVal: '8 GB', beforePct: '62%', afterVal: '0', afterPct: '0%' };
  const before = JSON.stringify(data);
  assert.deepEqual(importedMeasurement(data), { value: '0', pct: 0 });
  assert.equal(JSON.stringify(data), before);
});
test('missing and invalid readings remain missing and never become zero', () => {
  for (const value of ['', '-', 'N/A', '%', 'NaN', '-3%', '105%', '0x10']) {
    assert.equal(importedMeasurement({ afterPct: value }).pct, null, value);
  }
  assert.deepEqual(importedMeasurement(undefined), { value: '', pct: null });
  assert.deepEqual(
    importedMeasurement({ beforeVal: '4 GB', beforePct: '40%', afterVal: 'N/A', afterPct: 'N/A' }),
    { value: '4 GB', pct: 40 },
  );
  assert.equal(importedMeasurement({ afterPct: '0.32' }).pct, 32);
});
test('hide before/after wording in legacy snapshots without changing stored values', () => {
  const metric = { value: 82, basis: '점검 전', before: 82, after: null };
  const before = JSON.stringify(metric);
  assert.equal(measurementBasis(metric), '측정값');
  assert.equal(measurementBasis({ basis: '점검 후' }), '측정값');
  assert.equal(measurementBasis({ basis: '파일시스템 최대' }), '파일시스템 최대');
  assert.equal(JSON.stringify(metric), before);
});
test('network displays a single available value with the same compatibility order', () => {
  assert.equal(networkMeasurement({ networkBefore: '정상' }), '정상');
  assert.equal(networkMeasurement({ networkBefore: '이전 값', networkAfter: '측정값' }), '측정값');
  assert.equal(networkMeasurement({ networkBefore: '-', networkAfter: 'N/A' }), '—');
});
