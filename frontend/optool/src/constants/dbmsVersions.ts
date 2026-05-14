function numRange(start: number, end: number): number[] {
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
}

// DBMS 종류 → 시리즈 → 패치버전 트리
export const DBMS_TREE: Record<string, Record<string, string[]>> = {
  MariaDB: {
    '10.2': numRange(14, 44).map(n => `10.2.${n}`),
    '10.3': numRange(6, 39).map(n => `10.3.${n}`),
    '10.4': numRange(6, 32).map(n => `10.4.${n}`),
    '10.5': numRange(3, 25).map(n => `10.5.${n}`),
    '10.6': numRange(4, 19).map(n => `10.6.${n}`),
    '10.11': numRange(2, 10).map(n => `10.11.${n}`),
    '11.0': numRange(2, 6).map(n => `11.0.${n}`),
    '11.1': numRange(2, 6).map(n => `11.1.${n}`),
    '11.2': numRange(2, 5).map(n => `11.2.${n}`),
    '11.3': numRange(2, 3).map(n => `11.3.${n}`),
    '11.4': numRange(2, 5).map(n => `11.4.${n}`),
  },
  PostgreSQL: {
    '12': numRange(0, 20).map(n => `12.${n}`),
    '13': numRange(0, 16).map(n => `13.${n}`),
    '14': numRange(0, 13).map(n => `14.${n}`),
    '15': numRange(0, 8).map(n => `15.${n}`),
    '16': numRange(0, 4).map(n => `16.${n}`),
    '17': numRange(0, 2).map(n => `17.${n}`),
  },
  MySQL: {
    '5.7': numRange(0, 44).map(n => `5.7.${n}`),
    '8.0': numRange(0, 40).map(n => `8.0.${n}`),
    '8.4': numRange(0, 3).map(n => `8.4.${n}`),
  },
  Oracle: {
    '12c R1': ['12.1.0.1', '12.1.0.2'],
    '12c R2': ['12.2.0.1'],
    '19c': ['19.3', '19.5', '19.8', '19.10', '19.12', '19.14', '19.16', '19.18', '19.20', '19.22', '19.24'],
    '21c': ['21.3', '21.5', '21.6', '21.7', '21.8', '21.9', '21.10', '21.11', '21.12', '21.13'],
    '23c': ['23.2', '23.3', '23.4'],
  },
  'MS SQL Server': {
    '2017': [],
    '2019': [],
    '2022': [],
  },
  'SAP HANA': {
    '1.0': ['SPS 12'],
    '2.0': ['SPS 05', 'SPS 06', 'SPS 07', 'SPS 08'],
  },
}
