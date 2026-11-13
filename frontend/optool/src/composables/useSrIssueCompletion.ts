import { useQuasar } from 'quasar'
import { getAdminSR, type SRStatus } from 'src/services/sr'

export function useSrIssueCompletion() {
  const $q = useQuasar()
  return async (ids: string[], status: SRStatus): Promise<boolean> => {
    if (status !== 'COMPLETED') return false
    const requests = await Promise.all(ids.map(getAdminSR))
    if (!requests.some(sr => sr.convertedIssueId || sr.relatedIssueId)) return false
    return new Promise(resolve => {
      $q.dialog({
        title: '연결된 일감 완료',
        message: '스케줄 관리에서도 연결된 일감을 완료 처리할까요? 아니요를 선택하면 SR만 처리 완료됩니다.',
        persistent: true,
        ok: { label: '예', color: 'primary' },
        cancel: { label: '아니요', flat: true },
      }).onOk(() => resolve(true)).onCancel(() => resolve(false))
    })
  }
}
