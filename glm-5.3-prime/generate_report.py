#!/usr/bin/env python3
"""Generate a self-contained HTML benchmark report from engine-comparison-summary-data.json.

Usage: python3 generate_report.py
Output: engine-comparison-report.html (single file, no external assets)
"""
import json
import pathlib
from datetime import date

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "engine-comparison-summary-data.json"
OUT = HERE / "engine-comparison-report.html"

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Query Engine Benchmark Comparison — TPC-H &amp; TPC-DS</title>
<meta name="description" content="Self-contained benchmark report comparing five query engines on TPC-H and TPC-DS, single-node and 8-worker cluster, generated from engine-comparison-summary-data.json.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' rx='3' fill='%23131a24'/%3E%3Cpath d='M4 11.5 L8 5 L12 11.5' stroke='%23f59e0b' stroke-width='2' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
<style>
:root{
  --bg:#f5f6f8; --surface:#ffffff; --border:#e3e6eb; --border-strong:#c8cdd6;
  --text:#1c2430; --muted:#5c6675; --faint:#8a93a3;
  --ink:#111827; --rule:#d6dae1;
  --rust:#c2410c; --rust-lite:#fdeee5;
  --amber:#b45309; --amber-fill:#f59e0b;
  --teal:#0e7490; --teal-lite:#e3f2f6;
  --violet:#7c3aed; --violet-lite:#f0eafd;
  --slate:#52606f;
  --good-bg:#e9f5ee; --good-tx:#14532d;
  --bad-bg:#fdeeee; --bad-tx:#8f1d1d;
  --warn-bg:#fdf3e3; --warn-tx:#8a5a0b;
  --mono:ui-monospace,"SF Mono","Cascadia Mono","JetBrains Mono",Menlo,Consolas,monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);
  font-size:15px;line-height:1.55;text-rendering:optimizeLegibility}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px}
