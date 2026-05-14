export type NetworkEosEntry = { pattern: string; label: string; date: string }
export type NetworkManualEntry = { pattern: string; label: string; status: 'EOS' | 'ACTIVE' }

// 네트워크 기종 EoS 매핑 (Cisco Nexus 위주)
// 날짜 출처: Cisco End-of-Life 공지 기준 (Last Date of Support)
export const NETWORK_EOS_LIST: NetworkEosEntry[] = [
  // Nexus 2000 FEX
  { pattern: '2148t',       label: 'Nexus 2148T',        date: '2017-06' },
  { pattern: '2224tp',      label: 'Nexus 2224TP',       date: '2017-06' },
  { pattern: '2232pp',      label: 'Nexus 2232PP',       date: '2017-06' },
  { pattern: '2248tp',      label: 'Nexus 2248TP',       date: '2017-06' },
  // Nexus 3000 (구형)
  { pattern: '3016',        label: 'Nexus 3016',         date: '2019-10' },
  { pattern: '3048',        label: 'Nexus 3048',         date: '2021-01' },
  { pattern: '3064t',       label: 'Nexus 3064-T',       date: '2022-01' },
  { pattern: '3064x',       label: 'Nexus 3064-X',       date: '2022-01' },
  { pattern: '3064pq',      label: 'Nexus 3064PQ',       date: '2021-01' },
  { pattern: '3064',        label: 'Nexus 3064',         date: '2021-01' },
  // Nexus 5000
  { pattern: '5010',        label: 'Nexus 5010',         date: '2017-01' },
  { pattern: '5020',        label: 'Nexus 5020',         date: '2017-01' },
  { pattern: '5548p',       label: 'Nexus 5548P',        date: '2022-01' },
  { pattern: '5548up',      label: 'Nexus 5548UP',       date: '2022-01' },
  { pattern: '5596t',       label: 'Nexus 5596T',        date: '2022-01' },
  { pattern: '5596up',      label: 'Nexus 5596UP',       date: '2022-01' },
  { pattern: '5672up16g',   label: 'Nexus 5672UP-16G',   date: '2023-08' },
  { pattern: '5672up',      label: 'Nexus 5672UP',       date: '2023-08' },
  // Nexus 6000
  { pattern: '6001p',       label: 'Nexus 6001P',        date: '2022-10' },
  { pattern: '6001t',       label: 'Nexus 6001T',        date: '2022-10' },
  { pattern: '6004ef',      label: 'Nexus 6004EF',       date: '2023-10' },
  { pattern: '6004',        label: 'Nexus 6004',         date: '2023-10' },
  // Nexus 7000 (구형 섀시)
  { pattern: '7004',        label: 'Nexus 7004',         date: '2024-10' },
  { pattern: '7009',        label: 'Nexus 7009',         date: '2024-10' },
  { pattern: '7010',        label: 'Nexus 7010',         date: '2024-10' },
  { pattern: '7018',        label: 'Nexus 7018',         date: '2024-10' },
  // Nexus 9000 (구형)
  { pattern: '9372px',      label: 'Nexus 9372PX',       date: '2024-04' },
  { pattern: '9372tx',      label: 'Nexus 9372TX',       date: '2024-04' },
  { pattern: '9396px',      label: 'Nexus 9396PX',       date: '2024-04' },
  { pattern: '9396tx',      label: 'Nexus 9396TX',       date: '2024-04' },
  { pattern: '93120tx',     label: 'Nexus 93120TX',      date: '2024-04' },
  { pattern: '93128tx',     label: 'Nexus 93128TX',      date: '2024-04' },
  { pattern: 'c93180ycex',  label: 'Nexus C93180YC-EX',  date: '2027-11' },
  { pattern: '93180ycex',   label: 'Nexus 93180YC-EX',   date: '2027-11' },
  { pattern: 'c93180ycfx2', label: 'Nexus C93180YC-FX2', date: '2029-12' },
  { pattern: '93180ycfx2',  label: 'Nexus 93180YC-FX2',  date: '2029-12' },
  { pattern: 'c9336cfx2',   label: 'Nexus C9336C-FX2',   date: '2030-12' },
  { pattern: '9336cfx2',    label: 'Nexus 9336C-FX2',    date: '2030-12' },
  { pattern: 'c93240ycfx2', label: 'Nexus C93240YC-FX2', date: '2030-12' },
  { pattern: '93240ycfx2',  label: 'Nexus 93240YC-FX2',  date: '2030-12' },
  // Nexus 9500 chassis
  { pattern: 'c9504',       label: 'Nexus C9504',        date: '2030-12' },
  { pattern: '9504',        label: 'Nexus 9504',         date: '2030-12' },
  { pattern: 'c9508',       label: 'Nexus C9508',        date: '2030-12' },
  { pattern: '9508',        label: 'Nexus 9508',         date: '2030-12' },
  { pattern: 'nexus9500',   label: 'Nexus 9500',         date: '2030-12' },
  { pattern: 'n9k9500',     label: 'Nexus 9500 (N9K)',   date: '2030-12' },
  // Nexus 9332
  { pattern: 'c9332c',      label: 'Nexus C9332C',       date: '2030-12' },
  { pattern: '9332c',       label: 'Nexus 9332C',        date: '2030-12' },
  // Cisco MDS (파이버채널)
  { pattern: 'mds9148s',    label: 'MDS 9148S',          date: '2024-10' },
  { pattern: 'mds9148',     label: 'MDS 9148',           date: '2024-10' },
  // Cisco ASR 1001
  { pattern: 'asr1001x',    label: 'ASR 1001-X',         date: '2026-12' },
  { pattern: 'asr1001',     label: 'ASR 1001',           date: '2026-12' },
  // Cisco Catalyst 9000
  { pattern: 'c9200',       label: 'Catalyst 9200',      date: '2030-12' },
  { pattern: 'c9300',       label: 'Catalyst 9300',      date: '2030-12' },
  { pattern: 'c9400',       label: 'Catalyst 9400',      date: '2030-12' },
  // Cisco Catalyst 2960X
  { pattern: 'wsc2960x',    label: 'Catalyst WS-C2960X', date: '2026-01' },
  { pattern: '2960x',       label: 'Catalyst 2960-X',    date: '2026-01' },
  // Cisco HyperFlex FI
  { pattern: 'hxfi6454',    label: 'HyperFlex FI-6454',  date: '2029-12' },
  { pattern: 'fi6454',      label: 'FI-6454',            date: '2029-12' },
  // Piolink
  { pattern: 'pask3200x',   label: 'PAS-K3200X',         date: '2024-12' },
  { pattern: 'pask3200',    label: 'PAS-K3200',          date: '2024-12' },
  // Fujitsu PRIMERGY
  { pattern: 'rx1330m4',    label: 'PRIMERGY RX1330 M4',  date: '2028-06' },
]

