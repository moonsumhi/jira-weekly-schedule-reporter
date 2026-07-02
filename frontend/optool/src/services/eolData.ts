// 배포판|버전 → EoL 종료 일자 (YYYY-MM) 정적 맵
// EoL = 무상 보안 패치가 완전히 종료되는 시점 (Standard/Full 지원 기준)
const EOL_MAP: Record<string, string> = {
  // Ubuntu (Standard Support 종료 기준)
  'Ubuntu|18.04': '2023-04',
  'Ubuntu|20.04': '2025-04',
  'Ubuntu|22.04': '2027-04',
  'Ubuntu|24.04': '2029-04',

  // Rocky Linux
  'Rocky Linux|8':    '2029-05',
  'Rocky Linux|9':    '2032-05',

  // CentOS
  'CentOS|6':  '2020-11',
  'CentOS|7':  '2024-06',
  'CentOS|8':  '2021-12',

  // RHEL (Maintenance Support 2 종료 기준)
  'RHEL|7': '2026-06',
  'RHEL|8': '2029-05',
  'RHEL|9': '2032-05',

  // Debian (LTS 종료 기준)
  'Debian|10': '2024-06',
  'Debian|11': '2026-06',
  'Debian|12': '2028-06',

  // Amazon Linux
  'Amazon Linux|2':    '2025-06',
  'Amazon Linux|2023': '2028-03',

  // Windows Server (Extended Support 종료 기준)
  'Windows Server|2012':    '2023-10',
  'Windows Server|2012 R2': '2023-10',
  'Windows Server|2016':    '2027-01',
  'Windows Server|2019':    '2029-01',
  'Windows Server|2022':    '2031-10',
  'Windows Server|2025':    '2034-10',
  'Windows Server|1909':    '2021-05',
  'Windows Server|2004':    '2021-12',
  'Windows Server|20H2':    '2022-05',

  // Windows 10
  'Windows 10|22H2': '2025-10',

  // Windows 11
  'Windows 11|21H2': '2024-10',
  'Windows 11|22H2': '2025-10',
  'Windows 11|23H2': '2026-11',

  // Oracle Database (Extended Support 종료 기준)
  'Oracle|12c R1': '2021-07',
  'Oracle|12c R2': '2022-03',
  'Oracle|19c':    '2027-04',
  'Oracle|21c':    '2024-04',
  'Oracle|23c':    '2028-04',

  // MariaDB (EOL 종료 기준)
  'MariaDB|10.2':  '2022-05',
  'MariaDB|10.3':  '2023-05',
  'MariaDB|10.4':  '2024-06',
  'MariaDB|10.5':  '2025-06',
  'MariaDB|10.6':  '2026-07',
  'MariaDB|10.11': '2028-02',
  'MariaDB|11.0':  '2024-06',
  'MariaDB|11.1':  '2024-08',
  'MariaDB|11.2':  '2024-11',
  'MariaDB|11.3':  '2025-02',
  'MariaDB|11.4':  '2029-05',

  // PostgreSQL (EOL 종료 기준)
  'PostgreSQL|12': '2024-11',
  'PostgreSQL|13': '2025-11',
  'PostgreSQL|14': '2026-11',
  'PostgreSQL|15': '2027-11',
  'PostgreSQL|16': '2028-11',
  'PostgreSQL|17': '2029-11',

  // MySQL (Extended Support 종료 기준)
  'MySQL|5.7': '2023-10',
  'MySQL|8.0': '2026-04',
  'MySQL|8.4': '2032-04',

  // MS SQL Server (Extended Support 종료 기준)
  'MS SQL Server|2017': '2027-10',
  'MS SQL Server|2019': '2030-01',
  'MS SQL Server|2022': '2033-01',

  // SAP HANA (Mainstream Maintenance 종료 기준)
  'SAP HANA|1.0':    '2023-01',
  'SAP HANA|SPS 05': '2023-06',
  'SAP HANA|SPS 06': '2024-06',
  'SAP HANA|SPS 07': '2025-06',
  'SAP HANA|SPS 08': '2026-06',
}

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

  if (!eolDate) return null

  const today = new Date().toISOString().slice(0, 7)
  return { status: eolDate <= today ? 'O' : 'X', date: eolDate }
}
