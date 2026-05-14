import type { FieldValue } from 'src/types/assets'

export function parseSmartValue(text: string): FieldValue {
  const t = text.trim()
  if (t === '') return null
  if (t === 'true') return true
  if (t === 'false') return false

  const num = Number(t)
  if (!Number.isNaN(num) && /^-?\d+(\.\d+)?$/.test(t) && String(num) === t) return num

  if ((t.startsWith('{') && t.endsWith('}')) || (t.startsWith('[') && t.endsWith(']'))) {
    try {
      const parsed = JSON.parse(t) as unknown
      if (Array.isArray(parsed)) return parsed
      if (typeof parsed === 'object' && parsed !== null) return parsed as Record<string, unknown>
      return String(parsed)
    } catch {
      return t
    }
  }
  return t
}
