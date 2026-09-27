#!/usr/bin/env python3
"""Render the model-comparison report as one self-contained HTML file.

``render(payload)`` takes the dict produced by build_comparison.py and returns
HTML with the data, styles and scripts inlined. No network requests, no CDN, no
web fonts: the file opens correctly from file:// and prints cleanly.

The JSON is embedded inside a <script> tag, so '<' is escaped to prevent the
payload from closing the tag early.
"""
from __future__ import annotations

import json

PLACEHOLDER = "__COMPARISON_DATA__"
HASH_PLACEHOLDER = "__SOURCES_JSON__"

DOCUMENT = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Model comparison &mdash; cost, time and value per report</title>
<style>
:root{
  --bg:#f6f7f9; --panel:#fff; --ink:#151a21; --muted:#5c6673; --line:#e2e6ec;
  --accent:#2f5fd0; --good:#12805c; --warn:#a35a00; --bad:#b3261e;
  --bar:#3b6fd4; --bar-lb:#9fb4dd; --grid:#e8ebf1; --shadow:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.04);
  --d1:#3b6fd4; --d2:#2f9d8a; --d3:#7aa93c; --d4:#cf9a1f; --d5:#d97b3f; --d6:#c0586f; --d7:#8a6fc0;
}
@media (prefers-color-scheme:dark){
  :root{--bg:#11141a;--panel:#181c24;--ink:#e8ecf2;--muted:#98a2b3;--line:#2a3038;
  --accent:#7ea1f0;--good:#4ecfa0;--warn:#e0a44a;--bad:#f2807a;--bar:#5b8ae8;--bar-lb:#3c4a63;--grid:#232833;
  --shadow:0 1px 2px rgba(0,0,0,.4)}
}
[data-theme=light]{--bg:#f6f7f9;--panel:#fff;--ink:#151a21;--muted:#5c6673;--line:#e2e6ec;
  --accent:#2f5fd0;--good:#12805c;--warn:#a35a00;--bad:#b3261e;--bar:#3b6fd4;--bar-lb:#9fb4dd;--grid:#e8ebf1;
  --d1:#3b6fd4;--d2:#2f9d8a;--d3:#618c2c;--d4:#a8791a;--d5:#c2662b;--d6:#c0586f;--d7:#8a6fc0}
[data-theme=dark]{--bg:#11141a;--panel:#181c24;--ink:#e8ecf2;--muted:#98a2b3;--line:#2a3038;
  --accent:#7ea1f0;--good:#4ecfa0;--warn:#e0a44a;--bad:#f2807a;--bar:#5b8ae8;--bar-lb:#3c4a63;--grid:#232833;
  --d1:#6f9ae9;--d2:#4fc0ab;--d3:#a3cd63;--d4:#e5bb52;--d5:#e9a173;--d6:#d98a9c;--d7:#ad93e0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1560px;margin:0 auto;padding:32px 20px 72px}
header.top{display:flex;gap:16px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;margin-bottom:8px}
h1{font-size:26px;line-height:1.2;margin:0 0 6px}
.sub{color:var(--muted);margin:0;max-width:74ch}
h2{font-size:17px;margin:0 0 4px;letter-spacing:.01em}
h3{font-size:14px;margin:22px 0 8px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
section{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px 22px;margin-top:18px;box-shadow:var(--shadow)}
section>p.lede{color:var(--muted);margin:0 0 18px;max-width:90ch}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:14px}
.kpi{border:1px solid var(--line);border-radius:10px;padding:14px 15px;background:transparent}
.kpi .k{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
.kpi .v{font-size:23px;font-weight:600;margin-top:6px;font-variant-numeric:tabular-nums}
.kpi .n{font-size:12.5px;color:var(--muted);margin-top:5px}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:8px 7px;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child,td:first-child{padding-left:12px}
th:last-child,td:last-child{padding-right:12px}
/* The notes column carries tag chips rather than figures, so it may wrap: that
   lets the 12-column results table fit without a horizontal scrollbar. */
#tbl th:last-child,#tbl td:last-child{white-space:normal;min-width:140px}
th{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);
  cursor:pointer;user-select:none;position:sticky;top:0;background:var(--panel);z-index:1}
th.num,td.num{text-align:right}
th:focus-visible,button:focus-visible,a:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
tbody tr:hover{background:color-mix(in oklab,var(--accent) 6%,transparent)}
td .mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px}
.bar{height:9px;border-radius:5px;background:var(--bar);min-width:2px;display:block}
.bar.lb{background:repeating-linear-gradient(135deg,var(--bar-lb) 0 5px,transparent 5px 10px);border:1px solid var(--bar-lb)}
.stack{display:flex;height:20px;border-radius:5px;overflow:hidden;background:var(--grid);height:18px}
.stack span{display:block;height:100%;min-width:1px}
.swatch{display:inline-block;width:11px;height:11px;border-radius:3px;vertical-align:middle;margin-right:5px}
.chart{display:grid;gap:6px;margin-top:6px}
.row{display:grid;grid-template-columns:minmax(140px,240px) 1fr minmax(92px,auto);gap:10px;align-items:center}
.row .lbl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13.5px}
.row .val{text-align:right;font-variant-numeric:tabular-nums;font-size:13px;color:var(--ink)}
.track{position:relative;background:var(--grid);border-radius:5px;height:20px}
.track .bar{height:20px}
.axis{font-size:12px;color:var(--muted);margin-top:8px;display:flex;justify-content:space-between}
.scale{display:flex;gap:8px;align-items:center;margin:10px 0 6px;font-size:12.5px;color:var(--muted)}
.scale button{padding:4px 11px;font-size:12.5px;border-radius:999px}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:12.5px;color:var(--muted);margin-top:10px}
.legend i{display:inline-block;width:22px;height:9px;border-radius:5px;vertical-align:middle;margin-right:6px}
.tag{display:inline-block;font-size:11.5px;padding:1px 7px;border-radius:999px;border:1px solid var(--line);color:var(--muted)}
.tag.ok{color:var(--good);border-color:color-mix(in oklab,var(--good) 40%,var(--line))}
.tag.warn{color:var(--warn);border-color:color-mix(in oklab,var(--warn) 40%,var(--line))}
.tag.free{color:var(--good);border-color:color-mix(in oklab,var(--good) 40%,var(--line))}
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:14px 0}
button,select,input[type=search]{font:inherit;color:var(--ink);background:var(--panel);
  border:1px solid var(--line);border-radius:8px;padding:7px 11px}
button{cursor:pointer}
button:hover{border-color:var(--accent)}
button[aria-pressed=true]{border-color:var(--accent);color:var(--accent)}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:10px}
ul.tight{margin:8px 0 0;padding-left:20px}
ul.tight li{margin:4px 0}
.note{color:var(--muted);font-size:13.5px}
.formula{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px;
  line-height:1.7;background:var(--grid);border:1px solid var(--line);border-radius:8px;
  padding:12px 14px;margin:10px 0 4px;overflow-x:auto;white-space:pre;color:var(--ink)}
.formula b{color:var(--accent);font-weight:600}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px;
  background:var(--grid);padding:1px 5px;border-radius:4px}
