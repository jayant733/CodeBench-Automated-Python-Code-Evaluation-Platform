# UI Style Prompt — "Ink & Signal"

A portable design-system brief extracted from the AI Code Evaluation Suite dashboard.
Paste the whole thing into an AI coding assistant when starting a new project.

---

## The prompt

You are building the UI for a technical/data product. Use the design system below
**exactly**. It is a Swiss / International Typographic system: editorial poster
typography, hairline rules, zero ornament, one loud accent colour. Think Massimo
Vignelli's NYC subway signage rendered as a developer tool — not a generic SaaS
dashboard, not Material, not shadcn defaults.

### 1. Core principle

**Structure comes from typography, rules, and negative space — never from
rounded cards, drop shadows, or gradients.** Every visual boundary is a 1px
hairline or a flat colour-block change. If you are reaching for a border-radius
or a shadow to separate two things, you are solving it wrong: use a rule, a
background swap, or whitespace instead.

### 2. Design tokens

Declare these as CSS custom properties on `:root` and reference them everywhere.
Do not introduce colours outside this list plus the named greys.

```css
:root {
  --font-sans: "Aptos", "Segoe UI Variable", "Helvetica Neue", sans-serif;
  --font-mono: "Cascadia Code", "SFMono-Regular", Consolas, monospace;

  --ink:    #101311;              /* near-black green-cast — headers, footers, text */
  --paper:  #f2f0e8;              /* warm cream — the page background, never white */
  --signal: #c8ff4d;              /* acid lime — the ONLY accent */
  --ember:  #ff795c;              /* coral — errors + focus rings only */
  --line:   rgba(16, 19, 17, 0.2); /* the universal hairline */
}

body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 15px;
  line-height: 1.5;
  text-rendering: optimizeLegibility;
}
```

