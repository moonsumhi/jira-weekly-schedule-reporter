import { formEntryService, type FormEntry, type OriginalFile } from './formEntries';
import {
  getInspectionTasks,
  registerPlanInspection,
  searchInspectionAssets,
  type InspectionTask,
} from './inspection';
import { getErrorMessage } from 'src/utils/http/error';

export interface WorkDocumentInspection {
  month: string;
  plannedOn: string;
  assigneeId: string | null;
}

export function workDocumentDate(data: Record<string, unknown>): string {
  for (const section of Object.values(data)) {
    for (const row of Array.isArray(section) ? section : [section]) {
      if (!row || typeof row !== 'object') continue;
      for (const label of ['작업 일시', '작업 기간 (시작)', '작업일']) {
        const value = (row as Record<string, unknown>)[label];
        if (typeof value === 'string' && /^20\d{2}-\d{2}-\d{2}/.test(value))
          return value.slice(0, 10);
      }
    }
  }
  return '';
}

export async function documentInspectionTasks(
  id: string,
  month: string,
): Promise<InspectionTask[]> {
  const result = await getInspectionTasks(month, { work_plan_id: id, include_overdue: false });
  return result.items.filter((task) => task.month === month && task.state !== 'EXCLUDED');
}

export class WorkDocumentInspectionError extends Error {
  constructor(
    public entry: FormEntry,
    cause: unknown,
  ) {
    super(
      `작업계획서는 저장됐지만 서버 점검에 추가하지 못했습니다. 다시 저장하면 재시도합니다. ${getErrorMessage(cause, '')}`.trim(),
    );
  }
}

/** Save the document first; retain its ID/version if only inspection registration fails. */
export async function saveWorkDocument(options: {
  entry?: FormEntry;
  templateId: string;
  data: FormEntry['data'];
  originalFile?: OriginalFile | null;
  assetIds?: string[] | undefined;
  inspection?: WorkDocumentInspection | null | undefined;
}): Promise<FormEntry> {
  const { entry, templateId, data, originalFile, assetIds, inspection } = options;
  const targets = assetIds ?? entry?.linkedAssets?.map((asset) => asset.id) ?? [];
  let existing: InspectionTask[] = [];
  if (inspection) {
    if (!/^20\d{2}-(0[1-9]|1[0-2])$/.test(inspection.month))
      throw new Error('점검 월을 선택해 주세요.');
    if (entry) existing = await documentInspectionTasks(entry.id, inspection.month);
    if (!existing.length) {
      if (
        !/^20\d{2}-\d{2}-\d{2}$/.test(inspection.plannedOn) ||
        !inspection.plannedOn.startsWith(inspection.month)
      )
        throw new Error('선택한 점검 월에 맞는 작업 예정일을 입력해 주세요.');
      if (!targets.length) throw new Error('서버 점검에 추가할 자산을 선택해 주세요.');
      if (targets.length) {
        const available = new Set(
          (await searchInspectionAssets('', targets)).map((asset) => asset.id),
        );
        if (targets.some((id) => !available.has(id)))
          throw new Error('삭제된 자산이 포함되어 있습니다. 자산을 다시 선택해 주세요.');
      }
    }
  }
  const saved = entry
    ? await formEntryService.patch(entry.id, data, entry.version, assetIds)
    : await formEntryService.create(templateId, data, originalFile, assetIds);
  if (inspection && !existing.length) {
    try {
      await registerPlanInspection({
        month: inspection.month,
        work_plan_id: saved.id,
        asset_ids: targets,
        common: false,
        assignee_id: inspection.assigneeId,
        planned_on: inspection.plannedOn,
      });
    } catch (error) {
      // A lost response or a simultaneous registration must not create another task/document.
      let registered = false;
      try {
        registered = (await documentInspectionTasks(saved.id, inspection.month)).length > 0;
      } catch {
        /* Keep the original failure. */
      }
      if (!registered) throw new WorkDocumentInspectionError(saved, error);
    }
  }
  return saved;
}
