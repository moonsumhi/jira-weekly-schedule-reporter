import { DBMS_TREE } from 'src/constants/dbmsVersions'
import eolMapSnapshot from 'src/data/eol_map_snapshot.json'

// 배포판|버전 → EoL 종료 일자 (YYYY-MM) 스냅샷
// EoL = 무상 보안 패치가 완전히 종료되는 시점 (Standard/Full 지원 기준)
const EOL_MAP: Record<string, string> = eolMapSnapshot

export interface EolResult {
  /** 'O' = EoL 도달, 'X' = 미도달 */
  status: 'O' | 'X'
  date: string
}

export function eolStatusLabel(v: unknown): string {
  const s = typeof v === 'string' ? v.toUpperCase() : ''
  if (s === 'O') return 'EoL 지남'
  if (s === 'X') return '지원 기간 중'
  return '확인 불가'
}

export function eolStatusColor(v: unknown): string {
  const s = typeof v === 'string' ? v.toUpperCase() : ''
  if (s === 'O') return 'negative'
  if (s === 'X') return 'positive'
  return 'grey'
}

export function getAutoEol(dist: string, version: string): EolResult | null {
  // fields는 느슨한 타입이라 실제로는 문자열이 아닌 값(숫자 등)이 들어올 수 있음
  dist = String(dist ?? '')
  version = String(version ?? '')
  if (!dist) return null

  // dist|version 직접 조회
  let eolDate = EOL_MAP[`${dist}|${version}`]

  // 마이너 버전 포함 시 단계적으로 축약해 재시도
  // 예: 22.04.3 → 22.04 → 22 / 8.10 → 8
  if (!eolDate && version?.includes('.')) {
    const lastDot = version.lastIndexOf('.')
    const secondMajor = version.slice(0, lastDot)          // 22.04.3 → 22.04
    eolDate = EOL_MAP[`${dist}|${secondMajor}`]
    if (!eolDate) {
      const firstDot = version.indexOf('.')
      if (firstDot !== lastDot) {                           // 점이 2개 이상인 경우만
        const major = version.slice(0, firstDot)            // 22.04.3 → 22
        eolDate = EOL_MAP[`${dist}|${major}`]
      }
    }
  }

  // Oracle/SAP HANA 패치 버전은 숫자 축약만으로 19c/2.0 같은 시리즈를
  // 찾을 수 없으므로 DBMS 드롭다운의 소속 시리즈로 재조회한다.
  if (!eolDate) {
    const series = Object.entries(DBMS_TREE[dist] ?? {}).find(([, patches]) => patches.includes(version))?.[0]
    if (series) eolDate = EOL_MAP[`${dist}|${series}`]
  }

  if (!eolDate) return null

  const today = new Date().toISOString().slice(0, 7)
  return { status: eolDate <= today ? 'O' : 'X', date: eolDate }
}