**Supporting greys** (memorise these; don't invent new ones):

| Value     | Use                                                    |
| --------- | ------------------------------------------------------ |
| `#e7e8df` | panel title bars, sidebar rails                        |
| `#eef0ea` | inset stat cells, callout rows                         |
| `#e5e8e1` | empty meter/progress track                             |
| `#f5f6f1` | table row hover                                         |
| `#111512` | code surfaces (editors, terminal output, tool logs)    |
| `#c5cbc5` | body copy **on ink**                                    |
| `#8d958f` | muted mono labels **on ink**                            |
| `#353a36` / `#3b403c` | hairlines **on ink**                       |
| `#71776f` / `#6d746d` | muted mono labels **on paper**             |
| `#ffd9cf` + `#752817` | fail badge background + text               |
| `#ffe7e0` | error/risk callout background                           |
| `#88bc27` | "safe / info" rule accent                               |

### 3. Typography

Two families only. **Sans for content, mono for every piece of metadata.** The
mono/sans split is the single most important signal of this system — it is how a
label reads as a label without needing a box around it.

**Display headings** — poster-scale, tight, optically negative-tracked:

```css
h1 {
  font-size: clamp(54px, 7vw, 104px);  /* hero;  page heads: clamp(38px, 5vw, 66px) */
  font-weight: 620;                     /* not 700 — a variable-font mid-bold */
  line-height: 0.88;                    /* page heads: 0.9 */
  letter-spacing: -0.065em;             /* page heads: -0.055em */
  margin: 0;
}
```

**The serif accent.** Wrap one word or clause of each `h1` in `<em>` and render
it as a lime Georgia serif italic against the ink band. This is the system's
signature move — a single humanist note inside otherwise cold grotesque type.
Use it once per page, never more.

```css
h1 em {
  color: var(--signal);
  font-family: Georgia, "Times New Roman", serif;
  font-weight: 400;
}
```

Write headlines as **two lines split by `<br>`**, the second being the serif
clause: "Code evaluation, / *with receipts.*" · "Agent runs, / *step by step.*" ·
"Experiments, / *under version.*"

**Micro-labels** — every eyebrow, column header, badge, timestamp, unit, and
key in a definition list:

```css
.eyebrow {           /* section kicker; lime on ink */
  font-family: var(--font-mono);
  font-size: 10px;             /* table headers + dt/dd: 9px */
  line-height: 1;
  letter-spacing: 0.17em;      /* table headers: 0.13em; nav: 0.14em */
  text-transform: uppercase;
  color: var(--signal);
}
```

All numeric columns and metric values get `font-variant-numeric: tabular-nums`.

**Body copy** sits at 15–17px / 1.6, capped at `max-width: 390px–470px`, and is
introduced by a `border-top: 1px solid` rule with ~18–20px of padding above it.
A rule above a paragraph replaces a heading.

### 4. Shape language

- **`border-radius: 0` everywhere.** The only exceptions: status dots and live
  indicators (`999px`), and a single conic-gradient score ring.
- **Borders are always exactly `1px solid var(--line)`.** Never 2px, never a
  lighter/darker variant per component.
- **Accent bars are `border-left: 3px solid`** (callouts, findings) or `5px`
  (page-level error banners). Left rules, not full outlines.
- One shadow exists in the entire system: `0 18px 50px rgba(16, 19, 17, 0.12)`,
  used only on the main floating panel. Nothing else gets elevation.

### 5. Signature layout: ink band → pulled-up white panel

This is the page skeleton. Every route uses it.

1. A **dark ink band** at the top (`background: var(--ink); color: white`)
   containing the eyebrow, the display `h1`, one paragraph of copy, and a
   right-aligned metrics list. Grid: `minmax(0, 1fr) auto`, `align-items: end`,
   `padding: 54px 4vw 58px`.
2. The **content panel overlaps it** by pulling up 24px, so the white plane
   visibly cuts into the black band:

```css
.console-shell { padding: 0 3vw 80px; }

.console-panel {
  max-width: 1500px;
  margin: -24px auto 0;      /* the pull-up */
  position: relative;
  z-index: 2;                 /* required, or the ink band covers it */
  background: white;
  border: 1px solid var(--line);
  box-shadow: 0 18px 50px rgba(16, 19, 17, 0.12);
}
```

3. Each panel opens with a **`#e7e8df` title bar**: `min-height: 54px`,
   `padding: 12px 22px`, flex with `space-between`, a 16px `h2` at
   `letter-spacing: -0.03em` on the left, and a count / status pill / outbound
   link on the right.

Note the two background planes: the page is cream `--paper`, the panels are pure
`white`. That small step is what makes panels read as raised without a shadow.

**Metrics list** in the ink band — a `<dl>` capped by a lime rule:

```css
.page-metrics { margin: 0; min-width: 108px; border-top: 1px solid var(--signal); }
.page-metrics div {
  padding: 9px 0;
  display: flex; justify-content: space-between; gap: 18px;
  border-bottom: 1px solid #353a36;
}
.page-metrics dt, .page-metrics dd {
  margin: 0; font-family: var(--font-mono); font-size: 9px;
  letter-spacing: 0.08em; text-transform: uppercase;
}
.page-metrics dt { color: #8d958f; }
.page-metrics dd { color: white; font-variant-numeric: tabular-nums; }
```

### 6. Data tables

```css
.data-table { width: 100%; border-collapse: collapse; }

.data-table thead th {
  padding: 12px 22px;
  color: #71776f;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 400;              /* headers are NOT bold — mono + caps is enough */
  letter-spacing: 0.13em;
  text-align: left;
  text-transform: uppercase;
  white-space: nowrap;
  border-bottom: 1px solid var(--ink);   /* full-strength ink under the header */
}

.data-table tbody td {
  padding: 15px 22px;
  font-size: 13px;
  border-bottom: 1px solid var(--line);  /* hairline between rows */
}
.data-table tbody tr:last-child td { border-bottom: 0; }
.data-table tbody tr { transition: background 130ms ease; }
.data-table tbody tr:hover { background: #f5f6f1; }
```

Cell modifiers: `.num` (mono, tabular, right-aligned, nowrap) · `.mono` (mono
12px, for IDs) · `.stamp` (mono 11px, `#6a706a`, for timestamps).

Wrap tables in `overflow-x: auto` so they scroll instead of breaking the layout.

**ID links** get a lime underline that fills on hover — no colour change:

```css
.id-link {
  color: var(--ink);
  font-family: var(--font-mono); font-size: 12px;
  text-decoration: none;
  border-bottom: 2px solid var(--signal);
  transition: background 130ms ease;
}
.id-link:hover { background: var(--signal); }
```

### 7. Status pills

Flat colour blocks, mono caps, with a dot that inherits the text colour:

```css
.pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 8px;
  font-family: var(--font-mono); font-size: 9px; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase; white-space: nowrap;
}
.pill i { width: 6px; height: 6px; border-radius: 999px; background: currentColor; }

.pill--ok   { background: var(--signal); color: #24331b; }
.pill--run  { background: #e6e9e0;      color: #4a524a; }
.pill--fail { background: #ffd9cf;      color: #752817; }
.pill--idle { background: #eaece5;      color: #6d746d; }

.pill--run i { animation: pill-pulse 1.4s ease-in-out infinite; }
@keyframes pill-pulse { 50% { opacity: 0.25; } }
```

Only the in-progress state animates. Success and failure are static.

### 8. Charts and meters

No chart library defaults. Build primitives from flat blocks:

- **Bar meter** — 44×6px, track `#e5e8e1`, fill `var(--signal)`, switching to
  `var(--ember)` below threshold. Square, no radius, no label inside.
- **Score ring** — a 92px `conic-gradient(var(--signal) var(--score), #e5e8e1 0)`
  with a white `::after` inset 8px punching out the centre, and the number
  layered above at 28px/760.

### 9. Code and terminal surfaces

Anything showing machine output inverts to near-black `#111512` regardless of
the surrounding light page:

```css
.code-surface {
  background: #111512;
  color: #dce4da;
  font-family: var(--font-mono);
  font-size: 11px;          /* editors: 12px, line-height 1.65, tab-size 4 */
  line-height: 1.5;
}
.code-surface b    { color: var(--signal); font-weight: 700; }  /* the identifier */
.code-surface code { color: #9fb096; word-break: break-all; }   /* the payload  */
.code-surface span { margin-left: auto; color: #7d867d; font-size: 10px;
                     font-variant-numeric: tabular-nums; }      /* the duration */
```

Text inputs on these surfaces use `caret-color: var(--signal)` and `border: 0`.

### 10. Callouts and severity

A left rule plus a tinted background — never an icon-in-a-circle:

```css
.callout        { padding: 11px 14px; background: #eef0ea;
                  border-left: 3px solid #939b91; font-size: 12px; }
.callout--info  { border-color: #88bc27; }
.callout--error { background: #ffe7e0; border-color: var(--ember); }

/* page-level service banner */
.service-error  { padding: 14px 18px; background: #ffe1d8;
                  border-left: 5px solid var(--ember); display: flex; gap: 18px; }
```

### 11. Timeline

Sequential runs render as a numbered vertical trace:

```css
.timeline > li { position: relative; padding-left: 54px; padding-bottom: 20px; }
.timeline > li::before {           /* the connector */
  content: ""; position: absolute; left: 17px; top: 41px; bottom: 0;
  width: 1px; background: var(--line);
}
.timeline > li:last-child::before { display: none; }

.iteration-marker {                 /* zero-padded: 01, 02, 03 */
  position: absolute; left: 0; top: 0;
  width: 35px; height: 35px;
  display: grid; place-items: center;
  background: var(--ink); color: white;
  font-family: var(--font-mono); font-size: 11px; font-weight: 700;
}
```

### 12. Hairline grids

For stat clusters, produce dividers with a 1px gap over a coloured parent —
no per-cell borders and no double lines:

```css
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(154px, 1fr));
  gap: 1px;
  background: var(--line);          /* the gap shows through as the rule */
  border-bottom: 1px solid var(--line);
}
.stat { padding: 17px 20px; background: #eef0ea; }
.stat span   { display: block; color: #6d746d; font-family: var(--font-mono);
               font-size: 9px; letter-spacing: 0.1em; text-transform: uppercase; }
.stat strong { display: block; margin-top: 7px; font-size: 19px;
               letter-spacing: -0.035em; line-height: 1.15; }
```

### 13. Navigation, header, footer

- **Header**: `min-height: 72px`, `background: var(--ink)`, `padding: 0 4vw`,
  `border-bottom: 1px solid rgba(255, 255, 255, 0.14)`.
- **Brand mark**: a 34px lime square, mono 12px/800, `transform: rotate(-3deg)`.
  The tilt is deliberate — one hand-placed element against a rigid grid.
- **Nav links**: mono 10px, `letter-spacing: 0.14em`, uppercase, `#9aa29a`;
  hover → `rgba(255,255,255,.08)` + white; **active → full lime block with ink
  text at weight 700**, driven by `a[aria-current="page"]`.
- **Footer**: ink, `min-height: 80px`, mono 9px uppercase `letter-spacing: .12em`,
  colour `#9ea59e`, one line left, one line right.
- **Live indicator**: 7px lime dot with `box-shadow: 0 0 0 4px rgba(200,255,77,.12)`.

### 14. Interaction

- Transitions are **130–150ms ease**, on `background`, `color`, and `transform`
  only. Nothing eases longer.
- Selected list items take the lime background **and slide**:
  `transform: translateX(7px)`.
- Primary buttons: `background: var(--signal)`, `color: var(--ink)`,
  `font-weight: 760`, no radius, no border. Disabled → `#57604f` / `#aeb5aa`.
- Secondary buttons are bare underlined text, no chrome.
- **Focus rings are coral, not lime**, so focus never reads as "selected":
  `outline: 3px solid var(--ember); outline-offset: 3px` on `:focus-visible`.
- Respect `prefers-reduced-motion: reduce` with
  `transition: none !important; animation: none !important;`.

### 15. Responsive

Breakpoints at **1180px**, **820px**, **560px**.

- 1180: multi-column grids collapse to one; sticky sidebars go static.
- 820: hero grid → single column; `h1` → `clamp(50px, 13vw, 78px)`; side padding
  drops from `4vw` to `14px`.
- 560: header wraps, the wordmark and status note hide, nav moves to `order: 3`
  at full width with `overflow-x: auto`; the timeline flattens (drop the
  `padding-left` and the `::before` connector, make markers static and
  full-width); panels lose their pull-up.

### 16. Accessibility (non-negotiable)

- Real semantics: `<table>` with `<caption class="sr-only">` and
  `scope="col"`; `<dl>` for metrics; `<ol>` for timelines; `<nav aria-label>`.
- Active nav = `aria-current="page"` and style **from that attribute**, not from
  a class — the state is then correct for screen readers by construction.
- Never rely on lime alone to convey status; every pill carries a text label.
- Repeated links ("View in MLflow") need per-row `aria-label`s.
- Error banners get `role="alert"`.
- Ship an `.sr-only` utility.

### 17. Do not

- ...use rounded corners, gradients, glassmorphism, blur, or translucency.
- ...add a second accent colour. Lime signals; coral means error or focus. That's all.
- ...use pure white as a page background — it must be cream `#f2f0e8`.
- ...use drop shadows for hierarchy. One shadow, one panel.
- ...set label text in the sans family. Metadata is always mono + uppercase + tracked.
- ...use `font-weight: 700` for display headings — 620 is the display weight.
- ...centre body copy or let it exceed ~470px.
- ...introduce icon libraries. Typographic glyphs (`→`, `↗`, `←`) only.

---

## Condensed version

> Swiss/International Typographic design system, light-mode, editorial. Warm
> cream page `#f2f0e8`, near-black ink `#101311` header/hero/footer bands, pure
> white content panels that overlap the ink band by −24px with a single soft
> shadow. Acid-lime `#c8ff4d` is the only accent; coral `#ff795c` is errors and
> focus rings. Zero border-radius, every boundary a 1px `rgba(16,19,17,.2)`
> hairline. Poster-scale headings — `clamp(38px, 5vw, 66px)`, weight 620,
> line-height .9, letter-spacing −.055em — with one clause per page set in lime
> Georgia serif italic. All metadata (eyebrows, table headers, badges,
> timestamps, units) in uppercase mono at 9–10px with .1–.17em tracking; numbers
> tabular. Flat mono status pills with a 6px dot, only the running state pulses.
> Code and terminal surfaces invert to `#111512`. Transitions 130–150ms.
> No gradients, no glass, no icon library, no second accent.
