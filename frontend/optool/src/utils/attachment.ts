import { useAuthStore } from 'src/stores/auth'

/** 첨부파일 url(/api/uploads/pm/xxx.hwp)을 /app/uploads 기준 상대경로(pm/xxx.hwp)로 변환.
 * app/routers/attachments.py의 hwp-preview / docx-preview 엔드포인트 path 파라미터용. */
export function attachmentRelPath(url: string): string {
  return url.replace(/^\/api\/uploads\//, '')
}

export async function downloadAttachment(url: string, filename: string): Promise<void> {
  const token = useAuthStore().token
  const resp = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!resp.ok) throw new Error(`${resp.status}`)
  const blob = await resp.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}
