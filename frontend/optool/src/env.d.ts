declare module '@toast-ui/editor' {
  interface EditorOptions {
    el:               HTMLElement
    height?:          string
    minHeight?:       string
    initialValue?:    string
    initialEditType?: 'markdown' | 'wysiwyg'
    previewStyle?:    'tab' | 'vertical'
    placeholder?:     string
    toolbarItems?:    Array<string | string[]>
    events?:          Record<string, (...args: unknown[]) => void>
  }
  class Editor {
    constructor(options: EditorOptions)
    destroy(): void
    getMarkdown(): string
    setMarkdown(markdown: string): void
  }
  export default Editor
}

declare namespace NodeJS {
  interface ProcessEnv {
    NODE_ENV: string;
    VUE_ROUTER_MODE: 'hash' | 'history' | 'abstract' | undefined;
    VUE_ROUTER_BASE: string | undefined;

  }
}
