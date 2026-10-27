# Styling: migration to Tailwind tokens

> Status: **decided, not implemented** (2026-10-16). Nothing in `src/` follows this document yet.
> **Partly superseded on 2026-10-27** by `../shadcn-migration/shadcn-migration.md`: shadcn tokens replace D5 / § 3.1,
> shadcn components replace D6 / § 3.3, the `.dark` class replaces `data-theme` (§ 3.2), and § 6 "no new
> dependency" no longer holds. D1–D4, D7, § 3.4 and § 3.5 still apply.
> Scope: every `<style>` block and every class of `etlui/src/`, `src/styles/base.css`, `index.html`, the specs that
> select by class.

## 1. Why

Tailwind 4 is installed (`@tailwindcss/vite`, `@import "tailwindcss"` in `src/styles/base.css`), but most of the
styling is hand-written CSS with hard-coded colors. Measured on 2026-10-16:

| Where | Size | How |
|---|---|---|
| `<style>` blocks in 20 `.vue` files | ≈ 2 040 lines | plain CSS, hex / rgba literals |
| `ForecastRuns.vue` | 475 lines, **not scoped** | also styles `DiseaseCard` and `LevelColumn` (they have no `<style>`) |
| `src/styles/base.css` | ≈ 190 lines | ~30 `@apply` classes, half used once, `.fade-*` unused |
| 6 components (`App`, `Drawer`, `ConfigView`, `ForecastReportModal`, `JobStatus`, `LogsStreamPage`) | — | `@apply` + `@reference "tailwindcss"` mixed with plain CSS |
| `TrackerView/*`, `RecentActivity`, `LevelColumn` template | — | utilities in the template |

Problems this migration fixes:

1. **Four palettes mixed.** slate as hex in scoped CSS (`#94a3b8` ×22, `#1e293b` ×12, `#0f172a` ×9…), Tailwind
   `gray-*` in templates and `base.css`, an "Amazon" set in `App.vue` / `.btn-status` (`#131921`, `#232f3e`,
   `#febd69`, `#f0c14b`), one-offs (`#c00`, `#fee`, `#ddd`, `#1a1a1a`). 40+ distinct hex values, ~10 translucent
   white rgba for the same purpose (borders, surfaces).
2. **Three accents.** indigo `#4f46e5` (pipeline buttons), a purple gradient (`.btn-primary` of `base.css`, which
   lacks `bg-linear-to-*` so the gradient probably never renders — read from the code, not seen), yellow focus ring
   (`.form-input`).
3. **Two `.btn-primary`.** The global one in `base.css` (`w-full`, `shadow`, `flex`…) and
   `.forecast-runs .btn-primary`. The second wins on specificity, the properties it does not redefine leak into the
   `LevelColumn` buttons.
4. **Dark mode half-wired.** `#app` is always `gray-900`; the `dark:` variants of `base.css` follow
   `prefers-color-scheme` (no `@custom-variant`), so on a light OS `.card` is white on a dark page (`LogsStreamPage`).
5. **`base.css` redefines Tailwind utilities** (`.bg-gray-50 { @apply bg-gray-50 dark:… }`, same for `bg-blue-50`,
   `bg-red-50`).
6. **No scale.** Font sizes `0.8125rem` ×15, `0.875rem` ×14, `0.9375rem`…; radii `4px`, `8px`, `0.375rem`,
   `0.5rem`, `0.625rem`, `0.75rem`, `1rem`.
7. **Dead code.** `src/views/JobStatus.vue` was neither routed nor imported (deleted 2026-10-23, with its `base.css` classes and `.fade-*`).

## 2. Decisions

| # | Decision | Rejected |
|---|---|---|
| D1 | **Neutral palette = Tailwind `gray`.** | slate (current hex values) |
| D2 | **One accent = Tailwind `indigo`.** The "Amazon" yellow / navy of the header, the purple gradient and the yellow focus ring go. | keeping the brand yellow |
| D3 | **Light and dark theme**, following the OS by default, with a toggle in the header that overrides it. | dark only |
| D4 | **Tests select with `data-test`**, never with a styling class. State is asserted through `aria-*` or `data-state`, never through `classes()`. | keeping hook classes |
| D5 | **Colors are semantic tokens in `@theme`** (`src/styles/base.css`). Components use `bg-surface`, `text-muted`, `border-line`…, never `gray-800` or a hex. | raw palette utilities everywhere + `dark:` on each one |
| D6 | **A handful of component classes** in `@layer components` (buttons, card, input, badge). Everything else is utilities in the template. | `BaseButton` / `BaseCard` Vue components (YAGNI: they add a file and props for what a class does) |
| D7 | **CSS stays** only where utilities cannot reach or read badly: `dialog::backdrop`, `<progress>` pseudo-elements, scrollbar hiding, `@keyframes`. | arbitrary variants for everything |

