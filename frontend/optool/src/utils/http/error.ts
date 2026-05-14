import type { AxiosError } from 'axios'

export function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function detailToStr(v: unknown): string {
  if (typeof v === 'string') return v
  if (Array.isArray(v)) {
    return v.map((item) => {
      if (item && typeof item === 'object' && 'msg' in item) return String((item as Record<string, unknown>).msg)
      return typeof item === 'string' ? item : JSON.stringify(item)
    }).join(', ')
  }
  try { return JSON.stringify(v) } catch { return String(v) }
}

export function getErrorMessage(err: unknown, fallback: string): string {
  if (typeof err === 'object' && err !== null) {
    const ax = err as AxiosError<{ detail?: unknown; message?: unknown }>
    const detail = ax.response?.data?.detail
    if (detail) return detailToStr(detail)
    const msg = ax.response?.data?.message
    if (msg && typeof msg === 'string') return msg
    if (ax.message) return ax.message
  }
  return fallback
}
