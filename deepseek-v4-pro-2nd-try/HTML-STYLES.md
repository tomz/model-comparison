# HTML Styles — Optional Starting Points

_Illustrative static HTML scaffolds for the `html-generation` skill, not a
mandatory house style. Choose the delivery mode and visual direction first.
These examples use inline CSS; existing applications should keep their own
components/build pipeline. Adapt tokens, layout, typography, and component
rules to the brief. External assets are optional only when permitted; an offline
artifact must not depend on Google Fonts or any other network resource._

For a fresh design, use `frontend-design`; for inspection, use `ui-ux-review`.
Do not turn every brief into a centered hero and card grid. An editorial report,
dense dashboard, product page, and settings flow have different hierarchies.
Retain these examples only where they serve the intended content and task.

---

## Example shared design tokens and components

Use only the parts needed by the chosen design. This example carries a palette
(light + dark + auto), the
reset, typography, and the component classes (`.wrap`, `.card`, `.pill`,
`.callout`, `.toc`, `.metric`, tables, code).

```html
<style>
  :root {
    --fg: #1c1e21; --fg-soft: #4a4f57; --fg-mute: #626875;
    --bg: #fdfdfb; --bg-soft: #f4f4f0; --bg-card: #ffffff;
    --accent: #2c5aa0; --accent-soft: #e8eef7; --on-accent: #ffffff;
    --good: #17643f; --good-soft: #e3f2e8;
    --warn: #895017; --warn-soft: #fdf4e3;
    --bad:  #b8324a; --bad-soft:  #faeaee;
    --border: #d8d8d2; --border-soft: #ececea;
    --radius: 12px;
    --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, sans-serif;
    --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  }
  :root[data-theme="dark"] {
    --fg: #e6e7e9; --fg-soft: #b6bac3; --fg-mute: #8a8f99;
    --bg: #14171c; --bg-soft: #1c2027; --bg-card: #20242c;
    --accent: #6ea8ff; --accent-soft: #1a2842; --on-accent: #101f35;
    --good: #6fcb91; --good-soft: #14361f;
    --warn: #e2a85c; --warn-soft: #3a2a14;
    --bad:  #e88aa0; --bad-soft:  #421821;
    --border: #2e333c; --border-soft: #25292f;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --fg: #e6e7e9; --fg-soft: #b6bac3; --fg-mute: #8a8f99;
      --bg: #14171c; --bg-soft: #1c2027; --bg-card: #20242c;
      --accent: #6ea8ff; --accent-soft: #1a2842; --on-accent: #101f35;
      --good: #6fcb91; --good-soft: #14361f;
      --warn: #e2a85c; --warn-soft: #3a2a14;
      --bad: #e88aa0; --bad-soft: #421821;
      --border: #2e333c; --border-soft: #25292f;
    }
  }
  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }
  body {
    margin: 0; color: var(--fg); background: var(--bg);
    font-family: var(--sans); font-size: 15.5px; line-height: 1.65;
    -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: 1080px; margin: 0 auto; padding: 56px 32px 96px; }
  a { color: var(--accent); }
  :focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
  img, svg { max-width: 100%; }
  .table-scroll { max-width: 100%; overflow-x: auto; }
  h1 { font-size: 33px; font-weight: 700; letter-spacing: -0.015em; line-height: 1.18; margin: 0 0 12px; }
  h2 { font-size: 23px; font-weight: 700; margin: 56px 0 16px; padding-bottom: 8px;
       border-bottom: 2px solid var(--border-soft); scroll-margin-top: 20px; }
  h3 { font-size: 18px; font-weight: 650; margin: 32px 0 10px; }
  p { margin: 0 0 16px; }
  .eyebrow { font-size: 12px; text-transform: uppercase; letter-spacing: 0.12em;
             color: var(--accent); font-weight: 600; margin-bottom: 10px; }
  .subtitle { color: var(--fg-soft); font-size: 17px; max-width: 820px; }
  .meta { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 20px;
          color: var(--fg-mute); font-size: 13px; align-items: center; }
  .card { background: var(--bg-card); border: 1px solid var(--border);
          border-radius: var(--radius); padding: 22px 24px; }
  .grid { display: grid; gap: 18px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr)); }
  .pill { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px;
          font-weight: 600; background: var(--accent-soft); color: var(--accent); }
  .pill.good { background: var(--good-soft); color: var(--good); }
  .pill.warn { background: var(--warn-soft); color: var(--warn); }
  .pill.bad  { background: var(--bad-soft);  color: var(--bad); }
  .callout { border-left: 3px solid var(--accent); background: var(--accent-soft);
             padding: 14px 18px; border-radius: 0 8px 8px 0; margin: 18px 0; }
  .callout.good { border-color: var(--good); background: var(--good-soft); }
  .callout.warn { border-color: var(--warn); background: var(--warn-soft); }
  .callout.bad  { border-color: var(--bad);  background: var(--bad-soft); }
  table { width: 100%; border-collapse: collapse; margin: 18px 0; font-size: 14.5px; }
  th, td { text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--border-soft); }
  thead th { font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em;
             color: var(--fg-mute); border-bottom: 2px solid var(--border); }
  tbody tr:hover { background: var(--bg-soft); }
  code { font-family: var(--mono); font-size: 0.9em; background: var(--bg-soft);
         padding: 1px 5px; border-radius: 5px; }
  pre { background: var(--bg-soft); border: 1px solid var(--border-soft);
        border-radius: 10px; padding: 16px 18px; overflow-x: auto; line-height: 1.5; }
  pre code { background: none; padding: 0; }
  .metric { background: var(--bg-card); border: 1px solid var(--border);
            border-radius: var(--radius); padding: 18px 20px; }
  .metric .num { font-size: 30px; font-weight: 700; letter-spacing: -0.02em; }
  .metric .label { color: var(--fg-mute); font-size: 13px; margin-top: 4px; }
  .toc { background: var(--bg-soft); border: 1px solid var(--border-soft);
         border-radius: var(--radius); padding: 18px 22px; margin: 24px 0; }
  .toc a { display: block; padding: 3px 0; color: var(--fg-soft); text-decoration: none; }
  .toc a:hover { color: var(--accent); }
  .theme-toggle { position: fixed; top: 16px; right: 16px; border: 1px solid var(--border);
                  background: var(--bg-card); color: var(--fg-soft); border-radius: 8px;
                  padding: 6px 12px; font-size: 13px; cursor: pointer; }
  @media (max-width: 640px) { .wrap { padding: 36px 18px 72px; } h1 { font-size: 27px; } }
  @media (prefers-reduced-motion: reduce) {
    html { scroll-behavior: auto; scroll-snap-type: none; }
  }
</style>
```

