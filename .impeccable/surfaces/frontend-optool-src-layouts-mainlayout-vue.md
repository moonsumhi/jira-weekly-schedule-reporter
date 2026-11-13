---
version: 1
slug: "frontend-optool-src-layouts-mainlayout-vue"
primary_target: "frontend/optool/src/layouts/MainLayout.vue"
related_targets: ["frontend/optool/src/pages/IndexPage.vue","frontend/optool/src/components/EssentialLink.vue","frontend/optool/src/css/app.scss","frontend/optool/src/pages/auth/AuthPage.vue"]
---

# Backoffice redesign

Mode: Operate. Scope: application shell, home, authentication, and shared controls across existing routes. The user explicitly delegated template selection and requested implementation; proceed on that delegation without another selection interview. Product assumptions remain labeled in PRODUCT.md.

Reference: Untitled UI Figma free kit, https://www.untitledui.com/free-figma-ui-kit. Public dashboard preview inspected separately; do not import commercial assets, example data, or React code. Adapt the component grammar to Vue/Quasar and Korean text.

## Direction contract

THESIS: A clear operations workspace in which a user can locate the current task and its source. Replace the saturated header and inconsistent component treatments with a composed, consistent workspace.

OWN-WORLD: Cool off-white working ground, white navigation and content, ink headings, slate supporting text, blue primary actions with existing configurable theme colors. Korean system sans, a compact fixed type scale, outlined surfaces, restrained 12px corners. Status colors retain their domain meanings.

STORY: Identify the active workspace, review upcoming work, open its source, and keep navigation context while working in detailed tables and dialogs. No invented totals or performance claims.

FIRST VIEWPORT: A 248px left navigation column with product identity and account footer; a 64px white toolbar with contextual page name and utility actions. A title/date row introduces the home task grid. Existing movable and resizable modules remain functional. Tables use consistent headings and quiet row separators. Signature: the active destination and the toolbar name identify the same task, including filtered routes and linked detail screens.

FORM: Grounded sources considered: 1. Untitled UI working dashboards; 2. operational report indexes; 3. institutional staff directories and wayfinding; 4. technical reference publications; 5. timetable typography; 6. archival finding aids; 7. formal correspondence. Assigned index 3 contributes clear group navigation, a restrained compact row rhythm, and persistent location labels within the user-requested Figma dashboard vocabulary. seed:2574803ce7f0f01b. Code-led; no generated comp and no standing buildPath setting.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Verification

Keep permission checks, menu personalization, dashboard preferences, original records, and print output. Inspect desktop and mobile with local synthetic fixtures, including selected navigation, open menus/dialogs, empty states, tables and keyboard focus. No changes to operational data are needed. Keep screen styling out of printed documents.

## Dashboard calendar and movable cards

The initial desktop grid places 내 일감 보기 (2×2) beside 업무 바로가기 (1×2), with 달력 (2×3) on the left and 즐겨찾는 프로젝트 (1×3) below the shortcuts on the right. The consolidated shortcut card retains the saved `weeklyReport` key, position and explicit sizes. All four share the existing drag handle, 3×3 size picker, fixed header and scrollable body. Favorites remain a single vertical list at every width, with existing ordering, backlog links, more/less control and loading/error/empty states. 업무 바로가기 contains 이번 주 주간보고, 이번 달 월간보고 and 이번 달 서버점검 작업 목록. At the smallest saved height (h=1, 140px), the permitted destinations become compact horizontal actions with their 이번 주/이번 달 labels, keeping all three visible without scrolling. The size picker uses native buttons and supports keyboard activation.

Report shortcuts open the detail when exactly one report exists for the current period; zero or multiple reports open the period-filtered list. Monthly lists accept and track year/month route filters. Server inspection opens `/inspection/tasks?month=YYYY-MM`. Displayed periods update on the dashboard clock and destinations recalculate on activation using Korean dates, distinguishing ISO week years from calendar month years. Loading prevents duplicate report requests, while failures retain the dashboard and offer a retry through the same action.

The standalone D-Day card is retired. The calendar header provides D-Day 추가. Clicking a day cell opens the same creation dialog with that calendar date prefilled; the date number also supports Enter and Space. Existing event and overflow-link activation continues to open details rather than creating a D-Day. Clicking or pressing Enter on a calendar event opens a portaled day popover, also used by overflow links. It retains date, D-N/D-Day/D+N label, title and note; personal or admin-managed D-Days offer edit/delete, and the existing edit dialog retains creator-only completion. Shared events remain read-only for other users. Inspection events retain task navigation, admin date editing and reset; marked assigned issues open their existing detail dialog. All personal duty dates and precise shift times remain in the calendar. Existing audience rules and API authorization are unchanged.

