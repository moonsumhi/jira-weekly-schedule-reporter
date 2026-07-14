export type FieldType = 'text' | 'textarea' | 'date' | 'datetime' | 'select' | 'editor'

export interface SRTypeField {
  key: string
  label: string
  required: boolean
  type: FieldType
  options?: { value: string; label: string }[]
  rows?: number
  placeholder?: string
  half?: boolean  // col-6 width
}

export const SR_TYPE_FIELDS: Record<string, SRTypeField[]> = {
  IMPROVEMENT: [
    { key: 'currentProblem',    label: '현재 문제점',     required: true,  type: 'textarea', rows: 3, placeholder: '현재 어떤 점이 불편한지 구체적으로 설명해주세요.' },
    { key: 'improvementDetail', label: '개선 요청 내용',  required: true,  type: 'editor' },
    { key: 'expectedEffect',    label: '기대 효과',       required: true,  type: 'textarea', rows: 2, placeholder: '업무 시간 단축, 오류 감소, 편의성 향상 등' },
    { key: 'targetMenu',        label: '관련 화면 / 메뉴', required: false, type: 'text',     placeholder: '개선 대상 메뉴 또는 화면명' },
    { key: 'referenceCase',     label: '참고 사례',        required: false, type: 'textarea', rows: 2, placeholder: '비슷한 시스템, 화면, 예시 URL 등' },
    { key: 'completionCriteria',label: '완료 기준',        required: false, type: 'textarea', rows: 2, placeholder: '어떤 상태가 되면 완료로 볼 수 있는지' },
  ],

  BUG_FIX: [
    { key: 'errorScreen',    label: '오류 발생 화면', required: true,  type: 'text',     placeholder: '메뉴명, URL, 기능명', half: true },
    { key: 'occurredAt',     label: '발생 일시',      required: true,  type: 'datetime',                                    half: true },
    { key: 'errorMessage',   label: '오류 내용',      required: true,  type: 'textarea', rows: 2, placeholder: '화면에 표시된 메시지, 증상' },
    { key: 'reproduceSteps', label: '재현 절차',      required: true,  type: 'editor' },
    { key: 'expectedResult', label: '기대 동작',      required: true,  type: 'textarea', rows: 2, placeholder: '원래 어떻게 동작해야 하는지', half: true },
    { key: 'actualResult',   label: '실제 동작',      required: true,  type: 'textarea', rows: 2, placeholder: '실제로 어떻게 동작했는지',   half: true },
    { key: 'userEnvironment',label: '사용자 환경',    required: false, type: 'text',     placeholder: '브라우저, OS, 계정, 권한 등' },
  ],

  DATA_REQUEST: [
    { key: 'dataPurpose',          label: '데이터 요청 목적',  required: true,  type: 'textarea', rows: 2, placeholder: '분석, 보고, 검증, 연구 등' },
    { key: 'dataItems',            label: '요청 데이터 항목',  required: true,  type: 'editor' },
    { key: 'dataPeriodFrom',       label: '데이터 기간 (시작)', required: true, type: 'date',                                    half: true },
    { key: 'dataPeriodTo',         label: '데이터 기간 (종료)', required: true, type: 'date',                                    half: true },
    { key: 'dataCondition',        label: '대상 조건',          required: true,  type: 'textarea', rows: 2, placeholder: '특정 기관, 사용자, 시스템 등' },
    { key: 'containsPersonalInfo', label: '개인정보 포함 여부', required: true,  type: 'select',
      options: [{ value: 'yes', label: '포함' }, { value: 'no', label: '미포함' }, { value: 'unknown', label: '모름' }], half: true },
    { key: 'containsSensitiveInfo',label: '민감정보 포함 여부', required: true,  type: 'select',
      options: [{ value: 'yes', label: '포함' }, { value: 'no', label: '미포함' }, { value: 'unknown', label: '모름' }], half: true },
    { key: 'deliveryFormat',       label: '제공 형식',          required: true,  type: 'select',
      options: [{ value: 'csv', label: 'CSV' }, { value: 'excel', label: 'Excel' }, { value: 'sql', label: 'SQL 결과' }, { value: 'api', label: 'API' }, { value: 'other', label: '기타' }], half: true },
    { key: 'deliveryMethod',       label: '제공 방식',          required: true,  type: 'select',
      options: [{ value: 'internal', label: '내부망 전달' }, { value: 'permission', label: '권한 부여' }, { value: 'encrypted', label: '암호화 파일' }, { value: 'other', label: '기타' }], half: true },
    { key: 'approver',             label: '승인자',             required: true,  type: 'text',     placeholder: '부서장, 데이터 책임자 등' },
    { key: 'retentionDate',        label: '보관 / 파기 예정일', required: false, type: 'date' },
  ],

  PERMISSION: [
    { key: 'targetUser',          label: '권한 대상자',    required: true,  type: 'text',    placeholder: '이름, 소속, 계정 ID' },
    { key: 'requestedPermission', label: '요청 권한',      required: true,  type: 'text',    placeholder: '관리자, 조회자, 등록자 등' },
    { key: 'permissionReason',    label: '요청 사유',      required: true,  type: 'editor' },
    { key: 'permissionDuration',  label: '권한 사용 기간', required: true,  type: 'select',
      options: [{ value: 'permanent', label: '상시' }, { value: 'temporary', label: '임시' }, { value: 'specific', label: '특정 기간' }], half: true },
    { key: 'permissionExpiry',    label: '만료일',         required: false, type: 'date',                                    half: true },
    { key: 'approver',            label: '승인자',         required: true,  type: 'text',    placeholder: '부서장 또는 시스템 책임자' },
    { key: 'existingPermission',  label: '기존 권한 여부', required: false, type: 'select',
      options: [{ value: 'new', label: '신규' }, { value: 'change', label: '변경' }, { value: 'revoke', label: '회수' }] },
  ],

  CONFIG_CHANGE: [
    { key: 'configTarget',        label: '설정 대상',        required: true,  type: 'text',    placeholder: '시스템, 서버, 모듈, 메뉴 등' },
    { key: 'changeDetail',        label: '변경 요청 상세 내용', required: true, type: 'editor' },
    { key: 'currentValue',        label: '현재 설정값',      required: true,  type: 'textarea', rows: 2,                            half: true },
    { key: 'requestedValue',      label: '변경 요청값',      required: true,  type: 'textarea', rows: 2,                            half: true },
    { key: 'changeReason',        label: '변경 사유',        required: true,  type: 'textarea', rows: 3 },
    { key: 'impactScope',         label: '영향 범위',        required: true,  type: 'textarea', rows: 2, placeholder: '사용자, 기능, 연계 시스템 영향' },
    { key: 'applyDatetime',       label: '적용 희망 일시',   required: true,  type: 'datetime',                                     half: true },
    { key: 'serviceInterruption', label: '서비스 중단 여부', required: true,  type: 'select',
      options: [{ value: 'yes', label: '있음' }, { value: 'no', label: '없음' }, { value: 'unknown', label: '모름' }],              half: true },
    { key: 'rollbackPlan',        label: '롤백 방안',        required: false, type: 'textarea', rows: 2, placeholder: '문제 발생 시 원복 방법' },
    { key: 'verificationMethod',  label: '검증 방법',        required: false, type: 'textarea', rows: 2, placeholder: '변경 후 확인 방법' },
  ],

  SERVER_INFRA: [
    { key: 'targetServer',       label: '대상 서버 / 시스템', required: true,  type: 'text',    placeholder: '호스트명, IP, 시스템명' },
    { key: 'workType',           label: '요청 작업 유형',     required: true,  type: 'select',
      options: [
        { value: 'create',   label: '서버 생성' }, { value: 'restart', label: '서버 재기동' },
        { value: 'disk',     label: '디스크 증설' }, { value: 'firewall', label: '방화벽 정책' },
        { value: 'ssl',      label: 'SSL 인증서' }, { value: 'deploy',  label: '배포 환경' },
        { value: 'db',       label: 'DB 설정' }, { value: 'log',     label: '로그 수집' }, { value: 'other', label: '기타' },
      ] },
    { key: 'workDetail',         label: '요청 상세',          required: true,  type: 'editor' },
    { key: 'resourceInfo',       label: '리소스 정보',        required: false, type: 'text',    placeholder: 'CPU, Memory, Disk, Port 등' },
    { key: 'workDatetime',       label: '작업 희망 일시',     required: true,  type: 'datetime',                                    half: true },
    { key: 'serviceImpact',      label: '서비스 영향 여부',   required: true,  type: 'select',
      options: [{ value: 'stop', label: '서비스 중단' }, { value: 'delay', label: '처리 지연' }, { value: 'none', label: '무중단' }], half: true },
    { key: 'backupRequired',     label: '사전 백업 필요 여부',required: false, type: 'select',
      options: [{ value: 'yes', label: '필요' }, { value: 'no', label: '불필요' }] },
    { key: 'verificationMethod', label: '작업 후 확인 방법',  required: false, type: 'textarea', rows: 2, placeholder: '서비스 접속, 로그 확인 등' },
  ],

  SECURITY: [
    { key: 'securityRequestType', label: '보안 요청 유형',          required: true,  type: 'select',
      options: [
        { value: 'vulnerability',    label: '취약점 조치' }, { value: 'account',          label: '계정 점검' },
        { value: 'permission_revoke',label: '권한 회수' },   { value: 'log_check',        label: '로그 확인' },
        { value: 'other',            label: '기타' },
      ] },
    { key: 'securityIssue',        label: '취약점 또는 보안 이슈',  required: true,  type: 'editor' },
    { key: 'riskLevel',            label: '위험도',                  required: true,  type: 'select',
      options: [{ value: 'high', label: '상' }, { value: 'medium', label: '중' }, { value: 'low', label: '하' }], half: true },
    { key: 'diagnosisStandard',    label: '진단 기준',               required: false, type: 'text',    placeholder: 'ISMS-P, 내부 점검, 모의해킹 등',              half: true },
    { key: 'requestedAction',      label: '조치 요청 내용',          required: true,  type: 'textarea', rows: 3, placeholder: '어떤 조치를 원하는지 설명해주세요.' },
    { key: 'actionDeadline',       label: '조치 기한',               required: true,  type: 'date',                                                                  half: true },
    { key: 'evidenceRequired',     label: '증적 필요 여부',          required: true,  type: 'select',
      options: [{ value: 'yes', label: '필요' }, { value: 'no', label: '불필요' }],                                                                                  half: true },
    { key: 'evidenceFormat',       label: '증적 양식',               required: false, type: 'text',    placeholder: '캡처, 명령어 결과, 점검표 등' },
    { key: 'exceptionApproval',    label: '예외 승인 여부',          required: false, type: 'select',
      options: [{ value: 'yes', label: '예외 처리 필요' }, { value: 'no', label: '해당 없음' }] },
  ],

  FIREWALL: [
    { key: 'requestKind',    label: '신청 구분',          required: true,  type: 'select',
      options: [
        { value: 'new',    label: '신규 오픈' }, { value: 'change', label: '정책 변경' },
        { value: 'delete', label: '정책 삭제' }, { value: 'temp',   label: '임시 오픈' },
      ], half: true },
    { key: 'environment',    label: '적용 환경',          required: true,  type: 'select',
      options: [
        { value: 'production', label: '운영' }, { value: 'development', label: '개발' },
      ], half: true },
    { key: 'sourceIp',       label: '출발지 IP / 대역',   required: true,  type: 'text',    placeholder: '예: 10.1.2.3, 192.168.0.0/24', half: true },
    { key: 'destinationIp',  label: '목적지 IP / 대역',   required: true,  type: 'text',    placeholder: '예: 10.2.3.4, 0.0.0.0/0',      half: true },
    { key: 'portProtocol',   label: '포트 / 프로토콜',    required: true,  type: 'text',    placeholder: '예: TCP/443, UDP/53, ALL',      half: true },
    { key: 'direction',      label: '방향',               required: true,  type: 'select',
      options: [
        { value: 'inbound',  label: '인바운드 (외부 → 내부 트래픽)' },
        { value: 'outbound', label: '아웃바운드 (내부 → 외부 트래픽)' },
        { value: 'both',     label: '양방향 (상호 통신)' },
      ], half: true },
    { key: 'purpose',        label: '업무 목적',          required: true,  type: 'textarea', rows: 3, placeholder: '해당 방화벽 정책이 필요한 이유를 설명해주세요.' },
    { key: 'duration',       label: '적용 기간',          required: true,  type: 'select',
      options: [{ value: 'permanent', label: '상시' }, { value: 'temporary', label: '임시' }], half: true },
    { key: 'expiryDate',     label: '만료일',             required: false, type: 'date',                                                 half: true },
  ],

  ETC: [
    { key: 'description', label: '요청 상세 내용', required: true, type: 'editor' },
  ],
}