Optional theme toggle when both themes are requested. Additional JavaScript
depends on the actual interaction requirements; do not ship decorative controls
that imply unimplemented behavior.

```html
<button type="button" class="theme-toggle" aria-label="Toggle color theme" onclick="(function(){var r=document.documentElement;
  var d=r.getAttribute('data-theme')==='dark'||(!r.getAttribute('data-theme')&&window.matchMedia('(prefers-color-scheme: dark)').matches);
  r.setAttribute('data-theme',d?'light':'dark');})()">◐ theme</button>
```

Optional Google Fonts for network-enabled delivery only; use approved local
fonts or system fallbacks for offline output. Respect the existing brand fonts.

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<!-- then set --sans: "Inter", -apple-system, BlinkMacSystemFont, sans-serif; -->
```

---

## 1. document (an example for design docs, analysis, explainers)

```html
<!DOCTYPE html>
<html lang="en" data-theme="">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{TITLE}}</title>
  <!-- paste the shared design system <style> here -->
</head>
<body>
  <!-- Add the optional accessible theme toggle above only if both themes are needed. -->
  <div class="wrap">
    <header>
      <div class="eyebrow">{{KICKER}}</div>
      <h1>{{TITLE}}</h1>
      <p class="subtitle">{{ONE_LINE_SUMMARY}}</p>
      <div class="meta"><span><strong>{{AUTHOR}}</strong></span><span>{{DATE}}</span><span class="pill">{{TAG}}</span></div>
    </header>
    <nav class="toc">
      <strong>Contents</strong>
      <a href="#s1">1. Section one</a>
      <a href="#s2">2. Section two</a>
    </nav>
    <main>
      <section><h2 id="s1">1. Section one</h2><p>Real content…</p>
        <div class="callout good"><strong>Key point.</strong> Use callouts for the takeaway.</div>
      </section>
      <section><h2 id="s2">2. Section two</h2>
        <div class="table-scroll" tabindex="0" role="region" aria-label="Example data">
          <table><thead><tr><th>Thing</th><th>Value</th></tr></thead>
          <tbody><tr><td>A</td><td>1</td></tr></tbody></table>
        </div>
      </section>
    </main>
  </div>
</body>
</html>
```

## 2. comparison (tool/model/option matrices)

Same skeleton; lead with the **criteria**, use a sticky table header, and finish
each row group with a verdict callout. Use `.pill good/warn/bad` in cells for
at-a-glance scoring.

```html
<style>
  thead th { position: sticky; top: 0; background: var(--bg); }
  td .pill { min-width: 54px; text-align: center; }
</style>
<section>
  <h2>Verdict</h2>
  <div class="callout"><strong>Pick X if</strong> … <strong>pick Y if</strong> …</div>
  <table><thead><tr><th>Criterion</th><th>Option A</th><th>Option B</th></tr></thead>
  <tbody>
    <tr><td>Speed</td><td><span class="pill good">fast</span></td><td><span class="pill warn">ok</span></td></tr>
    <tr><td>Cost</td><td><span class="pill bad">$$$</span></td><td><span class="pill good">$</span></td></tr>
  </tbody></table>
