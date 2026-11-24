# App shell after the "Cloud-Based ETL Tool Dashboard" model

> Status: **proposed on 2026-11-23; plan and §4 confirmed by the owner on 2026-11-24; implemented on 2026-11-24, all
> 4 lots**. Not yet done: the §8 checklist ticked by hand with a real etlhub (the local DHIS2 was down, every check ran
> with etlhub mocked in the browser). Q1–Q5 answered by the owner on 2026-11-24 (§9). Mockups: the owner's private artifact "etlui Layout Proposal" (version 2, 2026-11-23); this file
> is the reference, the mockups only illustrate it. Builds on [../page-layout/page-layout.md](../page-layout/page-layout.md)
> and [../shadcn-migration/shadcn-migration.md](../shadcn-migration/shadcn-migration.md).

## 1. Goal

Give every etlui page the same frame as the reference: a fixed side menu, a top bar, a page header with its actions,
then cards and tables. **No feature is lost** (§8 is the checklist) and **etlhub does not change**: same routes, same
contracts, same data. Only the layout and the styling of the frame change; the content of the steps and of the
dialogs stays as it is.

## 2. The reference

Published Figma Make site `https://blank-eagle-39958912.figma.site/` ("Cloud-Based ETL Tool Dashboard", community
file 1537329550451808723), opened in headless Chromium on 2026-11-23. Real screens: **Dashboard**, **Monitors**,
**Job Scheduler**; EasyConnect, FlowBoard and TaskPlan are empty placeholders.

| Pattern | What it is |
|---|---|
| Side menu | Fixed on the left, brand at the top, icon + label per entry, active entry filled with the primary colour, a chevron to collapse it |
| Top bar | Page title, breadcrumb (`Home / Page`), then on the right: theme, settings, avatar and user name, a `…` menu |
| Page header | Title and one-line subtitle on the left, actions on the right (primary + outline) |
| Fact cards | 4 per row: label, big value, help line, tinted icon square |
| Lists | "Recent Jobs", "System Alerts": rows with a status icon, title, detail, status badge, time; "View All" in the card header |
| Tables | Tinted header row, icon + title + badge in the first cell, row actions at the end, search field, grid / list switch |

Not taken (§4 A9–A11): its colours (dark navy written as literals, dark only), its invented figures ("2.4TB",
"98.5%", trends), its phone layout (the menu stays open and cuts the content at 390 px).

## 3. Constraints

| # | Constraint | Source |
|---|---|---|
| C1 | Every feature of §8 still works, reachable from where §8 says | owner, 2026-11-23 |
| C2 | No etlhub change, no contract change (`ETLResponse`, `JobStatus`, WebSocket messages, routes) | `etlui/CLAUDE.md` Rules |
| C3 | Colours from tokens only (`src/styles/base.css`), light, dark and System themes | `etlui/CLAUDE.md` Method |
| C4 | Layering: views → composables / stores → services; no new service import in a view or component | `etlui/CLAUDE.md` Rules |
| C5 | shadcn-vue components added with `npx shadcn-vue@2.8.2 add <name>` (Node 22), the `base.css` diff reviewed after each | `etlui/CLAUDE.md` Commands |
| C6 | Specs keep their `data-test` selectors; a moved element keeps its `data-test`; a spec changes in the same commit as the behaviour | `etlui/CLAUDE.md` Method |
| C7 | yarn only, ponytail (`/ponytail`, level `full`), `yarn vitest run` and `yarn build` before and after each lot | root `CLAUDE.md`, `etlui/CLAUDE.md` |
| C8 | A shadcn-vue component (registry `https://www.shadcn-vue.com/r/index.json`, its blocks as models) before any new component of ours | owner, 2026-11-24 |

### shadcn first (C8)

