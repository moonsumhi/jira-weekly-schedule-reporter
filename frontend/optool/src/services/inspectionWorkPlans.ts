import { api } from 'boot/axios';
import type { WorkDocumentAsset } from './formEntries';
import type { FormTemplate } from './formTemplates';
import type { InspectionTask } from './inspection';

export interface InspectionWorkPlan {
  id: string;
  templateId: string;
  templateTitle: string;
  title: string;
  workDate: string;
  version: number;
  linkedAssets: WorkDocumentAsset[];
  isDeleted: boolean;
  unavailable: boolean;
  current?: InspectionWorkPlan | null;
}

export const displayWorkPlan = (plan: InspectionWorkPlan) => plan.current || plan;
export type InspectionWorkResult = InspectionWorkPlan;
export type InspectionDocumentKind = 'PLAN' | 'RESULT';
export function isWorkResultTemplate(template: FormTemplate | null) {
  if (template?.menu?.toLowerCase() !== 'job') return false;
  const key = (template.jiraIssueKey || '').toUpperCase();
  return key === 'JOB-RESULT' || (!key.startsWith('JOB-') && template.title.replace(/\s+/g, '').startsWith('작업결과서'));
}
export function isWorkPlanTemplate(template: FormTemplate | null) {
  if (template?.menu?.toLowerCase() !== 'job') return false;
  const key = (template.jiraIssueKey || '').toUpperCase();
  return (
    ['JOB-PLAN-SERVICE', 'JOB-PLAN-NONSERVICE'].includes(key) ||
    (!key.startsWith('JOB-') && template.title.replace(/\s+/g, '').startsWith('작업계획서'))
  );
}
export async function searchInspectionWorkPlans(search = '', assetIds: string[] = []) {
  return searchInspectionWorkDocuments('PLAN', search, assetIds);
}
export async function searchInspectionWorkDocuments(kind: InspectionDocumentKind, search = '', assetIds: string[] = []) {
  return (
    await api.get<{ items: InspectionWorkPlan[]; hasMore: boolean }>(
      `/inspection-tasks/${kind === 'RESULT' ? 'work-results' : 'work-plans'}`,
      {
        params: { search, asset_ids: assetIds.join(',') },
      },
    )
  ).data;
}
export async function saveInspectionWorkPlans(task: InspectionTask, workPlanIds: string[]) {
  return (
    await api.put<{ workPlans: InspectionWorkPlan[]; workPlansVersion: number }>(
      `/inspection-tasks/${task.issueId}/${task.month}/work-plans`,
      { work_plan_ids: workPlanIds, version: task.workPlansVersion || 0 },
    )
  ).data;
}