// 정확한 EoS 날짜 없이 지원 상태만 알려진 기종 목록
export const NETWORK_MANUAL_LIST: NetworkManualEntry[] = [
  // EoS 완료
  { pattern: 'secuimfd21000', label: 'SecuI MFD-21000',   status: 'EOS' },
  { pattern: 'mfd21000',      label: 'MFD-21000',         status: 'EOS' },
  { pattern: 'securegate',    label: 'SecureGate',        status: 'EOS' },
  { pattern: 'chakramax',     label: 'ChakraMax',         status: 'EOS' },
  { pattern: 'dguard',        label: 'D.Guard',           status: 'EOS' },
  { pattern: 'pc30',          label: '내PC지키미 3.0',     status: 'EOS' },
  // 지원 기간 중
  { pattern: 'paloalto',      label: 'Palo Alto',         status: 'ACTIVE' },
  { pattern: 'secuingf',      label: 'SecuI NGF',         status: 'ACTIVE' },
  { pattern: 'junipermag',    label: 'Juniper MAG',       status: 'ACTIVE' },
  { pattern: 'juniper',       label: 'Juniper',           status: 'ACTIVE' },
  { pattern: 'deepsecurity',  label: 'Deep Security',     status: 'ACTIVE' },
  { pattern: 'deepdiscovery', label: 'Deep Discovery',    status: 'ACTIVE' },
  { pattern: 'sparrow',       label: 'Sparrow',           status: 'ACTIVE' },
  { pattern: 'superserver',   label: 'SuperServer',       status: 'ACTIVE' },
  { pattern: 'wsus',          label: 'WSUS',              status: 'ACTIVE' },
  { pattern: 'bluemax',       label: 'BlueMax',           status: 'ACTIVE' },
  { pattern: 'pcfilter',      label: 'PC Filter',         status: 'ACTIVE' },
  { pattern: 'genian',        label: 'Genian',            status: 'ACTIVE' },
  { pattern: 'dbsafer',       label: 'DBSafer',           status: 'ACTIVE' },
  { pattern: 'secuve',        label: 'SecuVe',            status: 'ACTIVE' },
  { pattern: 'medialand',     label: 'Medialand',         status: 'ACTIVE' },
  { pattern: 'wshield',       label: 'W-Shield',          status: 'ACTIVE' },
  { pattern: 'secuway',       label: 'Secuway',           status: 'ACTIVE' },
  { pattern: 'vada',          label: 'VADA',              status: 'ACTIVE' },
  { pattern: 'coolfilter',    label: 'CoolFilter',        status: 'ACTIVE' },
  { pattern: 'dellpoweredge', label: 'Dell PowerEdge',    status: 'ACTIVE' },
  { pattern: 'spamsniper',    label: 'SpamSniper',        status: 'ACTIVE' },
  { pattern: 'sslu3000',      label: 'SSL U3000',         status: 'ACTIVE' },
  { pattern: 'wapple',        label: 'Wapple',            status: 'ACTIVE' },
  { pattern: 'serveri',       label: 'ServerI',           status: 'ACTIVE' },
  { pattern: 'ntp',           label: 'NTP',               status: 'ACTIVE' },
  { pattern: 'v3',            label: 'V3',                status: 'ACTIVE' },
]
