#!/usr/bin/env python3
"""Generate a self-contained HTML benchmark report from engine-comparison-summary-data.json."""

import json
from datetime import datetime

with open("../engine-comparison-summary-data.json") as f:
    data = json.load(f)

ENGINES = data["engines"]

def fmt_time(s):
    if s is None: return "—"
    if s < 1: return f"{s*1000:.0f}ms"
    if s < 60: return f"{s:.2f}s"
    if s < 3600:
        m, sec = divmod(s, 60)
        return f"{int(m)}m {sec:.0f}s"
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{int(h)}h {int(m)}m {sec:.0f}s"

def fmt_ratio(r):
    if r is None: return "—"
    if r < 1: return f"{1/r:.1f}× faster"
    if r == 1: return "1.00×"
    return f"{r:.1f}× slower"

def ratio_class(r):
    if r is None: return ""
    if r < 0.95: return "good"
    if r <= 1.05: return ""
    if r <= 2: return "warn"
    return "bad"

def pill(time_s, ratio=None):
    rc = ratio_class(ratio)
    ts = fmt_time(time_s)
    return f'<span class="pill {rc}">{ts}</span>'

# ── TPC-H totals ─────────────────────────────────────────────────────
tpc_h_rows = ""
for sf in ["1", "10", "100", "1000"]:
    entries = [e for e in data["totals"]["TPC-H"] if e["sf"] == sf]
    entries.sort(key=lambda e: ENGINES.index(e["engine"]) if e["engine"] in ENGINES else 99)
    cells = "".join(pill(e["time"], e.get("ratio")) for e in entries)
    tpc_h_rows += f"<tr><td><strong>SF {sf}</strong></td>{cells}</tr>\n"

# ── TPC-DS totals ────────────────────────────────────────────────────
tpc_ds_rows = ""
for sf in ["1", "10", "100", "1000"]:
    entries = [e for e in data["totals"]["TPC-DS"] if e["sf"] == sf]
    entries.sort(key=lambda e: ENGINES.index(e["engine"]) if e["engine"] in ENGINES else 99)
    cells = "".join(pill(e["time"], e.get("ratio")) for e in entries)
    tpc_ds_rows += f"<tr><td><strong>SF {sf}</strong></td>{cells}</tr>\n"

# ── Cluster comparison ───────────────────────────────────────────────
cluster_rows = ""
for sf in ["100", "1000", "10000"]:
    entries = data["cluster"][sf]
    r_entry = next((e for e in entries if "Spark Rust" in e["engine"] and "Gluten" not in e.get("engine_extra", "")), None)
    g_entry = next((e for e in entries if "Gluten" in e["engine"]), None)
    if r_entry and g_entry:
        r_time, g_time = r_entry["time"], g_entry["time"]
        ratio = g_time / r_time if r_time else None
        rc = ratio_class(ratio) if ratio else ""
        cluster_rows += f"""<tr>
            <td><strong>SF {sf}</strong></td>
            <td>{fmt_time(r_time)}</td>
            <td>{fmt_time(g_time)}</td>
            <td><span class="pill {rc}">{fmt_ratio(ratio) if ratio else '—'}</span></td>
            <td>{r_entry.get('cpuHours', 0):.1f}</td>
            <td>{g_entry.get('cpuHours', 0):.1f}</td>
            <td>{r_entry.get('memHours', 0):.1f}</td>
            <td>{g_entry.get('memHours', 0):.1f}</td>
        </tr>"""

# ── Wins ─────────────────────────────────────────────────────────────
wins_rows = ""
for sf in ["100", "1000", "10000"]:
    w = data["wins"][sf]
    wins_rows += f"<tr><td><strong>SF {sf}</strong></td><td>{w[0]}</td><td>{w[1]}</td></tr>"

# ── Hardware ─────────────────────────────────────────────────────────
hw = data["hardware"]
single_hw = hw.get("single_node", {})
cluster_hw = hw.get("cluster_workers", {})

# ── Embed data as JSON for client-side rendering ─────────────────────
single_json = json.dumps(data["single"])
cluster_q_json = json.dumps(data["clusterQueries"])

