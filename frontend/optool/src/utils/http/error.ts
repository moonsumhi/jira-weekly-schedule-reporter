import type { AxiosError } from 'axios'

export function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

// ctx 값(숫자/문자/불리언만 안전하게 표시 가능)을 표시용 문자열로 변환.
function ctxToStr(v: unknown): string {
  if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') return String(v)
  return ''
}

// FastAPI/Pydantic v2 검증 에러(422)의 raw type을 한글 메시지로 변환.
// 매핑에 없는 type은 원래 msg(영문)를 그대로 반환 — 새로 생긴 제약 조건을
// 놓치더라도 최소한 에러 발생 자체는 사용자에게 전달된다.
function translatePydanticError(item: Record<string, unknown>): string {
  const type = typeof item.type === 'string' ? item.type : ''
  const ctx = isRecord(item.ctx) ? item.ctx : {}
  const msg = typeof item.msg === 'string' ? item.msg : ''

  switch (type) {
    case 'string_too_long':
      return `최대 ${ctxToStr(ctx.max_length)}자까지 입력할 수 있습니다.`
    case 'string_too_short':
      return `최소 ${ctxToStr(ctx.min_length)}자 이상 입력해야 합니다.`
    case 'missing':
      return '필수 항목입니다.'
    case 'string_type':
    case 'int_type':
    case 'float_type':
    case 'bool_type':
    case 'int_parsing':
    case 'float_parsing':
    case 'datetime_parsing':
    case 'date_parsing':
      return '형식이 올바르지 않습니다.'
    case 'greater_than':
      return `${ctxToStr(ctx.gt)}보다 커야 합니다.`
    case 'greater_than_equal':
      return `${ctxToStr(ctx.ge)} 이상이어야 합니다.`
    case 'less_than':
      return `${ctxToStr(ctx.lt)}보다 작아야 합니다.`
    case 'less_than_equal':
      return `${ctxToStr(ctx.le)} 이하여야 합니다.`
    case 'value_error':
    case 'assertion_error':
      // 개발자가 model_validator 등에서 직접 raise한 메시지 — 대개 이미 한글이므로 그대로 사용
      return msg || '입력값을 확인해주세요.'
    default:
      return msg
  }
}

function detailToStr(v: unknown): string {
  if (typeof v === 'string') return v
  if (Array.isArray(v)) {
    return v.map((item) => {
      if (item && typeof item === 'object' && 'msg' in item) return translatePydanticError(item as Record<string, unknown>)
      return typeof item === 'string' ? item : JSON.stringify(item)
    }).join(', ')
  }
  try { return JSON.stringify(v) } catch { return String(v) }
}

export function getErrorMessage(err: unknown, fallback: string): string {
  if (typeof err === 'object' && err !== null) {
    const ax = err as AxiosError<{ detail?: unknown; message?: unknown }>
    const detail = ax.response?.data?.detail
    if (detail) return detailToStr(detail)
    const msg = ax.response?.data?.message
    if (msg && typeof msg === 'string') return msg
    if (ax.message) return ax.message
  }
  return fallback
}