export const TYPE_CARDS = [
  { value: 'IMPROVEMENT',  label: '기능 개선',    icon: 'tune',       desc: '불편한 기능 개선 요청' },
  { value: 'BUG_FIX',      label: '오류 수정',    icon: 'bug_report', desc: '오류 · 비정상 동작 신고' },
  { value: 'DATA_REQUEST', label: '데이터 요청',  icon: 'storage',    desc: '데이터 추출 · 제공' },
  { value: 'PERMISSION',   label: '권한 요청',    icon: 'lock_open',  desc: '시스템 접근 권한 신청' },
  { value: 'CONFIG_CHANGE',label: '설정 변경',    icon: 'settings',   desc: '시스템 · 서버 설정 변경' },
  { value: 'SERVER_INFRA', label: '서버 / 인프라', icon: 'dns',        desc: '서버 작업 · 인프라 요청' },
  { value: 'SECURITY',     label: '보안 조치',    icon: 'security',   desc: '취약점 조치 · 보안 점검' },
  { value: 'FIREWALL',     label: '방화벽 신청',  icon: 'lan',        desc: '방화벽 정책 오픈 · 변경 · 삭제' },
  { value: 'ETC',          label: '기타',         icon: 'more_horiz', desc: '위 항목에 해당하지 않는 요청' },
]