# ── CSS ──────────────────────────────────────────────────────────────
CSS = """<style>
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
  --bad: #e88aa0; --bad-soft: #421821;
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
.wrap { max-width: 1200px; margin: 0 auto; padding: 48px 32px 96px; }
a { color: var(--accent); }
:focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
img, svg { max-width: 100%; }
.table-scroll { max-width: 100%; overflow-x: auto; }
h1 { font-size: 33px; font-weight: 700; letter-spacing: -0.015em; line-height: 1.18; margin: 0 0 8px; }
h2 { font-size: 23px; font-weight: 700; margin: 56px 0 16px; padding-bottom: 8px;
     border-bottom: 2px solid var(--border-soft); scroll-margin-top: 20px; }
h3 { font-size: 18px; font-weight: 650; margin: 32px 0 10px; }
p { margin: 0 0 16px; }
.eyebrow { font-size: 12px; text-transform: uppercase; letter-spacing: 0.12em;
           color: var(--accent); font-weight: 600; margin-bottom: 10px; }
.subtitle { color: var(--fg-soft); font-size: 17px; max-width: 820px; }
.meta { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 16px;
        color: var(--fg-mute); font-size: 13px; align-items: center; }
.card { background: var(--bg-card); border: 1px solid var(--border);
        border-radius: var(--radius); padding: 22px 24px; }
.grid { display: grid; gap: 18px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr)); }
.grid-2 { display: grid; gap: 18px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 400px), 1fr)); }
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
table { width: 100%; border-collapse: collapse; margin: 18px 0; font-size: 14px; }
th, td { text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--border-soft); }
thead th { font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em;
           color: var(--fg-mute); border-bottom: 2px solid var(--border);
           position: sticky; top: 0; background: var(--bg); z-index: 1; }
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
                padding: 6px 12px; font-size: 13px; cursor: pointer; z-index: 100; }
.bar-wrap { display: flex; align-items: center; gap: 8px; margin: 4px 0; }
.bar-label { font-size: 12px; color: var(--fg-mute); min-width: 100px; text-align: right; }
.bar-track { flex: 1; height: 20px; background: var(--bg-soft); border-radius: 4px; overflow: hidden; position: relative; }
.bar-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
.bar-val { font-size: 12px; color: var(--fg-soft); min-width: 70px; font-variant-numeric: tabular-nums; }
.controls { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin: 16px 0; }
.controls select { padding: 6px 12px; border: 1px solid var(--border);
    border-radius: 6px; background: var(--bg-card); color: var(--fg); font-size: 14px; }
.controls label { font-size: 13px; color: var(--fg-mute); }
.status-pass { color: var(--good); font-weight: 600; }
.status-gap { color: var(--warn); font-weight: 600; }
.status-fail { color: var(--bad); font-weight: 600; }
@media (max-width: 768px) {
  .wrap { padding: 32px 16px 64px; }
  h1 { font-size: 27px; }
  .bar-label { min-width: 60px; font-size: 11px; }
  .bar-val { min-width: 50px; font-size: 11px; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; scroll-snap-type: none; }
  .bar-fill { transition: none; }
}
</style>"""

