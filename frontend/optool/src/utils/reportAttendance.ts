type DaysValue = string | number | null | undefined

function decimalDays(value: DaysValue): { coefficient: bigint; scale: number } | null {
  const text = String(value ?? '').trim()
  if (!text || !Number.isFinite(Number(text)) || Number(text) < 0) return null
  const match = /^\+?(\d+(?:\.\d*)?|\.\d+)(?:e([+-]?\d+))?$/i.exec(text)
  if (!match) return null
  const exponent = Number(match[2] || 0)
  if (Math.abs(exponent) > 324) return null
  const [whole = '', fraction = ''] = match[1]!.split('.')
  const scale = fraction.length - exponent
  const coefficient = BigInt((whole || '0') + fraction)
  return scale < 0 ? { coefficient: coefficient * 10n ** BigInt(-scale), scale: 0 } : { coefficient, scale }
}

export function validAttendanceDays(value: DaysValue): boolean {
  return String(value ?? '').trim() === '' || decimalDays(value) !== null
}

// Scale decimal inputs before subtracting so 0.3 - 0.1 stays 0.2 without
// rounding the user's input to an arbitrary number of decimal places.
export function attendanceRemaining(accrued: DaysValue, used: DaysValue): string | null {
  const a = decimalDays(accrued), b = decimalDays(used)
  if (!a || !b) return null
  const scale = Math.max(a.scale, b.scale)
  const difference = a.coefficient * 10n ** BigInt(scale - a.scale) - b.coefficient * 10n ** BigInt(scale - b.scale)
  if (difference === 0n) return '0'
  const sign = difference < 0n ? '-' : ''
  const digits = (difference < 0n ? -difference : difference).toString().padStart(scale + 1, '0')
  if (!scale) return sign + digits
  const fraction = digits.slice(-scale).replace(/0+$/, '')
  return sign + digits.slice(0, -scale) + (fraction ? '.' + fraction : '')
}
