export function displayValue(v: unknown): string {
  if (v === null || v === undefined || v === '') return '-'
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  if (v instanceof Date) return v.toISOString()
  try {
    return JSON.stringify(v)
  } catch {
    return '[unserializable]'
  }
}
