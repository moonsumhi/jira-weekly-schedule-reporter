/** Snapshot the page and nested lists before a teleported dialog takes focus. */
export function captureDialogScroll(browser: Window) {
  const left = browser.scrollX
  const top = browser.scrollY
  const elements = Array.from(browser.document.querySelectorAll<HTMLElement>(
    '.q-page-container, .q-page-container *, .q-dialog, .q-dialog *',
  ))
    .filter(element => element.scrollTop !== 0 || element.scrollLeft !== 0)
    .map(element => ({ element, left: element.scrollLeft, top: element.scrollTop }))

  return () => {
    for (const position of elements) {
      if (position.element.isConnected) {
        position.element.scrollTo({ left: position.left, top: position.top, behavior: 'instant' })
      }
    }
    browser.scrollTo({ left, top, behavior: 'instant' })
  }
}
