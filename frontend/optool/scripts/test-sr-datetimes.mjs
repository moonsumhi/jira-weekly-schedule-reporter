import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import { pathToFileURL } from 'node:url';
import ts from 'typescript';

const require = createRequire(import.meta.url);
const source = await readFile(new URL('../src/utils/time/kst.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
const resolved = outputText.replace(/from ['"]luxon['"]/, `from '${pathToFileURL(require.resolve('luxon')).href}'`);
const { formatKst, formatKstLocal } = await import(
  `data:text/javascript;base64,${Buffer.from(resolved).toString('base64')}`,
);

test('SR request times retain their entered Korean date and time', () => {
  assert.equal(formatKstLocal('2026-09-21T09:15'), '2026. 9. 21. 오전 9:15:00');
  assert.equal(formatKstLocal('2026-09-21T23:50'), '2026. 9. 21. 오후 11:50:00');
  assert.equal(formatKstLocal('2026-09-21T00:05:30'), '2026. 9. 21. 오전 12:05:30');
});

test('explicit timestamps convert to Korea without adding nine hours twice', () => {
  for (const value of ['2026-09-21T09:15:00+09:00', '2026-09-21T09:15:00+0900',
    '2026-09-21T00:15:00Z', '2026-09-20T17:15:00-07:00']) {
    assert.equal(formatKstLocal(value), '2026. 9. 21. 오전 9:15:00', value);
  }
});

test('system timestamps still interpret legacy timezone-free values as UTC', () => {
  assert.equal(formatKst('2026-09-21T00:15:00'), '2026. 9. 21. 오전 9:15:00');
  assert.equal(formatKst('2026-09-21T00:15:00Z'), '2026. 9. 21. 오전 9:15:00');
});

test('invalid legacy values remain readable', () => {
  assert.equal(formatKstLocal('시간 미상'), '시간 미상');
});