Tailwind 4 is configured in CSS (`@theme`): **no `tailwind.config.js`, no new dependency.**

## 3. Target design

### 3.1 Tokens (`src/styles/base.css`)

Semantic tokens, light values in `@theme`, dark values overridden on `[data-theme="dark"]`. Because the token
itself changes, templates need **no `dark:` variant** for colors.

```css
@import "tailwindcss";

@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));

@theme {
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;

  /* surfaces */
  --color-canvas: var(--color-gray-50);       /* page background */
  --color-surface: var(--color-white);        /* cards, dialogs, header */
  --color-surface-2: var(--color-gray-100);   /* hover, table head, nested blocks */
  --color-line: var(--color-gray-200);        /* borders, dividers */

  /* text */
  --color-fg: var(--color-gray-900);
  --color-muted: var(--color-gray-500);

  /* accent */
  --color-accent: var(--color-indigo-600);
  --color-accent-hover: var(--color-indigo-700);
  --color-accent-fg: var(--color-white);
  --color-accent-soft: var(--color-indigo-50);  /* selected / open run */

  /* status: text on a soft background */
  --color-success: var(--color-green-700);
  --color-success-soft: var(--color-green-50);
  --color-warning: var(--color-amber-700);
  --color-warning-soft: var(--color-amber-50);
  --color-danger: var(--color-red-700);
  --color-danger-soft: var(--color-red-50);
  --color-info: var(--color-blue-700);
  --color-info-soft: var(--color-blue-50);
}

@layer base {
  [data-theme="dark"] {
    --color-canvas: var(--color-gray-950);
    --color-surface: var(--color-gray-900);
    --color-surface-2: var(--color-gray-800);
    --color-line: var(--color-gray-700);
    --color-fg: var(--color-gray-100);
    --color-muted: var(--color-gray-400);
    --color-accent: var(--color-indigo-500);
    --color-accent-hover: var(--color-indigo-400);
    --color-accent-soft: color-mix(in oklab, var(--color-indigo-500) 15%, transparent);
    --color-success: var(--color-green-400);
    --color-success-soft: color-mix(in oklab, var(--color-green-500) 15%, transparent);
    --color-warning: var(--color-amber-300);
    --color-warning-soft: color-mix(in oklab, var(--color-amber-500) 15%, transparent);
    --color-danger: var(--color-red-400);
    --color-danger-soft: color-mix(in oklab, var(--color-red-500) 15%, transparent);
    --color-info: var(--color-blue-400);
    --color-info-soft: color-mix(in oklab, var(--color-blue-500) 15%, transparent);
  }

  html { color-scheme: light; }
  html[data-theme="dark"] { color-scheme: dark; }   /* native inputs, scrollbars, <dialog> follow */
  body { @apply bg-canvas text-fg font-sans antialiased; }
}
```

Exact shades are a starting point: adjust them during phase 2 by eye, in both themes, then do not add more tokens
without a second use.

Scale: **use Tailwind's default scale** (`text-xs/sm/base/lg`, `rounded-md/lg/xl`, `gap-*`, `p-*`). The odd values
(`0.8125rem`, `0.9375rem`, `0.625rem` radius) are rounded to the nearest step; no custom scale.

To verify when implementing (not checked yet):
- the dark block references `--color-gray-950`, `--color-indigo-400`…: check in `dist/assets/*.css` that Tailwind
  emits them. If unused palette variables are dropped, declare the palette with `@theme static` or reference the
  values directly.
- `dialog::backdrop` inherits custom properties from its `<dialog>` in current browsers; check Firefox and Safari.

### 3.2 Theme switch

Single source of truth: the `data-theme` attribute on `<html>`, always set (`"light"` or `"dark"`).

- **Before Vue mounts**, a small inline script in `index.html` sets it, to avoid a flash of the wrong theme:
  ```html
  <script>
    // ponytail: read once at load; an OS theme change while the page is open needs a reload. Add a matchMedia listener if users ask.
    try {
      var t = localStorage.getItem('theme')
      document.documentElement.dataset.theme =
        t === 'light' || t === 'dark' ? t : matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    } catch (e) { document.documentElement.dataset.theme = 'light' }
  </script>
  ```
  nginx sends no `Content-Security-Policy` today, so an inline script is allowed. If a CSP is added later, move it
  to a file in `public/` loaded in `<head>`.
- **Toggle**: one icon button in the `App.vue` header (sun / moon, `aria-label="Switch to dark theme"` /
  `"…light theme"`, `aria-pressed`). It flips `data-theme` and writes `localStorage.theme`. A few lines in `App.vue`;
  no composable, no store (nothing else reads it). Add `ICONS.sun` / `ICONS.moon` to `src/components/Icons`.
