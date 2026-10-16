function normalizedHeading(value: string): string {
  return value.replace(/[\s*_`~]/g, '').toLocaleLowerCase()
}

/** Returns only the text shown in the imported-content editor's original panel. */
export function originalImportedContent(source: string): string {
  const headings = [...source.matchAll(/^##\s+([^\n]+?)\s*$/gm)]
  const originalIndex = headings.findIndex((heading) => normalizedHeading(heading[1] ?? '') === '원본내용')
  const mappingIndex = headings.findIndex((heading) => normalizedHeading(heading[1] ?? '') === '매핑확인')

  if (originalIndex < 0 && mappingIndex < 0) return source
  if (originalIndex < 0) return ''

  const heading = headings[originalIndex]
  if (!heading || heading.index == null) return ''
  const end = headings[originalIndex + 1]?.index ?? source.length
  return source.slice(heading.index + heading[0].length, end).trim()
}

/** Ignores empty Markdown editor scaffolding while preserving text, tables, and images. */
export function hasMeaningfulImportedContent(source: string): boolean {
  const original = originalImportedContent(source)
  if (/!\[[^\]]*\]\([^)]*\)|<img\b/i.test(original)) return true

  const visibleText = original
    .replace(/<!--[\s\S]*?-->/g, ' ')
    // Imported section labels and editor placeholders are not unmapped data.
    .replace(/^\s*#{1,6}\s+[^\n]*$/gm, ' ')
    // WYSIWYG emits attributed empty breaks such as
    // <br class="ProseMirror-trailingBreak"> after the last character is
    // deleted. Strip editor markup tags, including their attributes, while
    // leaving literal angle-bracket text intact.
    .replace(/<\/?(?:p|br|div|span|table|thead|tbody|tfoot|tr|td|th|colgroup|col|ul|ol|li|h[1-6]|blockquote|pre|code|strong|em|b|i|u|s|hr)\b[^>]*>/gi, ' ')
    .replace(/&nbsp;|&#0*160;?|&#x0*a0;?|&amp;nbsp;/gi, ' ')
    .replace(/&(?:lt|gt|quot|apos);/gi, ' ')
    .replace(/&(?:#0*8203|#x0*200b|ZeroWidthSpace);?/gi, ' ')
    .replace(/^\s*\|(?:\s*\|)*\s*$/gm, '')
    .replace(/^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/gm, '')
    .replace(/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/gm, '')
    .replace(/[|\u200B-\u200D\uFEFF]/g, '')
    .trim()

  return visibleText.length > 0
}
