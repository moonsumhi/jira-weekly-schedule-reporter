import { api } from 'boot/axios';
import type { InspectionAsset } from './inspection';
import type { ResourceServer, ReportSource, ResourceMapping } from './inspectionReports';
import { useAuthStore } from 'src/stores/auth';

export interface ResourceTarget {
  asset: InspectionAsset;
  records: ResourceServer[];
}
export interface ResourceMonth {
  month: string;
  version: number;
  items: ResourceTarget[];
  source: ReportSource | null;
  sources: ReportSource[];
  comparison: ReportSource | null;
  otherRecords: ResourceServer[];
  records: ResourceServer[];
}
const base = '/inspection-resources';
// In-memory only: never persist exceptions as aliases or browser storage.
const sessionMappings = new Map<string, ResourceMapping[]>();
const scope = (month: string, sourceId: string) => `${useAuthStore().me?.id}:${month}:${sourceId}`;
export function getSessionMappings(month: string, sourceId: string) {
  return sessionMappings.get(scope(month, sourceId));
}
export function forgetMappings(month: string, sourceId: string) {
  sessionMappings.delete(scope(month, sourceId));
}
export function manualMappings(records: ResourceServer[]) {
  return records
    .filter((r) => r.mappingState === 'manual' && r.asset)
    .map((r) => ({ row_key: r.key, asset_id: r.asset!.id }));
}
export function rememberMappings(month: string, sourceId: string, records: ResourceServer[]) {
  sessionMappings.set(scope(month, sourceId), manualMappings(records));
}
export function changedMappings(
  records: ResourceServer[],
  rowKey: string,
  asset: InspectionAsset | null,
) {
  return [
    ...manualMappings(records).filter((m) => m.row_key !== rowKey),
    { row_key: rowKey, asset_id: asset?.id || null },
  ];
}
export async function previewResourceMonth(
  month: string,
  sourceId: string,
  mappings: ResourceMapping[],
) {
  return (
    await api.post<ResourceMonth>(`${base}/preview`, { month, source_id: sourceId, mappings })
  ).data;
}
export async function getResourceMonth(month: string, sourceId?: string) {
  const data = (await api.get<ResourceMonth>(base, { params: { month, source_id: sourceId } }))
    .data;
  const mappings = data.source && getSessionMappings(month, data.source.id);
  if (data.source && mappings?.length && useAuthStore().me?.isInternal !== false) {
    try {
      return await previewResourceMonth(
        month,
        data.source.id,
        mappings.filter((m) => data.records.some((r) => r.key === m.row_key)),
      );
    } catch (e) {
      if ((e as { response?: { status: number } }).response?.status !== 422) throw e;
      forgetMappings(month, data.source.id);
    }
  }
  return data;
}
export async function getResourceTargets() {
  return (await api.get<{ version: number; assets: InspectionAsset[] }>(`${base}/targets`)).data;
}
export async function saveResourceTargets(version: number, assetIds: string[]) {
  await api.put(`${base}/targets`, { version, asset_ids: assetIds });
}

export interface HostnameChange {
  key: string;
  hostname: string;
  sourceIp: string;
  ignoredIps: string[];
  matchedIps: string[];
  assetId: string | null;
  assetName: string;
  currentHostname: string;
  assetIp: string;
  status: 'ready' | 'review' | 'unchanged';
  reason: string;
}
export interface HostnamePreview {
  source: ReportSource;
  rows: HostnameChange[];
  revision: string;
}
export interface HostnameApplyResult {
  updatedIds: string[];
  skipped: { assetId: string; reason: string }[];
}
export async function previewHostnames(sourceId: string) {
  return (await api.get<HostnamePreview>(`${base}/${sourceId}/hostnames/preview`)).data;
}
export async function applyHostnames(sourceId: string, revision: string, assetIds: string[]) {
  return (
    await api.post<HostnameApplyResult>(`${base}/${sourceId}/hostnames/apply`, {
      revision,
      asset_ids: assetIds,
    })
  ).data;
}
