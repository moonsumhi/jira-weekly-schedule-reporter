import type { AxiosError } from 'axios'

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
