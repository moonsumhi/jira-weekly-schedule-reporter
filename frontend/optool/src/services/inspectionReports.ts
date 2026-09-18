import { api } from 'boot/axios';
import type { InspectionAsset, InspectionTask, InspectionResultInput } from './inspection';

export interface ReportProject {
  id: string;
  key: string;
  name: string;
}
export interface ReportParticipantRole {
  value: string;
  label: string;
}
export interface ReportParticipantUser {
  id: string;
  name: string;
  team: string;
  email: string;
}
export interface ReportParticipantTask {
  issueId: string;
  month: string;
  key: string;
  title: string;
}
export interface ReportParticipant {
  userId: string;
  name: string;
  team: string;
  roles: ReportParticipantRole[];
  workSummary: string;
  tasks: ReportParticipantTask[];
  assignedTasks?: ReportParticipantTask[];
}
export interface ReportParticipantInput {
  user_id: string;
  roles: string[];
  work_summary: string;
  issue_ids: string[];
}
export interface ReportSource {
  id: string;
  reportDate: string;
  title: string;
  uploadedAt: string | null;
  uploadedBy: string;
}
export interface ResourceMetric {
  value: number | null;
  basis: string;
  path?: string;
  delta: number | null;
}
export interface ReportAction {
  id: string;
  hostName: string;
  memo: string;
  actor: string;
  updatedAt?: string;
  isResolved: boolean;
  images: string[];
}
export interface ReportActionTarget {
  rowKey?: string;
  actionId?: string;
  hostName: string;
}
export interface ReportActionEditContext {
  hostName: string;
  action: ReportAction | null;
  actionToken: string | null;
  version: number;
}
export interface ResourceServer {
  key: string;
  identityKey: string;
  hostName: string;
  serverName: string;
  ip: string;
  cpu: ResourceMetric;
  ram: ResourceMetric;
  disk: ResourceMetric;
  level: 'none' | 'warning' | 'danger';
  findings: { label: string; level: string }[];
  logErrors: string;
  actionItems: string;
  asset: InspectionAsset | null;
  candidate: InspectionAsset | null;
  mappingState: string;
  mappingIssue?:
    'ambiguous_hostname' | 'hostname_mismatch' | 'missing_hostname' | 'asset_not_found' | null;
  action: ReportAction | null;
  detail: {
    cpu?: { beforeVal: string; beforePct: string; afterVal: string; afterPct: string };
    ram?: { beforeVal: string; beforePct: string; afterVal: string; afterPct: string };
    serverOs?: string;
    inspector?: string;
    inspectionStart?: string;
    inspectionEnd?: string;
    overallComment?: string;
    disks?: { filesystem: string; used: string; total: string; pct: string }[];
    hwChecks?: { item: string; ok: string | boolean; ng: string | boolean; na: string | boolean }[];
    securityChecks?: { item: string; result: string }[];
    services?: string[];
    swap?: { beforeVal: string; beforePct: string; afterVal: string; afterPct: string };
    networkBefore?: string;
    networkAfter?: string;
    allowedIps?: string;
    serverShutdown?: string;
    serverRestart?: string;
  };
}
export interface ReportTask extends InspectionTask {
  plannedStart?: string;
  plannedEnd?: string;
}
export type ReportKind = 'PLAN' | 'RESULT';
export interface InspectionPlanReference {
  id: string;
  title: string;
  month: string;
  revision: number;
  inspectionDate: string;
  plannedTime: string;
  finalizedAt: string;
  purpose: string;
  participants: ReportParticipant[];
  resourceTargets: InspectionAsset[];
  resourceChecks: string;
  tasks: ReportTask[];
}
export interface ReportSnapshot {
  resourceTargets?: InspectionAsset[];
  plan?: InspectionPlanReference | null;
  source: ReportSource | null;
  comparison: ReportSource | null;
  capturedAt: string;
  historicalReconstruction: boolean;
  thresholds: { warning: number; danger: number; version: number };
  servers: ResourceServer[];
  tasks: ReportTask[];
  carryover: ReportTask[];
  missingAssetResources: InspectionAsset[];
  unmatchedActions: ReportAction[];
  warnings: { code: string; label: string; count: number }[];
  stats: {
    planned: number;
    done: number;
    pending: number;
    rolled: number;
    excluded: number;
    completionRate: number | null;
    servers: number;
    warning: number;
    danger: number;
    missingResources: number;
  };
}
export interface ReportNote {
  id: string;
  content: string;
}
export interface InspectionReport {
  id: string;
  kind?: ReportKind;
  plannedTime?: string;
  resourceChecks?: string;
  month: string;
  projectIds: string[];
  projects: ReportProject[];
  scopeKey: string;
  revision: number;
  state: 'DRAFT' | 'FINAL';
  version: number;
  title: string;
  inspectionDate: string;
  purpose: string;
  overview: string;
  limitations: string;
  additionalNotes?: ReportNote[];
  participants?: ReportParticipant[];
  includeAppendix: boolean;
  includeImages: boolean;
  snapshot: ReportSnapshot;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  finalizedAt?: string;
  finalizedBy?: string;
  parentId?: string;
}
export type ReportSummary = Omit<InspectionReport, 'snapshot'>;
export interface ReportPreview {
  id: string;
  kind?: ReportKind;
  month: string;
  projects: ReportProject[];
  snapshot: ReportSnapshot;
  expiresAt: string;
}
export interface PreviewRequest {
  month: string;
  kind?: ReportKind;
  project_ids?: string[];
  source_id?: string | null;
  comparison_id?: string | null;
  include_images: boolean;
  report_id?: string;
  version?: number;
  mappings?: ResourceMapping[];
}
export interface ResourceMapping {
  row_key: string;
  asset_id: string | null;
}
export interface ReportEdit {
  title: string;
  inspection_date: string;
  purpose: string;
  overview: string;
  include_appendix: boolean;
  planned_time?: string;
  resource_checks?: string;
}
const base = '/monthly-inspection-reports';
export function reportNotes(report: InspectionReport): ReportNote[] {
  if (report.additionalNotes?.length) return report.additionalNotes;
  return report.limitations?.trim() ? [{ id: 'legacy', content: report.limitations }] : [];
}
export async function saveReportNotes(report: InspectionReport, notes: ReportNote[]) {
  return (
    await api.put<InspectionReport>(`${base}/${report.id}/notes`, {
      version: report.version,
      notes,
    })
  ).data;
}
export async function getReportParticipantOptions(q = '') {
  return (
    await api.get<{ users: ReportParticipantUser[]; roles: ReportParticipantRole[] }>(
      `${base}/participant-options`,
      { params: { q } },
    )
  ).data;
}
export async function saveReportParticipants(
  id: string,
  version: number,
  participants: ReportParticipantInput[],
) {
  return (await api.put<InspectionReport>(`${base}/${id}/participants`, { version, participants }))
    .data;
}
export async function reportOptions(month: string) {
  return (
    await api.get<{ projects: ReportProject[]; sources: ReportSource[]; inspectionDate: string }>(
      `${base}/options`,
      { params: { month } },
    )
  ).data;
}
export async function listReports(month: string, kind: ReportKind = 'RESULT') {
  return (await api.get<ReportSummary[]>(base, { params: { month, kind } })).data;
}
export async function getReport(id: string) {
  return (await api.get<InspectionReport>(`${base}/${id}`)).data;
}
export async function getReportAction(reportId: string, target: ReportActionTarget) {
  return (
    await api.get<ReportActionEditContext>(`${base}/${reportId}/action`, {
      params: { row_key: target.rowKey, action_id: target.actionId },
    })
  ).data;
}
export async function saveReportAction(
  reportId: string,
  target: ReportActionTarget,
  context: ReportActionEditContext,
  values: { memo: string; images: string[]; is_resolved: boolean },
) {
  return (
    await api.put<{ report: InspectionReport; warning: string }>(`${base}/${reportId}/action`, {
      ...values,
      row_key: target.rowKey,
      action_id: target.actionId,
      action_token: context.actionToken,
      version: context.version,
    })
  ).data;
}
export async function getReportTask(reportId: string, task: InspectionTask) {
  return (await api.get<InspectionTask>(`${base}/${reportId}/tasks/${task.issueId}/${task.month}`))
    .data;
}
export async function saveReportTaskResult(
  reportId: string,
  task: InspectionTask,
  body: InspectionResultInput,
) {
  await api.put(`${base}/${reportId}/tasks/${task.issueId}/${task.month}/result`, body);
}
export async function previewReport(body: PreviewRequest) {
  return (await api.post<ReportPreview>(`${base}/preview`, body)).data;
}
export async function createReport(previewId: string, clientId: string) {
  return (await api.post<InspectionReport>(base, { preview_id: previewId, client_id: clientId }))
    .data;
}
export async function editReport(report: InspectionReport, body: ReportEdit) {
  return (
    await api.patch<InspectionReport>(`${base}/${report.id}`, { ...body, version: report.version })
  ).data;
}
export async function refreshReport(report: InspectionReport, previewId: string) {
  return (
    await api.post<InspectionReport>(`${base}/${report.id}/refresh`, {
      preview_id: previewId,
      version: report.version,
    })
  ).data;
}
export async function syncReportResults(report: InspectionReport) {
  return (
    await api.post<InspectionReport>(`${base}/${report.id}/sync-results`, {
      version: report.version,
    })
  ).data;
}
export async function finalizeReport(report: InspectionReport) {
  return (
    await api.post<InspectionReport>(`${base}/${report.id}/finalize`, { version: report.version })
  ).data;
}
export async function reviseReport(report: InspectionReport) {
  return (await api.post<InspectionReport>(`${base}/${report.id}/revisions`)).data;
}
export const reportTime = (v?: string | null) =>
  v
    ? new Date(v).toLocaleString('ko-KR', {
        timeZone: 'Asia/Seoul',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—';
export const percent = (v?: number | null) =>
  v == null ? '—' : `${v.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}%`;