| Need | shadcn-vue | Our file |
|---|---|---|
| Side menu | `sidebar` (`Sidebar*`, `SidebarRail`), laid out like block `sidebar-07`; the block itself is not added (its `TeamSwitcher`, `NavProjects`, `NavUser` are not needed) | `components/AppSidebar.vue`, composition only |
| Top bar | `SidebarTrigger` + `Separator` + `Breadcrumb`, like block `dashboard-01`'s `SiteHeader` | none: in `App.vue` |
| Page header | `item` (`Item`, `ItemContent`, `ItemTitle` holding an `<h1>`, `ItemDescription`, `ItemActions`) | none (no `PageHeader.vue`) |
| Fact cards | `Card` + `CardHeader`, `CardDescription`, `CardTitle`, `CardAction` (icon), `CardFooter`, like `dashboard-01`'s `SectionCards` | none (no `StatCard`) |
| Recent Jobs | `Card` + `CardAction` ("View all") around the existing `Trace` lines | none |
| Tracking table | `Table` + `Badge`; `input-group` only if Q1 says yes | none |
| User name | plain text (`NavUser`'s `DropdownMenu` would hide Log out, against A2) | none |
| Two columns | no shadcn equivalent: a Tailwind grid in the page | `SideLayout.vue` removed |

## 4. Decisions to confirm

| # | Proposal | Why | Owner |
|---|---|---|---|
| A1 | Side menu = shadcn-vue `Sidebar`, `collapsible="icon"`; on a phone it is the Sheet it renders itself | It has collapse, keyboard shortcut, phone Sheet and remembered state; [../page-layout/page-layout.md](../page-layout/page-layout.md) P1 refused it for the Journal tree only (one list), not for the app menu | confirmed 2026-11-24 |
| A2 | Menu entries: Start a pass (`/`), Forecast, Journal, Tracking, Logs, Parameters; at the bottom API Docs, the version, **Log out** | Same routes as `App.vue` `navItems`; Log out stays at the bottom (owner, 2026-11-23) | confirmed 2026-11-24 |
| A3 | Top bar: menu trigger, page title, breadcrumb, then `ModeBadge`, `ThemeToggle` (its 3 choices), a gear to `/parameters`, the DHIS2 user name | The header's content today, in the reference's places | confirmed 2026-11-24 |
| A4 | Forecast's position breadcrumb (and its link, `goToPosition`) goes into the top bar | The reference puts the breadcrumb there; one breadcrumb per page | confirmed 2026-11-24 |
| A5 | A `PageHeader` (title, subtitle, actions) on every page; Forecast's actions: Pause the cycle, Abandon the cycle | They are page actions; today they sit under Recent Activity | confirmed 2026-11-24 |
| A6 | Forecast: 4 fact cards from etlhub's state only: Mode (with `ModeToggle`, frozen while the pass is active), Where you are, Job running (the lock), GEE variables of the pass | Replaces the mode card, the lock banner and the GEE note; no invented figure | confirmed 2026-11-24 |
| A7 | Recent Activity moves to a right column of Forecast, styled as "Recent Jobs", with "View all" → `/tracking` | The left side is the menu now | confirmed 2026-11-24 |
| A8 | Dialogs: same content and behaviour; only their header (title left, actions right) and footer (decisions bottom right) follow the page header | The reference has no dialog | confirmed 2026-11-24 |
| A9 | Colours stay etlui's tokens; at most a tint of `--sidebar` in dark mode | C3 | confirmed 2026-11-24 |
| A10 | Tracking: the reference's table style; its search field only if wanted (a new feature, not in today's etlui) | C1 is about keeping, not adding | closed 2026-11-24 (Q1): no search added |
| A11 | Phone (< `md`): menu as a Sheet behind the trigger, fact cards 2 per row then 1 | The reference's phone layout is broken | confirmed 2026-11-24 |

## 5. Target structure

```
App.vue
├─ toasts (popover="manual", unchanged)        ├─ LoadingScreen (unchanged)
└─ route meta.public (Login)? → <router-view/> alone, no shell
   else SidebarProvider
        ├─ AppSidebar          components/AppSidebar.vue   (menu, footer with API Docs, Log out, version)
        └─ SidebarInset        (renders <main>)
             ├─ <header>       in App.vue: trigger, title (meta.label), #app-crumbs (lot 2), right-hand items
             └─ <router-view/>
                  page = Item (shadcn, the page header) + content
                  two columns where needed: a Tailwind grid in the page (SideLayout removed)
```

