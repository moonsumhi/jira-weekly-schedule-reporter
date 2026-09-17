import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/utils/inspectionParticipants.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
const { assignedReportTasks, participantWork } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
const task = (issueId, assigneeId = 'one', overrides = {}) => ({
  issueId, month: '2026-09', state: 'ACTIVE',
  issue: { key: `OPS-${issueId}`, title: issueId, assigneeId, assigneeName: '동명이인', status: 'TODO' },
  ...overrides,
});
const report = (tasks) => ({ month: '2026-09', snapshot: { tasks, carryover: [task('old')] } });

test('match assignee IDs, including unfinished work, rather than display names', () => {
  const result = assignedReportTasks(report([task('1'), task('2', 'two'), task('3', null)]), 'one');
  assert.deepEqual(result.map((t) => t.issueId), ['1']);
});
test('exclude rolled, excluded and other-month tasks; never use carryover', () => {
  const result = assignedReportTasks(report([
    task('1'), task('2', 'one', { state: 'ROLLED' }),
    task('3', 'one', { state: 'EXCLUDED' }), task('4', 'one', { month: '2026-08' }),
  ]), 'one');
  assert.deepEqual(result.map((t) => t.issueId), ['1']);
});
test('deduplicate assigned tasks without modifying the report snapshot', () => {
  const data = report([task('1'), task('1')]);
  const before = JSON.stringify(data);
  assert.equal(assignedReportTasks(data, 'one').length, 1);
  assert.equal(JSON.stringify(data), before);
});
test('combine automatic and manual participation once, preserving manual-only history', () => {
  const assigned = { issueId: '1', key: 'OPS-1', title: '새로 반영한 제목' };
  const manual = { issueId: '1', key: 'OPS-1', title: '수동 연결 당시 제목' };
  const historical = { issueId: 'removed', key: 'OPS-0', title: '이전에 수행한 작업' };
  const person = { assignedTasks: [assigned], tasks: [manual, historical], workSummary: '수기 내용' };
  const before = JSON.stringify(person);
  assert.deepEqual(participantWork(person), [assigned, historical]);
  assert.equal(JSON.stringify(person), before);
});
test('legacy and final participants without automatic assignments retain saved manual work', () => {
  const manual = { issueId: '1', title: '확정 당시 업무' };
  assert.deepEqual(participantWork({ tasks: [manual] }), [manual]);
  assert.deepEqual(participantWork({ tasks: [], assignedTasks: [] }), []);
});