# ── JavaScript ───────────────────────────────────────────────────────
JS_TEMPLATE = """<script>
var SINGLE_DATA = __SINGLE_JSON__;
var CLUSTER_QUERY_DATA = __CLUSTER_Q_JSON__;
var ENGINES = __ENGINES_JSON__;

function fmtTime(s) {
  if (s == null) return '\u2014';
  if (s < 1) return Math.round(s*1000)+'ms';
  if (s < 60) return s.toFixed(2)+'s';
  if (s < 3600) { var m=Math.floor(s/60), sec=Math.round(s%60); return m+'m '+sec+'s'; }
  var h=Math.floor(s/3600), rem=s%3600, m=Math.floor(rem/60), sec=Math.round(rem%60);
  return h+'h '+m+'m '+sec+'s';
}

function fmtRatio(r) {
  if (r == null) return '\u2014';
  if (r < 1) return (1/r).toFixed(1)+'\u00d7 faster';
  if (r === 1) return '1.00\u00d7';
  return r.toFixed(1)+'\u00d7 slower';
}

function ratioClass(r) {
  if (r == null) return '';
  if (r < 0.95) return 'good';
  if (r <= 1.05) return '';
  if (r <= 2) return 'warn';
  return 'bad';
}

function pillHtml(time, ratio) {
  var rc = ratioClass(ratio);
  return '<span class="pill '+rc+'">'+fmtTime(time)+'</span>';
}

function renderSingleQueries() {
  var bench = document.getElementById('benchmark-select').value;
  var sf = document.getElementById('sf-select').value;
  var sort = document.getElementById('sort-select').value;
  var queries = SINGLE_DATA[bench][sf] || [];
  var tbody = document.getElementById('single-query-body');
  var chartDiv = document.getElementById('single-bar-chart');

  var rows = queries.slice();

  if (sort === 'duckdb-asc') {
    rows.sort(function(a,b) { return a.times[2] - b.times[2]; });
  } else if (sort === 'duckdb-desc') {
    rows.sort(function(a,b) { return b.times[2] - a.times[2]; });
  } else if (sort === 'ratio-desc') {
    rows.sort(function(a,b) {
      var ra = a.times[2] > 0 ? a.times[4] / a.times[2] : 0;
      var rb = b.times[2] > 0 ? b.times[4] / b.times[2] : 0;
      return rb - ra;
    });
  }

  var html = '';
  for (var i = 0; i < rows.length; i++) {
    var q = rows[i];
    var duckdb = q.times[2];
    html += '<tr><td><strong>Q'+q.q+'</strong></td>';
    for (var j = 0; j < 5; j++) {
      var ratio = duckdb > 0 ? q.times[j] / duckdb : null;
      html += '<td>'+pillHtml(q.times[j], ratio)+'</td>';
    }
    html += '</tr>';
  }
  tbody.innerHTML = html;

  var top15 = queries.slice().sort(function(a,b) { return b.times[2] - a.times[2]; }).slice(0, 15);
  var maxTime = top15[0] ? top15[0].times[2] : 1;
  var chartHtml = '<h3>Top Queries by DuckDB Time (SF '+sf+', '+bench+')</h3>';
  for (var k = 0; k < top15.length; k++) {
    var qq = top15[k];
    var pct = (qq.times[2] / maxTime * 100).toFixed(1);
    chartHtml += '<div class="bar-wrap">'+
      '<div class="bar-label">Q'+qq.q+'</div>'+
      '<div class="bar-track"><div class="bar-fill" style="width:'+pct+'%;background:var(--good)"></div></div>'+
      '<div class="bar-val">'+fmtTime(qq.times[2])+'</div>'+
      '</div>';
  }
  chartDiv.innerHTML = chartHtml;
}

function renderClusterQueries() {
  var sf = document.getElementById('cluster-sf-select').value;
  var sort = document.getElementById('cluster-sort-select').value;
  var queries = CLUSTER_QUERY_DATA[sf] || [];
  var tbody = document.getElementById('cluster-query-body');

  var rows = queries.slice();
  if (sort === 'ratio-asc') {
    rows.sort(function(a,b) { return (a.ratio||0) - (b.ratio||0); });
  } else if (sort === 'ratio-desc') {
    rows.sort(function(a,b) { return (b.ratio||0) - (a.ratio||0); });
  } else if (sort === 'diff-asc') {
    rows.sort(function(a,b) { return (a.diff||0) - (b.diff||0); });
  }

  var html = '';
  for (var i = 0; i < rows.length; i++) {
    var q = rows[i];
    var statusCls = q.status === 'pass' ? 'status-pass' : (q.status === 'gap' ? 'status-gap' : 'status-fail');
    var diffStr = q.diff != null ? (q.diff < 0 ? q.diff.toFixed(2)+'s' : '+'+q.diff.toFixed(2)+'s') : '\u2014';
    html += '<tr>'+
      '<td><strong>Q'+q.q+'</strong></td>'+
      '<td>'+fmtTime(q.r)+'</td>'+
      '<td>'+fmtTime(q.g)+'</td>'+
      '<td>'+diffStr+'</td>'+
      '<td>'+fmtRatio(q.ratio)+'</td>'+
      '<td>'+(q.cpu ? q.cpu[0].toFixed(1) : '\u2014')+'</td>'+
      '<td>'+(q.cpu ? q.cpu[1].toFixed(1) : '\u2014')+'</td>'+
      '<td>'+(q.memory ? q.memory[0].toFixed(1) : '\u2014')+'</td>'+
      '<td>'+(q.memory ? q.memory[1].toFixed(1) : '\u2014')+'</td>'+
      '<td><span class="'+statusCls+'">'+q.status+'</span></td>'+
      '</tr>';
  }
  tbody.innerHTML = html;
}

renderSingleQueries();
renderClusterQueries();
</script>"""