.foot{color:var(--muted);font-size:12.5px;margin-top:14px}
@media print{body{background:#fff}section{break-inside:avoid;box-shadow:none}
  .controls,header.top button{display:none}th{position:static}}
@media (max-width:640px){.row{grid-template-columns:1fr 92px;grid-template-areas:"lbl val" "track track"}
  .row .lbl{grid-area:lbl}.row .val{grid-area:val}.row .track{grid-area:track}}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div>
      <h1>Model comparison &mdash; cost, time and value per report</h1>
      <p class="sub">Every model was asked the same thing: produce a professional, self-contained HTML
      report from <code>engine-comparison-summary-data.json</code>. Below is how long each run took and
      what it cost, read from the finished TUI status bar in each directory's screenshot and cross-checked
      against the assistant's own usage log &mdash; then how good the resulting report was, and what
      value that represented for the money and time it took.</p>
    </div>
    <button id="theme" type="button" aria-label="Toggle colour theme">Theme</button>
  </header>

  <section aria-labelledby="h-summary">
    <h2 id="h-summary">Summary</h2>
    <p class="lede" id="lede"></p>
    <div class="kpis" id="kpis"></div>
  </section>

  <section aria-labelledby="h-cost">
    <h2 id="h-cost">Cost per model</h2>
    <p class="lede">Billed cost of the run, as printed on the status bar. Bars start at zero, so their
    length is directly proportional to spend. Prices span four orders of magnitude, so the linear view
    shows how concentrated the money is; switch to the log view to tell the cheap models apart. Bars run
    longest first, and values are printed next to each one.</p>
    <div class="scale" id="scale-cost" role="group" aria-label="Cost chart scale">
      <span>Scale</span>
      <button type="button" data-scale="linear" aria-pressed="true">Linear</button>
      <button type="button" data-scale="log" aria-pressed="false">Log</button>
    </div>
    <div class="chart" id="chart-cost" role="img" aria-label="Billed cost per model"></div>
    <div class="foot" id="foot-cost"></div>
  </section>

  <section aria-labelledby="h-time">
    <h2 id="h-time">Generation time per model</h2>
    <p class="lede">Wall-clock time in the turn that produced the report, on a zero-based axis so bar
    length is directly proportional to time and bars run longest first. Bars with a striped fill and a
    &ge; prefix are <strong>lower bounds</strong>: earlier turns had scrolled off the screen, so the
    visible turns are only part of the run.</p>
    <div class="scale" id="scale-time" role="group" aria-label="Time chart scale">
      <span>Scale</span>
      <button type="button" data-scale="linear" aria-pressed="true">Linear</button>
      <button type="button" data-scale="log" aria-pressed="false">Log</button>
    </div>
    <div class="chart" id="chart-time" role="img" aria-label="Generation time per model"></div>
    <div class="foot" id="foot-time"></div>
    <div class="legend">
      <span><i style="background:var(--bar)"></i>measured turn(s)</span>
      <span><i class="bar lb" style="display:inline-block;width:22px;height:9px"></i>lower bound (earlier turns not visible)</span>
    </div>
  </section>

  <section aria-labelledby="h-scatter">
    <h2 id="h-scatter">Does paying more buy speed?</h2>
    <p class="lede">Time against cost, both on log axes. A tight downward band would mean expensive runs
    were faster; the cloud below is broad, which is the main finding of this comparison.</p>
    <div id="scatter" role="img" aria-label="Scatter plot of cost against generation time"></div>
  </section>

  <section aria-labelledby="h-quality">
    <h2 id="h-quality">Report quality</h2>
    <p class="lede">Each generated report was scored 0&ndash;100 on how well it does the job of a
    benchmark report, from checks a machine can repeat. Two different things are on this page:
    <strong>cost and time</strong> above measure the run, while <strong>quality</strong> measures
    the artifact it produced. They are not the same axis &mdash; the dearest run is not the best
    report.</p>
    <div class="kpis" id="q-kpis"></div>
    <div class="chart" id="chart-quality" role="img" aria-label="Quality score per report"></div>
    <div class="legend" id="q-legend"></div>
    <h3>Rubric</h3>
    <p class="note">Pre-registered weights. Every point traces to a check recorded in
    <code>quality-ratings.json</code>; the evidence column in the table below lists what passed.</p>
    <div class="scroll"><table id="rubric"><thead><tr>
      <th>Dimension</th><th class="num">Weight</th><th>What it rewards</th>
    </tr></thead><tbody id="rubric-body"></tbody></table></div>
    <h3>What this ranking cannot judge</h3>
    <ul class="tight" id="q-caveats"></ul>
  </section>

  <section aria-labelledby="h-roi">
    <h2 id="h-roi">Return on investment</h2>
    <p class="lede">ROI here is <strong>value per unit of investment</strong>, where the value is the
    report's quality score and the investment is money and time. Quality points are not currency, so
    rather than invent a dollar figure the analysis asks the only question a buyer can act on:
    <em>at the quality this run achieved, what was the best deal available?</em> A run's cost is divided
    by the cheapest run that reached at least its quality, and its time by the fastest such run, giving
    an efficiency per axis. That alone is not ROI &mdash; it is normalised within a quality tier, so a
    cheap run that scraped a low bar would score as well as a cheap run that produced a strong report.
    Quality therefore enters again as a <strong>multiplier</strong>: the score is efficiency scaled by
    quality relative to the best achieved, so a report at half the best quality can never exceed 50,
    however little it cost. 100 means the best report at the best available price.</p>
    <div class="kpis" id="roi-kpis"></div>
    <div class="chart" id="chart-roi" role="img" aria-label="ROI efficiency score per run, segmented by factor"></div>
    <div class="legend" id="roi-chart-legend"></div>
    <h3>The value frontier</h3>
    <p class="note">The Pareto frontier holds runs that nothing beats on both axes at once. Every
    expensive run sits <em>inside</em> this frontier: dominated by something cheaper that scored at
    least as well. The chart marks the <strong>union</strong> of the cost and time frontiers
    (<span id="frontier-note"></span>), because a run can be the cheapest at its quality or the
    fastest at it without being both.</p>
    <div class="scroll"><table id="value"><thead><tr>
      <th>Run</th><th class="num">Quality</th><th class="num">Cost</th><th class="num">Time</th>
      <th class="num">$ / quality pt</th><th class="num">Cost vs best</th><th class="num">Time vs best</th>
      <th class="num" title="Quality per dollar alone">ROI $</th>
      <th class="num" title="Quality per dollar and second combined">ROI $+t</th>
      <th>Frontier</th>
    </tr></thead><tbody id="value-body"></tbody></table></div>
    <h3>Quality against cost</h3>
    <p class="lede">Cost on a log axis, quality on a linear one. The shaded frontier runs along the top
    left; points to its right cost more for no better report.</p>
    <div id="roi-scatter" role="img" aria-label="Scatter plot of quality against cost"></div>
    <h3>How the ROI score is calculated</h3>
    <p class="note">Every figure above is derived from a run's own quality score, cost and time, so the
    whole calculation can be re-run from <code>comparison-data.json</code>. Nothing is scored by hand
    and no dollar value is invented for a quality point.</p>
    <div class="formula" role="img" aria-label="ROI formula">attainment      <b>=</b> quality / best quality of any eligible run      (capped at 1)
cost_multiple   <b>=</b> cost / cheapest  run scoring >= this run's quality
time_multiple   <b>=</b> time / fastest   run scoring >= this run's quality
cost_efficiency <b>=</b> min(1, 1 / cost_multiple)      time_efficiency <b>=</b> min(1, 1 / time_multiple)

ROI $     <b>=</b> 100 &times; attainment &times; cost_efficiency
ROI $+t   <b>=</b> 100 &times; attainment &times; time_efficiency
ROI score <b>=</b> &radic;(ROI $ &times; ROI $+t)          &mdash; the headline, and the factor columns are its parts</div>
    <ul class="tight" id="roi-method"></ul>
    <p class="note">The score is capped at 100, quality is this project's rubric rather than a human
    judgement, and the money figures are one provider's list prices for one run each &mdash; not a
    negotiated rate or a throughput benchmark.</p>
    <h3>Caveats that change the recommendation</h3>
    <ul class="tight" id="roi-caveats"></ul>
  </section>

  <section aria-labelledby="h-table">
    <h2 id="h-table">Full results</h2>
    <p class="lede">Click any column heading to sort; the filter narrows by name. Cost and time come
    from the screenshots, quality from the generated report, ROI from both.</p>
    <div class="controls">
      <input type="search" id="q" placeholder="Filter by model or provider" aria-label="Filter models">
      <button id="f-all" type="button" aria-pressed="true">All</button>
      <button id="f-one" type="button" aria-pressed="false">One prompt</button>
      <button id="f-multi" type="button" aria-pressed="false">More than one</button>
    </div>
    <div class="scroll"><table id="tbl">
      <thead><tr>
        <th data-k="model">Model</th><th data-k="provider">Provider</th>
        <th data-k="effort">Effort</th><th data-k="quality_score" class="num">Quality</th>
        <th data-k="roi_score_cost" class="num" title="Quality per dollar alone">ROI $</th>
        <th data-k="roi_score" class="num" title="Quality per dollar and second">ROI $+t</th>
        <th data-k="prompts_at_least" class="num">Prompts &ge;</th>
        <th data-k="total_elapsed_s" class="num">Time</th>
        <th data-k="total_cost_usd" class="num">Cost</th>
        <th data-k="usage_cost_usd" class="num">Usage log</th>
        <th data-k="cost_per_min_usd" class="num">$ / min</th>
        <th data-k="tokens_per_s" class="num">tok/s</th>
        <th data-k="flags">Notes</th>
      </tr></thead>
      <tbody id="tbody"></tbody>
    </table></div>
    <div class="foot" id="tablenote"></div>
  </section>

  <section aria-labelledby="h-method">
    <h2 id="h-method">Method</h2>
    <h3>Where the numbers come from</h3>
    <ul class="tight">
      <li><strong>Time</strong> &mdash; the <code>Turn N done HH:MM:SS &rarr; HH:MM:SS in XmYYs</code>
        line for each turn, summed across the turns visible in that directory.</li>
      <li><strong>Cost</strong> &mdash; the status-bar total for the session. This figure is
        <em>cumulative</em>, so across several screenshots of one session the largest value is used,
        never a sum.</li>
      <li><strong>Usage log</strong> &mdash; the assistant's own <code>usage.jsonl</code>. Each run was
        matched to its log entry by the wall-clock overlap of the turn window, not by name or price
        (directories were renamed after the runs, so their recorded paths no longer match).</li>
      <li><strong>Quality</strong> &mdash; each attempt's generated report is opened in headless Chrome
        by <code>rate_quality.py</code> and scored against the rubric above; the score and the evidence
        for every check are written to <code>quality-ratings.json</code>. No human judgement is involved
        and no prose is read.</li>
      <li><strong>ROI</strong> &mdash; computed from quality, cost and time by
        <code>build_comparison.py</code>; the formula and its baselines are set out in the ROI section
        above. Every figure on this page is reproducible from <code>comparison-data.json</code>.</li>
    </ul>
    <h3>Reading the caveats</h3>
    <ul class="tight" id="caveats"></ul>
    <h3>What this is not</h3>
    <ul class="tight">
      <li>Not an evaluation of the <em>models</em>, only of these reports. Quality is scored by the
        rubric above and ROI is built from it; neither is a general capability benchmark.</li>
      <li>Not a controlled experiment. Runs are sequential, on one machine, at one effort level, and
        the harness changed between attempts, so treat differences as indicative rather than causal.</li>
      <li>Not exhaustive. Costs come from a single provider's price list at the time of the run.</li>
    </ul>
    <div class="foot" id="provenance"></div>
  </section>
</div>

<script id="data" type="application/json">__COMPARISON_DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const fmtUsd = (v) => v == null ? '&ndash;' : (v < 0.01 ? '$' + v.toFixed(4) : '$' + v.toFixed(2));
const fmtDur = (s) => {
  if (s == null) return '&ndash;';
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = Math.round(s % 60);
  return h ? `${h}h${String(m).padStart(2,'0')}m` : (m ? `${m}m${String(x).padStart(2,'0')}s` : `${x}s`);
};
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

const rows = DATA.models.slice().sort((a, b) => (b.total_cost_usd || 0) - (a.total_cost_usd || 0));

// Two attempt directories can run the same model, which would give two chart rows
// the same caption. Fall back to the (unique) directory name for those.
const NAME_COUNT = rows.reduce((m, r) => (m[r.model] = (m[r.model] || 0) + 1, m), {});
const lbl = (r) => (NAME_COUNT[r.model] > 1 ? r.directory : r.model);

/* Bar length must be proportional to the value it encodes, so the default scale is
   zero-based and linear. The log scale is offered as a toggle only, never as the
   default: on a log axis equal distances are equal ratios, which makes a bar look
   far longer than the value it stands for. */
function linearScale(values) {
  const hi = Math.max(...values.filter((v) => v > 0), 0) || 1;
  return (v) => v <= 0 ? 0 : (v / hi) * 100;
}
function logScale(values) {
  const pos = values.filter((v) => v > 0);
  const lo = Math.min(...pos), hi = Math.max(...pos);
  const span = Math.log10(hi) - Math.log10(lo) || 1;
  return (v) => v <= 0 ? 0 : ((Math.log10(v) - Math.log10(lo)) / span) * 100;
}

/* ---------- KPIs ---------- */
(function kpis() {
  const withCost = rows.filter((r) => r.total_cost_usd != null);
  const withTime = rows.filter((r) => r.total_elapsed_s != null);
  const costs = withCost.map((r) => r.total_cost_usd).sort((a, b) => a - b);
  const times = withTime.map((r) => r.total_elapsed_s).sort((a, b) => a - b);
  const median = (a) => a.length % 2 ? a[(a.length - 1) / 2] : (a[a.length / 2 - 1] + a[a.length / 2]) / 2;
  const totalCost = costs.reduce((a, b) => a + b, 0);
  const totalTime = times.reduce((a, b) => a + b, 0);
  const cheap = withCost[withCost.length - 1];
  const pricey = withCost[0];
  const byTime = withTime.slice().sort((a, b) => a.total_elapsed_s - b.total_elapsed_s);
  const fastest = byTime.find((r) => !r.time_is_lower_bound) || byTime[0];
  const slowest = byTime[byTime.length - 1];
  const providers = [...new Set(rows.map((r) => r.provider).filter(Boolean))];
  const efforts = [...new Set(rows.map((r) => r.effort).filter(Boolean))];
  const gateway = providers.length === 1
    ? `all via ${providers[0]}`
    : `${providers.length} providers`;
  const cards = [
    ['Runs compared', rows.length, `${gateway}, ${efforts.join('/') || 'n/a'} effort`],
    ['Combined cost', fmtUsd(totalCost), `median ${fmtUsd(median(costs))} per run`],
    ['Combined model time', fmtDur(totalTime), `median ${fmtDur(median(times))} per run`],
    ['Cheapest run', fmtUsd(cheap.total_cost_usd), esc(cheap.model)],
    ['Most expensive', fmtUsd(pricey.total_cost_usd), `${esc(pricey.model)} &mdash; ${(pricey.total_cost_usd / median(costs)).toFixed(0)}&times; the median`],
    ['Fastest run', fmtDur(fastest.total_elapsed_s) + (fastest.time_is_lower_bound ? '+' : ''),
      `${esc(fastest.model)}${fastest.time_is_lower_bound ? ' (a lower bound)' : ''}`],
    ['Slowest run', fmtDur(slowest.total_elapsed_s), esc(slowest.model)],
    ['Single-prompt runs', rows.filter((r) => r.prompts_at_least === 1).length,
      `${rows.filter((r) => r.prompts_at_least > 1).length} needed another prompt`],
  ];
  document.getElementById('kpis').innerHTML = cards.map(([k, v, n]) =>
    `<div class="kpi"><div class="k">${k}</div><div class="v">${v}</div><div class="n">${n}</div></div>`).join('');

  const paid = withCost.filter((r) => !r.free_tier);
  const paidLo = paid[paid.length - 1], paidHi = paid[0];
  document.getElementById('lede').innerHTML =
    `${rows.length} runs produced a report for a combined <strong>${fmtUsd(totalCost)}</strong> and
     <strong>${fmtDur(totalTime)}</strong> of model time. Cost tracks the model's price far more than
     the size of the job: among paid runs the cheapest was <strong>${fmtUsd(paidLo.total_cost_usd)}</strong>
     (${esc(paidLo.model)}) and the dearest <strong>${fmtUsd(paidHi.total_cost_usd)}</strong>
     (${esc(paidHi.model)}) &mdash; a
     <strong>${Math.round(paidHi.total_cost_usd / paidLo.total_cost_usd)}&times;</strong> spread, with one
     free-tier run at ${fmtUsd(cheap.total_cost_usd)} beyond it. Higher spend bought no reliable speed:
     see the scatter below.`;
})();

/* ---------- Bar charts ---------- */
function barChart(el, footEl, groupEl, key, fmt, lowerKey) {
  /* Rank each chart by the quantity it draws, longest first. Charts used to inherit
     the cost-sorted rows, which left the time chart in cost order and reading as
     unsorted. Ties keep that cost order. */
  const items = rows.filter((r) => r[key] != null)
    .sort((a, b) => b[key] - a[key]);
  const vals = items.map((r) => r[key]);
  const unit = key === 'total_cost_usd' ? 'dollars' : 'seconds';
  const modes = {
    linear: { pct: linearScale(vals),
      foot: 'Linear, zero-based axis &mdash; bar length is proportional to the value.' },
    log: { pct: logScale(vals),
      foot: `Log axis &mdash; equal distances are equal ratios, not equal ${unit}.` },
  };
  const buttons = [...groupEl.querySelectorAll('button[data-scale]')];
  function draw(mode) {
    const m = modes[mode];
    el.innerHTML = items.map((r) => {
      const lb = lowerKey && r[lowerKey];
      const label = (lb ? '&ge;&thinsp;' : '') + fmt(r[key]);
      return `<div class="row" title="${esc(lbl(r))}: ${label}">
      <span class="lbl">${esc(lbl(r))}</span>
      <span class="track"><span class="bar${lb ? ' lb' : ''}" style="width:${m.pct(r[key]).toFixed(2)}%"></span></span>
      <span class="val">${label}</span></div>`;
    }).join('');
    footEl.innerHTML = m.foot;
    buttons.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.scale === mode)));
  }
  buttons.forEach((b) => b.addEventListener('click', () => draw(b.dataset.scale)));
  draw('linear');
}
barChart(document.getElementById('chart-cost'), document.getElementById('foot-cost'),
  document.getElementById('scale-cost'), 'total_cost_usd', fmtUsd);
