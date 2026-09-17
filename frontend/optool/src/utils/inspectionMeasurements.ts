import type { ResourceMetric } from 'src/services/inspectionReports';

interface ImportedPerformance {
  beforeVal?: string;
  beforePct?: string;
  afterVal?: string;
  afterPct?: string;
}

function percentage(value: string | undefined): number | null {
  const text = (value || '').trim();
  if (!text) return null;
  const numeric = text.replace(/%$/, '').trim();
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(numeric)) return null;
  let number = Number(numeric);
  if (!text.includes('%') && number > 0 && number <= 1) number *= 100;
  return Number.isFinite(number) && number >= 0 && number <= 100 ? number : null;
}

function measuredText(value: string | undefined) {
  const text = (value || '').trim();
  return ['', '-', '—', 'n/a', 'na', 'none', 'null'].includes(text.toLowerCase()) ? '' : text;
}

// Keep the existing import fields compatible, but display one measurement per resource.
export function importedMeasurement(detail: ImportedPerformance | undefined) {
  const after = percentage(detail?.afterPct);
  const before = percentage(detail?.beforePct);
  const value =
    after != null
      ? measuredText(detail?.afterVal)
      : before != null
        ? measuredText(detail?.beforeVal)
        : measuredText(detail?.afterVal) || measuredText(detail?.beforeVal);
  return { value, pct: after ?? before };
}

// Old report snapshots may still contain these labels. Their saved values stay intact.
export function measurementBasis(metric: ResourceMetric) {
  return ['점검 전', '점검 후'].includes(metric.basis) ? '측정값' : metric.basis;
}

export function networkMeasurement(detail: { networkBefore?: string; networkAfter?: string }) {
  return measuredText(detail.networkAfter) || measuredText(detail.networkBefore) || '—';
}
