---
name: "ATOM Backoffice"
description: "한국어 운영 업무를 연결하는 차분한 작업 공간"
colors:
  primary: "#2563eb"
  canvas: "#f6f8fb"
  surface: "#ffffff"
  surface-subtle: "#f9fafb"
  text: "#182230"
  secondary: "#344054"
  muted: "#667085"
  border: "#e4e7ec"
  border-strong: "#cdd3dd"
  accent-soft: "#eef4ff"
  accent-ink: "#1d3f86"
typography:
  headline:
    fontSize: "24px"
    fontWeight: 700
    lineHeight: 1.35
    letterSpacing: "-0.6px"
  subtitle:
    fontSize: "18px"
    lineHeight: 1.45
    letterSpacing: "-0.3px"
  title:
    fontSize: "15px"
    fontWeight: 700
    lineHeight: 1.45
  body:
    fontFamily: "'Pretendard Variable', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
  table-body:
    fontSize: "13px"
  label:
    fontSize: "12px"
    fontWeight: 650
rounded:
  menu: "6px"
  control: "8px"
  surface: "12px"
spacing:
  control-gap: "8px"
  compact: "12px"
  content: "16px"
  panel: "20px"
  page: "24px"
  wide: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "7px 14px"
  button-outline:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    rounded: "{rounded.control}"
    padding: "7px 14px"
  button-flat:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.control}"
    padding: "4px 8px"
  input-outlined:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
  navigation-active:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent-ink}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  chip-dense:
    rounded: "{rounded.surface}"
    padding: "0 0.4em"
  workspace-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.surface}"
    padding: "{spacing.panel}"
  data-table:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    typography: "{typography.table-body}"
    rounded: "{rounded.surface}"
  tab-active:
    textColor: "{colors.accent-ink}"
---

# Design System: ATOM Backoffice

## Overview

**Creative North Star: "운영 업무의 안내 데스크"**

현재 위치와 업무 원본을 쉽게 찾는 한국어 작업 공간이다. 옅은 회색 바탕 위에 흰 탐색 영역과 작업 면을 두고, 짙은 제목과 작은 보조 설명으로 정보의 순서를 만든다. 표와 목록의 밀도를 유지하며 선택 상태와 주요 조작에 색을 사용한다.