barChart(document.getElementById('chart-time'), document.getElementById('foot-time'),
  document.getElementById('scale-time'), 'total_elapsed_s', fmtDur, 'time_is_lower_bound');

/* ---------- Scatter ---------- */
(function scatter() {
  const pts = rows.filter((r) => r.total_cost_usd > 0 && r.total_elapsed_s > 0);
  const W = 900, H = 380, P = 52;
  const lx = (v) => Math.log10(v), ly = (v) => Math.log10(v);
  const xs = pts.map((r) => lx(r.total_cost_usd)), ys = pts.map((r) => ly(r.total_elapsed_s));
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const px = (v) => P + ((lx(v) - x0) / (x1 - x0)) * (W - P * 1.4);
  const py = (v) => H - P - ((ly(v) - y0) / (y1 - y0)) * (H - P * 1.6);
  const dots = pts.map((r) => {
    const lb = r.time_is_lower_bound;
    return `<circle cx="${px(r.total_cost_usd).toFixed(1)}" cy="${py(r.total_elapsed_s).toFixed(1)}"
      r="4.5" fill="${lb ? 'none' : 'var(--bar)'}" stroke="var(--bar)" stroke-width="1.6"
      ${lb ? 'stroke-dasharray="2 2"' : ''}><title>${esc(r.model)}: ${fmtUsd(r.total_cost_usd)}, ${fmtDur(r.total_elapsed_s)}${lb ? ' (lower bound)' : ''}</title></circle>`;
  }).join('');
  const ticks = (v) => `<line x1="${px(v).toFixed(1)}" y1="${P * .4}" x2="${px(v).toFixed(1)}" y2="${H - P}" stroke="var(--grid)"/>`;
  const grid = [0.01, 0.1, 1, 10].filter((v) => v >= Math.pow(10, x0) && v <= Math.pow(10, x1)).map(ticks).join('');
  document.getElementById('scatter').innerHTML =
    `<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px;height:auto" role="presentation">
      ${grid}
      <line x1="${P}" y1="${H - P}" x2="${W - 8}" y2="${H - P}" stroke="var(--line)"/>
      <line x1="${P}" y1="${P * .4}" x2="${P}" y2="${H - P}" stroke="var(--line)"/>
      ${dots}
      <text x="${W / 2}" y="${H - 8}" text-anchor="middle" font-size="12" fill="var(--muted)">cost (log scale)</text>
      <text x="12" y="${H / 2}" text-anchor="middle" font-size="12" fill="var(--muted)"
        transform="rotate(-90 12 ${H / 2})">time (log scale)</text>
     </svg>
     <div class="legend"><span>solid &mdash; full turn visible</span>
     <span>hollow &mdash; lower bound</span></div>`;
})();

