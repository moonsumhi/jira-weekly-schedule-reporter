---
version: 1
slug: "frontend-optool-src-css-workspace-scss"
primary_target: "frontend/optool/src/css/workspace.scss"
related_targets: ["frontend/optool/src/css/app.scss", "frontend/optool/src/css/spaces.scss", "frontend/optool/src/pages", "frontend/optool/src/components/spaces/SpaceHeader.vue"]
---

# Consistent task pages

Mode: Operate. The user requests visual consistency and a modern finish across the existing application, explicitly preserving core behavior. Refine the established neutral ATOM workspace. Keep all page scripts, loading paths, permissions, model bindings, handlers, navigation targets, state meanings and document workflows.

Use the already self-hosted Pretendard Variable font throughout screen UI, with the existing system stack as fallback. Reuse the current surface, border, text and runtime accent tokens. Shared classes own outer page padding, a 24px/700 title (22px on mobile), descriptions, wrapping header actions, search bars, table framing and tabs. Keep domain-specific table density, diagrams, document layout and the user-configurable dashboard grid.

Replace the saturated project banner with the same page-header vocabulary, retaining project identity, metadata, statistics and shortcuts. Align monthly-report and space colors with existing tokens. Keep state hue families; known light status badges use dark text for readability. Use quiet borders on card hover and flat dialog headers, retaining destructive emphasis. Keep the SR stepper's steps while improving its interior spacing and choice descriptions. Put horizontal overflow inside the issue table; let the recurring-work explanation wrap.

Global presentation rules are screen-only. Keep the standalone weekly print view and report print rules unchanged. No external fonts, generated illustrations, invented data or new identity assets are required.

Verification uses local synthetic API fixtures. Review desktop, intermediate and mobile layouts, title metrics, long names, empty tables, data tables, dialogs, keyboard access, filter changes and navigation. Preserve fixtures outside production code. Evidence is recorded under `.impeccable/review/page-polish-*`; source invariance, TypeScript, lint and production compilation complete the implementation checks.


## Final review

- All 46 edited page scripts and the event, model, condition, loop, navigation and table-data bindings match the pre-task snapshot.
- Rendered 44 routes at 1440px and 390px with synthetic API fixtures, checking heading presence, font loading, horizontal fit and browser exceptions. Fixed the two narrow-layout findings in the issue table and recurring-work description.
- Rechecked nine affected and complex routes at 768px, 390px and 320px. All fit the viewport; the issue table scrolls inside its card. Retained the ability to view full table columns.
- Exercised project search/reset, project creation dialog sizing, SR project dialog sizing, SR type selection and next-step transition, weekly-report title navigation, calendar month navigation and event details, runtime theme colors and project tabs. No browser exceptions occurred.
- Evidence: `page-polish-full-metrics.json`, `page-polish-interaction-results.json`, and the matching desktop/mobile screenshots in `.impeccable/review/`. These checks use fixtures, not live operational records.
- Final checks passed: `vue-tsc --noEmit`, full frontend ESLint, whitespace check (preserving existing CRLF), and `npm run build` including lifecycle validation and the configured Vue/ESLint checker. Production output: `frontend/optool/dist/spa`. The existing bundle-size warning remains. Build log: `.impeccable/review/page-polish-build.log`.


## Inspection report refinement

The report page's scoped shell and toolbar rules loaded after equally specific shared rules, retaining extra horizontal padding and a large header. Remove the local shell padding at every breakpoint, keep the shared heading scale, and make only the detailed report toolbar sticky. Move contextual text below headings. Use the shared palette, card borders and readable metadata sizes for the list, history, outline and local dialogs. The empty state uses a standard document icon instead of a large document illustration. The month picker has enough width for its value and icon.

The page script, functional template bindings, print CSS and document component remain unchanged. Fixture browser checks covered empty/list/plan/result/edit states at 1440, 768, 390 and 320px; no page or dialog overflow. Month and document-kind navigation, revision history, finalized state, error retry and print-only chrome visibility passed with no browser exceptions. Targeted ESLint and whitespace checks passed. Evidence: `.impeccable/review/inspection-report-polish-results.json` and `page-polish-inspection-polish-*` captures.


## Monthly project work groups

Monthly report > 업무 현황 > 프로젝트별 now follows the weekly report's group structure: 완료, 진행 중, 차월 계획. Each group uses the shared `sortWorkItemsByDate` helper; empty groups show 없음. Row metadata, delayed badges, issue navigation and expansion/fullscreen controls are preserved. Monthly snapshot aggregation, personal/all/upcoming tabs and exports remain unchanged. Removed the unused cross-status timeline helper.

Verified group membership/order, overlapping current and next-period work, empty groups, issue detail navigation, all tabs and fullscreen using local fixtures at 1440/768/390/320px, and compared with the weekly screen. TypeScript, targeted ESLint and the three existing ordering tests passed. Evidence: `monthly-project-groups-results.json` and `page-polish-monthly-project-groups-*` in `.impeccable/review/`.
