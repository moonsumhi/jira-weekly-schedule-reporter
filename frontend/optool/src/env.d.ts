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
    hooks?: {
      addImageBlobHook?: (blob: Blob | File, callback: (url: string, altText?: string) => void) => void
    }
  }
  class Editor {
    constructor(options: EditorOptions)
    destroy(): void
    getMarkdown(): string
    setMarkdown(markdown: string): void
    exec(command: string, payload?: Record<string, string>): void
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