/* ---------- Quality ratings ---------- */
const QUAL = (DATA.quality_sources && DATA.quality_sources.ratings) || DATA.quality || [];
const QBY = Object.fromEntries(QUAL.map((q) => [q.directory, q]));
const DIMS = [
  ['data_fidelity', 'Correctness', 20, '--d1',
   'Embeds the dataset, renders known figures unchanged, no console errors.'],
  ['coverage', 'Completeness', 18, '--d2',
   'Both suites, single-node and cluster, per-query detail.'],
  ['analysis', 'Analysis', 18, '--d3',
   'Key findings, ratio/baseline comparisons, win counts, a method section.'],
  ['caveats', 'Caveats', 14, '--d4',
   'States limitations; separates canonical from reported time; flags source markers.'],
  ['presentation', 'Presentation', 12, '--d5',
   'Charts, large tables, dark mode, print styles, responsive layout.'],
  ['usability', 'Ease of use', 10, '--d6',
   'Navigation, sorting, filtering, drill-down, accessible controls.'],
  ['provenance', 'Provenance', 8, '--d7',
   'Keeps the builder, template, hashes, README and tests alongside the report.'],
];
(function quality() {
  const el = document.getElementById('chart-quality');
  if (!Object.keys(QBY).length) {
    el.innerHTML = '<p class="note">No quality ratings found. Run <code>rate_quality.py</code>.</p>';
    return;
  }
  const R = Object.values(QBY).slice().sort((a, b) => b.score - a.score);
  const scores = R.map((r) => r.score);
  const median = scores.length % 2 ? scores[(scores.length - 1) / 2]
    : (scores[scores.length / 2 - 1] + scores[scores.length / 2]) / 2;
  const best = R[0], worst = R[R.length - 1];
  const s = DATA.quality_stats || {};

  const cards = [
    ['Reports rated', R.length, 'one per attempt directory'],
    ['Median quality', median.toFixed(1) + '<span class="note">/100</span>',
      `range ${worst.score.toFixed(1)}&ndash;${best.score.toFixed(1)}`],
    ['Best report', best.score.toFixed(1), esc(best.directory)],
    ['Weakest report', worst.score.toFixed(1), esc(worst.directory)],
  ];
  if (s.cheapest_third_median_quality != null) {
    cards.push(['Cheapest third of runs', s.cheapest_third_median_quality.toFixed(1),
      `median cost $${s.cheapest_third_median_cost} &rarr; median quality ${s.cheapest_third_median_quality}`]);
    cards.push(['Dearest third of runs', s.dearest_third_median_quality.toFixed(1),
      `median cost $${s.dearest_third_median_cost} &rarr; median quality ${s.dearest_third_median_quality}`]);
  }
  document.getElementById('q-kpis').innerHTML = cards.map(([k, v, n]) =>
    `<div class="kpi"><div class="k">${k}</div><div class="v">${v}</div><div class="n">${n}</div></div>`).join('');

  el.innerHTML = R.map((r) => {
    const segs = DIMS.map(([key, , max, colour]) =>
      `<span style="width:${(r.breakdown[key] / 100 * 100).toFixed(2)}%;background:var(${colour})"
        title="${key}: ${r.breakdown[key]}/${max}"></span>`).join('');
    return `<div class="row" title="${esc(r.directory)}: ${r.score}/100">
      <span class="lbl">${esc(r.directory)}</span>
      <span class="track"><span class="stack">${segs}</span></span>
      <span class="val">${r.score.toFixed(1)}</span></div>`;
  }).join('');

  document.getElementById('q-legend').innerHTML = DIMS.map(([, name, max, colour]) =>
    `<span><i class="swatch" style="background:var(${colour})"></i>${name} <span class="note">${max}</span></span>`).join('');

  document.getElementById('rubric-body').innerHTML = DIMS.map(([, name, max, colour, desc]) =>
    `<tr><td><i class="swatch" style="background:var(${colour})"></i>${name}</td>
     <td class="num">${max}</td><td class="note">${desc}</td></tr>`).join('');

  const worstDims = DIMS.map(([key, name, max]) => {
    const avg = R.reduce((a, r) => a + r.breakdown[key], 0) / R.length;
    return [name, avg, max];
  }).sort((a, b) => (a[1] / a[2]) - (b[1] / b[2]));
  const c = [];
  const noRun = Object.keys(QBY).filter((d) => !rows.some((r) => r.directory === d));
  if (noRun.length) {
    c.push(`<strong>${noRun.length} report is scored but has no time or cost</strong>
      (${noRun.map(esc).join(', ')}): the directory holds a generated report but no screenshot, so it
      appears in the quality chart (${R.length} reports) and not in the run table (${rows.length} runs).`);
  }
  c.push(`<strong>Scores are structural, not aesthetic.</strong> They measure whether the report
    does the job of a benchmark report &mdash; data fidelity, coverage, analysis, caveats, presentation,
    navigation and provenance. Visual taste, prose quality and whether the conclusions are
    <em>interesting</em> need a human looking at the rendering, and are deliberately not scored.`);
  if (s.spearman_cost_quality != null) {
    const dir = s.spearman_cost_quality > 0 ? 'more' : 'less';
    c.push(`<strong>Spend and quality move together, weakly.</strong> Spearman rank correlation between
      a run's cost and its report quality is <strong>${s.spearman_cost_quality}</strong> (n=${s.n}), and
      between time and quality <strong>${s.spearman_time_quality}</strong>: runs that cost ${dir} and ran
      longer tended to score higher. Cheap runs still produced strong reports &mdash; the cheapest third
      reached a median ${s.cheapest_third_median_quality} against ${s.dearest_third_median_quality} for
      the dearest third. This is correlational, not causal: cost largely reflects the provider's
      price list, and runs are sequential on one machine.`);
    c.push(`<strong>Part of the time&ndash;quality link is definitional.</strong> This rubric rewards
      completeness and interactive features, and building more of those takes more turns; so "longer runs
      scored higher" is partly a restatement of the rubric rather than an independent finding.`);
  }
  c.push(`<strong>The weakest dimension across the corpus is ${worstDims[0][0].toLowerCase()}</strong>
    (mean ${worstDims[0][1].toFixed(1)}/${worstDims[0][2]}), and the strongest is
    ${worstDims[worstDims.length - 1][0].toLowerCase()}
    (mean ${worstDims[worstDims.length - 1][1].toFixed(1)}/${worstDims[worstDims.length - 1][2]}).`);
  c.push(`<strong>Rubric limits.</strong> The figure probes accept any legitimate rounding, but a report
    that shows cluster results only as ratios, without cluster elapsed or CPU-hour figures, still loses
    that check. Prose is not read, so a confidently wrong sentence scores the same as a correct one
    unless it changes a number or drops a section.`);
  document.getElementById('q-caveats').innerHTML = c.map((x) => `<li>${x}</li>`).join('');
})();

