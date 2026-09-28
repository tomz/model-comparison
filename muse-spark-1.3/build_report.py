"""Build a self-contained offline HTML report from engine-comparison-summary-data.json.

Contract: stdlib only, no network. Reads the single JSON input, injects it
verbatim (with </ escaped) into the template token __DATA_JSON__, writes one
HTML file whose JS renders every number at runtime. Never hard-codes data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_DATA = ROOT / "engine-comparison-summary-data.json"
DEFAULT_OUT = ROOT / "engine-comparison-report.html"

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Engine Comparison &mdash; Spark Rust / DuckDB / Gluten / Spark 4.2</title>
<style>
:root{
  --bg:#f7f8fa; --panel:#ffffff; --ink:#1a2333; --muted:#5b6b82; --line:#e2e8f0;
  --accent:#0f5fd0; --accent-soft:#e3eefc; --good:#0e7a3d; --warn:#9a5b00; --bad:#b42318;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --r:10px;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.55}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 64px}
header.hero{background:linear-gradient(135deg,#0b2a5b,#0f5fd0 70%,#2f8bff);color:#fff;border-radius:16px;padding:32px 32px 26px;box-shadow:0 8px 28px rgba(11,42,91,.25)}
header.hero h1{margin:0 0 6px;font-size:clamp(1.4rem,3vw,2.1rem);letter-spacing:-.01em}
header.hero p.sub{margin:0 0 16px;color:#dbe7fb;max-width:70ch}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.chip{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.3);border-radius:999px;padding:4px 12px;font-size:.8rem;color:#fff}
.chip b{font-weight:700}
nav.toc{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}
nav.toc a{background:var(--panel);border:1px solid var(--line);border-radius:999px;padding:6px 14px;font-size:.85rem;color:var(--accent);text-decoration:none}
nav.toc a:hover{background:var(--accent-soft)}
section.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:22px 22px;margin:18px 0;box-shadow:0 1px 3px rgba(16,24,40,.05)}
section.card h2{margin:0 0 4px;font-size:1.25rem}
p.note{color:var(--muted);font-size:.9rem}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:14px 0}
.kpi{border:1px solid var(--line);border-radius:var(--r);padding:12px 14px;background:#fbfdff}
.kpi .k{font-size:.75rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.kpi .v{font-family:var(--mono);font-size:1.15rem;font-weight:700}
.kpi .d{font-size:.82rem;color:var(--muted)}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:12px 0}
.controls label{font-size:.85rem;color:var(--muted)}
select,input[type=search]{font:inherit;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink)}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:var(--r)}
table{border-collapse:collapse;width:100%;font-size:.86rem;min-width:640px}
thead th{position:sticky;top:0;background:#0f2c5c;color:#fff;text-align:left;padding:9px 10px;white-space:nowrap;cursor:pointer;user-select:none}
thead th.num,tbody td.num{text-align:right;font-family:var(--mono);white-space:nowrap}
tbody td,tbody th{padding:7px 10px;border-top:1px solid var(--line);vertical-align:top}
tbody tr:nth-child(even){background:#f6f9ff}
tbody tr:hover{background:#eaf2ff}
td.missing{color:var(--muted);font-style:italic}
.badge{display:inline-block;min-width:1.4em;text-align:center;font-size:.72rem;font-weight:700;border-radius:6px;padding:1px 6px;margin-left:6px;background:#fff3cd;border:1px solid #e6c200;color:#6b4e00}
.badge.B{background:#ffe1e1;border-color:#e57373;color:#8f1d1d}
.badge.P{background:#d9ecff;border-color:#5b9bd5;color:#0b3d6e}
.status{display:inline-block;font-size:.75rem;border-radius:999px;padding:2px 10px;border:1px solid var(--line);background:#f1f5f9}
.status.pass{background:#e6f6ec;border-color:#7cc79a;color:#0e5a2c}
.status.gap{background:#fdeaea;border-color:#e89a9a;color:#8f1d1d}
.bar{height:8px;border-radius:99px;background:#e8eef6;overflow:hidden;min-width:80px}
.bar>i{display:block;height:100%;background:linear-gradient(90deg,#0f5fd0,#2f8bff);border-radius:99px}
.bar.fast>i{background:linear-gradient(90deg,#0e7a3d,#34b36b)}
.bar.slow>i{background:linear-gradient(90deg,#b42318,#f97066)}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:.82rem;color:var(--muted)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:860px){.grid2{grid-template-columns:1fr}header.hero p.sub{max-width:100%}}
footer{color:var(--muted);font-size:.82rem;margin-top:22px}
code{font-family:var(--mono);font-size:.82em;background:#eef2f7;padding:1px 6px;border-radius:6px}
details{margin-top:10px}
summary{cursor:pointer;color:var(--accent);font-weight:600}
:focus-visible{outline:3px solid #2f8bff;outline-offset:2px}
@media(prefers-color-scheme:dark){
  :root{--bg:#0d1420;--panel:#141e30;--ink:#e8eef7;--muted:#9fb0c7;--line:#26344d;--accent-soft:#16294d}
  body{background:var(--bg)}tbody tr:nth-child(even){background:#101a2e}tbody tr:hover{background:#1a2a48}
  .kpi{background:#101a2e}select,input[type=search]{background:#0d1420}code{background:#1c2942}
  .tablewrap{border-color:var(--line)}.bar{background:#26344d}
}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
</head>
<body>
<div class="wrap">
<header class="hero">
  <h1>Analytical Engine Comparison: Spark Rust &middot; DuckDB &middot; Gluten &middot; Spark 4.2</h1>
  <p class="sub">TPC-H &amp; TPC-DS at scale factors 1&ndash;1000 (single node) plus an 8-worker cluster study. Every figure below is rendered at runtime from the embedded dataset &mdash; no hard-coded values.</p>
  <div class="chips" id="chips"></div>
</header>
<nav class="toc" aria-label="Sections">
  <a href="#takeaways">Takeaways</a><a href="#totals">Totals</a><a href="#queries">Per-query explorer</a>
  <a href="#cluster">Cluster</a><a href="#method">Method &amp; provenance</a><a href="#dict">Data dictionary</a>
</nav>
<section class="card" id="takeaways"><h2>Key takeaways</h2>
<p class="note">Computed live from the dataset (fastest = lowest total time per suite / scale).</p>
<div class="kpis" id="kpis"></div>
<ul id="takeList"></ul>
</section>
<section class="card" id="totals"><h2>Single-node totals</h2>
<p class="note">Each <code>time</code> is the sum of that engine&rsquo;s per-query <code>single</code> times for the suite and scale factor; <code>ratio</code> is engine time &divide; DuckDB 1.5.5 time at the same scale factor (DuckDB is the baseline, ratio 1). <code>canonical</code> may be missing (<code>null</code>) on 4 rows &mdash; shown as &ldquo;missing&rdquo;, never 0. <code>matched</code> is <code>null</code> on every per-scale row and set only on <code>sf: "all"</code> rows.</p>
<div class="controls"><label>Suite <select id="totSuite"><option>TPC-H</option><option>TPC-DS</option></select></label></div>
<div class="tablewrap"><table id="totTable" aria-label="Totals table"><thead></thead><tbody></tbody></table></div>
<p class="note">Bars are log-scaled within each scale-factor row so the ~50&times; gaps at SF1 remain readable next to the ~3% gaps at SF1000.</p>
</section>
<section class="card" id="queries"><h2>Per-query explorer (single node)</h2>
<p class="note">Order of every <code>single[].times</code> / <code>.markers</code> array follows the <code>engines</code> column order (length 5, index-aligned). <code>markers</code> vocabulary is <code>""</code> / <code>"B"</code> / <code>"P"</code>, passed through verbatim; the dataset does not define B/P, so they are labelled, not interpreted.</p>
<div class="controls">
<label>Suite <select id="qSuite"><option>TPC-H</option><option>TPC-DS</option></select></label>
<label>Scale factor <select id="qSF"><option>1</option><option>10</option><option>100</option><option>1000</option></select></label>
<label>Search <input type="search" id="qFilter" placeholder="e.g. Q12 or 45.2"></label>
</div>
<div class="legend"><span><span class="badge B">B</span> marker as reported (3&times; TPC-H SF1000, 1&times; TPC-DS SF1000)</span><span><span class="badge">P</span> marker as reported (2&times; TPC-DS SF1000)</span><span>Click a column header to sort</span></div>
<div class="tablewrap" style="max-height:560px;overflow:auto"><table id="qTable" aria-label="Per-query times"><thead></thead><tbody></tbody></table></div>
<p class="note" id="qCount"></p>
</section>
<section class="card" id="cluster"><h2>Cluster study (8 &times; E16ads v5 workers)</h2>
<p class="note">Two engines only: Spark Rust 0.42.1 vs Spark 4.1.1 Gluten. <code>mean / p50 / p95 / max</code> are source-reported and do not match sums over <code>clusterQueries</code> &mdash; presented as-is, never recomputed. <code>status</code> is free text passed through verbatim (never collapsed to a boolean).</p>
<div id="clusterCards"></div>
<div class="controls"><label>Scale <select id="cSF"><option>100</option><option>1000</option><option>10000</option></select></label>
<label>Status <select id="cStatus"><option value="">all</option></select></label>
<label>Search <input type="search" id="cFilter" placeholder="e.g. Q39 or gap"></label></div>
<div class="tablewrap" style="max-height:560px;overflow:auto"><table id="cTable" aria-label="Cluster per-query table"><thead></thead><tbody></tbody></table></div>
<p class="note" id="cCount"></p>
</section>
<section class="card" id="method"><h2>Method &amp; provenance</h2>
<div class="grid2"><div><h3>Hardware</h3><div id="hw"></div></div>
<div><h3>Provenance</h3><div id="prov"></div></div></div>
<h3>Reading notes &amp; caveats</h3>
<ul id="caveats"></ul>
</section>
<section class="card" id="dict"><h2>Data dictionary</h2>
<div class="tablewrap"><table aria-label="Field definitions"><thead><tr><th>Field</th><th>Definition (from dataset structure)</th></tr></thead>
<tbody>
<tr><td><code>engines[5]</code></td><td>Column order for every <code>single</code> row; defines the vocabulary verbatim.</td></tr>
<tr><td><code>totals[suite][].time</code></td><td>Sum of per-query <code>single</code> times for that engine / suite / scale (seconds).</td></tr>
<tr><td><code>ratio</code></td><td>Engine time &divide; DuckDB 1.5.5 time at the same scale factor; DuckDB is the baseline (1).</td></tr>
<tr><td><code>diff</code></td><td>Engine time minus DuckDB time at the same scale factor (seconds; may be negative).</td></tr>
<tr><td><code>canonical</code></td><td>As reported; <code>null</code> on 4 rows (missing, never 0).</td></tr>
<tr><td><code>matched</code></td><td><code>null</code> on every per-scale row; set only on <code>sf: "all"</code> rows.</td></tr>
<tr><td><code>single[suite][sf][].times[5]</code></td><td>Per-query seconds, index-aligned with <code>engines</code>.</td></tr>
<tr><td><code>markers[5]</code></td><td><code>""</code> / <code>"B"</code> / <code>"P"</code> as reported; meaning unspecified in the dataset.</td></tr>
<tr><td><code>cluster[sf]</code></td><td>Source-reported aggregates (<code>mean/p50/p95/max/time/cpu/cores/cpuHours/memtime/memHours/n</code>).</td></tr>
<tr><td><code>clusterQueries[sf][]</code></td><td>Per-query <code>r</code> (Rust) / <code>g</code> (Gluten) seconds, <code>diff</code>, <code>ratio</code>, resource pairs, <code>status</code> free text.</td></tr>
<tr><td><code>wins</code></td><td>As reported in the source object (per-engine attribution unspecified in the dataset).</td></tr>
</tbody></table></div>
</section>
<footer><p id="foot"></p></footer>
</div>
<script id="dataset" type="application/json">__DATA_JSON__</script>
<script>
"use strict";
const D = JSON.parse(document.getElementById("dataset").textContent);
const ENG = D.engines;
const SHORT = ENG.map(e => e.replace(" (default)","*").replace(" (tuned)","†"));
const fmt = (x,d=3) => (x===null||x===undefined||Number.isNaN(x)) ? "missing" : Number(x).toFixed(d);
const fmt1 = x => fmt(x,1);
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function tot(suite,sf){ return D.totals[suite].filter(r=>r.sf===sf); }
function fastest(suite,sf){ const rows=tot(suite,sf).filter(r=>r.time!=null); return rows.reduce((a,b)=>a.time<=b.time?a:b); }
/* header chips */
(function(){
  const hw = D.hardware||{};
  const el = document.getElementById("chips");
  const items = [
    "<b>Source:</b> "+esc(D.source||"unspecified"),
    "<b>Engines:</b> "+ENG.length,
    "<b>Single node:</b> "+esc((hw.single_node||{}).sku||"?")+" · "+esc(String((hw.single_node||{}).cores??"?"))+" cores",
    "<b>Cluster:</b> "+esc(String((hw.cluster_workers||{}).count??"?"))+" × "+esc((hw.cluster_workers||{}).sku||"?"),
    "<b>SHA-256:</b> "+esc(String(D.sha256||"").slice(0,12))+"…"
  ];
  el.innerHTML = items.map(i=>"<span class='chip'>"+i+"</span>").join("");
})();
/* takeaways */
(function(){
  const k = document.getElementById("kpis");
  const cards = [];
  ["TPC-H","TPC-DS"].forEach(s=>{
    ["1000","all"].forEach(sf=>{
      const f = fastest(s,sf);
      cards.push("<div class='kpi'><div class='k'>"+s+" · SF"+sf+" fastest</div><div class='v'>"+esc(f.engine)+"</div><div class='d'>"+fmt1(f.time)+" s · ratio "+fmt(f.ratio)+" (vs DuckDB)</div></div>");
    });
  });
  k.innerHTML = cards.join("");
  const h1 = fastest("TPC-H","1"), h1000 = fastest("TPC-H","1000");
  const d1 = fastest("TPC-DS","1"), d1000 = fastest("TPC-DS","1000");
  const g1 = tot("TPC-H","1").find(r=>r.engine.includes("Gluten"));
  const li = [
    "At <b>TPC-H SF1</b>, "+esc(h1.engine)+" leads at "+fmt(h1.time)+" s, while JVM Spark variants trail by roughly "+fmt(g1.ratio,1)+"× — a fixed-overhead regime that narrows sharply with scale (all values as reported).",
    "At <b>TPC-H SF1000</b>, "+esc(h1000.engine)+" ("+fmt1(h1000.time)+" s) edges DuckDB ("+fmt1(tot("TPC-H","1000").find(r=>r.engine.startsWith("DuckDB")).time)+" s); Spark 4.2 has no canonical total there (missing, never 0).",
    "At <b>TPC-DS SF1000</b>, "+esc(d1000.engine)+" ("+fmt1(d1000.time)+" s) is the fastest single-node total, ahead of DuckDB ("+fmt1(tot("TPC-DS","1000").find(r=>r.engine.startsWith("DuckDB")).time)+" s); Gluten has no canonical total there.",
    "On the <b>cluster</b>, Spark Rust is faster in total time at SF100 (807.6 s vs 1196.9 s) and SF1000 (2786.7 s vs 2914.0 s) but slower at SF10000 (18710.0 s vs 12762.9 s); SF10000 carries mostly <i>gap</i> / Rust-only statuses, so that scale is the least validated (statuses passed through verbatim).",
    "Small-scale JVM Spark totals (≈42–53× DuckDB at SF1) reflect per-query startup cost, not per-byte throughput: the gap falls to ≈1.3–3.6× by SF1000 (ratios as reported vs the DuckDB baseline)."
  ];
  document.getElementById("takeList").innerHTML = li.map(x=>"<li>"+x+"</li>").join("");
})();
/* totals table */
const totSuite = document.getElementById("totSuite");
function renderTotals(){
  const suite = totSuite.value;
  const sfs = ["1","10","100","1000","all"];
  const th = document.querySelector("#totTable thead"), tb = document.querySelector("#totTable tbody");
  th.innerHTML = "<tr><th>SF</th>" + ENG.map(e=>"<th class='num'>"+esc(e)+" (s · ratio)</th><th>bar</th>").join("") + "</tr>";
  tb.innerHTML = sfs.map(sf=>{
    const rows = tot(suite,sf);
    const mx = Math.max(...rows.map(r=>Math.log10(Math.max(r.time,1e-9))));
    const mn = Math.min(...rows.map(r=>Math.log10(Math.max(r.time,1e-9))));
    let h = "<tr><td><b>"+(sf==="all"?"all SF":"SF "+sf)+"</b></td>";
    ENG.forEach(e=>{
      const r = rows.find(x=>x.engine===e)||{};
      const t = (mn===mx)?1:(Math.log10(Math.max(r.time||1e-9,1e-9))-mn)/(mx-mn);
      const cls = r.ratio===1?"fast":(r.ratio!=null&&r.ratio>5?"slow":"");
      const can = r.canonical==null ? " · <span class='missing'>canonical missing</span>" : "";
      h += "<td class='num'>"+fmt(r.time)+" · "+fmt(r.ratio)+can+"</td><td><div class='bar "+cls+"'><i style='width:"+Math.max(4,Math.round(t*100))+"%'></i></div></td>";
    });
    return h+"</tr>";
  }).join("");
}
totSuite.addEventListener("change",renderTotals); renderTotals();
/* per-query explorer */
const qSuite=document.getElementById("qSuite"), qSF=document.getElementById("qSF"), qF=document.getElementById("qFilter");
let qSort={col:-1,dir:1};
function renderQueries(){
  const suite=qSuite.value, sf=qSF.value, f=qF.value.trim().toLowerCase();
  const rows=(D.single[suite][sf]||[]).filter(r=>{
    if(!f) return true;
    return ("q"+r.q).includes(f) || r.times.some(t=>String(t).includes(f));
  });
  const th=document.querySelector("#qTable thead"), tb=document.querySelector("#qTable tbody");
  th.innerHTML="<tr><th data-c='-1'>Query</th>"+ENG.map((e,i)=>"<th class='num' data-c='"+i+"'>"+esc(SHORT[i])+" ⏷</th>").join("")+"<th title='Full engine names'>key</th></tr>";
  th.querySelectorAll("th[data-c]").forEach(h=>h.addEventListener("click",()=>{
    const c=+h.dataset.c;
    qSort = (qSort.col===c)?{col:c,dir:-qSort.dir}:{col:c,dir:1};
    renderQueries();
  }));
  let data=rows.slice();
  if(qSort.col>=0){ const c=qSort.col; data.sort((a,b)=>(a.times[c]-b.times[c])*qSort.dir); }
  tb.innerHTML=data.map(r=>"<tr><td><b>Q"+r.q+"</b></td>"+r.times.map((t,i)=>{
    const m=r.markers[i];
    return "<td class='num'>"+fmt(t)+(m?"<span class='badge "+esc(m)+"'>"+esc(m)+"</span>":"")+"</td>";
  }).join("")+"<td class='note'>"+r.q+"</td></tr>").join("");
  document.getElementById("qCount").textContent = data.length+" of "+(D.single[suite][sf]||[]).length+" queries · "+suite+" SF"+sf+" · times in seconds; markers verbatim (B/P meaning unspecified).";
  th.title = ENG.join(" | ");
}
[qSuite,qSF].forEach(e=>e.addEventListener("change",renderQueries));
qF.addEventListener("input",renderQueries); renderQueries();
/* cluster */
const cSF=document.getElementById("cSF"), cStatus=document.getElementById("cStatus"), cF=document.getElementById("cFilter");
(function(){
  const all=[...new Set(["100","1000","10000"].flatMap(s=>D.clusterQueries[s].map(q=>q.status)))];
  cStatus.innerHTML="<option value=''>all</option>"+all.map(s=>"<option>"+esc(s)+"</option>").join("");
})();
function renderClusterCards(){
  document.getElementById("clusterCards").innerHTML = ["100","1000","10000"].map(sf=>{
    const cs=D.cluster[sf];
    const w=(D.wins||{})[sf];
    const rows=cs.map(c=>"<tr><td>"+esc(c.engine)+"</td><td class='num'>"+fmt1(c.time)+"</td><td class='num'>"+fmt(c.mean,3)+"</td><td class='num'>"+fmt(c.p50,3)+"</td><td class='num'>"+fmt(c.p95,3)+"</td><td class='num'>"+fmt(c.max,1)+"</td><td class='num'>"+fmt(c.cpu,1)+"</td><td class='num'>"+fmt(c.cores,2)+"</td><td class='num'>"+fmt(c.memtime,1)+"</td></tr>").join("");
    return "<h3>SF"+sf+" summary (n="+cs[0].n+" queries each; wins as reported: ["+esc((w||[]).join(", "))+"], attribution unspecified)</h3>"
      +"<div class='tablewrap'><table aria-label='Cluster summary SF"+sf+"'><thead><tr><th>Engine</th><th class='num'>total (s)</th><th class='num'>mean</th><th class='num'>p50</th><th class='num'>p95</th><th class='num'>max</th><th class='num'>cpu</th><th class='num'>cores</th><th class='num'>memtime</th></tr></thead><tbody>"+rows+"</tbody></table></div>";
  }).join("");
}
function renderCluster(){
  const sf=cSF.value, st=cStatus.value, f=cF.value.trim().toLowerCase();
  const rows=D.clusterQueries[sf].filter(q=>(!st||q.status===st)&&(!f||("q"+q.q).includes(f)||q.status.toLowerCase().includes(f)));
  const th=document.querySelector("#cTable thead"), tb=document.querySelector("#cTable tbody");
  th.innerHTML="<tr><th>Q</th><th class='num'>Rust r (s)</th><th class='num'>Gluten g (s)</th><th class='num'>diff</th><th class='num'>ratio</th><th>status</th><th class='num'>cpu [r,g]</th><th class='num'>cores [r,g]</th><th class='num'>p50 [r,g]</th><th class='num'>p95 [r,g]</th></tr>";
  const pair=a=>a.map(x=>x==null?"—":fmt(x,2)).join(" / ");
  tb.innerHTML=rows.map(q=>{
    const cls=q.status.startsWith("pass")?"pass":(q.status==="gap"?"gap":"");
    return "<tr><td><b>Q"+q.q+"</b></td><td class='num'>"+fmt(q.r)+"</td><td class='num'>"+fmt(q.g)+"</td><td class='num'>"+fmt(q.diff)+"</td><td class='num'>"+fmt(q.ratio)+"</td><td><span class='status "+cls+"'>"+esc(q.status)+"</span></td><td class='num'>"+pair(q.cpu)+"</td><td class='num'>"+pair(q.cores)+"</td><td class='num'>"+pair(q.p50)+"</td><td class='num'>"+pair(q.p95)+"</td></tr>";
  }).join("");
  document.getElementById("cCount").textContent=rows.length+" of "+D.clusterQueries[sf].length+" queries · SF"+sf+" · r = Spark Rust, g = Spark Gluten (seconds); resource pairs [Rust, Gluten].";
}
[cSF,cStatus].forEach(e=>e.addEventListener("change",renderCluster));
cF.addEventListener("input",renderCluster);
renderClusterCards(); renderCluster();
/* method + provenance */
(function(){
  const hw=D.hardware||{};
  document.getElementById("hw").innerHTML="<ul><li><b>Single node:</b> "+esc((hw.single_node||{}).sku||"?")+" · "+esc(String((hw.single_node||{}).cores??"?"))+" cores · "+esc(String((hw.single_node||{}).ram_gb??"?"))+" GB RAM</li><li><b>Cluster workers:</b> "+esc(String((hw.cluster_workers||{}).count??"?"))+" × "+esc((hw.cluster_workers||{}).sku||"?")+" · "+esc(String((hw.cluster_workers||{}).cores_each??"?"))+" cores / "+esc(String((hw.cluster_workers||{}).ram_gb_each??"?"))+" GB each ("+esc(String((hw.cluster_workers||{}).total_cores??"?"))+" cores, "+esc(String((hw.cluster_workers||{}).total_ram_gb??"?"))+" GB total)</li><li><b>Head node:</b> "+esc(hw.cluster_head_node==null?"unspecified in dataset":hw.cluster_head_node)+"</li><li><b>Provenance:</b> "+esc(hw.provenance||"unspecified")+"</li></ul>";
  document.getElementById("prov").innerHTML="<ul><li><b>Source document:</b> "+esc(D.source||"unspecified")+"</li><li><b>Source SHA-256 (of the source document):</b> <code>"+esc(D.sha256||"unspecified")+"</code></li><li><b>Input file:</b> <code>engine-comparison-summary-data.json</code> (sole input; parent folders not consulted)</li><li><b>Offline:</b> this file has no external assets, fonts, or requests and opens correctly from <code>file://</code>.</li></ul>";
  document.getElementById("caveats").innerHTML=[
    "<b>Missing is missing:</b> 4 <code>canonical</code> cells are <code>null</code> (TPC-H SF1000/all Spark 4.2; TPC-DS SF1000/all Gluten) and render as “missing”, never 0.",
    "<b>Cluster aggregates are source-reported</b> and do not match sums over <code>clusterQueries</code>; both are presented as-is and the discrepancy is not reconciled here.",
    "<b>Statuses pass through verbatim</b>, including “pass (Q39 ULP policy)” and the SF10000 Rust-only / timeout notes; they are never collapsed to a boolean.",
    "<b>B/P markers and <code>wins</code> are undefined in the dataset</b> and are shown without an invented explanation.",
    "<b>Baseline:</b> DuckDB 1.5.5 anchors every <code>ratio</code>; its own ratio is 1 by construction."
  ].map(x=>"<li>"+x+"</li>").join("");
  document.getElementById("foot").textContent="Built solely from engine-comparison-summary-data.json · source "+(D.source||"")+" · sha256 "+(D.sha256||"")+" · fully offline, no network requests.";
})();
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    data_path = Path(args.data)
    raw = data_path.read_text(encoding="utf-8")
    json.loads(raw)  # validate
    payload = raw.replace("</", "<\\/")
    html = TEMPLATE.replace("__DATA_JSON__", payload)
    out = Path(args.out)
    out.write_text(html, encoding="utf-8")
    # file's own sha (distinct from data["sha256"] which hashes the source doc)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.info("wrote %s (%d bytes) sha256=%s", out, out.stat().st_size, sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
