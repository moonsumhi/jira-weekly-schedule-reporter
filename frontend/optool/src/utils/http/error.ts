import type { AxiosError } from 'axios'

export function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

export function getErrorMessage(err: unknown, fallback: string) {
  if (typeof err === 'object' && err !== null) {
    const ax = err as AxiosError<{ detail?: string; message?: string }>
    return (
      ax.response?.data?.detail ||
      ax.response?.data?.message ||
      ax.message ||
      fallback
    )
  }
  return fallback
}
