const liveDialogTokens = new Set<string>()

/** Keep a temporary, same-URL history entry while a dialog is open. */
export function createDialogHistory(browser: Window, onBack: () => void) {
  const key = '__optoolIssueDialog'
  const token = `${Date.now()}-${Math.random()}`
  let active = false
  let desiredOpen = false
  let disposed = false
  let url = ''
  let pending: Promise<void> | undefined
  let resolvePending: (() => void) | undefined

  function onPop(event: PopStateEvent) {
    if (!active || event.state?.[key] === token) return
    const sameUrl = browser.location.href === url
    active = false
    liveDialogTokens.delete(token)
    browser.removeEventListener('popstate', onPop, true)
    if (sameUrl) event.stopImmediatePropagation()
    const notify = desiredOpen && !pending
    if (!pending) desiredOpen = false
    const resolve = resolvePending
    pending = undefined
    resolvePending = undefined
    resolve?.()
    if (notify && !disposed) onBack()
  }

  function open() {
    desiredOpen = true
    if (disposed || active) return
    url = browser.location.href
    const state = { ...browser.history.state, [key]: token }
    // Reuse a marker restored by Forward or a page reload.
    if (browser.history.state?.[key] && !liveDialogTokens.has(browser.history.state[key])) browser.history.replaceState(state, '', url)
    else browser.history.pushState(state, '', url)
    active = true
    liveDialogTokens.add(token)
    browser.addEventListener('popstate', onPop, true)
  }

  function close(): Promise<void> {
    desiredOpen = false
    if (pending) return pending
    if (!active) return Promise.resolve()
    if (browser.history.state?.[key] !== token || browser.location.href !== url) {
      active = false
      liveDialogTokens.delete(token)
      browser.removeEventListener('popstate', onPop, true)
      return Promise.resolve()
    }
    pending = new Promise<void>((resolve) => { resolvePending = resolve })
    browser.history.back()
    return pending
  }

  async function setOpen(value: boolean) {
    if (!value) return close()
    desiredOpen = true
    if (pending) await pending
    if (!disposed && desiredOpen) open()
  }

  return {
    setOpen,
    close,
    dispose() {
      disposed = true
      void close()
    },
  }
}
