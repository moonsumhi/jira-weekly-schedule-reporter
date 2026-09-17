import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

const source = await readFile(
  new URL('../src/utils/inspectionReportResources.ts', import.meta.url),
  'utf8',
);
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
const { resourceReview, inspectionActionNote } = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`
);
const metric = (value) => ({ value, delta: null, basis: '점검 후' });
const server = (key, cpu = 20, ram = 40, disk = 60) => ({
  key,
  cpu: metric(cpu),
  ram: metric(ram),
  disk: metric(disk),
  level: 'none',
  findings: [],
  actionItems: '-',
  action: null,
});
const snapshot = (servers, warning = 80, danger = 90) => ({
  servers,
  thresholds: { warning, danger, version: 1 },
});

test('show only affected resources and put danger before warning and missing measurements', () => {
  const result = resourceReview(
    snapshot([
      server('normal'),
      server('missing', 0, null),
      server('warning', 80),
      server('danger', 79, 90, 95),
    ]),
  );
  assert.deepEqual(
    result.map((r) => r.server.key),
    ['danger', 'warning', 'missing'],
  );
  assert.deepEqual(
    result[0].metrics.map((m) => [m.kind, m.level]),
    [
      ['ram', 'danger'],
      ['disk', 'danger'],
    ],
  );
  assert.deepEqual(
    result[1].metrics.map((m) => [m.kind, m.level]),
    [['cpu', 'warning']],
  );
});

test('zero is a valid measurement and a partial missing measurement stays visible', () => {
  const result = resourceReview(snapshot([server('zero', 0, 0, 0), server('partial', null, 0, 1)]));
  assert.equal(result.length, 1);
  assert.equal(result[0].server.key, 'partial');
  assert.deepEqual(
    result[0].metrics.map((m) => [m.kind, m.level]),
    [['cpu', 'missing']],
  );
});

test('use each report’s saved thresholds, including the exact warning and danger boundaries', () => {
  const result = resourceReview(
    snapshot([server('normal', 84), server('warning', 85), server('danger', 95)], 85, 95),
  );
  assert.deepEqual(
    result.map((r) => [r.server.key, r.metrics[0].level]),
    [
      ['danger', 'danger'],
      ['warning', 'warning'],
    ],
  );
});

test('hardware and other findings remain visible after merging action details into resources', () => {
  const row = {
    ...server('hardware'),
    level: 'danger',
    findings: [{ label: 'H/W · Disk LED', level: 'danger' }],
    asset: null,
  };
  const result = resourceReview(
    snapshot([
      server('unlinked-normal'),
      { ...server('security'), findings: [{ label: '보안 · 취약', level: 'warning' }] },
      { ...server('service'), findings: [{ label: '서비스 · nginx down', level: 'warning' }] },
      { ...server('log'), findings: [{ label: '로그 · 3', level: 'warning' }] },
      row,
    ]),
  );
  assert.deepEqual(
    result.map((r) => r.server.key),
    ['hardware', 'security', 'service', 'log'],
  );
  assert.deepEqual(result[0].metrics, []);
  assert.deepEqual(result[0].findings, row.findings);
});

test('placeholder action notes do not make normal servers appear in the review', () => {
  for (const value of [
    '',
    ' ',
    '-',
    '—',
    '--',
    '없음',
    '정상',
    'N/A',
    '0',
    '이상 없음',
    '특이사항 없음',
  ]) {
    assert.equal(inspectionActionNote(value), '', value);
    assert.deepEqual(
      resourceReview(snapshot([{ ...server('normal'), actionItems: value }])),
      [],
      value,
    );
  }
  assert.equal(
    inspectionActionNote('  백업 정책 확인\n보관 기간 조정  '),
    '백업 정책 확인\n보관 기간 조정',
  );
});

test('show pending actions and actionable import notes but hide normal completed history', () => {
  const completed = { isResolved: true, memo: '작업 완료', images: ['evidence'] };
  const result = resourceReview(
    snapshot([
      { ...server('complete'), action: completed, actionItems: '이전 조치 요청' },
      { ...server('pending'), action: { ...completed, isResolved: false } },
      { ...server('note'), actionItems: '백업 정리 필요' },
      { ...server('still-warning', 85), action: completed },
    ]),
  );
  assert.deepEqual(
    result.map((r) => r.server.key),
    ['still-warning', 'pending', 'note'],
  );
  assert.equal(
    result[0].server.action.isResolved,
    true,
    'measured warnings stay visible even after an action completes',
  );
  assert.equal(result[1].pendingAction, true);
  assert.equal(result[2].pendingAction, true);
});

test('usage findings are not duplicated and saved thresholds remain authoritative', () => {
  const result = resourceReview(
    snapshot(
      [
        { ...server('normal', 81), findings: [{ label: 'CPU 81%', level: 'warning' }] },
        {
          ...server('warning', 85),
          findings: [
            { label: 'CPU 85%', level: 'warning' },
            { label: 'H/W · RAM 오류', level: 'danger' },
          ],
        },
      ],
      85,
      95,
    ),
  );
  assert.equal(result.length, 1);
  assert.deepEqual(result[0].findings, [{ label: 'H/W · RAM 오류', level: 'danger' }]);
  assert.equal(result[0].metrics[0].metric.value, 85);
});

test('preserve all snapshot rows and measurements for full view and export', () => {
  const data = snapshot([
    { ...server('normal'), action: { isResolved: true, memo: '기존 조치', images: ['evidence'] } },
    server('warning', 80),
    server('danger', 99),
    server('unknown', null, null, null),
  ]);
  const before = JSON.stringify(data);
  const result = resourceReview(data);
  assert.equal(JSON.stringify(data), before);
  assert.equal(result.length, 3);
  assert.equal(result.find((r) => r.server.key === 'unknown').metrics.length, 3);
  assert.deepEqual(
    data.servers.map((s) => s.key),
    ['normal', 'warning', 'danger', 'unknown'],
  );
});

test('no data and all readings below the threshold produce no exception rows', () => {
  assert.deepEqual(resourceReview(snapshot([])), []);
  assert.deepEqual(resourceReview(snapshot([server('normal', 79.9, 30, 20)])), []);
});
