interface EditorModelAdapter {
  read(): string
  write(value: string): void
  emit(value: string): void
  onCompositionSettled(): void
}

/** Keep Vue model echoes from replacing the DOM owned by the native IME. */
export function createEditorModelSync(adapter: EditorModelAdapter) {
  let composing = false
  let applying = false
  let disposed = false
  let lastEmitted: string | undefined
  let compositionTimer: ReturnType<typeof setTimeout> | undefined

  function cancelCompositionTimer() {
    if (compositionTimer !== undefined) clearTimeout(compositionTimer)
    compositionTimer = undefined
  }

  function publish() {
    if (disposed || composing || applying) return
    const value = adapter.read()
    lastEmitted = value
    adapter.emit(value)
  }

  return {
    get composing() { return composing },
    publish,
    applyExternal(value: string) {
      if (disposed || composing || value === lastEmitted) return
      if (value === adapter.read()) return
      lastEmitted = undefined
      applying = true
      try {
        adapter.write(value)
      } finally {
        applying = false
      }
    },
    compositionStart() {
      cancelCompositionTimer()
      composing = true
    },
    compositionEnd() {
      cancelCompositionTimer()
      // Our capture listener runs before ProseMirror's compositionend handler.
      // Wait for its final input/DOM observer updates, including microtasks.
      compositionTimer = setTimeout(() => {
        compositionTimer = undefined
        if (disposed) return
        composing = false
        publish()
        adapter.onCompositionSettled()
      }, 0)
    },
    dispose() {
      disposed = true
      cancelCompositionTimer()
    },
  }
}
