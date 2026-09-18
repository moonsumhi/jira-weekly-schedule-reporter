import { api } from 'boot/axios';
import { STATUS_LABEL, type IssueStatus } from './pm/issue';
import type { InspectionWorkPlan, InspectionWorkResult } from './inspectionWorkPlans';
import { assetCategories, type AssetCategory } from './assetLinks';

export interface InspectionAsset {
  id: string;
  category?: InspectionAssetCategory;
  name: string;
  ip: string;
  assetName: string;
  status: string;
  isDeleted: boolean;
  current?: InspectionAsset | null;
}
export const inspectionAssetCategories = assetCategories;
export type InspectionAssetCategory = AssetCategory;
export interface InspectionResult {
  workResults?: InspectionWorkResult[];
  content: string;
  performedOn: string | null;
  followUp: string;
  version: number;
  updatedAt: string;
  updatedBy: string;
}
export interface InspectionResultInput {
  version: number;
  content: string;
  performed_on: string | null;
  follow_up: string;
  work_result_ids?: string[];
}
export const hasInspectionResult = (task: InspectionTask) => !!(
  task.result?.content?.trim() || task.result?.workResults?.some((ref) => !ref.unavailable && !ref.isDeleted)
);
export async function saveInspectionResult(
  task: InspectionTask,
  body: InspectionResultInput,
) {
  return (
    await api.put<InspectionResult>(`/inspection-tasks/${task.issueId}/${task.month}/result`, body)
  ).data;
}
export interface InspectionTask {
  sourceType?: 'ISSUE' | 'WORK_PLAN';
  taskVersion?: number;
  workPlan?: InspectionWorkPlan;
  plannedOn?: string;
  workPlans?: InspectionWorkPlan[];
  workPlansVersion?: number;
  result?: InspectionResult;
  issueId: string;
  month: string;
  state: 'ACTIVE' | 'ROLLED' | 'EXCLUDED';
  common: boolean;
  assets: InspectionAsset[];
  reason: string;
  fromMonth?: string;
  toMonth?: string;
  overdue: boolean;
  issueDeleted: boolean;
  createdAt?: string;
  completedSnapshot?: InspectionTask['issue'];
  issue: {
    id: string;
    projectId: string;
    key: string;
    title: string;
    status: IssueStatus;
    assigneeId: string | null;
    assigneeName: string;
  };
}
export async function registerPlanInspection(payload: {
  month: string;
  work_plan_id: string;
  asset_ids: string[];
  common: boolean;
  assignee_id: string | null;
  planned_on: string;
}) {
  return (
    await api.post<{ issueId: string; month: string }>('/inspection-tasks/from-work-plan', payload)
  ).data;
}
export async function changePlanInspection(
  task: InspectionTask,
  values: {
    status?: IssueStatus;
    assignee_id?: string | null;
    planned_on?: string;
    asset_ids?: string[];
    common?: boolean;
  },
) {
  return (
    await api.patch<{ version: number }>(`/inspection-tasks/${task.issueId}/${task.month}/plan`, {
      ...values,
      version: task.taskVersion,
    })
  ).data;
}
export const formatInspectionMonth = (month: string) =>
  `${month.slice(0, 4)}년 ${Number(month.slice(5))}월`;
export function inspectionStatusLabel(task: InspectionTask) {
  if (task.state === 'ROLLED') return '이월';
  if (task.state === 'EXCLUDED') return '제외';
  return STATUS_LABEL[task.issue.status];
}
export const thisMonth = () =>
  new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
  }).format(new Date());
export async function getInspectionTasks(
  month: string,
  params: Record<string, string | boolean> = {},
) {
  return (
    await api.get<{ inspectionDate: string; items: InspectionTask[] }>('/inspection-tasks', {
      params: { month, ...params },
    })
  ).data;
}
export async function searchInspectionAssets(
  search = '',
  ids: string[] = [],
  category?: InspectionAssetCategory,
) {
  return (
    await api.get<InspectionAsset[]>('/inspection-tasks/assets', {
      params: { search, ids: ids.join(','), category },
    })
  ).data;
}
export async function registerInspection(payload: {
  month: string;
  issue_id: string;
  asset_ids: string[];
  common: boolean;
  work_plan_ids?: string[];
}) {
  return (await api.post('/inspection-tasks', payload)).data as { issueId: string; month: string };
}
export async function changeInspection(
  task: InspectionTask,
  payload: {
    action: 'rollover' | 'exclude' | 'targets';
    reason?: string;
    asset_ids?: string[];
    common?: boolean;
  },
) {
  await api.patch(`/inspection-tasks/${task.issueId}/${task.month}`, payload);
}
export function inspectionError(error: unknown): string {
  const e = error as { response?: { data?: { detail?: unknown } } };
  const detail = e.response?.data?.detail;
  return typeof detail === 'string'
    ? detail
    : '처리 중 오류가 발생했습니다. 입력 내용을 확인한 후 다시 시도해 주세요.';
}

export async function getInspectionDate(month: string) {
  return (
    await api.get<{ inspectionDate: string }>('/inspection-tasks/schedule', { params: { month } })
  ).data.inspectionDate;
}
