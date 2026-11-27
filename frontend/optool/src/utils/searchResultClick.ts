/** Keep IME blur from refiltering/replacing the pressed result before click. */
export function preserveSearchResultClick(event: MouseEvent, input?: HTMLElement | null) {
  if (event.button === 0 && input && input.ownerDocument.activeElement === input) {
    // Navigation still happens on click, not mousedown; keyboard activation is unchanged.
    event.preventDefault()
  }
}
