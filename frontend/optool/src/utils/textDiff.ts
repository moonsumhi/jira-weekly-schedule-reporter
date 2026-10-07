export type TextDiffSegment = { kind: 'same' | 'added' | 'removed'; text: string }

export function diffTextCharacters(beforeText: string, afterText: string): TextDiffSegment[] {
  const before = Array.from(beforeText)
  const after = Array.from(afterText)
  const rowSize = after.length + 1
  const cellCount = (before.length + 1) * rowSize

  if (cellCount > 500_000) {
    let prefixLength = 0
    while (prefixLength < before.length && prefixLength < after.length && before[prefixLength] === after[prefixLength]) prefixLength += 1
    let suffixLength = 0
    while (suffixLength < before.length - prefixLength && suffixLength < after.length - prefixLength && before[before.length - suffixLength - 1] === after[after.length - suffixLength - 1]) suffixLength += 1
    const fallback: TextDiffSegment[] = [
      { kind: 'same', text: before.slice(0, prefixLength).join('') },
      { kind: 'removed', text: before.slice(prefixLength, before.length - suffixLength).join('') },
      { kind: 'added', text: after.slice(prefixLength, after.length - suffixLength).join('') },
      { kind: 'same', text: suffixLength ? before.slice(before.length - suffixLength).join('') : '' },
    ]
    return fallback.filter(segment => segment.text.length > 0)
  }

  const matrix = new Uint32Array(cellCount)
  const matrixValue = (row: number, column: number) => matrix[row * rowSize + column] ?? 0
  for (let beforeIndex = before.length - 1; beforeIndex >= 0; beforeIndex -= 1) {
    for (let afterIndex = after.length - 1; afterIndex >= 0; afterIndex -= 1) {
      const cell = beforeIndex * rowSize + afterIndex
      matrix[cell] = before[beforeIndex] === after[afterIndex]
        ? matrixValue(beforeIndex + 1, afterIndex + 1) + 1
        : Math.max(matrixValue(beforeIndex + 1, afterIndex), matrixValue(beforeIndex, afterIndex + 1))
    }
  }

  const segments: TextDiffSegment[] = []
  const append = (kind: TextDiffSegment['kind'], character: string) => {
    const last = segments[segments.length - 1]
    if (last?.kind === kind) last.text += character
    else segments.push({ kind, text: character })
  }
  let beforeIndex = 0
  let afterIndex = 0
  while (beforeIndex < before.length || afterIndex < after.length) {
    const beforeCharacter = before[beforeIndex]
    const afterCharacter = after[afterIndex]
    if (beforeIndex < before.length && afterIndex < after.length && beforeCharacter === afterCharacter) {
      append('same', beforeCharacter!)
      beforeIndex += 1
      afterIndex += 1
    } else if (afterIndex < after.length && (beforeIndex === before.length || matrixValue(beforeIndex, afterIndex + 1) >= matrixValue(beforeIndex + 1, afterIndex))) {
      append('added', afterCharacter!)
      afterIndex += 1
    } else {
      append('removed', beforeCharacter!)
      beforeIndex += 1
    }
  }
  return segments
}