</section>
```

## 3. dashboard (metrics / benchmark results)

KPI cards in a grid + pure-CSS bars (no chart library). Pair with the
`benchmarking` skill's result data.

```html
<section>
  <div class="grid">
    <div class="metric"><div class="num">3.2×</div><div class="label">faster vs baseline (p95)</div></div>
    <div class="metric"><div class="num">99.4%</div><div class="label">pass rate</div></div>
    <div class="metric"><div class="num">$0.07</div><div class="label">cost / run</div></div>
  </div>
  <h2>Latency by case</h2>
  <!-- pure-CSS bar: width = value%, color via var() -->
  <div style="display:grid;gap:8px;margin-top:12px">
    <div><div style="font-size:13px;color:var(--fg-mute)">case-a — 120ms</div>
      <div style="height:10px;background:var(--accent);border-radius:5px;width:60%"></div></div>
    <div><div style="font-size:13px;color:var(--fg-mute)">case-b — 200ms</div>
      <div style="height:10px;background:var(--warn);border-radius:5px;width:100%"></div></div>
  </div>
</section>
```

## 4. landing (product / project intro)

One possible hero + supporting content + CTA composition. Choose centered,
split, editorial, or image-led structure based on the brief; cards are optional.
Keep the primary action clear rather than giving every element equal emphasis.

```html
<style>
  .hero { text-align: center; padding: 80px 0 48px; }
  .hero h1 { font-size: 46px; }
  .cta { display: inline-block; background: var(--accent); color: var(--on-accent); font-weight: 600;
         padding: 12px 26px; border-radius: 10px; text-decoration: none; margin-top: 20px; }
  @media (max-width: 640px){ .hero h1 { font-size: 32px; } }
</style>
<div class="wrap">
  <section class="hero">
    <div class="eyebrow">{{KICKER}}</div>
    <h1>{{PRODUCT}}</h1>
    <p class="subtitle" style="margin:0 auto">{{VALUE_PROP}}</p>
    <a class="cta" href="{{LINK}}">Get started →</a>
  </section>
  <section class="grid">
    <div class="card"><h3>Feature</h3><p>Benefit, not just description.</p></div>
    <div class="card"><h3>Feature</h3><p>…</p></div>
    <div class="card"><h3>Feature</h3><p>…</p></div>
  </section>
</div>
```

## 5. deck (scroll-snap slides for a talk/walkthrough)

```html
<style>
  html { scroll-snap-type: y mandatory; }
  .slide { min-height: 100vh; display: flex; flex-direction: column; justify-content: center;
           padding: 8vh 8vw; scroll-snap-align: start; border-bottom: 1px solid var(--border-soft); }
  .slide h2 { border: none; font-size: 38px; margin-top: 0; }
  .slide .big { font-size: 64px; font-weight: 800; letter-spacing: -0.03em; }
</style>
<section class="slide"><div class="eyebrow">Talk title</div><h1 style="font-size:52px">{{TITLE}}</h1><p class="subtitle">{{PRESENTER}} · {{DATE}}</p></section>
<section class="slide"><h2>The problem</h2><p class="subtitle">One idea per slide.</p></section>
<section class="slide"><div class="big">3.2×</div><p class="subtitle">Back the claim with one number.</p></section>
```

## 6. editorial (rich illustrated reference / long-form explainer)

Serif display headings, figures with captions, and sidenote callouts. Set a serif
display face for headings while keeping the sans body.

```html
<style>
  h1, h2, h3 { font-family: Newsreader, Georgia, "Times New Roman", serif; }
  figure { margin: 28px 0; }
  figure img, figure svg { width: 100%; border-radius: var(--radius); border: 1px solid var(--border-soft); }
  figcaption { color: var(--fg-mute); font-size: 13px; margin-top: 8px; text-align: center; }
  .lead { font-size: 20px; line-height: 1.5; color: var(--fg-soft); }
</style>
<div class="wrap" style="max-width: 760px">
  <header><h1>{{TITLE}}</h1><p class="lead">{{LEAD_PARAGRAPH}}</p></header>
  <p>Body…</p>
  <figure><svg viewBox="0 0 600 200"><!-- inline SVG diagram --></svg>
    <figcaption>Figure 1. Caption.</figcaption></figure>
  <div class="callout"><strong>Aside.</strong> Use callouts as sidenotes.</div>
</div>
```

---

## Notes

- For **diagrams**, prefer inline `<svg>` (self-contained) or render a Mermaid
  graph to SVG and inline it — see the `diagramming` skill.
- For **accessibility** (contrast, focus, landmarks, alt text) the page must pass
  the `accessibility` skill's relevant checks. Measure the actual foreground/
  background pairs and interactive states; this example is not a conformance
  certificate.
- To **restyle**, preserve or introduce semantic tokens, then change layout,
  type, and components where the direction requires it. Token changes alone
  cannot turn every template into the right composition.
- **Escape** user/data-derived values for their specific text/attribute/URL
  context and validate destinations (`security-appsec`).
- **Render and inspect** desktop/mobile views with actual image inputs, then
  verify interactions. Templates are not substitutes for observing the result.