a{color:#1d4ed8} a:hover{color:#1e3a8a}
:focus-visible{outline:2px solid #2563eb;outline-offset:2px;border-radius:3px}
h1,h2,h3{color:var(--ink);line-height:1.2;margin:0}
p{margin:.4em 0}
.mono{font-family:var(--mono)}
.muted{color:var(--muted)}
.small{font-size:12.5px}

/* ---------- masthead ---------- */
.masthead{background:linear-gradient(180deg,#10161f 0%,#18222e 100%);color:#e8ecf2;padding:44px 0 34px}
.masthead .kicker{font-size:11.5px;letter-spacing:.18em;text-transform:uppercase;color:#9fb0c3;font-weight:600}
.masthead h1{font-size:clamp(26px,4vw,38px);color:#fff;margin:10px 0 8px;letter-spacing:-.01em}
.masthead .sub{color:#b9c5d3;font-size:16px;max-width:60ch}
.meta-chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}
.chip{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.08);
  border:1px solid rgba(255,255,255,.16);color:#dbe3ec;border-radius:999px;
  padding:4px 12px;font-size:12px}
.chip .k{color:#93a3b5}
.chip code{font-family:var(--mono);font-size:11.5px;color:#f1d59a}

/* ---------- sections ---------- */
section{padding:44px 0 8px}
.sec-head{display:flex;align-items:baseline;gap:14px;border-bottom:1px solid var(--rule);
  padding-bottom:12px;margin-bottom:22px;flex-wrap:wrap}
.sec-num{font-family:var(--mono);font-size:12px;color:var(--faint);letter-spacing:.08em}
.sec-head h2{font-size:clamp(20px,2.6vw,26px);letter-spacing:-.01em}
.sec-sub{flex-basis:100%;color:var(--muted);max-width:88ch;margin:2px 0 0}

/* ---------- cards & KPIs ---------- */
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;
  box-shadow:0 1px 2px rgba(16,22,31,.04)}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}
.kpi{padding:18px 18px 14px;display:flex;flex-direction:column;gap:4px}
.kpi .kpi-val{font-family:var(--mono);font-size:27px;font-weight:700;color:var(--ink);
  letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.kpi .kpi-label{font-size:13px;font-weight:600;color:var(--text)}
.kpi .kpi-ctx{font-size:12.5px;color:var(--muted);line-height:1.45}
.kpi.pos .kpi-val{color:var(--good-tx)} .kpi.neg .kpi-val{color:var(--bad-tx)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin-top:14px}
.hw{padding:18px}
.hw h3{font-size:14px;margin-bottom:2px}
.hw .hw-tag{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--faint);font-weight:600}
.hw dl{display:grid;grid-template-columns:auto 1fr;gap:4px 18px;margin:12px 0 0;font-size:13.5px}
.hw dt{color:var(--muted)} .hw dd{margin:0;font-weight:600;font-variant-numeric:tabular-nums}
.hw .prov{margin-top:12px;font-size:12px;color:var(--faint)}

/* ---------- legends ---------- */
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;margin:0 0 10px;padding:0;list-style:none}
.legend li{display:flex;align-items:center;gap:7px;font-size:12.5px;color:var(--text)}
.legend svg{flex:none}

/* ---------- charts ---------- */
.chart-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0}
.chart-card{padding:16px 16px 10px}
.chart-card h3{font-size:13.5px;margin-bottom:2px}
.chart-card .chart-sub{font-size:12px;color:var(--muted);margin:0 0 8px}
.chart-card svg{width:100%;height:auto;display:block}
.chart-note{font-size:11.5px;color:var(--faint);margin:6px 0 0}
@media (max-width:900px){.chart-grid{grid-template-columns:1fr}}

/* ---------- tabs ---------- */
.tabs{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 14px}
.tab{appearance:none;border:1px solid var(--border);background:var(--surface);color:var(--muted);
  font:inherit;font-size:13px;font-weight:600;padding:6px 14px;border-radius:8px;cursor:pointer}
.tab:hover{border-color:var(--border-strong);color:var(--text)}
.tab[aria-selected="true"]{background:var(--ink);border-color:var(--ink);color:#fff}
.tabset .panel[hidden]{display:none}

/* ---------- tables ---------- */
.table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:10px;
  background:var(--surface);box-shadow:0 1px 2px rgba(16,22,31,.04)}
table.data{border-collapse:collapse;width:100%;font-size:13px}
table.data caption{text-align:left;padding:12px 14px 4px;font-size:13.5px;font-weight:600;color:var(--ink)}
table.data th,table.data td{padding:7px 12px;text-align:left;border-bottom:1px solid var(--border);
  white-space:nowrap;vertical-align:middle}
table.data thead th{position:sticky;top:0;background:#f2f4f7;border-bottom:1px solid var(--border-strong);
  font-size:11.5px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);z-index:2}
table.data tbody tr:last-child td{border-bottom:none}
table.data tbody tr:nth-child(even){background:#fafbfc}
table.data .num,table.data th.num{text-align:right;font-variant-numeric:tabular-nums}
table.data td.num{font-family:var(--mono);font-size:12.5px}
table.data th.sortable{cursor:pointer;user-select:none}
table.data th.sortable:hover{color:var(--text)}
table.data th[aria-sort]::after{content:"";display:inline-block;margin-left:5px;border:4px solid transparent}
table.data th[aria-sort="ascending"]::after{border-bottom-color:var(--muted);transform:translateY(-3px)}
table.data th[aria-sort="descending"]::after{border-top-color:var(--muted);transform:translateY(2px)}
tr.agg td,tr.agg th{border-top:2px solid var(--border-strong);background:#f6f8fa}
tr.agg:nth-child(even){background:#f6f8fa}
td.best{background:var(--good-bg)!important;color:var(--good-tx);font-weight:700}
td.best strong{color:inherit}
.pos{color:var(--good-tx)} .neg{color:var(--bad-tx)}
.sf-cell{font-weight:700;color:var(--ink);font-size:12.5px}
.eng{font-weight:600}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--c,#999);
  margin-right:8px;vertical-align:-1px}
.badge{display:inline-block;font-family:var(--mono);font-size:10.5px;font-weight:700;line-height:1;
  padding:3px 6px;border-radius:5px;vertical-align:2px;margin-left:6px}
.badge.b{background:var(--warn-bg);color:var(--warn-tx)}
.badge.p{background:var(--teal-lite);color:var(--teal)}
.st{display:inline-block;font-size:11px;font-weight:700;padding:3px 8px;border-radius:6px;line-height:1.2}
.st-pass{background:var(--good-bg);color:var(--good-tx)}
.st-gap{background:var(--warn-bg);color:var(--warn-tx)}
.st-note{background:var(--violet-lite);color:#5b21b6;max-width:340px;white-space:normal}
tr.main{cursor:pointer}
tr.main:hover{background:#f2f6fa}
tr.detail td{background:#f8fafc;border-bottom:1px solid var(--border)}
tr.detail[hidden]{display:none}
.detail-box{padding:8px 4px 10px}
.detail-box table{border-collapse:collapse;font-size:12.5px}
.detail-box th,.detail-box td{padding:4px 14px 4px 0;text-align:left}
.detail-box td{font-family:var(--mono);font-variant-numeric:tabular-nums}
.detail-box thead th{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.caret{display:inline-block;width:0;height:0;border:4.5px solid transparent;border-left-color:var(--faint);
  margin-right:7px;vertical-align:-1px;transition:transform .12s ease}
tr.main[aria-expanded="true"] .caret{transform:rotate(90deg)}

/* ---------- explorer ---------- */
.explorer{margin-top:18px;padding:18px}
.explorer h3{font-size:15px}
.explorer .expl-sub{font-size:12.5px;color:var(--muted);margin:2px 0 14px}
.win-chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.win-chip{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;color:var(--muted);
  background:#f2f4f7;border:1px solid var(--border);border-radius:999px;padding:4px 12px}
.win-chip b{font-variant-numeric:tabular-nums;color:var(--text)}
.hint{font-size:11.5px;color:var(--faint);margin:8px 0 0}

/* ---------- notes ---------- */
.notes .card{padding:20px;margin-bottom:14px}
.notes h3{font-size:14.5px;margin-bottom:6px}
.notes ul{margin:8px 0 0;padding-left:20px}
.notes li{margin:4px 0;font-size:13.5px}
.notes code{font-family:var(--mono);font-size:12px;background:#f2f4f7;border-radius:4px;padding:1px 5px}

/* ---------- footer ---------- */
footer{margin-top:48px;background:#10161f;color:#9fb0c3;padding:26px 0;font-size:12.5px}
footer .wrap{display:flex;flex-wrap:wrap;gap:8px 24px;justify-content:space-between}
footer code{font-family:var(--mono);color:#c8d2de;font-size:11.5px}

/* ---------- tooltip ---------- */
#tip{position:fixed;z-index:50;pointer-events:none;background:#10161f;color:#e8ecf2;
  border-radius:8px;padding:9px 12px;font-size:12px;line-height:1.5;max-width:320px;
  box-shadow:0 6px 20px rgba(0,0,0,.28);opacity:0;transition:opacity .08s}
#tip.on{opacity:1}
#tip .t{font-weight:700;margin-bottom:3px}
#tip .r{display:flex;justify-content:space-between;gap:16px;font-variant-numeric:tabular-nums}
#tip .r span:last-child{font-family:var(--mono)}

/* ---------- misc ---------- */
.hover-col{fill:transparent}
.hover-col:hover{fill:rgba(28,36,48,.05)}
noscript{display:block;background:var(--bad-bg);color:var(--bad-tx);padding:14px;border-radius:8px;margin:20px 0}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
@media print{
  body{background:#fff}
  .masthead{background:#fff;color:#000;border-bottom:2px solid #000}
  .masthead h1{color:#000}.masthead .sub{color:#333}
  .card,.table-wrap{box-shadow:none}
  .tabs{display:none}.tabset .panel[hidden]{display:block}
  tr.detail{display:none!important}
}
</style>
</head>
<body>

<header class="masthead">
  <div class="wrap">
    <div class="kicker">Benchmark Report</div>
    <h1>Query Engine Comparison</h1>
    <p class="sub">Five engines on TPC-H and TPC-DS — single-node runs at scale factors 1–1000, plus an 8-worker cluster head-to-head at scale factors 100–10000.</p>
    <div class="meta-chips">
      <span class="chip"><span class="k">Engines</span> 5</span>
      <span class="chip"><span class="k">Benchmarks</span> TPC-H · TPC-DS</span>
      <span class="chip"><span class="k">Source</span> <code>engine-comparison-summary-data.json</code></span>
      <span class="chip"><span class="k">SHA-256</span> <code id="sha-chip"></code></span>
      <span class="chip">Self-contained · no external assets</span>
    </div>
  </div>
</header>

<main class="wrap">
  <noscript>This report renders its tables and charts with JavaScript. The data is embedded in this file, but a JavaScript-enabled browser is required to view it.</noscript>

  <section id="overview">
    <div class="sec-head">
      <span class="sec-num">01</span><h2>Overview</h2>
      <p class="sec-sub">Key figures computed directly from the source data. Ratios for single-node totals are relative to DuckDB 1.5.5; cluster figures compare Spark Rust 0.42.1 against Spark 4.1.1 Gluten on TPC-DS.</p>
    </div>
    <div class="kpi-grid" id="kpis"></div>
    <div class="cards" id="hardware"></div>
  </section>

  <section id="single">
    <div class="sec-head">
      <span class="sec-num">02</span><h2>Single-node results</h2>
      <p class="sec-sub">All queries of each benchmark run at scale factors 1, 10, 100 and 1000 on one node. “Total time” is the sum of per-query times as reported in the source data; ratio and Δ are relative to DuckDB 1.5.5 (the baseline, ratio 1.00×). The “All” row aggregates the four scale factors.</p>
    </div>
    <div id="totals-tables"></div>

    <div class="tabset" id="bench-tabs">
      <div class="tabs" role="tablist" aria-label="Benchmark">
        <button class="tab" role="tab" aria-selected="true" data-tab="tpch">TPC-H</button>
        <button class="tab" role="tab" aria-selected="false" data-tab="tpcds">TPC-DS</button>
      </div>
      <div class="panel" data-panel="tpch" role="tabpanel">
        <div class="chart-grid">
          <div class="card chart-card"><h3>Total time by scale factor</h3><p class="chart-sub">Log–log; steeper slope means worse scaling.</p><div id="chart-scale-tpch"></div></div>
          <div class="card chart-card"><h3>Ratio vs DuckDB 1.5.5</h3><p class="chart-sub">Log scale; below the 1.0× line is faster than DuckDB.</p><div id="chart-ratio-tpch"></div></div>
        </div>
      </div>
      <div class="panel" data-panel="tpcds" role="tabpanel" hidden>
        <div class="chart-grid">
          <div class="card chart-card"><h3>Total time by scale factor</h3><p class="chart-sub">Log–log; steeper slope means worse scaling.</p><div id="chart-scale-tpcds"></div></div>
          <div class="card chart-card"><h3>Ratio vs DuckDB 1.5.5</h3><p class="chart-sub">Log scale; below the 1.0× line is faster than DuckDB.</p><div id="chart-ratio-tpcds"></div></div>
        </div>
      </div>
    </div>

    <div class="explorer card tabset" id="single-explorer">
      <h3>Per-query times</h3>
      <p class="expl-sub">Fastest engine per query is highlighted. Click a column header to sort. Superscript badges mark results flagged in the source data (see Notes).</p>
      <div class="tabs" role="tablist" aria-label="Benchmark and scale factor">
        <button class="tab" role="tab" aria-selected="true" data-stab="TPC-H">TPC-H</button>
        <button class="tab" role="tab" aria-selected="false" data-stab="TPC-DS">TPC-DS</button>
        <span class="vsep" aria-hidden="true"></span>
        <button class="tab" role="tab" aria-selected="true" data-ssf="1">SF 1</button>
        <button class="tab" role="tab" aria-selected="false" data-ssf="10">SF 10</button>
        <button class="tab" role="tab" aria-selected="false" data-ssf="100">SF 100</button>
        <button class="tab" role="tab" aria-selected="false" data-ssf="1000">SF 1000</button>
      </div>
      <div class="win-chips" id="single-wins"></div>
      <div id="single-table"></div>
    </div>
  </section>

  <section id="cluster">
    <div class="sec-head">
      <span class="sec-num">03</span><h2>Cluster results — Spark Rust vs Spark Gluten</h2>
      <p class="sec-sub">TPC-DS, 99 queries per scale factor, on an 8-worker cluster. Two engines are compared: Spark Rust 0.42.1 and Spark 4.1.1 Gluten. Per-query ratio = Spark Rust ÷ Spark Gluten; values below 1.0× mean Spark Rust was faster. “Wins” counts queries each engine finished first; queries where one engine produced no valid result are excluded from wins.</p>
    </div>
    <div id="cluster-agg"></div>

    <div class="chart-grid" style="grid-template-columns:1fr 1fr 1fr">
      <div class="card chart-card"><h3>Total time (s)</h3><p class="chart-sub">Log scale — lower is better.</p><div id="chart-ctime"></div></div>
      <div class="card chart-card"><h3>CPU-hours consumed</h3><p class="chart-sub">Log scale — lower is better.</p><div id="chart-ccpu"></div></div>
      <div class="card chart-card"><h3>Queries won</h3><p class="chart-sub">Of 99 queries per scale factor.</p><div id="chart-cwins"></div></div>
    </div>

    <div class="explorer card tabset" id="cluster-explorer">
      <h3>Per-query comparison</h3>
      <p class="expl-sub">Click a row to expand resource metrics; click a column header to sort. The strip chart shows the per-query ratio — bars below the 1.0× line favor Spark Rust.</p>
      <div class="tabs" role="tablist" aria-label="Cluster scale factor">
        <button class="tab" role="tab" aria-selected="true" data-csf="100">SF 100</button>
        <button class="tab" role="tab" aria-selected="false" data-csf="1000">SF 1000</button>
        <button class="tab" role="tab" aria-selected="false" data-csf="10000">SF 10000</button>
      </div>
      <div class="win-chips" id="cluster-wins"></div>
      <div class="card chart-card" style="margin-bottom:14px"><div id="chart-cratio"></div></div>
      <div id="cluster-table"></div>
    </div>
  </section>

  <section id="notes" class="notes">
    <div class="sec-head">
      <span class="sec-num">04</span><h2>Notes &amp; provenance</h2>
      <p class="sec-sub">Caveats carried by the source data itself, plus report provenance.</p>
    </div>
    <div id="notes-body"></div>
  </section>
</main>

<footer>
  <div class="wrap">
    <div>Generated <span id="gen-date"></span> · every figure is taken from, or computed arithmetically from, <code>engine-comparison-summary-data.json</code></div>
    <div>Source data: <code id="src-name"></code> · SHA-256 <code id="sha-full"></code></div>
  </div>
</footer>

<div id="tip" role="tooltip" aria-hidden="true"></div>

<script type="application/json" id="data-payload">__DATA__</script>
<script>
"use strict";
const D = JSON.parse(document.getElementById("data-payload").textContent);

/* ---------- constants ---------- */
const ENGINES = D.engines;
const ECOLOR = {
  "Spark Rust 0.42.1 (default)":"#c2410c",
  "Spark Rust 0.42.1 (tuned)":"#f59e0b",
  "DuckDB 1.5.5":"#0e7490",
  "Spark 4.1.1 Gluten":"#7c3aed",
  "Spark 4.2":"#52606f"
};
const ESHAPE = {
  "Spark Rust 0.42.1 (default)":"circle",
  "Spark Rust 0.42.1 (tuned)":"diamond",
  "DuckDB 1.5.5":"square",
  "Spark 4.1.1 Gluten":"triangle",
  "Spark 4.2":"cross"
};
const SHORT = {
  "Spark Rust 0.42.1 (default)":"Spark Rust · default",
  "Spark Rust 0.42.1 (tuned)":"Spark Rust · tuned",
  "DuckDB 1.5.5":"DuckDB 1.5.5",
  "Spark 4.1.1 Gluten":"Spark 4.1.1 Gluten",
  "Spark 4.2":"Spark 4.2"
};
const CR = "Spark Rust 0.42.1", CG = "Spark 4.1.1 Gluten";
const CCOL = {[CR]:"#c2410c", [CG]:"#7c3aed"};
const BENCHES = ["TPC-H","TPC-DS"];
const SFS = ["1","10","100","1000"];
const CSFS = ["100","1000","10000"];
const BASE = "DuckDB 1.5.5";

/* ---------- formatting ---------- */
const fmtTime = v => v==null ? "—" :
  v>=1000 ? Math.round(v).toLocaleString("en-US") :
  v>=100  ? v.toFixed(1) : v>=10 ? v.toFixed(2) : v.toFixed(3);
const fmtRatio = v => v==null ? "—" : v.toFixed(2)+"×";
const fmtDiff = v => v==null||v===0 ? "—" :
  (v>0?"+":"−") + fmtTime(Math.abs(v));
const fmtShort = v => v>=1000 ? Math.round(v).toLocaleString("en-US")
  : v>=100 ? v.toFixed(0) : v>=10 ? v.toFixed(1) : v.toFixed(2);
const esc = s => String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
const lg = Math.log10;

/* ---------- lookup helpers ---------- */
const tot = (bench, engine, sf="all") =>
  D.totals[bench].find(r => r.sf===sf && r.engine===engine);
const clus = (sf, engine) => D.cluster[sf].find(r => r.engine===engine);

/* ---------- masthead / footer meta ---------- */
document.getElementById("sha-chip").textContent = D.sha256.slice(0,14) + "…";
document.getElementById("sha-full").textContent = D.sha256;
document.getElementById("src-name").textContent = D.source;
document.getElementById("gen-date").textContent = "__GEN_DATE__";

/* ---------- KPI cards ---------- */
(function renderKPIs(){
  const thAll = tot("TPC-H", "Spark Rust 0.42.1 (default)");
  const tdsTuned = tot("TPC-DS", "Spark Rust 0.42.1 (tuned)");
  const tdsBase = tot("TPC-DS", BASE);
  const th42 = tot("TPC-H", "Spark 4.2");
  const thBase = tot("TPC-H", BASE);
  const c100r = clus("100", CR), c100g = clus("100", CG);
  const c1000r = clus("1000", CR), c1000g = clus("1000", CG);
  const c10000r = clus("10000", CR), c10000g = clus("10000", CG);
  const w100 = D.wins["100"], w10000 = D.wins["10000"];
  const excl10000 = 99 - w10000[0] - w10000[1];
  const cards = [
    {val: fmtRatio(thAll.ratio), cls: "pos",
     label: "Spark Rust (default) vs DuckDB — TPC-H, all SFs",
     ctx: `Total ${fmtTime(thAll.time)} s vs ${fmtTime(thBase.time)} s across 88 queries`},
    {val: fmtRatio(tdsTuned.ratio), cls: "pos",
     label: "Spark Rust (tuned) vs DuckDB — TPC-DS, all SFs",
     ctx: `Fastest aggregate of the five engines: ${fmtTime(tdsTuned.time)} s vs ${fmtTime(tdsBase.time)} s`},
    {val: fmtRatio(th42.ratio), cls: "neg",
     label: "Spark 4.2 vs DuckDB — TPC-H, all SFs",
     ctx: `Slowest of the five: ${fmtTime(th42.time)} s vs ${fmtTime(thBase.time)} s`},
    {val: `${w100[0]} / 99`, cls: "pos",
     label: "Cluster queries won by Spark Rust at SF 100",
     ctx: `Total time ${fmtTime(c100r.time)} s vs ${fmtTime(c100g.time)} s — ${fmtRatio(c100g.time/c100r.time)} faster overall`},
    {val: (c1000g.cpuHours/c1000r.cpuHours).toFixed(1)+"×", cls: "pos",
     label: "Cluster CPU-hours advantage for Spark Rust at SF 1000",
     ctx: `${fmtShort(c1000r.cpuHours)} vs ${fmtShort(c1000g.cpuHours)} CPU-hours for the same 99 queries`},
    {val: `${w10000[1]} / ${99-excl10000}`, cls: "neg",
     label: "Cluster queries won by Spark Gluten at SF 10000",
     ctx: `Gluten total ${fmtTime(c10000g.time)} s vs Spark Rust ${fmtTime(c10000r.time)} s; ${excl10000} queries excluded`}
  ];
  document.getElementById("kpis").innerHTML = cards.map(c => `
    <div class="card kpi ${c.cls}">
      <div class="kpi-val">${c.val}</div>
      <div class="kpi-label">${esc(c.label)}</div>
      <div class="kpi-ctx">${esc(c.ctx)}</div>
    </div>`).join("");
})();

/* ---------- hardware ---------- */
(function renderHardware(){
  const s = D.hardware.single_node, w = D.hardware.cluster_workers;
  document.getElementById("hardware").innerHTML = `
    <div class="card hw">
      <div class="hw-tag">Single node</div>
      <h3>${esc(s.sku)}</h3>
      <dl>
        <dt>Cores</dt><dd>${s.cores}</dd>
        <dt>RAM</dt><dd>${s.ram_gb} GB</dd>
        <dt>Runs</dt><dd>TPC-H &amp; TPC-DS, SF 1–1000</dd>
      </dl>
    </div>
    <div class="card hw">
      <div class="hw-tag">Cluster — workers</div>
      <h3>${w.count} × ${esc(w.sku)}</h3>
      <dl>
        <dt>Cores each</dt><dd>${w.cores_each}</dd>
        <dt>RAM each</dt><dd>${w.ram_gb_each} GB</dd>
        <dt>Total cores</dt><dd>${w.total_cores}</dd>
        <dt>Total RAM</dt><dd>${w.total_ram_gb.toLocaleString("en-US")} GB</dd>
      </dl>
      <div class="prov">Hardware provenance: ${esc(D.hardware.provenance)}.</div>
    </div>`;
})();

/* ---------- totals tables ---------- */
(function renderTotals(){
  let html = "";
  for (const bench of BENCHES){
    const rows = D.totals[bench];
    html += `<div class="table-wrap" style="margin-bottom:18px">
      <table class="data">
        <caption>${bench} — totals by engine and scale factor (times in seconds)</caption>
        <thead><tr>
          <th scope="col">Scale</th><th scope="col">Engine</th>
          <th scope="col" class="num">Queries</th>
          <th scope="col" class="num">Total time (s)</th>
          <th scope="col" class="num">Δ vs DuckDB (s)</th>
          <th scope="col" class="num">Ratio</th>
          <th scope="col" class="num">Canonical (s)</th>
          <th scope="col" class="num">Matched</th>
        </tr></thead><tbody>`;
    for (const sf of [...SFS, "all"]){
      const grp = ENGINES.map(e => rows.find(r => r.sf===sf && r.engine===e));
      const min = Math.min(...grp.map(r => r.time));
      grp.forEach((r, i) => {
        const best = r.time === min, base = r.engine === BASE;
        html += `<tr${sf==="all" ? ' class="agg"' : ""}>`;
        if (i===0) html += `<th scope="rowgroup" rowspan="5" class="sf-cell">${sf==="all" ? "All SFs" : "SF "+sf}</th>`;
        html += `<td class="eng"><span class="dot" style="--c:${ECOLOR[r.engine]}" title="${esc(r.engine)}"></span>${esc(SHORT[r.engine])}</td>`;
        html += `<td class="num">${r.n}</td>`;
        html += `<td class="num${best ? " best" : ""}">${best ? "<strong>" : ""}${fmtTime(r.time)}${best ? "</strong>" : ""}</td>`;
        html += `<td class="num ${r.diff>0?"neg":r.diff<0?"pos":""}">${base ? '<span class="muted">baseline</span>' : fmtDiff(r.diff)}</td>`;
        html += `<td class="num">${base ? "1.00×" : fmtRatio(r.ratio)}</td>`;
        html += `<td class="num">${r.canonical==null ? "—" : fmtTime(r.canonical)}</td>`;
        html += `<td class="num">${r.matched==null ? "—" : fmtRatio(r.matched)}</td></tr>`;
      });
    }
    html += "</tbody></table></div>";
  }
  document.getElementById("totals-tables").innerHTML = html;
})();

/* ---------- SVG helpers ---------- */
function markerSVG(shape, cx, cy, color, r=4.6){
  switch(shape){
    case "circle":   return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${color}" stroke="#fff" stroke-width="1.4"/>`;
    case "diamond":  return `<rect x="${cx-r}" y="${cy-r}" width="${2*r}" height="${2*r}" transform="rotate(45 ${cx} ${cy})" fill="${color}" stroke="#fff" stroke-width="1.4"/>`;
    case "square":   return `<rect x="${cx-r}" y="${cy-r}" width="${2*r}" height="${2*r}" fill="${color}" stroke="#fff" stroke-width="1.4"/>`;
    case "triangle": return `<path d="M ${cx} ${cy-r-1} L ${cx+r+1} ${cy+r} L ${cx-r-1} ${cy+r} Z" fill="${color}" stroke="#fff" stroke-width="1.4"/>`;
    case "cross":    return `<path d="M ${cx-r} ${cy-r} L ${cx+r} ${cy+r} M ${cx+r} ${cy-r} L ${cx-r} ${cy+r}" stroke="${color}" stroke-width="2.4" stroke-linecap="round" fill="none"/>`;
  }
  return "";
}
function legendHTML(engines){
  return `<ul class="legend">` + engines.map(e => `
    <li><svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">${markerSVG(ESHAPE[e],7,7,ECOLOR[e],4.4)}</svg>${esc(e)}</li>`).join("") + `</ul>`;
}
function decadeTicks(min, max){
  const t = [];
  for (let e = Math.floor(lg(min)); e <= Math.ceil(lg(max)); e++){
    const v = Math.pow(10, e);
    if (v >= min*0.999 && v <= max*1.001) t.push(v);
  }
  return t.length ? t : [min, max];
}

/* ---------- log–log line chart ---------- */
function lineChart(el, cfg){
  const W=640, H=380, L=62, R=16, T=16, B=44;
  const iw = W-L-R, ih = H-T-B;
  const [x0,x1] = cfg.xDomain, [y0,y1] = cfg.yDomain;
  const X = v => L + iw * (lg(v)-lg(x0)) / (lg(x1)-lg(x0));
  const Y = v => T + ih * (1 - (lg(v)-lg(y0)) / (lg(y1)-lg(y0)));
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(cfg.aria)}" font-family="inherit">`;
  for (const v of cfg.yTicks){
    const y = Y(v);
    s += `<line x1="${L}" y1="${y}" x2="${W-R}" y2="${y}" stroke="#e7eaee" stroke-width="1"/>`;
    s += `<text x="${L-8}" y="${y+4}" text-anchor="end" font-size="11" fill="#8a93a3">${fmtShort(v)}</text>`;
  }
  for (const xt of cfg.xTicks){
    const x = X(xt.v);
    s += `<line x1="${x}" y1="${T}" x2="${x}" y2="${T+ih}" stroke="#eef1f4" stroke-width="1"/>`;
    s += `<text x="${x}" y="${T+ih+18}" text-anchor="middle" font-size="11" fill="#8a93a3">${esc(xt.label)}</text>`;
  }
  s += `<line x1="${L}" y1="${T+ih}" x2="${W-R}" y2="${T+ih}" stroke="#c8cdd6" stroke-width="1"/>`;
  s += `<line x1="${L}" y1="${T}" x2="${L}" y2="${T+ih}" stroke="#c8cdd6" stroke-width="1"/>`;
  s += `<text x="${L+iw/2}" y="${H-6}" text-anchor="middle" font-size="11" fill="#5c6675">${esc(cfg.xLabel)}</text>`;
  s += `<text transform="translate(14 ${T+ih/2}) rotate(-90)" text-anchor="middle" font-size="11" fill="#5c6675">${esc(cfg.yLabel)}</text>`;
  if (cfg.refLine){
    const y = Y(cfg.refLine.v);
    s += `<line x1="${L}" y1="${y}" x2="${W-R}" y2="${y}" stroke="#0e7490" stroke-width="1.4" stroke-dasharray="5 4"/>`;
    s += `<text x="${W-R-4}" y="${y-6}" text-anchor="end" font-size="10.5" fill="#0e7490" font-weight="600">${esc(cfg.refLine.label)}</text>`;
  }
  for (const se of cfg.series){
    const pts = se.points.map(p => [X(p.x), Y(p.y)]);
    s += `<polyline points="${pts.map(p=>p.map(n=>n.toFixed(1)).join(",")).join(" ")}" fill="none" stroke="${se.color}" stroke-width="${se.dash?2.2:2.6}"${se.dash?` stroke-dasharray="${se.dash}"`:""} stroke-linejoin="round" stroke-linecap="round"/>`;
    pts.forEach(p => { s += markerSVG(se.shape, p[0], p[1], se.color); });
  }
  for (const xt of cfg.xTicks){
    const x = X(xt.v);
    s += `<rect class="hover-col" x="${x-iw/(cfg.xTicks.length*2)}" y="${T}" width="${iw/cfg.xTicks.length}" height="${ih}" data-tt="${esc(xt.tipTitle)}" data-tb="${esc(xt.tipBody)}"/>`;
  }
  s += `</svg>`;
  el.innerHTML = s;
}

/* ---------- single-node charts ---------- */
(function renderScalingCharts(){
  for (const bench of BENCHES){
    const key = bench === "TPC-H" ? "tpch" : "tpcds";
    const series = ENGINES.map(e => ({
      name: e, color: ECOLOR[e], shape: ESHAPE[e],
      dash: e === "Spark Rust 0.42.1 (tuned)" ? "6 4" : null,
      points: SFS.map(sf => ({x: +sf, y: tot(bench, e, sf).time}))
    }));
    const times = series.flatMap(se => se.points.map(p => p.y));
    const yMin = Math.pow(10, Math.floor(lg(Math.min(...times)))-0.15);
    const yMax = Math.pow(10, Math.ceil(lg(Math.max(...times)))+0.15);
    const xTicks = SFS.map(sf => {
      const tipTitle = `${bench} · SF ${sf}`;
      const tipBody = ENGINES.map(e => {
        const r = tot(bench, e, sf);
        return `${SHORT[e]}\t${fmtTime(r.time)} s`;
      }).sort((a,b) => parseFloat(a.split("\t")[1].replace(",","")) - parseFloat(b.split("\t")[1].replace(",",""))).join("\n");
      return {v: +sf, label: "SF "+sf, tipTitle, tipBody};
    });
    lineChart(document.getElementById("chart-scale-"+key), {
      series, xDomain: [1, 1000], yDomain: [yMin, yMax],
      yTicks: decadeTicks(yMin, yMax), xTicks,
      xLabel: "Scale factor (log)", yLabel: "Total time in s (log)",
      aria: `${bench} total time by scale factor, log-log chart, five engines`
    });

    const rSeries = ENGINES.filter(e => e !== BASE).map(e => ({
      name: e, color: ECOLOR[e], shape: ESHAPE[e],
      dash: e === "Spark Rust 0.42.1 (tuned)" ? "6 4" : null,
      points: SFS.map(sf => ({x: +sf, y: tot(bench, e, sf).ratio}))
    }));
    const ratios = rSeries.flatMap(se => se.points.map(p => p.y));
    const rMin = Math.min(0.75, Math.min(...ratios)*0.85);
    const rMax = Math.max(...ratios)*1.25;
    const rTicks = [0.5, 1, 2, 5, 10, 20, 50].filter(v => v >= rMin && v <= rMax);
    const rXTicks = SFS.map(sf => {
      const tipTitle = `${bench} · SF ${sf} — ratio vs DuckDB`;
      const tipBody = ENGINES.filter(e => e !== BASE).map(e => {
        const r = tot(bench, e, sf);
        return `${SHORT[e]}\t${fmtRatio(r.ratio)}`;
      }).join("\n");
      return {v: +sf, label: "SF "+sf, tipTitle, tipBody};
    });
    lineChart(document.getElementById("chart-ratio-"+key), {
      series: rSeries, xDomain: [1, 1000], yDomain: [rMin, rMax],
      yTicks: rTicks, xTicks: rXTicks, refLine: {v: 1, label: "DuckDB parity 1.0×"},
      xLabel: "Scale factor (log)", yLabel: "Ratio vs DuckDB (log)",
      aria: `${bench} ratio to DuckDB by scale factor, log chart`
    });
    const panel = document.querySelector(`[data-panel="${key}"]`);
    const legend = document.createElement("div");
    legend.innerHTML = legendHTML(ENGINES);
    panel.querySelector(".chart-grid").before(legend);
  }
})();

/* ---------- single-node per-query explorer ---------- */
const singleState = {bench: "TPC-H", sf: "1", sortKey: "q", sortDir: 1};
function renderSingleWins(){
  const rows = D.single[singleState.bench][singleState.sf];
  const counts = {}; ENGINES.forEach(e => counts[e] = 0);
  rows.forEach(r => counts[ENGINES[r.times.indexOf(Math.min(...r.times))]]++);
  document.getElementById("single-wins").innerHTML =
    `<span class="win-chip">Fastest on</span>` +
    ENGINES.filter(e => counts[e] > 0).map(e =>
      `<span class="win-chip"><span class="dot" style="--c:${ECOLOR[e]}"></span>${esc(SHORT[e])} <b>${counts[e]}</b> / ${rows.length}</span>`
    ).join("");
}
function renderSingleTable(){
  const {bench, sf, sortKey, sortDir} = singleState;
  let rows = [...D.single[bench][sf]];
  if (sortKey === "q") rows.sort((a,b) => (a.q-b.q)*sortDir);
  else rows.sort((a,b) => (a.times[+sortKey]-b.times[+sortKey])*sortDir);
  let h = `<div class="table-wrap"><table class="data"><thead><tr><th scope="col" class="sortable num" data-sk="q" aria-sort="${sortKey==="q" ? (sortDir>0?"ascending":"descending") : "none"}">Q</th>`;
  ENGINES.forEach((e, i) => {
    h += `<th scope="col" class="sortable num" data-sk="${i}" title="${esc(e)} (seconds)" aria-sort="${sortKey==String(i) ? (sortDir>0?"ascending":"descending") : "none"}">${esc(SHORT[e])}</th>`;
  });
  h += `</tr></thead><tbody>`;
  for (const r of rows){
    const min = Math.min(...r.times);
    h += `<tr><th scope="row" class="num">${r.q}</th>`;
    r.times.forEach((t, i) => {
      const mk = r.markers[i];
      h += `<td class="num${t===min ? " best" : ""}">${t===min ? "<strong>" : ""}${fmtTime(t)}${t===min ? "</strong>" : ""}${mk ? ` <span class="badge ${mk==="B"?"b":"p"}" title="Flagged ‘${mk}’ in source data — see Notes">${mk}</span>` : ""}</td>`;
    });
    h += `</tr>`;
  }
  h += `</tbody></table></div>`;
  document.getElementById("single-table").innerHTML = h;
}
document.getElementById("single-explorer").addEventListener("click", e => {
  const tab = e.target.closest("[data-stab],[data-ssf]");
  if (tab){
    if (tab.dataset.stab){ singleState.bench = tab.dataset.stab; }
    else { singleState.sf = tab.dataset.ssf; }
    singleState.sortKey = "q"; singleState.sortDir = 1;
    document.querySelectorAll("#single-explorer [data-stab]").forEach(b => b.setAttribute("aria-selected", b.dataset.stab===singleState.bench));
    document.querySelectorAll("#single-explorer [data-ssf]").forEach(b => b.setAttribute("aria-selected", b.dataset.ssf===singleState.sf));
    renderSingleWins(); renderSingleTable();
    return;
  }
  const th = e.target.closest("th.sortable");
  if (th && th.closest("#single-table")){
    const k = th.dataset.sk;
    if (singleState.sortKey === k) singleState.sortDir *= -1;
    else { singleState.sortKey = k; singleState.sortDir = 1; }
    renderSingleTable();
  }
});
renderSingleWins(); renderSingleTable();

/* ---------- cluster aggregate table ---------- */
(function renderClusterAgg(){
  let html = `<div class="table-wrap"><table class="data">
    <caption>Cluster TPC-DS — aggregate run metrics per engine and scale factor</caption>
    <thead><tr>
      <th scope="col">Scale</th><th scope="col">Engine</th><th scope="col" class="num">Queries</th>
      <th scope="col" class="num">Total time (s)</th><th scope="col" class="num">CPU (core·s)</th>
      <th scope="col" class="num">Avg cores</th><th scope="col" class="num">Mem-time (GB·s)</th>
      <th scope="col" class="num">CPU-hours</th><th scope="col" class="num">Mem-hours (GB·h)</th>
      <th scope="col" class="num">Mean (s)</th><th scope="col" class="num">p50 (s)</th>
      <th scope="col" class="num">p95 (s)</th><th scope="col" class="num">Max (s)</th>
    </tr></thead><tbody>`;
  for (const sf of CSFS){
    const grp = [clus(sf, CR), clus(sf, CG)];
    const minTime = Math.min(...grp.map(r => r.time));
    grp.forEach((r, i) => {
      const best = r.time === minTime;
      html += `<tr>`;
      if (i===0) html += `<th scope="rowgroup" rowspan="2" class="sf-cell">SF ${sf}</th>`;
      html += `<td class="eng"><span class="dot" style="--c:${CCOL[r.engine]}"></span>${esc(r.engine)}</td>`;
      html += `<td class="num">${r.n}</td>`;
      html += `<td class="num${best ? " best" : ""}">${best ? "<strong>" : ""}${fmtTime(r.time)}${best ? "</strong>" : ""}</td>`;
      html += `<td class="num">${fmtTime(r.cpu)}</td><td class="num">${r.cores.toFixed(1)}</td>`;
      html += `<td class="num">${fmtTime(r.memtime)}</td><td class="num">${r.cpuHours.toFixed(2)}</td>`;
      html += `<td class="num">${r.memHours.toFixed(2)}</td><td class="num">${r.mean.toFixed(2)}</td>`;
      html += `<td class="num">${r.p50.toFixed(2)}</td><td class="num">${r.p95.toFixed(2)}</td>`;
      html += `<td class="num">${r.max.toFixed(2)}</td></tr>`;
    });
  }
  html += `</tbody></table></div>
    <p class="chart-note">CPU = total core-seconds; Avg cores = CPU ÷ total time; Mem-time = memory (GB) × time (s). Mean, p50, p95 and Max are per-query latency statistics in seconds. Field names follow the source data.</p>`;
  document.getElementById("cluster-agg").innerHTML = html;
})();

/* ---------- cluster charts ---------- */
function groupedBars(el, cfg){
  const W=640, H=330, L=56, R=14, T=26, B=40;
  const iw=W-L-R, ih=H-T-B;
  const [y0,y1] = cfg.yDomain;
  const Y = v => T + ih * (1 - (lg(v)-lg(y0)) / (lg(y1)-lg(y0)));
  const catW = iw / cfg.cats.length;
  const barW = Math.min(64, catW*0.32);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(cfg.aria)}" font-family="inherit">`;
  for (const v of cfg.yTicks){
    const y = Y(v);
    s += `<line x1="${L}" y1="${y}" x2="${W-R}" y2="${y}" stroke="#e7eaee"/>`;
    s += `<text x="${L-8}" y="${y+4}" text-anchor="end" font-size="11" fill="#8a93a3">${fmtShort(v)}</text>`;
  }
  s += `<line x1="${L}" y1="${T+ih}" x2="${W-R}" y2="${T+ih}" stroke="#c8cdd6"/>`;
  s += `<text transform="translate(13 ${T+ih/2}) rotate(-90)" text-anchor="middle" font-size="11" fill="#5c6675">${esc(cfg.yLabel)}</text>`;
  cfg.cats.forEach((cat, ci) => {
    const cx = L + catW*ci + catW/2;
    s += `<text x="${cx}" y="${H-14}" text-anchor="middle" font-size="11.5" fill="#5c6675" font-weight="600">${esc(cat.label)}</text>`;
    cfg.series.forEach((se, si) => {
      const v = se.values[ci];
      const bx = cx - (cfg.series.length*barW + (cfg.series.length-1)*6)/2 + si*(barW+6);
      const by = Y(v);
      s += `<rect x="${bx.toFixed(1)}" y="${by.toFixed(1)}" width="${barW}" height="${(T+ih-by).toFixed(1)}" rx="3" fill="${se.color}" data-tt="${esc(cat.tipTitle)}" data-tb="${esc(cat.tipBodies[si])}"/>`;
      s += `<text x="${(bx+barW/2).toFixed(1)}" y="${(by-6).toFixed(1)}" text-anchor="middle" font-size="11" fill="#1c2430" font-weight="600">${fmtShort(v)}</text>`;
    });
  });
  s += `</svg>`;
  el.innerHTML = s + `<ul class="legend">${cfg.series.map(se => `<li><span class="dot" style="--c:${se.color}"></span>${esc(se.name)}</li>`).join("")}</ul>`;
}
(function renderClusterCharts(){
  const cats = CSFS.map(sf => ({
    label: "SF "+sf,
    tipTitle: `Cluster TPC-DS · SF ${sf}`,
    tipBodies: [`${CR}\t${fmtTime(clus(sf,CR).time)} s`, `${CG}\t${fmtTime(clus(sf,CG).time)} s`]
  }));
  groupedBars(document.getElementById("chart-ctime"), {
    cats, yDomain: [100, 30000], yTicks: [100, 1000, 10000],
    yLabel: "Total time (s, log)",
    series: [{name: CR, color: CCOL[CR], values: CSFS.map(sf => clus(sf,CR).time)},
             {name: CG, color: CCOL[CG], values: CSFS.map(sf => clus(sf,CG).time)}],
    aria: "Cluster total time by scale factor, two engines, log scale"
  });
  groupedBars(document.getElementById("chart-ccpu"), {
    cats, yDomain: [1, 300], yTicks: [1, 10, 100],
    yLabel: "CPU-hours (log)",
    series: [{name: CR, color: CCOL[CR], values: CSFS.map(sf => clus(sf,CR).cpuHours)},
             {name: CG, color: CCOL[CG], values: CSFS.map(sf => clus(sf,CG).cpuHours)}],
    aria: "Cluster CPU-hours by scale factor, two engines, log scale"
  });
  /* wins stacked horizontal */
  (function winsChart(){
    const W=640, H=210, L=14, R=14, T=10, B=34;
    const iw=W-L-R, rowH=44, gap=14;
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Queries won per scale factor, stacked bars" font-family="inherit">`;
    CSFS.forEach((sf, i) => {
      const y = T + i*(rowH+gap);
      const [wr, wg] = D.wins[sf];
      const excl = 99 - wr - wg;
      const wR = iw*wr/99, wG = iw*wg/99, wE = iw*excl/99;
      s += `<text x="${L}" y="${y-4}" font-size="11.5" fill="#5c6675" font-weight="600">SF ${sf}</text>`;
      let x = L;
      const seg = (w, color, label, dark) => {
        if (w <= 0) return;
        s += `<rect x="${x.toFixed(1)}" y="${y}" width="${Math.max(0,w-1.5).toFixed(1)}" height="${rowH-14}" rx="3" fill="${color}"/>`;
        if (w > 44) s += `<text x="${(x+w/2).toFixed(1)}" y="${y+(rowH-14)/2+4}" text-anchor="middle" font-size="12" font-weight="700" fill="${dark ? "#fff" : "#334155"}">${label}</text>`;
        x += w;
      };
      seg(wR, CCOL[CR], wr, true);
      seg(wG, CCOL[CG], wg, true);
      seg(wE, "#dbe1e8", excl ? `${excl} excl.` : "", false);
      s += `<text x="${L+iw}" y="${y-4}" text-anchor="end" font-size="11" fill="#8a93a3">99 queries</text>`;
    });
    s += `</svg>`;
    document.getElementById("chart-cwins").innerHTML = s +
      `<ul class="legend"><li><span class="dot" style="--c:${CCOL[CR]}"></span>${esc(CR)}</li><li><span class="dot" style="--c:${CCOL[CG]}"></span>${esc(CG)}</li><li><span class="dot" style="--c:#dbe1e8"></span>excluded</li></ul>`;
  })();
})();

/* ---------- cluster ratio strip chart ---------- */
function ratioStrip(sf){
  const rows = D.clusterQueries[sf];
  const W=960, H=230, L=52, R=12, T=14, B=36;
  const iw=W-L-R, ih=H-T-B;
  const [y0,y1] = [0.1, 10];
  const Y = v => T + ih * (1 - (lg(v)-lg(y0)) / (lg(y1)-lg(y0)));
  const bw = iw/rows.length;
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Per-query ratio Spark Rust divided by Spark Gluten, SF ${sf}" font-family="inherit">`;
  for (const v of [0.1, 0.25, 0.5, 1, 2, 4, 10]){
    const y = Y(v);
    s += `<line x1="${L}" y1="${y}" x2="${W-R}" y2="${y}" stroke="${v===1 ? "#334155" : "#e7eaee"}" stroke-width="${v===1 ? 1.4 : 1}"${v===1 ? "" : ' stroke-dasharray="2 3"'}/>`;
    s += `<text x="${L-6}" y="${y+4}" text-anchor="end" font-size="10.5" fill="#8a93a3">${v}×</text>`;
  }
  const py = Y(1);
  rows.forEach((r, i) => {
    const x = L + i*bw + bw/2;
    if (r.ratio == null){
      s += `<circle cx="${x}" cy="${py}" r="3.4" fill="#94a3b8" stroke="#fff" stroke-width="1" data-tt="Q${r.q} — excluded" data-tb="${esc(r.status)}"/>`;
      return;
    }
    const y = Y(Math.min(Math.max(r.ratio, y0), y1));
    const winner = r.ratio < 1 ? CR : CG;
    s += `<rect x="${(x-bw*0.34).toFixed(2)}" y="${Math.min(y,py).toFixed(2)}" width="${(bw*0.68).toFixed(2)}" height="${Math.max(2, Math.abs(py-y)).toFixed(2)}" rx="1.5" fill="${CCOL[winner]}" data-tt="Q${r.q} · SF ${sf}" data-tb="${esc(`${CR}\t${r.r==null?"—":r.r+" s"}\n${CG}\t${r.g==null?"—":r.g+" s"}\nratio\t${fmtRatio(r.ratio)}\nstatus\t${r.status}`)}"/>`;
  });
  for (let q = 1; q <= 99; q += 10){
    const x = L + (q-1)*bw + bw/2;
    s += `<text x="${x}" y="${H-16}" text-anchor="middle" font-size="10.5" fill="#8a93a3">${q}</text>`;
  }
  s += `<text x="${L+iw/2}" y="${H-3}" text-anchor="middle" font-size="11" fill="#5c6675">Query number</text>`;
  s += `<text transform="translate(12 ${T+ih/2}) rotate(-90)" text-anchor="middle" font-size="11" fill="#5c6675">Rust ÷ Gluten (log)</text>`;
  s += `</svg>`;
  document.getElementById("chart-cratio").innerHTML = s +
    `<p class="chart-note">Bars below the 1.0× line: Spark Rust faster. Gray dots: query excluded (no valid ratio). Hover any bar for details.</p>`;
}

/* ---------- cluster per-query explorer ---------- */
const clusterState = {sf: "100", sortKey: "q", sortDir: 1};
function renderClusterWins(){
  const [wr, wg] = D.wins[clusterState.sf];
  const excl = 99 - wr - wg;
  document.getElementById("cluster-wins").innerHTML =
    `<span class="win-chip"><span class="dot" style="--c:${CCOL[CR]}"></span>${esc(CR)} wins <b>${wr}</b></span>` +
    `<span class="win-chip"><span class="dot" style="--c:${CCOL[CG]}"></span>${esc(CG)} wins <b>${wg}</b></span>` +
    (excl ? `<span class="win-chip"><span class="dot" style="--c:#94a3b8"></span>excluded <b>${excl}</b></span>` : "");
}
function statusBadge(st){
  if (st === "pass") return `<span class="st st-pass">pass</span>`;
  if (st === "gap") return `<span class="st st-gap">gap</span>`;
  if (st.startsWith("pass")) return `<span class="st st-pass" title="${esc(st)}">${esc(st)}</span>`;
  return `<span class="st st-note" title="${esc(st)}">note — see Notes</span>`;
}
function renderClusterTable(){
  const {sf, sortKey, sortDir} = clusterState;
  let rows = [...D.clusterQueries[sf]];
  const val = r => r[sortKey];
  rows.sort((a,b) => {
    const va = val(a), vb = val(b);
    if (va == null && vb == null) return (a.q-b.q)*sortDir;
    if (va == null) return 1;
    if (vb == null) return -1;
    return (va-vb)*sortDir || (a.q-b.q);
  });
  const sortAttr = k => clusterState.sortKey===k ? (clusterState.sortDir>0 ? "ascending" : "descending") : "none";
  let h = `<div class="table-wrap"><table class="data"><thead><tr>
    <th scope="col" class="sortable num" data-ck="q" aria-sort="${sortAttr("q")}">Q</th>
    <th scope="col" class="sortable num" data-ck="r" aria-sort="${sortAttr("r")}">${esc(CR)} (s)</th>
    <th scope="col" class="sortable num" data-ck="g" aria-sort="${sortAttr("g")}">${esc(CG)} (s)</th>
    <th scope="col" class="sortable num" data-ck="diff" aria-sort="${sortAttr("diff")}">Δ (s)</th>
    <th scope="col" class="sortable num" data-ck="ratio" aria-sort="${sortAttr("ratio")}">Ratio</th>
    <th scope="col">Status</th></tr></thead><tbody>`;
  for (const r of rows){
    const rustWins = r.ratio != null && r.ratio < 1;
    const glutWins = r.ratio != null && r.ratio > 1;
    const open = clusterState.open === r.q;
    h += `<tr class="main" data-q="${r.q}" tabindex="0" aria-expanded="${open}" aria-controls="cd-${r.q}">
      <th scope="row" class="num"><span class="caret" aria-hidden="true"></span>${r.q}</th>
      <td class="num${rustWins ? " best" : ""}">${r.r==null ? "—" : (rustWins ? "<strong>" : "") + fmtTime(r.r) + (rustWins ? "</strong>" : "")}</td>
      <td class="num${glutWins ? " best" : ""}">${r.g==null ? "—" : (glutWins ? "<strong>" : "") + fmtTime(r.g) + (glutWins ? "</strong>" : "")}</td>
      <td class="num ${r.diff>0?"neg":r.diff<0?"pos":""}">${fmtDiff(r.diff)}</td>
      <td class="num">${fmtRatio(r.ratio)}</td>
      <td>${statusBadge(r.status)}</td></tr>`;
    h += `<tr class="detail" id="cd-${r.q}"${open ? "" : " hidden"}><td colspan="6"><div class="detail-box">
      <table><thead><tr><th></th><th>${esc(CR)}</th><th>${esc(CG)}</th></tr></thead><tbody>
        <tr><td>CPU (core·s)</td><td>${r.cpu[0]==null?"—":r.cpu[0].toLocaleString("en-US")}</td><td>${r.cpu[1]==null?"—":r.cpu[1].toLocaleString("en-US")}</td></tr>
        <tr><td>Avg cores</td><td>${r.cores[0]==null?"—":r.cores[0]}</td><td>${r.cores[1]==null?"—":r.cores[1]}</td></tr>
        <tr><td>Memory (GB)</td><td>${r.memory[0]==null?"—":r.memory[0]}</td><td>${r.memory[1]==null?"—":r.memory[1]}</td></tr>
        <tr><td>Mem-time (GB·s)</td><td>${r.memtime[0]==null?"—":r.memtime[0].toLocaleString("en-US")}</td><td>${r.memtime[1]==null?"—":r.memtime[1].toLocaleString("en-US")}</td></tr>
        <tr><td>p50 (s)</td><td>${r.p50[0]==null?"—":r.p50[0]}</td><td>${r.p50[1]==null?"—":r.p50[1]}</td></tr>
        <tr><td>p95 (s)</td><td>${r.p95[0]==null?"—":r.p95[0]}</td><td>${r.p95[1]==null?"—":r.p95[1]}</td></tr>
        <tr><td>Max (s)</td><td>${r.max[0]==null?"—":r.max[0]}</td><td>${r.max[1]==null?"—":r.max[1]}</td></tr>
      </tbody></table>
      ${r.status.startsWith("pass") || r.status==="gap" ? "" : `<p class="small" style="margin:8px 0 0"><b>Status (verbatim):</b> ${esc(r.status)}</p>`}
    </div></td></tr>`;
  }
  h += `</tbody></table></div><p class="hint">Δ = Spark Rust − Spark Gluten (negative favors Spark Rust). Ratio = Spark Rust ÷ Spark Gluten.</p>`;
  document.getElementById("cluster-table").innerHTML = h;
}
document.getElementById("cluster-explorer").addEventListener("click", e => {
  const tab = e.target.closest("[data-csf]");
  if (tab){
    clusterState.sf = tab.dataset.csf;
    clusterState.sortKey = "q"; clusterState.sortDir = 1; clusterState.open = null;
    document.querySelectorAll("#cluster-explorer [data-csf]").forEach(b => b.setAttribute("aria-selected", b.dataset.csf===clusterState.sf));
    renderClusterWins(); ratioStrip(clusterState.sf); renderClusterTable();
    return;
  }
  const th = e.target.closest("th.sortable");
  if (th && th.closest("#cluster-table")){
    const k = th.dataset.ck;
    if (clusterState.sortKey === k) clusterState.sortDir *= -1;
    else { clusterState.sortKey = k; clusterState.sortDir = 1; }
    renderClusterTable();
    return;
  }
  const main = e.target.closest("tr.main");
  if (main){
    const q = +main.dataset.q;
    clusterState.open = clusterState.open === q ? null : q;
    renderClusterTable();
  }
});
document.getElementById("cluster-explorer").addEventListener("keydown", e => {
  if ((e.key === "Enter" || e.key === " ") && e.target.matches("tr.main")){
    e.preventDefault();
    const q = +e.target.dataset.q;
    clusterState.open = clusterState.open === q ? null : q;
    renderClusterTable();
  }
});
renderClusterWins(); ratioStrip("100"); renderClusterTable();

/* ---------- notes ---------- */
(function renderNotes(){
  const markers = [];
  for (const bench of BENCHES) for (const sf of SFS) for (const r of D.single[bench][sf])
    r.markers.forEach((m, i) => { if (m) markers.push({bench, sf, q: r.q, engine: ENGINES[i], m, time: r.times[i]}); });
  const excl = D.clusterQueries["10000"].filter(r => r.r == null || r.g == null);
  const w = D.wins["10000"];
  let html = `<div class="card"><h3>Flagged results (markers in the source data)</h3>
    <p class="small muted">The source data flags individual results with single-letter markers. Their meaning is not defined in the data file; they are reproduced here verbatim.</p>
    <ul>${markers.map(m => `<li><code>${m.m}</code> — ${m.bench}, SF ${m.sf}, Q${m.q}, ${esc(m.engine)} (${fmtTime(m.time)} s)</li>`).join("")}</ul></div>`;
  html += `<div class="card"><h3>Cluster SF 10000 — queries excluded from wins</h3>
    <p class="small muted">At SF 10000, ${w[0]} + ${w[1]} = ${w[0]+w[1]} of 99 queries are counted in wins. The remaining ${99-w[0]-w[1]} queries have no valid head-to-head ratio; their statuses, verbatim:</p>
    <ul>${excl.map(r => `<li>Q${r.q} — ${esc(r.status)}</li>`).join("")}</ul></div>`;
  html += `<div class="card"><h3>Wins counting rule</h3>
    <p class="small">Wins are reported in the source data as <code>[Spark&nbsp;Rust, Spark&nbsp;Gluten]</code> per scale factor. The counts include ties: a query where both engines record the same time counts as a win for both. At SF 100, Q56 is a tie (10.16&nbsp;s for both engines), which is why the counts sum to 99 rather than 98. Queries where one engine has no valid result are excluded from both counts.</p></div>`;
  html += `<div class="card"><h3>Aggregate fields</h3>
    <p class="small">In the totals tables, <code>canonical</code> and <code>matched</code> are aggregate fields reported only on the “All SFs” rows of the source data; they are shown as reported (— where absent). Per-scale-factor <code>Δ</code> and <code>ratio</code> are relative to DuckDB 1.5.5, which is the baseline (Δ = 0, ratio = 1). The “All SFs” total equals the sum of the four scale-factor totals.</p></div>`;
  html += `<div class="card"><h3>Provenance</h3>
    <ul>
      <li>Input file: <code>engine-comparison-summary-data.json</code> (single input for this report; all figures derive from it).</li>
      <li>Underlying source recorded in the data: <code>${esc(D.source)}</code>, SHA-256 <code>${esc(D.sha256)}</code>.</li>
      <li>Hardware: ${esc(D.hardware.provenance)} — single node ${esc(D.hardware.single_node.sku)} (${D.hardware.single_node.cores} cores / ${D.hardware.single_node.ram_gb} GB); cluster ${D.hardware.cluster_workers.count} × ${esc(D.hardware.cluster_workers.sku)} (${D.hardware.cluster_workers.total_cores} cores / ${D.hardware.cluster_workers.total_ram_gb.toLocaleString("en-US")} GB total).</li>
      <li>This report adds no external data; derived figures (win counts, KPI ratios, chart axes) are arithmetic transformations of the input.</li>
    </ul></div>`;
  document.getElementById("notes-body").innerHTML = html;
})();

/* ---------- generic tabs (benchmark charts) ---------- */
document.querySelectorAll(".tabset").forEach(ts => {
  const tabs = ts.querySelectorAll(".tab[data-tab]");
  if (!tabs.length) return;
  tabs.forEach(t => t.addEventListener("click", () => {
    tabs.forEach(x => x.setAttribute("aria-selected", x === t));
    ts.querySelectorAll(".panel").forEach(p => p.hidden = p.dataset.panel !== t.dataset.tab);
  }));
});

/* ---------- tooltip ---------- */
(function tooltip(){
  const tip = document.getElementById("tip");
  let active = null;
  function show(el){
    active = el;
    const title = el.getAttribute("data-tt") || "";
    const body = (el.getAttribute("data-tb") || "").split("\n").map(line => {
      const [k, v] = line.split("\t");
      return `<div class="r"><span>${esc(k||"")}</span><span>${esc(v||"")}</span></div>`;
    }).join("");
    tip.innerHTML = (title ? `<div class="t">${esc(title)}</div>` : "") + body;
    tip.classList.add("on");
    tip.setAttribute("aria-hidden", "false");
  }
  function move(e){
    if (!active) return;
    const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
    let x = e.clientX + pad, y = e.clientY + pad;
    if (x + w > innerWidth - 8) x = e.clientX - w - pad;
    if (y + h > innerHeight - 8) y = e.clientY - h - pad;
    tip.style.left = x + "px"; tip.style.top = y + "px";
  }
  document.addEventListener("mouseover", e => {
    const el = e.target.closest("[data-tt]");
    if (el && el !== active) show(el);
    else if (!el && active){ active = null; tip.classList.remove("on"); tip.setAttribute("aria-hidden","true"); }
  });
  document.addEventListener("mousemove", move);
  document.addEventListener("scroll", () => { active = null; tip.classList.remove("on"); }, {passive:true});
})();
</script>
</body>
</html>
"""


def verify(data):
    """Sanity-check relationships the report's labels rely on; print warnings only."""
    warn = []
    engines = data["engines"]
    base = "DuckDB 1.5.5"
    for bench, rows in data["totals"].items():
        for r in rows:
            if r["engine"] == base:
                if not (r["diff"] == 0 and r["ratio"] == 1):
                    warn.append(f"{bench}: baseline row not diff=0/ratio=1")
        # 'all' == sum of SF totals
        for e in engines:
            s = sum(x["time"] for x in rows if x["sf"] in ("1", "10", "100", "1000") and x["engine"] == e)
            a = next(x["time"] for x in rows if x["sf"] == "all" and x["engine"] == e)
            if abs(s - a) > 1e-3:
                warn.append(f"{bench} {e}: all ({a}) != sum of SFs ({s})")
    # cluster ratio == r/g, diff == r-g
    for sf, rows in data["clusterQueries"].items():
        for r in rows:
            if r["r"] is not None and r["g"] is not None:
                if abs(r["ratio"] - r["r"] / r["g"]) > 0.002:
                    warn.append(f"cluster sf={sf} q={r['q']}: ratio != r/g")
                if abs(r["diff"] - (r["r"] - r["g"])) > 0.002:
                    warn.append(f"cluster sf={sf} q={r['q']}: diff != r-g")
    # wins counts match per-query comparison
    for sf, (wr, wg) in data["wins"].items():
        rows = data["clusterQueries"][sf]
        c_r = sum(1 for r in rows if r["r"] is not None and r["g"] is not None and r["r"] <= r["g"])
        c_g = sum(1 for r in rows if r["r"] is not None and r["g"] is not None and r["r"] > r["g"])
        if (c_r, c_g) != (wr, wg):
            warn.append(f"wins sf={sf}: reported {wr}/{wg}, computed {c_r}/{c_g}")
    return warn


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    for w in verify(data):
        print("WARN:", w)
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    html = TEMPLATE.replace("__DATA__", payload).replace("__GEN_DATE__", date.today().isoformat())
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT.name}: {OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