- No "follow system" third state in the UI: clearing `localStorage.theme` gives it back. Add it only if asked.
- `vue3-hot-toast`: check its toasts in both themes; style them through its options if they stay light.

### 3.3 Component classes (`@layer components` in `base.css`)

Only patterns used 3+ times. Each uses tokens only.

| Class | Replaces | Content (indicative) |
|---|---|---|
| `.btn` | `.forecast-runs .btn`, `.approval-btn`, `.btn-link-secondary`, `.mode-btn`, the FileDropzone `.btn`, dialog buttons | `inline-flex items-center justify-center gap-2 min-h-11 px-4 py-2 rounded-lg text-sm font-semibold border border-line bg-surface text-fg hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-50 disabled:cursor-not-allowed` |
| `.btn-primary` | `.btn-primary` (both), `.approval-btn-primary`, `.btn-status` | `.btn` + `bg-accent border-accent text-accent-fg hover:bg-accent-hover` |
| `.btn-danger` | `.forecast-runs .btn-danger`, reject / delete buttons | `.btn` + `bg-danger-soft border-danger text-danger` |
| `.btn-sm` | `.btn-small` | `min-h-8 px-3 py-1 text-xs` |
| `.card` | `.card`, `.card-padded`, `.activity-section`, `.disease-card`, `.action-card` box | `bg-surface border border-line rounded-xl` (padding stays a utility: `p-6`) |
| `.input` | `.form-input`, `ConfigView` inputs, `LoginForm` inputs | `w-full px-3 py-2 rounded-lg border border-line bg-surface text-fg placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent` |
| `.badge` | status pills of `RequestTable`, `ActionCard`, `LevelColumn`, `app-badge`, `live-badge` | `inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold` + a color utility pair (`bg-success-soft text-success`…) |

Everything in today's `base.css` not in this table is deleted (`bg-*-50` overrides, `section-header`,
`heading-primary`, `card-empty`, `icon-*`, `spinner-xs`, `activity-*`, `grid-cols-2-md`, `flex-row-*`,
`btn-status`, `btn-link-secondary`, `.fade-*`) and replaced by utilities where it is used.

### 3.4 State-driven styles

Today the state is a class built from data: `` `item-${row.look}` ``, `` `job-${row.job}` ``,
`` `status-${status.key}` ``, `is-open`, `is-active`, `is-disabled`, `is-dragging`, `has-file`, `has-error`.
Tailwind cannot generate classes from runtime strings. Rule:

- **Semantic state → ARIA attribute**, styled with `aria-*` variants:
  - active disease in the nav → `aria-current="true"` → `aria-[current=true]:bg-accent-soft`
  - disabled dropzone / label → native `disabled` where the element supports it, else `aria-disabled="true"`
  - open run (`LevelColumn`) → `aria-current="true"` on the section (it is "the current run")
- **Other state → `data-state` attribute**, styled with `data-*` variants:
  `<li :data-state="row.look" class="data-[state=success]:text-success data-[state=error]:text-danger …">`.
  For a long list of states, a `Record<Look, string>` of classes next to `LOOK_TEXT` in the component is fine.
- The same attribute is what tests assert (§ 3.5): one attribute serves both.

### 3.5 Tests: `data-test`

Rule: **a spec never selects or asserts a styling class.** It uses `[data-test="…"]`, a role / tag, an ARIA
attribute or `data-state`. Naming: kebab-case, the noun the user sees (`level-column`, `steps-tile`).

Inventory of class selectors in specs (2026-10-16) and their replacement:

