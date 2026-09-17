import type { ReportSnapshot, ReportTask } from 'src/services/inspectionReports';

const taskKey = (task: ReportTask) => `${task.month}:${task.issueId}`;
const assetKey = (task: ReportTask) =>
  task.assets
    .map((asset) => asset.id)
    .sort()
    .join(',');

export function inspectionPlanComparison(snapshot: ReportSnapshot) {
  if (!snapshot.plan) return null;
  const actual = new Map(snapshot.tasks.map((task) => [taskKey(task), task]));
  const planned = new Set(snapshot.plan.tasks.map(taskKey));
  const pairs: { planned: ReportTask | null; actual: ReportTask | null }[] = [
    ...snapshot.plan.tasks.map((task) => ({
      planned: task,
      actual: actual.get(taskKey(task)) || null,
    })),
    ...snapshot.tasks
      .filter((task) => !planned.has(taskKey(task)) && task.state !== 'EXCLUDED')
      .map((task) => ({ planned: null, actual: task })),
  ];
  const rows = pairs.map((pair) => {
    const before = pair.planned,
      after = pair.actual;
    const changes: string[] = [];
    if (before && after) {
      if (before.issue.title !== after.issue.title) changes.push('작업명 변경');
      if (before.issue.assigneeId !== after.issue.assigneeId) changes.push('담당자 변경');
      if (before.common !== after.common || assetKey(before) !== assetKey(after))
        changes.push('대상 자산 변경');
      if (
        (before.plannedStart || '') !== (after.plannedStart || '') ||
        (before.plannedEnd || '') !== (after.plannedEnd || '')
      )
        changes.push('일정 변경');
    }
    const status =
      !after || after.state === 'EXCLUDED'
        ? '미실시'
        : after.state === 'ROLLED'
          ? '이월'
          : after.issue.status === 'DONE'
            ? '완료'
            : '미완료';
    return { ...pair, task: after || before!, added: !before, changes, status };
  });
  return {
    rows,
    changes: rows.filter(
      (row) => row.added || row.changes.length || row.status === '미실시' || row.status === '이월',
    ),
    planned: snapshot.plan.tasks.length,
    completed: rows.filter((row) => row.planned && row.status === '완료').length,
    pending: rows.filter((row) => row.planned && row.status === '미완료').length,
    omitted: rows.filter((row) => row.planned && row.status === '미실시').length,
    rolled: rows.filter((row) => row.planned && row.status === '이월').length,
    added: rows.filter((row) => row.added).length,
  };
}