/* ---------- ROI ---------- */
(function roi() {
  const R = DATA.roi || { stats: {} };
  const by = Object.fromEntries(rows.map((r) => [r.directory, r]));
  const ranked = (R.models || []).map((d) => by[d]).filter((r) => r && r.roi_score != null);
  const s = R.stats || {};
  if (!ranked.length) {
    document.getElementById('roi-kpis').innerHTML =
      '<p class="note">No ROI data. Run build_comparison.py.</p>';
    return;
  }

  const cards = [
    ['Best value (money + time)', s.best_roi_score == null ? '&ndash;' : s.best_roi_score + '<span class="note">/100</span>',
      `${esc(s.best_roi || '')} &mdash; best report at the best price`],
    ['Best value (money only)', s.best_roi_cost_score == null ? '&ndash;' : s.best_roi_cost_score + '<span class="note">/100</span>',
      s.best_roi_cost === s.best_roi
        ? `${esc(s.best_roi_cost || '')} &mdash; same winner; ranking differs below`
        : esc(s.best_roi_cost || '')],
    ['Best report overall', by[s.best_roi_at_quality] ? by[s.best_roi_at_quality].quality_score.toFixed(1) : '&ndash;',
      `${esc(s.best_roi_at_quality || '')} &mdash; also the best value, at ROI ${s.best_roi_at_quality_score}/100`],
    ['Median ROI', s.median_roi_cost == null ? '&ndash;' : String(s.median_roi_cost),
      `money only; ${s.median_roi_time} when time counts too`],
    ['Overpaying runs', s.overpaid_count == null ? '&ndash;' : String(s.overpaid_count),
      `&ge;10&times; the going rate; worst ${s.worst_cost_multiple_paid == null ? '?' :
        s.worst_cost_multiple_paid.toFixed(0)}&times; (${esc(s.worst_cost_multiple_paid_model || '')})`],
  ];
  document.getElementById('roi-kpis').innerHTML = cards.map(([k, v, n]) =>
    `<div class="kpi"><div class="k">${k}</div><div class="v">${v}</div><div class="n">${n}</div></div>`).join('');

  const max = Math.max(...ranked.map((r) => r.roi_score));
  const el = document.getElementById('chart-roi');
  const ROI_FACTORS = [
    ['quality_attainment', 'Quality', '--d1'],
    ['cost_efficiency', 'Money', '--d2'],
    ['time_efficiency', 'Speed', '--d5'],
  ];
  // Each factor is a multiplier in (0,1]; the score is their product x 100. Bar
  // length is the score, and the slices are the factor *levels* in proportion, so
  // a factor at full marks shows as the largest slice. An earlier version sized
  // slices by shortfall (|log|), which gave a perfect factor zero width -- the
  // opposite of what "Money: 100%" should look like.
  el.innerHTML = ranked.map((r) => {
    const levels = ROI_FACTORS.map(([key]) => Math.max(0, Number(r[key]) || 0));
    const totalLevel = levels.reduce((a, b) => a + b, 0) || 1;
    const segs = ROI_FACTORS.map(([, name, colour], i) => {
      const width = (levels[i] / totalLevel) * r.roi_score;
      return `<span style="width:${width.toFixed(2)}%;background:var(${colour})"
        title="${name}: ${(levels[i] * 100).toFixed(0)}% of full marks"></span>`;
    }).join('');
    return `<div class="row" title="${esc(lbl(r))}: ROI ${r.roi_score}/100">
      <span class="lbl">${esc(lbl(r))}</span>
      <span class="track"><span class="stack">${segs}</span></span>
      <span class="val">${r.roi_score}</span></div>`;
  }).join('');
  const legend = document.getElementById('roi-chart-legend');
  if (legend) {
    legend.innerHTML = ROI_FACTORS.map(([, name, colour]) =>
      `<span><i class="swatch" style="background:var(${colour})"></i>${name}</span>`).join('') +
      '<span class="note">bar length is the score; slice size shows each factor’s level, ' +
      'so the weakest factor is the thinnest slice</span>';
  }

  const vt = ranked.slice().sort((a, b) => (b.quality_score - a.quality_score) || (a.total_cost_usd - b.total_cost_usd));
  document.getElementById('value-body').innerHTML = vt.map((r) => `<tr>
    <td><span class="mono">${esc(lbl(r))}</span></td>
    <td class="num">${r.quality_score.toFixed(1)}</td>
    <td class="num">${fmtUsd(r.total_cost_usd)}</td>
    <td class="num">${r.time_is_lower_bound ? '&ge;' : ''}${fmtDur(r.total_elapsed_s)}</td>
    <td class="num">${r.usd_per_point == null ? '&ndash;' : '$' + r.usd_per_point.toFixed(5)}</td>
    <td class="num">${r.cost_multiple_paid == null ? '&ndash;' : r.cost_multiple_paid.toFixed(r.cost_multiple_paid < 10 ? 2 : 0) + '&times;'}</td>
    <td class="num">${r.time_multiple == null ? '&ndash;' : r.time_multiple.toFixed(2) + '&times;'}</td>
    <td class="num"><strong>${r.roi_score_cost == null ? '&ndash;' : r.roi_score_cost}</strong></td>
    <td class="num">${r.roi_score == null ? '&ndash;' : r.roi_score}</td>
    <td>${r.pareto_cost ? '<span class="tag ok">cost</span>' : ''}${r.pareto_time ? '<span class="tag ok">time</span>' : ''}</td>
  </tr>`).join('');

  // quality vs cost, log x. Frontier drawn as a step line.
  const W = 900, H = 380, P = 58;
  const pts = ranked.filter((r) => r.total_cost_usd > 0);
  const xs = pts.map((r) => Math.log10(r.total_cost_usd));
  const qs = pts.map((r) => r.quality_score);
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const q0 = Math.min(...qs) - 3, q1 = Math.max(...qs) + 3;
  const px = (c) => P + ((Math.log10(c) - x0) / (x1 - x0)) * (W - P - 16);
  const py = (q) => H - P - ((q - q0) / (q1 - q0)) * (H - P - 22);
  const fr = (R.cost_frontier || []).map((d) => by[d]).filter(Boolean)
    .sort((a, b) => a.total_cost_usd - b.total_cost_usd);
  let step = '';
  if (fr.length) {
    step = `<polyline points="${fr.map((r) => `${px(r.total_cost_usd).toFixed(1)},${py(r.quality_score).toFixed(1)}`).join(' ')}"
      fill="none" stroke="var(--good)" stroke-width="1.5" stroke-dasharray="4 3" opacity=".85"/>`;
  }
  const dots = pts.map((r) => `
    <circle cx="${px(r.total_cost_usd).toFixed(1)}" cy="${py(r.quality_score).toFixed(1)}"
      r="4.5" fill="${r.on_frontier ? 'var(--good)' : 'none'}" stroke="${r.on_frontier ? 'var(--good)' : 'var(--bar)'}"
      stroke-width="1.6" ${r.time_is_lower_bound && !r.on_frontier ? 'stroke-dasharray="2 2"' : ''}>
      <title>${esc(lbl(r))}: quality ${r.quality_score.toFixed(1)}, ${fmtUsd(r.total_cost_usd)}${r.on_frontier ? ' (frontier)' : ''}</title></circle>`).join('');
  document.getElementById('roi-scatter').innerHTML =
    `<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px;height:auto" role="presentation">
      <line x1="${P}" y1="${H - P}" x2="${W - 8}" y2="${H - P}" stroke="var(--line)"/>
      <line x1="${P}" y1="${P * .5}" x2="${P}" y2="${H - P}" stroke="var(--line)"/>
      ${step}${dots}
      <text x="${W / 2}" y="${H - 10}" text-anchor="middle" font-size="12" fill="var(--muted)">cost (log scale)</text>
      <text x="14" y="${H / 2}" text-anchor="middle" font-size="12" fill="var(--muted)"
        transform="rotate(-90 14 ${H / 2})">quality score</text></svg>
     <div class="legend"><span><i style="background:var(--good)"></i>on the value frontier</span>
     <span><i style="background:transparent;border:1.6px solid var(--bar)"></i>dominated &mdash; cheaper runs scored as well</span></div>`;

  const cheapest = rows.slice().sort((a, b) => a.total_cost_usd - b.total_cost_usd)[0];
  const dearest = rows.slice().sort((a, b) => b.total_cost_usd - a.total_cost_usd)[0];
  const best = by[s.best_roi_at_quality];
  const c = [];
  c.push(`<strong>Quality is a multiplier, not a floor.</strong> A run's ceiling is set by how good its
    report was, so a report at half the best quality can never score above 50, however little it cost.
    The cheapest run, <strong>${esc(cheapest.model)}</strong> at ${fmtUsd(cheapest.total_cost_usd)},
    scored ${cheapest.quality_score.toFixed(1)}/100 and is therefore capped near
    ${cheapest.quality_attainment != null ? Math.round(cheapest.quality_attainment * 100) : '?'} &mdash;
    cheap alone no longer wins. (An earlier version treated quality as a bar to clear, which let a cheap
    45.9-quality report out-rank a cheap 86.9-quality one.)`);
  if (s.best_roi_cost && s.best_roi) {
    const sameWinner = s.best_roi_cost === s.best_roi;
    c.push(`<strong>Money alone reorders the field${sameWinner ? '' : ' and changes the winner'}.</strong>
      ${sameWinner
        ? `Both rankings put <strong>${esc(s.best_roi)}</strong> first, because it is both the best report
           and cheap. Below that they diverge: money-only rewards the cheapest quality per dollar, while
           money+time also charges runs for being slow.`
        : `Money-only prefers <strong>${esc(s.best_roi_cost)}</strong>; money+time prefers
           <strong>${esc(s.best_roi)}</strong>.`}
      Pick the axis that matches your constraint &mdash; if your own waiting time is free, the money-only
      column is the honest one.`);
  }
  if (best && dearest && dearest.directory !== best.directory) {
    const factor = dearest.total_cost_usd / best.total_cost_usd;
    const gap = best.quality_score - dearest.quality_score;
    c.push(`<strong>Spending more actively hurt.</strong> The best report
      (<strong>${esc(best.model)}</strong>, ${best.quality_score.toFixed(1)}/100) cost
      ${fmtUsd(best.total_cost_usd)}. The most expensive run
      (<strong>${esc(dearest.model)}</strong>) cost <strong>${factor.toFixed(0)}&times;</strong> as much
      and ${gap >= 0 ? `scored <strong>${gap.toFixed(1)} points lower</strong>` :
        `scored only ${Math.abs(gap).toFixed(1)} points higher`}. Price and quality are not aligned in
      this corpus.`);
  }
  if (s.best_roi && s.best_roi_at_quality && s.best_roi !== s.best_roi_at_quality) {
    const top = by[s.best_roi_at_quality], cheap = by[s.best_roi];
    const gain = cheap ? (top.quality_score - cheap.quality_score).toFixed(1) : '?';
    c.push(`<strong>The best report is not the cheapest run.</strong> ${esc(s.best_roi_at_quality)}
      produced the highest-scoring report at ${fmtUsd(top.total_cost_usd)}, against
      ${cheap ? fmtUsd(cheap.total_cost_usd) : '&ndash;'} for ${esc(s.best_roi)} &mdash; so the extra
      spend bought ${gain} quality points.`);
  }
  c.push(`<strong>Every expensive run is dominated.</strong> ${s.overpaid_count} of ${ranked.length} runs
    spent at least ten times the going rate for the quality they reached; the worst was
    ${s.worst_cost_multiple_paid == null ? '?' : s.worst_cost_multiple_paid.toFixed(0)}&times;
    (${esc(s.worst_cost_multiple_paid_model || '')}).
    ${s.frontier_all_below_median_cost
      ? `The cheapest frontier holds ${s.frontier_size} runs, the dearest at ${fmtUsd(s.frontier_max_cost)}
         against a median run cost of ${fmtUsd(s.median_cost)} &mdash; no run at or above the median cost
         is on it. Counting the fastest-at-each-quality frontier too, ${s.frontier_union_size} of
         ${ranked.length} runs are on one frontier or the other.`
      : `The cheapest frontier holds ${s.frontier_size} runs; the dearest fronts a cost of
         ${fmtUsd(s.frontier_max_cost)}.`}`);
  c.push(`<strong>Doubling the quality does not double the usefulness, but it does double this score.</strong>
    Value is assumed linear in the quality score. If what you actually need is only "good enough to
    publish", read the table by quality first and price second rather than by ROI alone. Cheapest is
    not the same as best: ${esc(s.best_roi || '')} scores highest, and it is not the cheapest run.`);
  c.push(`<strong>One run's time is a lower bound.</strong> Runs whose elapse time is flagged
    <span class="tag warn">time &ge;</span> spent longer than shown, so their time multiple is optimistic
    and their ROI is, if anything, overstated.`);
  const sens = s.sensitivity || {};
  const agree = sens.all_weights_agree !== false;
  c.push(`<strong>Weights are a choice; this score fixes them at one-to-one, then checks.</strong> Money and
    time are combined as an equal-weight geometric mean. Re-weighting between 1:3 and 3:1
    ${agree
      ? `still selects <strong>${esc(sens['cost_weight_0.5'] || s.best_roi || '?')}</strong>, so the pick does
         not depend on how the two costs are traded off.`
      : `changes the pick (speed-favouring: ${esc(sens['cost_weight_0.25'] || '?')};
         cost-favouring: ${esc(sens['cost_weight_0.75'] || '?')}), so state the weighting you were hired to
         optimise before quoting a winner.`} At an even weighting the re-weighted and ROI orderings are
    the same by construction, which is what makes the comparison meaningful.`);
  document.getElementById('roi-caveats').innerHTML = c.map((x) => `<li>${x}</li>`).join('');

  // Method bullets: cite the baselines actually used, so the formula above is
  // checkable against the table rather than a generic restatement.
  const m = [];
  const freeOn = ranked.filter((r) => r.free_tier);
  const noCost = DATA.models.filter((r) => r.quality_score != null && r.total_cost_usd == null);
  m.push(`<strong>A run has to have all three inputs to be scored.</strong>
    ${R.n} of ${DATA.models.length} runs qualified (quality, cost and time all present).
    ${noCost.length ? `${noCost.length} scored report${noCost.length === 1 ? '' : 's'}
      (${noCost.map((r) => esc(r.model)).join(', ')}) ${noCost.length === 1 ? 'is' : 'are'} absent from
      every ROI figure because no screenshot could be read for it &mdash; quality alone cannot buy a
      baseline.` : 'Every scored report also had a readable screenshot.'}`);
  m.push(`<strong>The baseline is the cheapest (or fastest) run at the same quality or better.</strong>
    Not the cheapest run overall: a $0.001 report scoring 40 is not the benchmark for an 88. Requiring
    "at least this quality" is what makes the ratio a like-for-like price. A free-tier run can therefore
    set the floor for <em>time</em>, but is excluded from the cost baseline
    ${freeOn.length ? `&mdash; ${freeOn.map((r) => esc(r.model)).join(', ')} would cut it to near zero` : ''}.`);
  m.push(`<strong>Efficiency is capped at 1, so nothing scores above 100.</strong> A run that was itself
    the best deal available scores efficiency 1; paying 10&times; the going rate scores 0.1. The cap keeps
    a free or instant outlier from inflating a run past "best report, best price".`);
  const w = by[s.best_roi];
  const co = ranked.filter((r) => r.free_tier).length;
  if (w) {
    const cm = w.cost_multiple_paid == null ? null : w.cost_multiple_paid.toFixed(2);
    const tm = w.time_multiple == null ? null : w.time_multiple.toFixed(2);
    m.push(`<strong>Worked example &mdash; the winner, ${esc(w.model)}:</strong> quality
      ${w.quality_score.toFixed(1)} against the best ${s.best_roi_at_quality_score != null && by[s.best_roi_at_quality]
        ? by[s.best_roi_at_quality].quality_score.toFixed(1) : '&ndash;'} gives attainment
      ${w.quality_attainment == null ? '&ndash;' : w.quality_attainment.toFixed(3)}; it cost
      ${fmtUsd(w.total_cost_usd)}${cm ? `, or ${cm}&times; the cheapest run at equal-or-better quality
      (cost efficiency ${w.cost_efficiency.toFixed(3)})` : ''}${tm ? `, and took ${tm}&times; the fastest
      such run (time efficiency ${w.time_efficiency.toFixed(3)})` : ''}. That gives ROI $
      ${w.roi_score_cost} and ROI $+t ${w.roi_score_time}, so the headline is
      &radic;(${w.roi_score_cost} &times; ${w.roi_score_time}) = <strong>${w.roi_score}</strong>.`);
  }
  // The winner is often a 1.00×/1.00× dead heat, which shows nothing about how the
  // factors bite. Name the biggest overpayer as the instructive counter-example.
  const worst = ranked.slice().sort((a, b) => (b.cost_multiple_paid || 0) - (a.cost_multiple_paid || 0))[0];
  if (worst && worst.cost_multiple_paid > 1.05) {
    const lo = ranked.slice().sort((a, b) => a.roi_score - b.roi_score)[0];
    m.push(`<strong>Worked example &mdash; the worst buy, ${esc(worst.model)}:</strong> a strong report at
      quality ${worst.quality_score.toFixed(1)} (attainment ${worst.quality_attainment.toFixed(3)}), but it
      cost ${fmtUsd(worst.total_cost_usd)} &mdash; ${worst.cost_multiple_paid.toFixed(0)}&times; the cheapest
      run at equal-or-better quality, so cost efficiency falls to ${worst.cost_efficiency.toFixed(3)}. High
      quality cannot rescue it: ROI $ is ${worst.roi_score_cost}, and the headline
      ${worst.roi_score}. ${lo && lo.directory !== worst.directory
        ? `The weakest run overall is ${esc(lo.model)} at ${lo.roi_score}.` : ''}`);
  }
  const sens2 = s.sensitivity || {};
  m.push(`<strong>Money and time are combined 1:1, and the weighting is tested.</strong> The headline is
    the geometric mean of the two axes, so the two factor columns multiply out to it. Re-scoring with
    money weighted 1:3, 1:1 and 3:1 ${sens2.all_weights_agree
      ? `selects the same run (<strong>${esc(sens2['cost_weight_0.5'] || s.best_roi || '?')}</strong>),
         so the pick does not hinge on the trade-off you assume.`
      : `changes the pick, so state the trade-off you are paid to optimise.`}
    The weights enter in log space as <code>log(attainment) + w&middot;log(cost_eff) +
    (1&minus;w)&middot;log(time_eff)</code>, which at w=0.5 is exactly the headline ordering.`);
  m.push(`<strong>The frontier is weight-free, and is not the same as the ranking.</strong> Sorting runs
    by cost and keeping each one that beats the best quality seen so far leaves the set that nothing
    beats on both axes at once: ${s.frontier_size} runs by cost, ${s.time_frontier_size} by time,
    ${s.frontier_union_size} of ${R.n} on one or the other. A run can sit on the frontier and still score
    poorly on ROI if it is the only thing at its quality &mdash; the frontier answers "is anything
    better?", ROI answers "how much worse is this?"`);
  document.getElementById('roi-method').innerHTML = m.map((x) => `<li>${x}</li>`).join('');
  const fn = document.getElementById('frontier-note');
  if (fn) {
    fn.textContent = `${s.frontier_union_size} of ${R.n} runs: ${s.frontier_size} cheapest at their quality, `
      + `${s.time_frontier_size} fastest at theirs`;
  }
})();