[Untitled UI 무료 Figma 키트](https://www.untitledui.com/free-figma-ui-kit)의 대시보드 구성 언어를 Vue·Quasar에 맞게 적용했다. 상용 키트 자산이나 React 구현을 가져오지 않았다. 이 문서는 완료된 공통 구현을 기록하며, 실제 앱 이름·탭 제목·테마·메뉴 표현은 관리자 설정을 따른다.

**Key Characteristics:**

- 흰 작업 면과 얇은 경계선으로 구획한다.
- 선택 메뉴와 상단 위치 이름을 함께 유지한다.
- 주요 조작, 선택 상태, 업무 상태의 색 역할을 구분한다.
- 넓은 화면의 업무 밀도와 작은 화면의 읽기 순서를 함께 보존한다.

근거는 공통 스타일, 레이아웃, 홈, 인증, SR, 자산, 점검 구현과 대표 화면이다. 로컬 합성 데이터로 확인한 브라우저 결과는 전체 화면의 실제 데이터 종단 간 검증을 뜻하지 않는다.

## Colors

차가운 중립색이 작업 바탕을 만들고, 기본 파란색이 주요 조작을 식별한다. frontmatter는 기본값이며 실제 화면의 CSS 변수가 우선한다.

### Primary

- **업무 파랑** (`primary`): 주요 버튼과 제품 아이콘. 런타임 `--q-primary`로 연결한다.
- **선택 바탕** (`accent-soft`): 현재 메뉴와 텍스트 선택의 옅은 면.
- **선택 잉크** (`accent-ink`): 현재 메뉴, 활성 탭, 키보드 포커스의 짙은 색.

`accent-soft`와 `accent-ink`는 호환성 대체값이다. `color-mix` 지원 환경에서는 각각 `color-mix(in srgb, var(--q-primary) 8%, white)`, `color-mix(in srgb, var(--q-primary) 46%, #182230)`를 사용한다. 파랑·빨강·노랑·초록·검정·회색의 기존 테마 선택을 유지한다.

### Neutral

- **작업 바탕** (`canvas`), **흰 작업 면** (`surface`), **보조 면** (`surface-subtle`): 페이지, 카드·입력, 표 머리글과 비활성 입력에 적용한다.
- **본문 잉크** (`text`), **보조 제목** (`secondary`), **설명 회색** (`muted`): 제목·본문, 머리글, 설명·빈 상태·계정 이메일의 위계를 나눈다.
- **면 경계** (`border`), **입력 경계** (`border-strong`): 구획과 입력 가능 영역을 구분한다.

### Named Rules

**The Theme Continuity Rule.** 주요 조작과 현재 위치는 런타임 테마를 따른다. 관리자가 정한 메뉴 이름·아이콘·색상과 업무 상태의 의미를 보존한다.

상태와 위험도의 색상 계열은 유지한다. 업무 페이지와 대화상자의 기존 grey-5, blue-4/5, orange-6, green-6, red-6 상태 배지는 같은 색상 계열의 옅은 바탕과 짙은 글자로 통일한다. 선택 필터, 사용자 지정 라벨·팀 색상과 경고 동작은 유지한다.

## Typography

**Body Font:** 화면에서는 로컬 Pretendard Variable v1.3.9를 먼저 사용하고 기존 한국어 시스템 산세리프 스택을 대체 서체로 둔다. 제목·본문·입력·버튼·대화상자가 같은 글꼴을 공유한다. 글꼴 변경은 화면 전용이며 문서 인쇄용 글꼴은 유지한다.

**Sidebar Font:** `#workspace-navigation` 안에서는 로컬 제공하는 Pretendard Variable v1.3.9를 우선하고 `--bo-font`를 대체 서체로 사용한다. 앱의 `@font-face`는 `/fonts/pretendard/PretendardVariable.woff2`와 `font-display: swap`을 사용하며, 원본 출처·SHA-256과 SIL OFL 1.1 라이선스는 같은 폰트 디렉터리에 보관한다. 동일한 로컬 글꼴을 이제 업무 화면에서도 사용한다. 사이드바의 기존 크기와 굵기는 유지한다. 브랜드는 20px/700, 행간 1.3; 상위 메뉴는 14px/500, 하위 메뉴는 13px/450, 선택 메뉴는 600을 쓴다. 메뉴 행간은 1.45, 팀 설명과 메뉴 보조 문구는 12px/1.5다.

**Character:** 짧은 제목, 보통 굵기의 본문, 작은 보조 설명으로 표와 목록을 빠르게 읽게 한다. 버튼은 대문자 변환 없이 원문을 표시한다.

### Hierarchy

- **Headline**: 모든 업무 페이지의 제목은 `bo-page-title`로 통일한다(24px/700, 행간 1.4). 대시보드는 별도 인사말·제목 없이 카드로 시작한다.
- **Subtitle**: 화면 안의 보조 구역 제목.
- **Title**: 홈 모듈 제목.
- **Body**: 설명, 입력, 기본 화면 텍스트.
- **Table body**: 조밀한 업무 행. 숫자는 표에서 `tabular-nums`를 사용한다.
- **Label**: 공통 표 머리글. SR 머리글에는 기존 화면별 크기(13px)가 적용된다.

작은 화면에서 페이지 제목은 22px로 줄어든다. 상태 숫자·문서 본문 제목은 페이지 제목과 구분하고 자체 정보 위계를 유지한다.

## Layout

기본 셸은 왼쪽 탐색(248px), 상단 도구 모음(64px), 남은 폭을 쓰는 작업 영역으로 구성된다. 계정 영역은 탐색 하단에 고정하고 메뉴 영역은 독립적으로 스크롤한다. 메뉴가 접히는 경계는 Quasar drawer 설정(1024px)을 따른다.

업무 페이지의 공통 여백은 28px 32px 40px이며, 화면 폭 1023px 이하에서 24px, 599px 이하에서 20px 16px 32px로 바뀐다. 바깥 최대 폭은 1664px로, 넓은 화면의 콘텐츠는 1600px를 쓴다. 제목 행 아래에는 24px(모바일 20px)를 두고 설명은 제목 아래 6px 간격으로 배치한다. 작은 화면의 도구 모음은 56px이고 팀 이름과 버전을 숨긴다.

홈은 최대 폭(1600px), 열 사이 간격(16px), 기본 3열을 사용한다. 1100px 이하에서 2열, 600px 이하에서 1열이다. 모듈은 사용자가 옮기고 크기를 바꿀 수 있으며, 140px 행 단위와 16px 간격을 유지한다. 제목은 모듈 내부 스크롤 밖에 남는다. 이 홈 배치를 모든 업무 화면의 고정 격자로 확대하지 않는다.

작은 화면에서 SR 검색·상태 필터·빠른 필터는 읽는 순서대로 줄을 나누고 자산 검색은 한 줄의 폭을 확보한다. 넓은 표는 표 영역 안에서 가로 스크롤한다. 인증은 최대 폭 460px의 중앙 카드이며 작은 화면에서는 위쪽 정렬로 바뀐다.

## Elevation & Depth

카드와 표는 얇은 경계선으로 구분하고 공통 직사각형 버튼의 기본 그림자를 제거한다. 메뉴와 대화상자는 떠 있는 레이어로 표현한다. 자산의 고정 열 등 기존 화면별 구조 표현은 별도 규칙으로 남는다.

### Shadow Vocabulary

- **떠 있는 레이어** (`0 12px 32px rgb(16 24 40 / 14%)`): 메뉴와 대화상자.
- **대화상자 배경막** (`rgb(16 24 40 / 38%)`): 열린 대화상자 뒤의 맥락을 낮춘다.

**The Quiet Surface Rule.** 기본 작업 면은 경계선으로 구획하고, 공통 그림자는 떠 있는 조작 영역에 사용한다.

## Shapes

작업 면은 부드러운 사각형(`rounded.surface`), 입력과 버튼·메뉴는 더 작은 모서리(`rounded.control`)를 사용한다. 메뉴 항목과 툴팁은 `rounded.menu`를 쓴다. 원형 아이콘 버튼, 아바타, 촘촘한 칩은 해당 Quasar 형태를 유지한다. 문서 표와 기존 상세 양식의 모서리를 공통 카드 규칙으로 강제하지 않는다.

## Components

### Buttons

기본·외곽선·평면 버튼을 기존 작업의 중요도에 맞게 사용한다. 일반 버튼의 최소 높이는 38px, 촘촘한 버튼은 30px이다. 굵기는 600이며 일반 여백과 촘촘한 여백은 frontmatter를 따른다. 호버와 눌림은 Quasar 상태 레이어, 키보드 접근은 포커스 표시를 사용한다. 공통 버튼 상태 전환은 160ms ease-out이며 모션 감소 설정에서는 이 전환을 제거한다.

### Inputs / Fields

흰 면, 강한 경계선, 입력 모서리를 사용한다. 라벨과 placeholder는 설명 회색, 입력값은 본문 잉크다. 오류는 Quasar `negative`, 비활성은 보조 면으로 표현한다. 키보드 포커스는 입력 컨트롤 전체를 둘러싸며 일반 포커스는 2px 외곽선과 3px 간격, 입력은 2px 간격을 사용한다. 실제 높이는 dense 여부와 화면을 따른다.

### Navigation

상위 항목은 최소 높이 44px, 하위 항목은 40px이며 아이콘·텍스트 정렬을 유지한다. 현재 항목은 선택 바탕과 선택 잉크, 굵기 600으로 표시하고 `aria-current="page"`를 제공한다. 활성 그룹은 펼친다. 검색 쿼리와 연결된 상세 화면에서도 관련 메뉴를 찾는다. 작은 화면에서는 메뉴를 선택하면 drawer를 닫는다. 본문 건너뛰기는 포커스 때 나타난다.

기존 메뉴 아이콘 중 대응 항목이 있는 이름은 `sidebarIcons.ts`에서 같은 의미의 Material Symbols Outlined SVG로 표시한다. 상위 아이콘은 20px, 하위 아이콘은 18px이다. 저장된 아이콘 설정과 알 수 없는 사용자 아이콘, 설정된 글자·아이콘 색상은 보존하며 현재 항목에는 기존 선택 색상을 적용한다. 사이드카 탐색 예시는 SVG 경로를 포함하고, 앱에서 정의한 Pretendard를 사용할 수 없으면 시스템 스택으로 표시한다. 예시 자체는 폰트를 내려받지 않는다.

### Chips

필터 칩은 선택·제외·미선택을 색과 외곽선, 아이콘으로 구분한다. SR 상태 필터는 미선택 → 포함 → 제외 → 해제 순서다. 작은 화면의 SR 칩은 최소 높이(28px)를 확보한다. 단순 상태 배지를 클릭 가능한 필터처럼 취급하지 않는다.

### Cards / Containers

흰 면과 경계선으로 묶고 홈 패널은 20px, 작은 화면에서는 16px 안쪽 여백을 쓴다. 빈 상태는 실제 데이터 부재를 설명하는 문장으로 남긴다. 홈 모듈의 이동·크기 설정과 내부 스크롤을 보존한다.

### Tables / Tabs

공통 표 머리글은 44px, 본문 행은 48px이며 dense 표는 각각 38px와 40px이다. 개별 자산 표 등의 명시적 행 높이는 유지한다. 조용한 행 경계와 호버 면(`rgb(24 34 48 / 3%)`)을 사용한다. 탭은 최소 높이(42px), 활성 잉크, 아래쪽 2px 표시선으로 현재 영역을 나타낸다.

## Do's and Don'ts

### Do:

- **Do** 공통 화면에는 `--bo-*`와 `--q-primary`를 사용하고 테마 변경을 반영한다.
- **Do** 선택 메뉴, 상단 위치 이름, 연결된 업무 원본의 관계를 유지한다.
- **Do** 작은 화면에서는 필터의 줄을 나누고 넓은 표는 자체 영역에서 스크롤한다.
- **Do** 키보드 포커스, 오류, 비활성, 빈 상태를 구별한다.
- **Do** 공통 화면 스타일을 `@media screen`에 두어 기존 인쇄 문서의 형식을 보존한다.

### Don't:

- **Don't** 관리자 설정의 앱 이름·탭 제목·메뉴 표현을 고정 브랜드 값으로 덮어쓰지 않는다.
- **Don't** 업무 상태 색을 장식용 테마 색으로 바꾸거나 샘플 수치를 실제 실적으로 표시하지 않는다.
- **Don't** 기존 자산·점검의 개별 색상과 문서 양식 값을 새 공통 토큰으로 승격하지 않는다.
- **Don't** 사이드카의 합성 명도 단계를 앱에서 사용하는 색상 토큰으로 취급하지 않는다.



## Shared task-page presentation

`src/css/workspace.scss` owns the screen-only `bo-page`, `bo-page-heading`, `bo-page-title`, `bo-page-description`, `bo-page-actions` and `bo-filterbar` patterns. Page templates opt into these classes without changing their data loading, permissions, models, events or navigation. Add these classes to future task pages instead of introducing another page-specific title scale or outer padding.

Project detail uses a neutral heading with its existing avatar, metadata and shortcuts. Monthly reports and spaces inherit the shared surface, border, text and accent tokens. Card hover uses the accent border; tables inside an existing panel avoid a second border. Report, inspection and task-specific document content retain their structure. The calendar toolbar, empty table state, field corners, tabs and narrow dialogs follow the same control vocabulary. The SR wizard keeps its steps and adds consistent interior padding and readable type-choice descriptions.

The desktop/mobile review uses synthetic local API fixtures. `page-polish-before-*` and `page-polish-after-*` record the initial representative comparison; `page-polish-full-*` records broader route coverage. These are UI checks, not live operational-data verification. Final interaction and build evidence are recorded with the matching review files.
