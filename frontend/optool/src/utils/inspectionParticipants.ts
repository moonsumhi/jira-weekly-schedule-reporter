import type {
  InspectionReport,
  ReportParticipant,
  ReportParticipantTask,
} from '../services/inspectionReports';

export function assignedReportTasks(
  report: InspectionReport,
  userId: string,
): ReportParticipantTask[] {
  const linked = new Map<string, ReportParticipantTask>();
  for (const task of report.snapshot.tasks) {
    if (task.month !== report.month || task.state !== 'ACTIVE' || task.issue.assigneeId !== userId)
      continue;
    linked.set(task.issueId, {
      issueId: task.issueId,
      month: task.month,
      key: task.issue.key,
      title: task.issue.title,
    });
  }
  return [...linked.values()];
}

export function participantWork(person: ReportParticipant): ReportParticipantTask[] {
  // Prefer the captured assigned-task title while preserving explicit manual links.
  const linked = new Map((person.assignedTasks || []).map((task) => [task.issueId, task]));
  for (const task of person.tasks) {
    if (!linked.has(task.issueId)) linked.set(task.issueId, task);
  }
  return [...linked.values()];
}
