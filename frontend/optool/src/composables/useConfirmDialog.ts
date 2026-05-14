import { useQuasar } from 'quasar'

interface ConfirmOptions {
  title: string
  message: string
  html?: boolean
  okLabel?: string
  okColor?: string
  cancelLabel?: string
}

export function useConfirmDialog() {
  const $q = useQuasar()

  function confirm(options: ConfirmOptions): Promise<void> {
    return new Promise((resolve, reject) => {
      $q.dialog({
        title: options.title,
        message: options.message,
        html: options.html ?? false,
        cancel: { label: options.cancelLabel ?? '취소', flat: true },
        ok: { label: options.okLabel ?? '확인', color: options.okColor ?? 'primary' },
      })
        .onOk(() => resolve())
        .onCancel(() => reject(new Error('cancelled')))
        .onDismiss(() => reject(new Error('cancelled')))
    })
  }

  return { confirm }
}