| Today | Component | Specs | Replacement |
|---|---|---|---|
| `.action-card` | `ActionCard` | `Dashboard` | `[data-test="action-card"]` |
| `.admin-zone` | `ForecastRuns` | `Dashboard` | `[data-test="admin-zone"]` |
| `.carousel` | `ForecastRuns` | `Dashboard` | `[data-test="carousel"]` |
| `.disease-nav a` + `classes().includes('is-active')` | `ForecastRuns` | `Dashboard` | `[data-test="disease-nav"] a` + `attributes('aria-current')` |
| `.forecast-runs` | `ForecastRuns` | `Dashboard` | `[data-test="forecast-runs"]` |
| `.todo` | `ForecastRuns` | `Dashboard` | `[data-test="todo"]` |
| `.disease-card` | `DiseaseCard` | `Dashboard` | `[data-test="disease-card"]` |
| `.level-column` + `classes().includes('is-open')` | `LevelColumn` | `Dashboard` | `[data-test="level-column"]` + `attributes('aria-current')` |
| `.card-steps`, `.steps-tile`, `.tile-nav`, `.data-check`, `.item`, `.item-tech`, `.item-time` | `LevelColumn` | `Dashboard` | same names as `data-test` |
| `.dropzone` + `classes().includes('is-disabled')` | `FileDropzone` | `Dashboard` | `[data-test="dropzone"]` + `attributes('aria-disabled')` |
| `.file-input > div` + `classes()` contains `status-row` / `dropzone` (order check) | `FileDropzone` | `FileDropzone` | `findAll('[data-test="file-input"] > [data-test]').map(d => d.attributes('data-test'))` |
| `.status-row`, `.default-status` | `FileDropzone` | `FileDropzone`, `Dashboard` | same names as `data-test` |
| `.impact-dialog` | `ImpactDialog` | `Dashboard` | `[data-test="impact-dialog"]` |
| `.mode-btn` | `ModeToggle` | `Dashboard` | `[data-test="mode-btn"]` |
| `.detail-btn` | `RequestTable`, `RecentActivity` | `TrackerView`, `RecentActivity` | `[data-test="detail-btn"]` |
| `.fixed` (a Tailwind utility!) for the detail modal | `TrackerView`, `RecentActivity` | `TrackerView` | `[data-test="request-detail"]` on the modal root |
| `.job-logs-section`, `.live-badge` | `JobLogsPanel` | `TrackerView`, `RecentActivity` | same names as `data-test` |

`data-test` attributes stay in the production build (a few bytes, no need for a build step to strip them).

## 4. Migration plan

One phase = one commit (or one PR), app working at every step. Before and after each phase:
`yarn vitest run`, `yarn build`, then look at the touched pages **in both themes** with `yarn dev` (against an
`etlhub` with `DRYRUN=true`; no type-check or visual test exists to do it for you).

| Phase | Content | Visual change |
|---|---|---|
| **1. Test hooks** | Add `data-test` / `aria-current` / `aria-disabled` / `data-state` to the components of § 3.5, rewrite the specs to use them. Styling classes untouched. **Done 2026-10-27** (shadcn-migration lot 2). | none |
| **2. Foundation** | `base.css`: tokens, dark override, `@custom-variant dark`, component classes (§ 3.3), delete the dead classes. `index.html` script, toggle in `App.vue`. `#app` background → `bg-canvas`. (`JobStatus.vue` already deleted, 2026-10-23.) | header, global background, every page using a deleted `base.css` class (fix them in this phase) |
| **3. Shell and simple pages** | `App`, `Drawer`, `LoginForm`, `ParametersPage`, `ConfigView`, `LogsStreamPage`, `TrackerView/*` (replace raw `gray-*` utilities with tokens). | small |
| **4. Dialogs** | `BaseDialog` (box + backdrop stay CSS, colors → tokens), `ConfirmDialog`, `ImpactDialog`, `PreviewDialog`, `ConfigPreview`, `CsvPreview`, `ForecastReportModal`. | small |
| **5. Dashboard, steps 1 and 3** | `Dashboard`, `Accordion`, `ActionCard`, `ModeToggle`, `RecentActivity`, `FileDropzone`. | medium |
| **6. Step 2 (forecast runs)** | `ForecastRuns`, `DiseaseCard`, `LevelColumn`: delete the 475-line global block, utilities in each template, states via § 3.4. Largest and riskiest: its own commit. | medium |
| **7. Clean-up** | `grep` for leftovers (§ 5), update `etlui/CLAUDE.md` (module map, styling rule). | none |

## 5. Definition of done

- `grep -rnE '#[0-9a-fA-F]{3,8}\b|rgba?\(' src --include=*.vue` → nothing (except an SVG `fill` if justified).
- `grep -rnE '\b(bg|text|border|divide|ring)-(gray|slate|indigo|yellow|purple)-[0-9]' src --include=*.vue` → nothing:
  components use tokens, palette names live in `base.css` only.
- `grep -rn 'dark:' src --include=*.vue` → nothing, or a justified exception.
- `grep -rnE "find(All)?\\(['\"]\\." src --include=*.spec.ts` → nothing; `grep -rn 'classes()' src --include=*.spec.ts` → nothing.
- Remaining `<style>` blocks only hold what § D7 allows; total CSS ≈ 150–250 lines (estimate).
- `yarn vitest run` and `yarn build` pass; every route checked by eye in light and dark.

## 6. Out of scope / open

- No new dependency (no headless UI kit, no icon pack, no `tailwind-merge`).
- The Google Fonts `Inter` link in `index.html` stays as it is.
- Contrast: check WCAG AA on `text-muted` over `bg-surface-2` in both themes during phase 2 (not measured).
- `etlui/package-lock.json`, once tracked by git although the project is yarn-only, was deleted on 2026-10-23.