JS = JS_TEMPLATE.replace("__SINGLE_JSON__", single_json)
JS = JS.replace("__CLUSTER_Q_JSON__", cluster_q_json)
JS = JS.replace("__ENGINES_JSON__", json.dumps(ENGINES))

today = datetime.now().strftime('%Y-%m-%d')

HTML = f"""<!DOCTYPE html>
<html lang="en" data-theme="">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Query Engine Benchmark Comparison — TPC-H / TPC-DS</title>
{CSS}
</head>
<body>
<button type="button" class="theme-toggle" aria-label="Toggle color theme" onclick="(function(){{var r=document.documentElement;var d=r.getAttribute('data-theme')==='dark'||(!r.getAttribute('data-theme')&&window.matchMedia('(prefers-color-scheme: dark)').matches);r.setAttribute('data-theme',d?'light':'dark');}})()">◐ theme</button>

<div class="wrap">

<header>
  <div class="eyebrow">Benchmark Report &mdash; {today}</div>
  <h1>Query Engine Performance Comparison</h1>
  <p class="subtitle">TPC-H and TPC-DS benchmarks across five engines: Spark Rust (native), DuckDB, and Apache Spark (JVM + Gluten) at scale factors 1&ndash;10,000.</p>
  <div class="meta">
    <span>Source: <code>{data['source']}</code></span>
    <span>SHA256: <code>{data['sha256'][:12]}</code></span>
  </div>
</header>

<nav class="toc">
  <strong>Contents</strong>
  <a href="#hardware">Hardware Configuration</a>
  <a href="#summary">Executive Summary</a>
  <a href="#tpc-h-totals">TPC-H Totals</a>
  <a href="#tpc-ds-totals">TPC-DS Totals</a>
  <a href="#single-query">Single-Node Query Detail</a>
  <a href="#cluster">Cluster Comparison</a>
  <a href="#cluster-query">Cluster Per-Query Detail</a>
  <a href="#wins">Win/Loss Summary</a>
</nav>

<section>
  <h2 id="hardware">Hardware Configuration</h2>
  <div class="grid-2">
    <div class="card">
      <h3>Single Node</h3>
      <table>
        <tr><td>SKU</td><td><strong>{single_hw.get('sku', '—')}</strong></td></tr>
        <tr><td>Cores</td><td>{single_hw.get('cores', '—')}</td></tr>
        <tr><td>RAM</td><td>{single_hw.get('ram_gb', '—')} GB</td></tr>
      </table>
    </div>
    <div class="card">
      <h3>Cluster Workers</h3>
      <table>
        <tr><td>SKU</td><td><strong>{cluster_hw.get('sku', '—')}</strong></td></tr>
        <tr><td>Count</td><td>{cluster_hw.get('count', '—')} nodes</td></tr>
        <tr><td>Cores / node</td><td>{cluster_hw.get('cores_each', '—')}</td></tr>
        <tr><td>RAM / node</td><td>{cluster_hw.get('ram_gb_each', '—')} GB</td></tr>
        <tr><td>Total cores</td><td><strong>{cluster_hw.get('total_cores', '—')}</strong></td></tr>
        <tr><td>Total RAM</td><td><strong>{cluster_hw.get('total_ram_gb', '—')} GB</strong></td></tr>
      </table>
    </div>
  </div>
</section>

<section>
  <h2 id="summary">Executive Summary</h2>
  <div class="grid">
    <div class="metric">
      <div class="num">5</div>
      <div class="label">Engines tested</div>
    </div>
    <div class="metric">
      <div class="num">2</div>
      <div class="label">Benchmark suites (TPC-H + TPC-DS)</div>
    </div>
    <div class="metric">
      <div class="num">4</div>
      <div class="label">Scale factors (1 → 10,000)</div>
    </div>
    <div class="metric">
      <div class="num">242</div>
      <div class="label">Total query variants</div>
    </div>
  </div>
  <div class="callout good">
    <strong>Key finding:</strong> DuckDB 1.5.5 is the fastest single-node engine across all TPC-H scale factors.
    Spark Rust 0.42.1 (both default and tuned) is within 1&ndash;33% of DuckDB, while JVM-based Spark
    (4.1.1 Gluten and 4.2) is 8&ndash;53× slower at SF&nbsp;1, narrowing to 1.8&ndash;2.3× at SF&nbsp;100.
    In the cluster comparison, Spark Rust leads Spark Gluten at all scale factors.
  </div>
</section>

<section>
  <h2 id="tpc-h-totals">TPC-H Totals (22 queries)</h2>
  <p class="subtitle">Total wall-clock time across all 22 TPC-H queries. Ratios are relative to DuckDB (fastest single-node baseline).</p>
  <div class="table-scroll" tabindex="0" role="region" aria-label="TPC-H totals">
    <table>
      <thead>
        <tr>
          <th>Scale</th>
          <th>Spark Rust<br><small>default</small></th>
          <th>Spark Rust<br><small>tuned</small></th>
          <th>DuckDB 1.5.5</th>
          <th>Spark 4.1.1<br><small>Gluten</small></th>
          <th>Spark 4.2</th>
        </tr>
      </thead>
      <tbody>
        {tpc_h_rows}
      </tbody>
    </table>
  </div>
</section>

<section>
  <h2 id="tpc-ds-totals">TPC-DS Totals (99 queries)</h2>
  <p class="subtitle">Total wall-clock time across all 99 TPC-DS queries.</p>
  <div class="table-scroll" tabindex="0" role="region" aria-label="TPC-DS totals">
    <table>
      <thead>
        <tr>
          <th>Scale</th>
          <th>Spark Rust<br><small>default</small></th>
          <th>Spark Rust<br><small>tuned</small></th>
          <th>DuckDB 1.5.5</th>
          <th>Spark 4.1.1<br><small>Gluten</small></th>
          <th>Spark 4.2</th>
        </tr>
      </thead>
      <tbody>
        {tpc_ds_rows}
      </tbody>
    </table>
  </div>
</section>

<section>
  <h2 id="single-query">Single-Node Query Detail</h2>
  <p class="subtitle">Per-query wall-clock times. Select a benchmark and scale factor to explore individual query performance.</p>

  <div class="controls">
    <label for="benchmark-select">Benchmark:</label>
    <select id="benchmark-select" onchange="renderSingleQueries()">
      <option value="TPC-H">TPC-H</option>
      <option value="TPC-DS">TPC-DS</option>
    </select>
    <label for="sf-select">Scale Factor:</label>
    <select id="sf-select" onchange="renderSingleQueries()">
      <option value="1">SF 1</option>
      <option value="10">SF 10</option>
      <option value="100">SF 100</option>
      <option value="1000">SF 1000</option>
    </select>
    <label for="sort-select">Sort by:</label>
    <select id="sort-select" onchange="renderSingleQueries()">
      <option value="q">Query #</option>
      <option value="duckdb-asc">DuckDB time ↑</option>
      <option value="duckdb-desc">DuckDB time ↓</option>
      <option value="ratio-desc">Slowdown vs DuckDB ↓</option>
    </select>
  </div>

  <div class="table-scroll" tabindex="0" role="region" aria-label="Single-node query detail">
    <table id="single-query-table">
      <thead>
        <tr>
          <th>Q</th>
          <th>Spark Rust<br><small>default</small></th>
          <th>Spark Rust<br><small>tuned</small></th>
          <th>DuckDB 1.5.5</th>
          <th>Spark 4.1.1<br><small>Gluten</small></th>
          <th>Spark 4.2</th>
        </tr>
      </thead>
      <tbody id="single-query-body"></tbody>
    </table>
  </div>

  <div id="single-bar-chart" style="margin-top: 24px;"></div>
</section>

<section>
  <h2 id="cluster">Cluster Comparison: Spark Rust vs Spark 4.1.1 Gluten</h2>
  <p class="subtitle">TPC-DS at scale factors 100, 1,000, and 10,000 on an 8-node cluster (128 cores, 1 TB RAM total).</p>
  <div class="table-scroll" tabindex="0" role="region" aria-label="Cluster comparison">
    <table>
      <thead>
        <tr>
          <th>Scale</th>
          <th>Spark Rust<br><small>time</small></th>
          <th>Spark Gluten<br><small>time</small></th>
          <th>Ratio</th>
          <th>Rust<br><small>CPU·h</small></th>
          <th>Gluten<br><small>CPU·h</small></th>
          <th>Rust<br><small>GB·h</small></th>
          <th>Gluten<br><small>GB·h</small></th>
        </tr>
      </thead>
      <tbody>
        {cluster_rows}
      </tbody>
    </table>
  </div>
</section>

<section>
  <h2 id="cluster-query">Cluster Per-Query Detail</h2>
  <p class="subtitle">Per-query comparison of Spark Rust vs Spark 4.1.1 Gluten on the cluster. <span class="status-pass">pass</span> = Rust faster, <span class="status-gap">gap</span> = Gluten faster, <span class="status-fail">fail</span> = error.</p>

  <div class="controls">
    <label for="cluster-sf-select">Scale Factor:</label>
    <select id="cluster-sf-select" onchange="renderClusterQueries()">
      <option value="100">SF 100</option>
      <option value="1000">SF 1,000</option>
      <option value="10000">SF 10,000</option>
    </select>
    <label for="cluster-sort-select">Sort by:</label>
    <select id="cluster-sort-select" onchange="renderClusterQueries()">
      <option value="q">Query #</option>
      <option value="ratio-asc">Ratio (Rust best) ↑</option>
      <option value="ratio-desc">Ratio (Gluten best) ↓</option>
      <option value="diff-asc">Abs diff (Rust best) ↑</option>
    </select>
  </div>

  <div class="table-scroll" tabindex="0" role="region" aria-label="Cluster per-query detail">
    <table id="cluster-query-table">
      <thead>
        <tr>
          <th>Q</th>
          <th>Rust<br><small>time</small></th>
          <th>Gluten<br><small>time</small></th>
          <th>Diff</th>
          <th>Ratio</th>
          <th>Rust<br><small>CPU</small></th>
          <th>Gluten<br><small>CPU</small></th>
          <th>Rust<br><small>mem</small></th>
          <th>Gluten<br><small>mem</small></th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody id="cluster-query-body"></tbody>
    </table>
  </div>
</section>

<section>
  <h2 id="wins">Win/Loss Summary (Cluster)</h2>
  <p class="subtitle">Number of queries where Spark Rust wins vs Spark 4.1.1 Gluten at each scale factor.</p>
  <div class="table-scroll" tabindex="0" role="region" aria-label="Win/loss summary">
    <table>
      <thead>
        <tr><th>Scale</th><th>Spark Rust wins</th><th>Spark Gluten wins</th></tr>
      </thead>
      <tbody>
        {wins_rows}
      </tbody>
    </table>
  </div>
</section>

<footer style="margin-top: 64px; padding-top: 24px; border-top: 1px solid var(--border-soft); color: var(--fg-mute); font-size: 13px;">
  <p>Generated {today} from <code>{data['source']}</code>. All times are wall-clock seconds unless otherwise noted. Ratios &gt; 1 indicate slowdown relative to the baseline (DuckDB for single-node, Spark Rust for cluster).</p>
</footer>

</div><!-- .wrap -->
{JS}
</body>
</html>"""

with open("engine-comparison-report.html", "w") as f:
    f.write(HTML)
print("Wrote engine-comparison-report.html")