# Page layout, side panels and "where am I"

> Status: **implemented on 2026-10-27** (owner's requests of the day, one at a time). Builds on
> [../shadcn-migration/shadcn-migration.md](../shadcn-migration/shadcn-migration.md). The etlhub side of the passes
> (new pass after a pause, pass folders, `POST /pipeline/passes`) is in
> `etlhub/docs/decision-design/pass-folders/pass-folders.md`.

## 1. What changed

| # | Request | Built |
|---|---|---|
| L1 | One layout for Forecast, Journal and Tracking: a side panel on the left, the page beside it | `components/SideLayout.vue`: optional `side` slot, fixed on the left, `clamp(10rem, 16vw, 20rem)` wide (16 % of the screen), 1rem under the header; the page is padded only as much as needed, so they never overlap; same place with or without a panel (Tracking has none) |
| L2 | A scrollbar only when the panel is longer than the screen | shadcn `ScrollArea` inside the panel; the panel keeps its content's height (`max-height: inherit` down to the viewport) |
| L3 | Header fixed at the top; 1rem under it on every page | `App.vue`: header `sticky top-0 z-40`, `main` `pt-4` (was `py-8`) |
| L4 | Recent Activity in the side panel, shown even empty; Pause / Abandon under it | Forecast's `side` slot: `RecentActivity` (a `<details open>`, "No activity yet") then the two buttons (they were at the bottom of the page) |
| L5 | Recent Activity entries with the colour and icon of their status, details when unfolded | one shadcn `Trace` line per entry: green `CircleCheck` / red `CircleX` (Trace's `status="error"`); unfolding shows the message and "Request and logs" |
| L6 | Journal: the cycles as a foldable tree, in the side panel like Recent Activity | years → months → passes with shadcn `Collapsible` (the look of shadcn's file tree, block `sidebar-11`, without its `Sidebar`); months open for the target month and the selected pass's month |
| L7 | Journal passes shown like Recent Activity, their details organised | one `Trace` line per pass (state icon and colour: active `CirclePlay`, paused `CirclePause`, complete `CircleCheck`, abandoned `CircleX`); a click selects the pass and unfolds a list "label … value" (started by, started, events, last event), the layout of the body of AI Elements' `Context` |
| L8 | Forecast: "current step" as a breadcrumb step / run / item | shadcn `Breadcrumb` next to the cycle, from `position(state)` (`config/pipeline.ts`) |
| L9 | The last breadcrumb leads to the current item, blinking orange when no job runs | `positionItem(state)` + `goToPosition`: reopens the step's accordion section and points to its card, or opens the open run's Steps dialog at the item's stage; `utils/attention.ts` scrolls there and blinks the button to click (`data-attention`, 3 orange blinks, a steady ring with reduced motion) |
| L10 | Home is not reachable while a pass is active | `HomeView` replaces the route with `/forecast` as soon as the state shows an active pass |

## 2. Decisions

| # | Decision | Why |
|---|---|---|
| P1 | No shadcn "FileTree" (it does not exist in shadcn-vue's 68 components): its block `sidebar-11` rebuilt with `Collapsible` only | `Sidebar` needs a provider and many files for one list |
| P2 | AI Elements' `Context` not installed: only its row layout is reused | it needs the npm packages `ai` and `tokenlens`, and its parts are about AI tokens |
| P3 | The redirect of Home lives in `HomeView`, not in the router guard | the router only reads `stores/auth` (etlui rule); Home shows "Loading…" for a moment before leaving |
| P4 | The breadcrumb's item is read from etlhub's statuses and `launchable`: the running item, else the next launchable one (`nextItem`, shared with "To do now"), else the first one not in success | etlui computes no rule |
| P5 | The 77px header height is written in `SideLayout` (`ponytail:` note) | one place; a shared CSS variable if the header changes |

## 3. Components added (shadcn-vue CLI 2.8.2, Node 22)

`collapsible`, `trace`, `scroll-area`, `breadcrumb`: no new npm dependency, `base.css` untouched by the CLI. Trace's
`shimmer` utility (for `status="running"`) is not defined here: Recent Activity has no running entry.

## 4. Not verified

- Nothing was seen in a real browser against a real etlhub: the specs mock the API (happy-dom).
- The panel's scrolling (L2), the sticky header (L3) and the blinking (L9) were not seen at all. The 77px header was
  measured on a screenshot of the login page.
- On a screen narrower than about 1000px the panel stays at 10rem: the page gets narrower than 84 %.

Checks: `components/__tests__/SideLayout.spec.ts`, `config/__tests__/pipeline.spec.ts`,
`views/Dashboard/__tests__/Dashboard.spec.ts` and `RecentActivity.spec.ts`, `views/Journal/__tests__/JournalView.spec.ts`,
`views/Home/__tests__/HomeView.spec.ts`.
