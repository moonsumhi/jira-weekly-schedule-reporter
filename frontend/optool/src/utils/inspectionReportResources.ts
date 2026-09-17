import type {
  ReportSnapshot,
  ResourceMetric,
  ResourceServer,
} from 'src/services/inspectionReports';

const metricKinds = ['cpu', 'ram', 'disk'] as const;
const metricLabels = { cpu: 'CPU', ram: 'RAM', disk: '디스크' };

export function inspectionActionNote(value?: string) {
  const text = (value || '').trim();
  const normalized = text.replace(/\s+/g, '').toLowerCase();
  return /^[-–—]+$/.test(normalized) ||
    [
      '',
      '없음',
      '정상',
      '양호',
      'ok',
      'n/a',
      'na',
      'none',
      'null',
      '0',
      '이상없음',
      '해당없음',
      '특이사항없음',
    ].includes(normalized)
    ? ''
    : text;
}

export function resourceReview(snapshot: Pick<ReportSnapshot, 'servers' | 'thresholds'>) {
  return snapshot.servers
    .map((server) => ({
      server,
      // Usage warnings are already shown with their measurements, using saved thresholds.
      findings: server.findings.filter(
        (finding) => !/^(CPU|RAM|디스크)\s+[\d.]+%$/.test(finding.label.trim()),
      ),
      pendingAction:
        server.action?.isResolved === false ||
        (!server.action && !!inspectionActionNote(server.actionItems)),
      metrics: metricKinds
        .filter((kind) => {
          const value = server[kind].value;
          return value == null || value >= snapshot.thresholds.warning;
        })
        .map((kind) => ({
          kind,
          label: metricLabels[kind],
          metric: server[kind],
          level: resourceMetricLevel(server[kind].value, snapshot.thresholds),
        })),
    }))
    .filter((row) => row.metrics.length || row.findings.length || row.pendingAction)
    .sort(
      (a, b) =>
        resourcePriority(a.server, snapshot.thresholds, a.findings) -
        resourcePriority(b.server, snapshot.thresholds, b.findings),
    );
}

export function resourceMetricLevel(
  value: ResourceMetric['value'],
  thresholds: ReportSnapshot['thresholds'],
) {
  return value == null
    ? 'missing'
    : value >= thresholds.danger
      ? 'danger'
      : value >= thresholds.warning
        ? 'warning'
        : 'neutral';
}

function resourcePriority(
  server: ResourceServer,
  thresholds: ReportSnapshot['thresholds'],
  findings: ResourceServer['findings'],
) {
  const ranks = { danger: 0, warning: 1, missing: 2, neutral: 3 };
  return Math.min(
    ...metricKinds.map((kind) => ranks[resourceMetricLevel(server[kind].value, thresholds)]),
    ...findings.map((finding) => (finding.level === 'danger' ? ranks.danger : ranks.warning)),
  );
}