/* ---------- Table ---------- */
let sortKey = 'total_cost_usd', sortDir = -1, filterMode = 'all';
function flagsOf(r) {
  const t = [];
  if (r.free_tier) t.push('<span class="tag free">free tier</span>');
  if (r.cost_agrees) t.push('<span class="tag ok" title="screenshot cost matches usage.jsonl within $0.01">&check;</span>');
  else if (r.usage_cost_usd != null) t.push('<span class="tag warn" title="screenshot and usage log disagree">&#8800;</span>');
  if (r.time_is_lower_bound) t.push('<span class="tag warn" title="earlier turns scrolled off screen">time &ge;</span>');
  if (r.turn_is_lower_bound) t.push('<span class="tag">turns &ge;</span>');
  return t.join(' ') || '<span class="note">&mdash;</span>';
}
function render() {
  const q = document.getElementById('q').value.trim().toLowerCase();
  let list = rows.filter((r) => {
    if (q && !(`${r.model} ${r.provider}`.toLowerCase().includes(q))) return false;
    if (filterMode === 'one' && r.prompts_at_least !== 1) return false;
    if (filterMode === 'multi' && r.prompts_at_least <= 1) return false;
    return true;
  });
  list.sort((a, b) => {
    const x = a[sortKey], y = b[sortKey];
    if (x == null) return 1; if (y == null) return -1;
    return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y))) * sortDir;
  });
  document.getElementById('tbody').innerHTML = list.map((r) => {
    const q = QBY[r.directory];
    const qcell = q ? `<strong>${q.score.toFixed(1)}</strong>` : '&ndash;';
    const qt = q ? ` title="Correctness ${q.breakdown.data_fidelity}/20 · Coverage ${q.breakdown.coverage}/18 · Analysis ${q.breakdown.analysis}/18 · Caveats ${q.breakdown.caveats}/14 · Presentation ${q.breakdown.presentation}/12 · Ease ${q.breakdown.usability}/10 · Provenance ${q.breakdown.provenance}/8 · from ${esc(q.deliverable || '')}"` : '';
    return `<tr>
    <td><span class="mono">${esc(r.model)}</span></td>
    <td>${esc(r.provider || '&ndash;')}</td>
    <td>${esc(r.effort || '&ndash;')}</td>
    <td class="num"${qt}>${qcell}</td>
    <td class="num">${r.roi_score_cost == null ? '&ndash;' : r.roi_score_cost}</td>
    <td class="num">${r.roi_score == null ? '&ndash;' : r.roi_score}</td>
    <td class="num">${r.prompts_at_least > 1 ? '&ge;' : ''}${r.prompts_at_least}</td>
    <td class="num">${r.time_is_lower_bound ? '&ge;' : ''}${fmtDur(r.total_elapsed_s)}</td>
    <td class="num">${fmtUsd(r.total_cost_usd)}</td>
    <td class="num">${fmtUsd(r.usage_cost_usd)}</td>
    <td class="num">${r.cost_per_min_usd == null ? '&ndash;' : '$' + r.cost_per_min_usd.toFixed(3)}</td>
    <td class="num">${r.tokens_per_s == null ? '&ndash;' : r.tokens_per_s}</td>
    <td>${flagsOf(r)}</td></tr>`;
  }).join('') ||
    '<tr><td colspan="13" class="note">No models match this filter.</td></tr>';
  document.getElementById('tablenote').textContent =
    `Showing ${list.length} of ${rows.length} runs. "$ / min" is the burn rate while the model worked.`;
}
$$('#tbl th').forEach((th) => {
  th.tabIndex = 0;
  const go = () => {
    const k = th.dataset.k;
    sortDir = (sortKey === k) ? -sortDir : (['model', 'provider', 'effort', 'flags'].includes(k) ? 1 : -1);
    sortKey = k; render();
  };
  th.addEventListener('click', go);
  th.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
});
document.getElementById('q').addEventListener('input', render);
[['f-all', 'all'], ['f-one', 'one'], ['f-multi', 'multi']].forEach(([id, mode]) => {
  document.getElementById(id).addEventListener('click', () => {
    filterMode = mode;
    $$('.controls button[id^=f-]').forEach((b) => b.setAttribute('aria-pressed', String(b.id === id)));
    render();
  });
});
render();

