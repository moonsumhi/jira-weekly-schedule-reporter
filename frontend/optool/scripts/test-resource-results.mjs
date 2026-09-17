import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/utils/inspectionResources.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
const { buildResourceResults, matchesResourceResult } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
const asset = (id, name = id) => ({ id, name, ip: '192.0.2.1', assetName: `서버 ${id}`, isDeleted: false });
const metric = (value) => ({ value, delta: null, basis: '요약' });
const record = (key, overrides = {}) => ({
  key, hostName: key, ip: '192.0.2.1', cpu: metric(0), ram: metric(40), disk: metric(50),
  asset: null, level: 'none', findings: [], logErrors: '0', actionItems: '-', ...overrides,
});
const month = (records, assets = [], source = {}) => ({ records, items: assets.map((asset) => ({ asset, records: [] })), source });

test('all imported results remain visible before targets are configured', () => {
  const rows = buildResourceResults(month([record('one'), record('two')]));
  assert.equal(rows.length, 2);
  assert.equal(rows.filter((row) => matchesResourceResult(row, 'unlinked')).length, 2);
  assert.equal(rows.filter((row) => matchesResourceResult(row, 'attention')).length, 0);
});
test('merge measured and unmeasured targets without duplicating an automatically connected asset', () => {
  const a = asset('a'), b = asset('b');
  const rows = buildResourceResults(month([record('one', { asset: a }), record('outside')], [a, b]));
  assert.equal(rows.length, 3);
  assert.deepEqual(rows.filter((row) => matchesResourceResult(row, 'missing')).map((row) => row.asset.id), ['b']);
  assert.equal(rows.filter((row) => matchesResourceResult(row, 'measured')).length, 2);
  assert.equal(rows.find((row) => row.asset?.id === 'a').regular, true);
});
test('zero readings are valid while missing readings require review', () => {
  const rows = buildResourceResults(month([record('zero'), record('missing', { cpu: metric(null) })]));
  assert.equal(rows[0].record.cpu.value, 0);
  assert.equal(rows[0].attention, false);
  assert.equal(rows[1].attention, true);
  assert.equal(rows[1].status.label, '측정값 없음');
  assert.ok(rows[1].notes.includes('CPU 측정값 없음'));
});
test('no source is waiting for registration, not a normal or zero-valued inspection', () => {
  const row = buildResourceResults(month([], [asset('a')], null))[0];
  assert.equal(row.record, null);
  assert.equal(row.status.label, '등록 대기');
  assert.equal(matchesResourceResult(row, 'measured'), false);
  assert.equal(matchesResourceResult(row, 'missing'), true);
});
test('duplicate measurements of one asset remain distinct and flag a review', () => {
  const a = asset('a');
  const rows = buildResourceResults(month([record('one', { asset: a }), record('two', { asset: a })], [a]));
  assert.equal(rows.length, 2);
  assert.notEqual(rows[0].key, rows[1].key);
  assert.ok(rows.every((row) => row.attention && row.record));
});
test('action and log findings are surfaced without flagging no-issue text', () => {
  const rows = buildResourceResults(month([
    record('fine', { actionItems: '이상 없음' }), record('action', { actionItems: '로그 정리 필요', logErrors: '2', findings: [{ label: 'RAM 82%' }] }),
    record('log', { logErrors: '3', level: 'warning', findings: [{ label: '로그 · 3' }] }),
    record('danger', { level: 'danger', cpu: metric(95), findings: [{ label: 'CPU 95%' }] }),
  ]));
  assert.equal(rows[0].attention, false);
  assert.equal(rows[1].attention, true);
  assert.deepEqual(rows[1].notes.slice(0, 2), ['로그 정리 필요', '로그 · 2']);
  assert.deepEqual(rows[2].notes, ['로그 · 3']);
  assert.ok(rows[3].status.rank < rows[2].status.rank);
});
test('filters and search include current asset names and action text without changing source data', () => {
  const data = month([record('uploaded-name', { asset: asset('a', '현재 호스트'), actionItems: '디스크 정리 필요' })]);
  const original = JSON.stringify(data);
  const row = buildResourceResults(data)[0];
  for (const search of [' UPLOADED-NAME ', '현재 호스트', '서버 a', '디스크 정리']) assert.ok(matchesResourceResult(row, 'attention', search));
  assert.equal(matchesResourceResult(row, 'unlinked', '현재 호스트'), false);
  assert.equal(matchesResourceResult(row, 'missing'), false);
  assert.equal(JSON.stringify(data), original);
});