On first introduction of the movable shortcuts or retirement of D-Day, use the requested arrangement while preserving custom card sizes and unrelated asset-column presets. Later custom order and size persist through the account preferences API; report actions require PM access and server inspection independently requires `server_check` access. The shortcut card remains available when either permission is present. Narrow screens stack the cards. The calendar retains month navigation, today, Korean-date semantics, retry, and portaled overflow handling. The standalone duty, EoS and server resource cards also remain retired.

Verification: `scripts/test-dashboard-layout.mjs` covers migration, custom layout persistence, permission changes, duplicate/retired IDs and non-mutation of saved sizes. `.impeccable/review/dashboard-layout-results.json` and `dashboard-layout-*.png` record browser interactions and responsive checks. `.impeccable/review/dashboard-shortcuts/results.json` and `final-*.png` record the consolidated actions, responsive and compact layouts, report routing, Korean period rollover, loading/error recovery, permission combinations and preference persistence using local synthetic fixtures. No new system tokens or identity.

## Sidebar typography and icon refinement

The user requested a more current sidebar font and icon treatment. Retain the existing Operate identity, configurable labels and colors, navigation behavior, and all content outside the sidebar. The family exception is scoped to `#workspace-navigation`: locally served Pretendard Variable v1.3.9 with the unchanged `--bo-font` system stack as fallback. The app owns the font face; `public/fonts/pretendard/` contains the WOFF2, SIL OFL 1.1 license, source URL and SHA-256. The design preview does not fetch a font.

Use the implemented 20px/700 brand, 14px/500 top-level menus, 13px/450 child menus and 600 selected weight; menu line height is 1.45 and team/menu supporting text is 12px/1.5. Known legacy menu icons render as equivalent Material Symbols Outlined SVGs at 20px or 18px for children through `src/utils/sidebarIcons.ts`; unknown custom icons and configured colors retain their existing behavior. Global body typography and token roles remain unchanged.

Verification evidence: `.impeccable/review/sidebar-modern-*.png` and `sidebar-modern-results.json` cover actual Korean Pretendard rendering with unchanged page typography, desktop and expanded groups, keyboard focus, mobile and tablet navigation, a viewport equivalent to 200% browser zoom, long labels and account details, font failure fallback, configured themes and menu colors, permission-limited navigation, account access and logout. The recorded browser checks report no errors. Build, TypeScript and ESLint checks also passed in the implementation handoff.


## My assigned work

The home card is titled 내 일감 보기. Combine only the current user's unfinished assigned PM issues and assigned SRs; never substitute reporter/requester ownership. Completed/legacy-completed PM issues and draft, completed, confirming, closed, cancelled or rejected SRs are excluded. SR fetching uses the existing operator/manager permission rules and follows every page of the assigned filter. The dedicated PM my-issues endpoint has no recent-50 cutoff, so older overdue work remains available. When an active assigned SR and its linked PM issue are both present, show the SR once with its current planned deadline (falling back to its desired deadline); PM-only access still shows the assigned issue.

Show actual total, overdue and due-today counts above the list. Sort overdue work first by oldest deadline, then due today, upcoming deadlines, paused SRs and undated work. Make overdue rows distinguishable with a pale red surface, an error icon, and explicit N일 지연 text; show 오늘 마감 separately and retain the absolute due date. Business-date comparisons use the parent's Korean day and update at midnight. Preserve the SR domain rule that on-hold work is not counted as overdue. Row buttons open the original issue dialog or SR detail. The header shortcut opens the assigned view. Container-based stacking supports a narrow resized card as well as mobile.

Loading and source-specific errors are distinct from an empty list. A failed source keeps available work visible, labels the counts as loaded items, and offers retry. An issue update or deletion reloads both permitted sources. The card participates in the movable grid described above, with custom sizes retained during the requested arrangement change. Verification lives in `scripts/test-my-work.mjs`, `tests/test_dashboard_my_work.py`, and `.impeccable/review/my-work-results.json` with `my-work-*.png`. No new system tokens or identity.
