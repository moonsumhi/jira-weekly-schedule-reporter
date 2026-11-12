import { onBeforeUnmount, onMounted } from 'vue'

/** Keep an open report current without interrupting a dialog or a hidden tab. */
export function useReportAutoRefresh(enabled: () => boolean, refresh: () => Promise<void>) {
  let timer: ReturnType<typeof setInterval> | undefined
  let pending = false
  async function check() {
    if (pending || !enabled() || document.visibilityState !== 'visible'
      || document.querySelector('.q-dialog')) return
    pending = true
    try { await refresh() } finally { pending = false }
  }
  const onVisible = () => { void check() }
  onMounted(() => {
    timer = setInterval(onVisible, 30_000)
    window.addEventListener('focus', onVisible)
    document.addEventListener('visibilitychange', onVisible)
  })
  onBeforeUnmount(() => {
    clearInterval(timer)
    window.removeEventListener('focus', onVisible)
    document.removeEventListener('visibilitychange', onVisible)
  })
}