/* ---------- Caveats from the data ---------- */
(function caveats() {
  const c = [];
  const lbTime = rows.filter((r) => r.time_is_lower_bound);
  if (lbTime.length) c.push(`<strong>${lbTime.length} of ${rows.length} runs have lower-bound times.</strong>
    In those screenshots the earliest visible turn is not turn 1 &mdash; earlier output had scrolled off
    &mdash; so the figure is a minimum. ${lbTime.map((r) => esc(r.model)).slice(0, 6).join(', ')}${lbTime.length > 6 ? ', &hellip;' : ''}.`);
  const shared = rows.filter((r) => (r.notes || []).some((n) => n.includes('also served other models')));
  if (shared.length) c.push(`<strong>${shared.length} run(s) share a session with another model</strong>
    (${shared.map((r) => esc(r.model)).join(', ')}): the operator switched models mid-session, so the usage-log
    total for those covers more than the one artifact and exceeds the screenshot figure. The screenshot number is
    the better estimate for that run alone.`);
  const disagreements = rows.filter((r) => r.cost_agrees === false && !(r.notes || []).some((n) => n.includes('also served')));
  if (disagreements.length) c.push(`<strong>${disagreements.length} run(s) disagree</strong> between the screenshot
    and the usage log: ${disagreements.map((r) => esc(r.model)).join(', ')}.`);
  c.push(`<strong>Costs are cumulative, not additive.</strong> The status bar shows the running session total, so
    summing several screenshots of one run would overcount; the maximum has been taken instead.`);
  const rejected = rows.filter((r) => (r.notes || []).some((n) => n.includes('OCR decimal loss')));
  if (rejected.length) c.push(`<strong>One OCR misread was corrected:</strong>
    ${rejected.map((r) => esc(r.model)).join(', ')} printed a cost whose decimal point tesseract dropped
    (<code>$0.860</code> read as <code>860</code>). The implausible value was discarded rather than reported.`);
  const dropped = (DATA.excluded || []).map((e) => e.directory);
  if (dropped.length) c.push(`<strong>Excluded:</strong> ${dropped.map(esc).join(', ')} &mdash; no screenshot in the
    directory, so there is no time or cost evidence to read.`);
  const orphans = DATA.unmatched_usage_sessions || [];
  if (orphans.length) c.push(`<strong>${orphans.length} usage-log session(s) match no artifact</strong>
    (${orphans.map((o) => `${esc((o.models || []).join('/'))} at ${o.start}`).join('; ')}). These are the harness
    sessions, an aborted attempt, and a follow-up run; they are reported here rather than folded into any model.`);
  document.getElementById('caveats').innerHTML = c.map((x) => `<li>${x}</li>`).join('');
  const s = DATA.sources || {};
  document.getElementById('provenance').innerHTML =
    `Source: ${s.screenshots} screenshots across ${s.directories} directories, read with
     ${esc(s.ocr || 'tesseract')}. Usage log: <code>${esc(s.usage_jsonl || '')}</code>.
     Metrics digest <code>${esc((s.metrics_sha256 || '').slice(0, 16))}&hellip;</code>.`;
})();

/* ---------- Theme ---------- */
(function theme() {
  const b = document.getElementById('theme');
  const saved = localStorage.getItem('mc-theme');
  if (saved) document.documentElement.dataset.theme = saved;
  b.addEventListener('click', () => {
    const cur = document.documentElement.dataset.theme
      || (matchMedia('(prefers-color-scheme:dark)').matches ? 'dark' : 'light');
    const next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem('mc-theme', next);
  });
})();
</script>
</body>
</html>
"""


def render(payload: dict) -> str:
    """Inline the comparison payload into the standalone document."""
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    data = data.replace("</", "<\\/").replace("<!--", "<\\!--")
    sources = json.dumps(payload.get("sources", {}), separators=(",", ":"), ensure_ascii=False)
    html = DOCUMENT.replace(PLACEHOLDER, data)
    html = html.replace(HASH_PLACEHOLDER, sources)
    return html
