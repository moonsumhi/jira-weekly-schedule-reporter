import type { InspectionAsset } from '../services/inspection';
import type { ResourceMonth } from '../services/inspectionResources';
import type { ResourceServer } from '../services/inspectionReports';

export type ResourceFilter = 'all' | 'measured' | 'attention' | 'missing' | 'unlinked';
export interface ResourceResultRow {
  key: string;
  name: string;
  ip: string;
  asset: InspectionAsset | null;
  record: ResourceServer | null;
  regular: boolean;
  attention: boolean;
  notes: string[];
  status: { label: string; tone: string; rank: number };
}
const kinds = ['cpu', 'ram', 'disk'] as const;
const noFinding = (value: string | undefined) =>
  [
    '',
    '-',
    '없음',
    '정상',
    '양호',
    'ok',
    'n/a',
    'na',
    'none',
    '0',
    '이상없음',
    '이상 없음',
    'false',
  ].includes((value || '').trim().toLowerCase());

export function buildResourceResults(data: ResourceMonth): ResourceResultRow[] {
  const targets = new Set(data.items.map((item) => item.asset.id));
  const counts = new Map<string, number>();
  for (const record of data.records) {
    if (record.asset) counts.set(record.asset.id, (counts.get(record.asset.id) || 0) + 1);
  }
  const rows: ResourceResultRow[] = data.records.map((record) => {
    const missing = kinds.filter((kind) => record[kind].value === null);
    const duplicate = !!record.asset && (counts.get(record.asset.id) || 0) > 1;
    const action = !noFinding(record.actionItems);
    const metricFinding = (label: string) => /^(CPU|RAM|디스크)\s/.test(label);
    const notes = action ? [record.actionItems] : [];
    notes.push(
      ...record.findings
        .filter((finding) => !metricFinding(finding.label))
        .map((finding) => finding.label),
    );
    if (
      !noFinding(record.logErrors) &&
      !record.findings.some((finding) => finding.label.startsWith('로그 ·'))
    )
      notes.push(`로그 · ${record.logErrors}`);
    if (missing.length)
      notes.push(
        `${missing.map((kind) => ({ cpu: 'CPU', ram: 'RAM', disk: '디스크' })[kind]).join(' · ')} 측정값 없음`,
      );
    if (duplicate) notes.push('한 자산에 점검 결과가 여러 건 연결되어 있습니다.');
    notes.push(
      ...record.findings
        .filter((finding) => metricFinding(finding.label))
        .map((finding) => finding.label),
    );
    const attention = record.level !== 'none' || notes.length > 0;
    const status =
      record.level === 'danger'
        ? { label: '위험', tone: 'danger', rank: 0 }
        : record.level === 'warning'
          ? { label: '주의', tone: 'warning', rank: 1 }
          : attention
            ? { label: missing.length ? '측정값 없음' : '확인 필요', tone: 'warning', rank: 2 }
            : { label: '사용량 양호', tone: 'normal', rank: 5 };
    return {
      key: `record:${record.key}`,
      name: record.hostName,
      ip: record.ip,
      record,
      asset: record.asset,
      regular: !!record.asset && targets.has(record.asset.id),
      attention,
      notes: [...new Set(notes)],
      status,
    };
  });
  for (const { asset } of data.items) {
    if (counts.has(asset.id)) continue;
    rows.push({
      key: `target:${asset.id}`,
      name: asset.name || asset.assetName,
      ip: asset.ip,
      asset,
      record: null,
      regular: true,
      attention: false,
      notes: [
        asset.isDeleted
          ? '삭제된 자산입니다. 정기 점검 대상에서 제외해 주세요.'
          : data.source
            ? '선택한 점검 데이터에 이 서버의 측정값이 없습니다.'
            : '해당 월의 점검 Excel 파일을 업로드해 주세요.',
      ],
      status: {
        label: asset.isDeleted ? '삭제된 자산' : data.source ? '결과 없음' : '등록 대기',
        tone: 'muted',
        rank: 3,
      },
    });
  }
  return rows;
}

export function matchesResourceResult(row: ResourceResultRow, filter: ResourceFilter, search = '') {
  const matches =
    filter === 'all' ||
    (filter === 'measured' && !!row.record) ||
    (filter === 'attention' && row.attention) ||
    (filter === 'missing' && !row.record) ||
    (filter === 'unlinked' && !!row.record && !row.asset);
  const text = [
    row.name,
    row.ip,
    row.asset?.name,
    row.asset?.assetName,
    row.asset?.ip,
    row.record?.serverName,
    ...row.notes,
  ]
    .join(' ')
    .toLowerCase();
  return matches && text.includes(search.trim().toLowerCase());
}