- The page title comes from the route: a `meta.label` next to the existing `meta.title` (the tab title).
- A page puts its breadcrumb into the top bar with `<Teleport to="#app-crumbs">` (Forecast only today). The target
  exists before the page renders because the shell renders first.
- `SideLayout` was a panel **fixed** on the left of the screen, under the 77 px header. Lot 1 removed it: Forecast
  and Journal write their grid (`lg:grid-cols-[clamp(10rem,16vw,20rem)_minmax(0,1fr)]`), Tracking needs none, so
  nothing is fixed any more except the menu and the top bar.
- `main.ts` mounts the app after `router.isReady()`: before it, the route has no meta yet and the shell would flash
  on Login.
- `Drawer.vue` is no longer used once `Sidebar` renders its own phone Sheet: delete it in lot 1 with its usages.

## 6. Lots

Each lot ships alone, with its specs, after `yarn vitest run` and `yarn build`, checked in light and dark at 1280,
1440 and 390 px wide. One commit per lot (or more), never a lot left half done on `main`.

### Lot 1 — the shell (done 2026-11-24)

What was done, where it differs from the steps below: no `AppTopBar.vue` (the bar is in `App.vue`); `SideLayout`
removed instead of reworked; `#app-crumbs` moves to lot 2 (its only user); `AppSidebar` is tested through
`src/__tests__/App.spec.ts` (it needs `SidebarProvider`), no separate spec; `add sidebar` added no token to
`base.css` and raised `@lucide/vue`, `@vueuse/core`, `cn` in `package.json`: those raises were reverted (the
lockfile's versions work), the `--sidebar-*` tokens written by hand as the card's colours. Checked: 177 tests,
`yarn build`, headless Chromium at 1440 / 1280 light and dark, folded menu kept after a reload, 390 px Sheet and
Log out, etlhub mocked in the browser (the local DHIS2 was down, so no real session).


1. `nvm use`, then `npx shadcn-vue@2.8.2 add sidebar`. It brings its dependencies (expected: `separator`, `sheet`,
   `tooltip`, `skeleton`, `input`, `button`; check what it really adds). Review the `base.css` diff: the CLI adds
   `--sidebar-*` tokens; give them values from the existing tokens, in both themes.
2. `components/AppSidebar.vue`: the entries of A2 with `@lucide/vue` icons, active entry from the route
   (`router-link-active`), footer as A2. Log out: `useAuthStore().logout()` (C4), `data-test="logout"` kept.
3. `components/AppTopBar.vue`: `SidebarTrigger`, `route.meta.label`, `<div id="app-crumbs">`, `ModeBadge`,
   `ThemeToggle`, a gear `router-link` to `/parameters`, the user's `displayName` (or `username`).
4. `App.vue`: the structure of §5; remove the old header, the hamburger and `Drawer`; Login (`meta.public`)
   renders without the shell.
5. `SideLayout.vue` → a grid (`side` slot, prop `side: 'start' | 'end'`, default `start`), no `fixed`, no 77 px.
   Forecast, Journal and Tracking keep using it until lots 2 and 3.
6. Specs: `src/__tests__/App.spec.ts` (Log out now in the sidebar footer; no shell on Login),
   new `components/__tests__/AppSidebar.spec.ts` (entries, active one, Log out), `SideLayout.spec.ts` rewritten
   for the grid. `ModeBadge.spec.ts` and `ThemeToggle.spec.ts` unchanged.
7. Docs: `etlui/CLAUDE.md` (module map: `components/`, `App.vue` navigation gotcha, Drawer removed) and the status
   of this file.

Done when: every route is reachable from the menu at 1440 px and from the trigger at 390 px; the menu collapses to
icons and stays collapsed after a reload; Log out, API Docs, the mode badge and the theme's 3 choices are there.

### Lot 2 — Forecast (done 2026-11-24)

What was done, where it differs from the steps below: the page header is a shadcn `Item` (title an `<h2>`: the top
bar holds the page's `<h1>`); `ModeToggle` itself became the Mode fact card (a `Card`, Home included) rather than a
toggle inside a card; the other three are plain `Card`s, no `StatCard`; the step cards show etlhub's `done` /
`accessible` (Done / In progress / Not open yet): an item count would read "3 of 71" in step ②; the fact cards keep
their own height (`items-start`), the Mode card being taller (its hints); `RecentActivity` is a `Card` (no longer a
foldable `<details>`); the dialogs (step 7) needed no change: `PreviewDialog`, the Steps dialog and
`ForecastReportModal` already had their title left, actions right and decisions bottom right. The two-column grid
needs `grid-cols-[minmax(0,1fr)]` on a narrow page, or step ②'s carousel widens it past the screen. Checked: 178
tests, `yarn build`, headless Chromium with etlhub mocked (active pass, a lock, step ② open): 1440 light and dark,
1280, 390 (no horizontal scroll), the breadcrumb's link opening the Steps dialog, Home's Mode card. The §8 Forecast
rows were not ticked by hand with a real etlhub.


1. `npx shadcn-vue@2.8.2 add item`: the page header (C8), no `PageHeader.vue`; `<div id="app-crumbs">` in App's top bar.
2. `Dashboard.vue`: the "ETL Pipeline" heading and the cycle line become the PageHeader (title `Cycle <cycle>`,
   subtitle: pass, state, started by, Journal link, the paused and "not started" texts); Pause / Abandon move to
   its `actions`, same disabled rule (`busy || state.lock != null`), same `ConfirmDialog`s.
3. The breadcrumb (`data-test="position"`, `position-link`) moves into `#app-crumbs` with `Teleport`;
   `goToPosition` unchanged.
4. Fact cards (A6), in one row above the accordion: Mode (`ModeToggle` inside, `frozen`, `data-test="mode-frozen"`),
   Where you are (from `position()` / `positionItem()`), Job running (today's lock banner text, the other mode's job
   included, `role="status"` kept), GEE variables (`data-test="pass-gee"` kept). A small `StatCard` only if the four
   share enough markup; otherwise plain `Card`s.
5. `SideLayout side="end"`: `RecentActivity` (`data-test="activity-aside"` kept) with "View all" → `/tracking`.
6. Accordion: step headers styled as cards (number, title, progress text); content unchanged (cards, Review and
   Approve, Details, `ForecastRuns`, system update cards).
7. Dialogs (A8): `PreviewDialog` header and footer, the Steps dialog header (`LevelColumn`), `ForecastReportModal`
   header: same buttons, aligned. No behaviour change: their specs must pass untouched.
8. Specs: `Dashboard.spec.ts` (positions of the moved elements; selectors unchanged), `RecentActivity.spec.ts`.

Done when: every Forecast row of §8 is ticked by hand once in test mode.

### Lot 3 — Journal and Tracking (done 2026-11-24)

What was done, where it differs from the steps below: Journal: page header (`Item`) as planned, plus Refresh in its
actions; the step filter moved next to the table's pager (it filters the table); its grid is a container query
(`@3xl`) like Forecast's; the tree card unchanged. Tracking: its existing "Filter by endpoint" field (sent to etlhub)
stays in the page header next to Refresh; the table already had the tinted header, status badges and Detail at the
end: added the Job ID column and the first cell "method + endpoint + short request id" (the Request ID column
merged into it), endpoints on one line (the table scrolls in its box on a phone). Q1 unanswered: no client-side search.
Every page header drops `Item`'s padding (`p-0`): the page's spacing is enough. Checked: 180 tests, `yarn build`,
headless Chromium with etlhub mocked (a paused pass, 4 events, a lock, 5 requests): 1440 light and dark, 390 (no
horizontal scroll). Seen, not changed: in the Journal tree, a pass line truncates its "test" badge ("te…") when the
column is narrow.


1. Journal: `SideLayout side="start"` inside the page for the tree (it no longer sits under the screen's edge);
   PageHeader: title the selected pass, subtitle its details (`passDetails`), actions Export CSV, and Resume /
   Abandon for a paused pass; the "Job lock" zone becomes a card under the table (same `ConfirmDialog`).
2. Tracking: PageHeader (Refresh in its actions); table in the reference's style: tinted header, method + URL,
   status badge (`utils/status.ts`), duration, job id, Detail at the end of the row (`RequestDialog` unchanged);
   paging and order (`useTablePaging`) unchanged. Search field only if Q1 says so.
3. Specs: `JournalView.spec.ts`, `TrackerView.spec.ts`.

### After the lots (owner, 2026-11-24)

- Page width: every page's content spans 95% of the space beside the menu from `md` (`App.vue`: `md:w-[95%]`, centred),
  instead of `max-w-7xl` (1280 px, 77% of it on a 1920 px screen); Parameters' own `max-w-4xl` removed. The same 95%
  applies with the menu folded (the request named the open menu; ask if the folded one should differ). Measured in
  headless Chromium: 95% at 1280, 1440 and 1920 px, no horizontal scroll at 390.
- A step card's title takes the free space (`flex-1`): without a progress text it was centred in its header.

### Lot 4 — Home, Logs, Parameters, finish (done 2026-11-24)

What was done, where it differs from the steps below: Home's Start is in the page header as a plain click (`@click`,
no form: the page has no text field to submit with Enter); its cards: Mode (`ModeToggle`, a card itself since lot 2)
and "The pass" stacked on the left, "Parameters of this pass" on the right; that list wraps a long value only where
needed (`wrap-anywhere`, it cut words with `break-all`) with an `auto` label column. Logs and Parameters: an `Item`
page header each. Removed from `base.css`: `.heading-primary` (no user left). The loading screen between pages went
from 1 s to 500 ms (`ROUTE_LOADING_MS`, the owner's value; its spec reads the constant). Checked: 180 tests,
`yarn build`, headless Chromium with etlhub mocked: Login, Home (and its opening dialog), Forecast, Journal,
Tracking, Logs, Parameters in light 1440, dark 1440 and light 390: no console error, no horizontal scroll.


1. Home: PageHeader ("Start a pass", Start in its actions), two cards: the pass (mode, cycle, new or resume, GEE
   variables) and "Parameters of the pass"; the opening dialog unchanged. The route guard (`beforeEnter`) unchanged.
2. Logs: PageHeader over the live stream. Parameters: PageHeader over its vertical tabs (already the reference's
   pattern).
3. A last pass on all pages in light, dark and phone width; `etlui/CLAUDE.md` and this file's status updated.

## 7. Dialogs: what does not change

Content, buttons, their order and labels, `data-test`s, opening order (`components/ui/dialog/openOrder.ts`), toasts
above dialogs, `DialogContent` staying open when a toast is clicked, the posting overlay of Review and Approve. The
list: Review and Approve, Details (Imported data in DHIS2), Forecast Report, file preview (JSON / CSV), Impact,
the 4 confirmations (delete a file, pause, abandon the cycle, abandon the run), the run's Steps, Request and logs,
Home's opening dialog, the Journal's confirmations.

## 8. Feature checklist (acceptance)

Tick each one in test mode at the end of the lot that moves it.

**Shell**
- [ ] Navigation to Start a pass, Forecast, Journal, Tracking, Logs, Parameters; API Docs (new tab); version
- [ ] Log out at the bottom of the menu (`auth.logout()`, back to `/login` even if the request fails)
- [ ] Mode badge (TEST MODE · DRYRUN / PRODUCTION · DHIS2 writes), updated right after a mode change
- [ ] Theme: System, Light, Dark, remembered
- [ ] Job toasts (bottom right, above dialogs), 500 ms loading screen between pages (`ROUTE_LOADING_MS`; 1 s until 2026-11-24), "Back to Home…" screen
- [ ] `/` sends to `/forecast` while a pass is active; `/admin/config` opens Parameters › Configuration

**Forecast**
- [ ] Cycle, pass id, state, started by, Journal link; paused note; "not started" note
- [ ] Position breadcrumb; its last item opens the step / the Steps dialog at the item and blinks when no job runs
- [ ] Mode toggle, disabled with its reason while the pass is active; DRYRUN shown
- [ ] Running job (and "a job of the other mode")
- [ ] GEE variables of the pass
- [ ] Pause the cycle, Abandon the cycle (confirmations, disabled while a job runs)
- [ ] Recent Activity: entries with status, message, "Request and logs"; emptied when the mode changes
- [ ] Accordion of the 3 steps, open by default, a folded step keeps its state
- [ ] Step ①: Import GEE, Pivot COM, Pivot CSB cards (status, last update, disabled when not launchable or a job runs); Review and Approve card (approval status, then Build Analytics'); imports approval line; Details
- [ ] Step ②: To do now; disease tabs; "n of 3 levels published"; carousel and its arrows; run cards: status, progress, Open, "Available once the open run is done", Read and approve, View report; open run highlighted
- [ ] Steps dialog: 4 columns and their marks, Abandon this run, Launch / Relaunch / Skip, Read and approve, Run / Relaunch the data check
- [ ] Input files: drop or choose, Upload, Replace, Preview (local, server, default), Delete, Use default, server file size and date, disabled outside the open run
- [ ] Step ③: Build Analytics, Update Key (refused in test mode)
- [ ] Dialogs of §7, each opened once

**Home, Journal, Tracking, Logs, Parameters**
- [ ] Home: opening dialog (mode, then month), month picker, New pass / Resume paused pass, GEE checkboxes (Start disabled with none), parameters of the pass, confirmation after a complete or paused pass
- [ ] Journal: years / months / passes tree with state icons, pass details, journal table (order, rows per page, step filter, test events marked), `carried_over` rows, row → Request and logs, Export CSV, Resume / Abandon, Job lock and its release (with confirmation)
- [ ] Tracking: last 500 requests, rows per page, order, Detail with refusal reason and job logs (live while running)
- [ ] Logs: live stream
- [ ] Parameters: Profile, DHIS2, Configuration (Save, Reload from .env, Pivot token status), GEE variables; `?section=`

## 9. Open questions

| # | Question |
|---|---|
| Q1 | Tracking: add the reference's search field (filters the 500 loaded requests by URL, job id or status)? Tracking already has a "Filter by endpoint" field sent to etlhub on Refresh (seen 2026-11-24): the question is a client-side search on top of it. **Answer (owner, 2026-11-24): keep the endpoint filter as it is, no client-side search** |
| Q2 | Menu collapsed or open by default on a 1280 px screen (step ②'s carousel needs the width). **Answer (owner, 2026-11-24): open** (shadcn's default), then the user's choice kept |
| Q3 | Menu label of `/`: "Start a pass" (what it does) or "Home" (today). **Answer (owner, 2026-11-24): "Start a pass"** |
| Q4 | Keep the "ETL Hub v1.0" badge (bottom of the menu) or drop it. **Answer (owner, 2026-11-24): kept**, as plain text, hidden when folded |
| Q5 | Login without the shell loses the theme toggle there. **Answer (owner, 2026-11-24): no shell** (as §5) |

## 10. Not verified

- The mockups and §8 come from the code and `etlui/CLAUDE.md`; etlui was not compared on screen with them.
- The reference's collapsed menu was not seen (the capture did not trigger it).
- The shell was not seen with a real session nor with `ModeBadge` showing (etlhub mocked, see lot 1).
- [../page-layout/page-layout.md](../page-layout/page-layout.md) L10 / P3 (Home's redirect in `HomeView`) are out of
  date since 2026-11-23: the route's `beforeEnter` does it (`src/router/index.ts`); `HomeView` keeps the redirect
  for a pass started while it is open.
