#!/usr/bin/env python3
"""Generate a self-contained HTML report from engine-comparison-summary-data.json."""

import html
import json
import statistics as st

SRC = "engine-comparison-summary-data.json"
OUT = "engine-comparison-report.html"

with open(SRC) as fh:
    D = json.load(fh)

ENGINES = D["engines"]
HW = D["hardware"]
SF_ORDER = ["1", "10", "100", "1000"]
CLUSTER_SF = ["100", "1000", "10000"]

# Short labels + series colors for the five single-node engines.
SHORT = {
    "Spark Rust 0.42.1 (default)": "Spark Rust (default)",
    "Spark Rust 0.42.1 (tuned)": "Spark Rust (tuned)",
    "DuckDB 1.5.5": "DuckDB 1.5.5",
    "Spark 4.1.1 Gluten": "Spark 4.1.1 Gluten",
    "Spark 4.2": "Spark 4.2",
}
COLOR = {
    "Spark Rust 0.42.1 (default)": "var(--c-rust)",
    "Spark Rust 0.42.1 (tuned)": "var(--c-rust2)",
    "DuckDB 1.5.5": "var(--c-duck)",
    "Spark 4.1.1 Gluten": "var(--c-glu)",
    "Spark 4.2": "var(--c-sp42)",
}
BASE = "DuckDB 1.5.5"


def e(s):
    """Escape for HTML text/attribute context."""
    return html.escape(str(s), quote=True)


def secs(v, digits=3):
    """Format seconds with thousands separators."""
    if v is None:
        return "—"
    return f"{v:,.{digits}f}"


def dur(v):
    """Seconds -> compact human duration."""
    if v is None:
        return "—"
    if v < 1:
        return f"{v * 1000:,.0f} ms"
    if v < 90:
        return f"{v:,.2f} s"
    if v < 5400:
        m, s = divmod(v, 60)
        return f"{int(m)}m {s:04.1f}s"
    h, rem = divmod(v, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}h {int(m):02d}m"


def ratio_pill(r, invert=False):
    """Colored pill for a speedup ratio (lower is better when invert=False)."""
    if r is None:
        return '<span class="pill">n/a</span>'
    good, bad = (r <= 1.05, r >= 1.5) if not invert else (r >= 0.95, r <= 0.67)
    cls = "good" if good else ("bad" if bad else "warn")
    return f'<span class="pill {cls}">{r:,.3f}&times;</span>'


def bar(pct, color, label=""):
    """Horizontal bar; pct is 0-100 of the row maximum."""
    w = max(float(pct), 0.35)
    return (
        f'<div class="bar" role="img" aria-label="{e(label)}">'
        f'<span style="width:{w:.2f}%;background:{color}"></span></div>'
    )


# --------------------------------------------------------------------------
# Derived figures
# --------------------------------------------------------------------------
totals = {b: {} for b in ("TPC-H", "TPC-DS")}
for bench, rows in D["totals"].items():
    for r in rows:
        totals[bench].setdefault(r["sf"], {})[r["engine"]] = r

single = D["single"]
cluster = D["cluster"]
cq = D["clusterQueries"]
wins = D["wins"]

# Per-SF per-engine aggregates for single-node runs.
agg = {}
for bench, sfs in single.items():
    for sf, rows in sfs.items():
        for i, eng in enumerate(ENGINES):
            ts = [r["times"][i] for r in rows]
            agg[(bench, sf, eng)] = {
                "mean": st.mean(ts),
                "median": st.median(ts),
                "min": min(ts),
                "max": max(ts),
                "total": sum(ts),
            }

# Headline: all-SF totals row.
allrow = {b: totals[b]["all"] for b in ("TPC-H", "TPC-DS")}

# Best engine per (bench, sf) by total time.
best = {}
for bench, sfs in single.items():
    for sf in SF_ORDER:
        best[(bench, sf)] = min(ENGINES, key=lambda x: agg[(bench, sf, x)]["total"])

# Cluster derived facts.
cluster_stats = {}
for sf in CLUSTER_SF:
    rows = cq[sf]
    valid = [r for r in rows if r["r"] is not None and r["g"] is not None]
    r_tot = cluster[sf][0]
    g_tot = cluster[sf][1]
    cluster_stats[sf] = {
        "n": len(rows),
        "valid": len(valid),
        "r_wins": wins[sf][0],
        "g_wins": wins[sf][1],
        "r_time": r_tot["time"],
        "g_time": g_tot["time"],
        "time_ratio": r_tot["time"] / g_tot["time"],
        "cpu_ratio": g_tot["cpu"] / r_tot["cpu"],
        "cores_r": r_tot["cores"],
        "cores_g": g_tot["cores"],
        "memtime_ratio": g_tot["memtime"] / r_tot["memtime"],
        "cpu_hours_r": r_tot["cpuHours"],
        "cpu_hours_g": g_tot["cpuHours"],
        "mem_hours_r": r_tot["memHours"],
        "mem_hours_g": g_tot["memHours"],
        "p50_r": r_tot["p50"],
        "p50_g": g_tot["p50"],
        "p95_r": r_tot["p95"],
        "p95_g": g_tot["p95"],
        "max_r": r_tot["max"],
        "max_g": g_tot["max"],
        "mean_r": r_tot["mean"],
        "mean_g": g_tot["mean"],
        "n_r": r_tot["n"],
        "n_g": g_tot["n"],
    }

# Cluster exceptions (non-pass/non-gap statuses).
exceptions = {}
for sf in CLUSTER_SF:
    ex = [r for r in cq[sf] if r["status"] not in ("pass", "gap")]
    if ex:
        exceptions[sf] = ex

# Single-node data-quality markers.
marker_rows = []
for bench, sfs in single.items():
    for sf, rows in sfs.items():
        for r in rows:
            ms = [(i, m) for i, m in enumerate(r["markers"]) if m]
            if ms:
                marker_rows.append((bench, sf, r["q"], ms, r["times"]))

MARKER_TEXT = {"B": "best-of flagged", "P": "partial / provisional"}

# Cluster per-SF worst regressions and biggest wins.
cluster_extremes = {}
for sf in CLUSTER_SF:
    rows = [r for r in cq[sf] if r["diff"] is not None]
    cluster_extremes[sf] = {
        "worst": sorted(rows, key=lambda r: -r["diff"])[:5],
        "best": sorted(rows, key=lambda r: r["diff"])[:5],
    }

# --------------------------------------------------------------------------
# HTML fragments
# --------------------------------------------------------------------------
parts = []
A = parts.append

A(
    """<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Query Engine Comparison — TPC-H / TPC-DS Benchmark Report</title>
<meta name="description" content="Self-contained benchmark report comparing five single-node query engines on TPC-H and TPC-DS, plus a two-engine distributed cluster comparison.">
<style>
:root{
  --fg:#15181d; --fg-soft:#454b55; --fg-mute:#666d79;
  --bg:#fbfbf9; --bg-soft:#f2f2ee; --bg-card:#ffffff; --bg-sunk:#f7f7f4;
  --accent:#1f5fa8; --accent-soft:#e7eff9; --on-accent:#ffffff;
  --good:#12603c; --good-soft:#e0f1e7;
  --warn:#8a4f12; --warn-soft:#fdf1e0;
  --bad:#a92b45; --bad-soft:#fbe8ec;
  --border:#d9d9d2; --border-soft:#e9e9e4;
  --c-rust:#1f5fa8; --c-rust2:#4a8fd4; --c-duck:#12603c;
  --c-glu:#a92b45; --c-sp42:#c47f18;
  --radius:12px; --radius-sm:8px;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
  --shadow:0 1px 2px rgba(20,24,32,.05),0 4px 14px rgba(20,24,32,.045);
}
:root[data-theme="dark"]{
  --fg:#e7e9ec; --fg-soft:#b7bcc5; --fg-mute:#8d939e;
  --bg:#11141a; --bg-soft:#191d25; --bg-card:#1b1f27; --bg-sunk:#161a21;
  --accent:#79aeff; --accent-soft:#17263f; --on-accent:#0d1a2e;
  --good:#6ecb93; --good-soft:#12321f;
  --warn:#e3aa60; --warn-soft:#3a2a13;
  --bad:#ec8fa4; --bad-soft:#3f1720;
  --border:#2f3540; --border-soft:#252a32;
  --c-rust:#79aeff; --c-rust2:#a8cbff; --c-duck:#6ecb93;
  --c-glu:#ec8fa4; --c-sp42:#e3aa60;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 4px 14px rgba(0,0,0,.3);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --fg:#e7e9ec; --fg-soft:#b7bcc5; --fg-mute:#8d939e;
    --bg:#11141a; --bg-soft:#191d25; --bg-card:#1b1f27; --bg-sunk:#161a21;
    --accent:#79aeff; --accent-soft:#17263f; --on-accent:#0d1a2e;
    --good:#6ecb93; --good-soft:#12321f;
    --warn:#e3aa60; --warn-soft:#3a2a13;
    --bad:#ec8fa4; --bad-soft:#3f1720;
    --border:#2f3540; --border-soft:#252a32;
    --c-rust:#79aeff; --c-rust2:#a8cbff; --c-duck:#6ecb93;
    --c-glu:#ec8fa4; --c-sp42:#e3aa60;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 4px 14px rgba(0,0,0,.3);
  }
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);
  font-size:15.5px;line-height:1.62;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 28px 96px}
a{color:var(--accent)}
:focus-visible{outline:3px solid var(--accent);outline-offset:2px;border-radius:4px}
img,svg{max-width:100%}
h1,h2,h3,h4{line-height:1.22;margin:0}
h1{font-size:clamp(28px,4.4vw,40px);font-weight:720;letter-spacing:-.022em}
h2{font-size:clamp(21px,2.6vw,26px);font-weight:700;letter-spacing:-.014em;
  margin:64px 0 6px;scroll-margin-top:76px}
h3{font-size:17.5px;font-weight:660;margin:34px 0 8px}
h4{font-size:14.5px;font-weight:660;margin:22px 0 6px}
p{margin:0 0 15px}
.lede{color:var(--fg-soft);font-size:17.5px;max-width:76ch;margin-top:14px}
.muted{color:var(--fg-mute)}
.small{font-size:13px}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
.num{font-variant-numeric:tabular-nums}

/* ---------- masthead ---------- */
.masthead{border-bottom:1px solid var(--border);background:var(--bg-card);
  position:sticky;top:0;z-index:50;box-shadow:0 1px 0 rgba(20,24,32,.04)}
.masthead-in{max-width:1180px;margin:0 auto;padding:11px 28px;
  display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.brand{font-weight:700;font-size:14.5px;letter-spacing:-.01em;white-space:nowrap}
.brand span{color:var(--fg-mute);font-weight:500}
.mast-nav{display:flex;gap:4px;flex-wrap:wrap;margin-left:auto}
.mast-nav a{font-size:13px;color:var(--fg-soft);text-decoration:none;
  padding:5px 10px;border-radius:7px;white-space:nowrap}
.mast-nav a:hover{background:var(--bg-soft);color:var(--accent)}
.theme-btn{border:1px solid var(--border);background:var(--bg);color:var(--fg-soft);
  border-radius:8px;padding:6px 11px;font-size:13px;cursor:pointer;font-family:inherit}
.theme-btn:hover{color:var(--accent);border-color:var(--accent)}

/* ---------- hero ---------- */
.hero{padding:60px 0 8px}
.eyebrow{font-size:11.5px;text-transform:uppercase;letter-spacing:.14em;
  color:var(--accent);font-weight:680;margin-bottom:14px}
.hero-grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(0,1fr);
  gap:44px;align-items:start}
@media (max-width:900px){.hero-grid{grid-template-columns:1fr;gap:28px}}
.factlist{border:1px solid var(--border);border-radius:var(--radius);
  background:var(--bg-card);padding:6px 18px;box-shadow:var(--shadow)}
.factlist div{display:flex;justify-content:space-between;gap:16px;
  padding:9px 0;border-bottom:1px solid var(--border-soft);font-size:13.5px}
.factlist div:last-child{border-bottom:0}
.factlist dt,.factlist .k{color:var(--fg-mute);flex:0 1 auto;min-width:0}
.factlist .v{font-weight:600;text-align:right;flex:1 1 auto;min-width:0}
@media (max-width:520px){
  .factlist div{flex-direction:column;gap:2px}
  .factlist .v{text-align:left}
}

/* ---------- KPI ---------- */
.kpis{display:grid;gap:16px;margin:34px 0 0;
  grid-template-columns:repeat(auto-fit,minmax(min(100%,215px),1fr))}
.kpi{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);
  padding:17px 19px;box-shadow:var(--shadow)}
.kpi .n{font-size:29px;font-weight:720;letter-spacing:-.028em;line-height:1.1}
.kpi .l{color:var(--fg-mute);font-size:12.5px;margin-top:5px;line-height:1.45}
.kpi .sub{font-size:12px;color:var(--fg-soft);margin-top:7px}

/* ---------- cards / layout ---------- */
.card{background:var(--bg-card);border:1px solid var(--border);
  border-radius:var(--radius);padding:20px 22px;box-shadow:var(--shadow)}
.grid2{display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(min(100%,330px),1fr))}
.grid3{display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(min(100%,250px),1fr))}
.callout{border-left:3px solid var(--accent);background:var(--accent-soft);
  padding:14px 18px;border-radius:0 var(--radius-sm) var(--radius-sm) 0;margin:20px 0}
.callout.good{border-color:var(--good);background:var(--good-soft)}
.callout.warn{border-color:var(--warn);background:var(--warn-soft)}
.callout.bad{border-color:var(--bad);background:var(--bad-soft)}
.callout p:last-child{margin-bottom:0}
.callout strong{font-weight:680}

/* ---------- pills ---------- */
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;
  font-weight:640;background:var(--accent-soft);color:var(--accent);white-space:nowrap}
.pill.good{background:var(--good-soft);color:var(--good)}
.pill.warn{background:var(--warn-soft);color:var(--warn)}
.pill.bad{background:var(--bad-soft);color:var(--bad)}
.pill.plain{background:var(--bg-soft);color:var(--fg-soft)}
.legend{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0 4px;font-size:12.5px;color:var(--fg-soft)}
.legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px;
  vertical-align:-1px}

/* ---------- tables ---------- */
.table-scroll{overflow-x:auto;border:1px solid var(--border);border-radius:var(--radius);
  background:var(--bg-card);box-shadow:var(--shadow)}
table{width:100%;border-collapse:collapse;font-size:14px}
caption{text-align:left;padding:13px 16px 0;font-size:12.5px;color:var(--fg-mute)}
th,td{padding:9px 14px;text-align:right;border-bottom:1px solid var(--border-soft);
  white-space:nowrap}
th:first-child,td:first-child{text-align:left}
/* key/value tables: wrap instead of forcing width */
table.kv{font-size:13.5px}
table.kv th,table.kv td{white-space:normal;padding:7px 0;vertical-align:top}
table.kv th[scope="row"]{width:44%;padding-right:14px;color:var(--fg-mute);font-weight:500}
thead th{position:sticky;top:52px;background:var(--bg-card);z-index:2;
  font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--fg-mute);
  font-weight:660;border-bottom:2px solid var(--border)}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:var(--bg-sunk)}
tr.tot td{font-weight:680;background:var(--bg-sunk);border-top:2px solid var(--border)}
tr.tot:hover td{background:var(--bg-sunk)}
td.win{color:var(--good);font-weight:660}
th[scope="row"]{font-weight:600;color:var(--fg)}
.tbl-note{font-size:12.5px;color:var(--fg-mute);margin:9px 2px 0}

/* ---------- bars ---------- */
.bar{height:9px;background:var(--bg-soft);border-radius:5px;overflow:hidden;min-width:70px}
.bar span{display:block;height:100%;border-radius:5px}
.barrow{display:grid;grid-template-columns:minmax(120px,190px) 1fr minmax(84px,auto);
  gap:12px;align-items:center;padding:5px 0}
.barrow .bl{font-size:13px;color:var(--fg-soft);overflow:hidden;text-overflow:ellipsis}
.barrow .bv{font-size:12.5px;color:var(--fg-mute);text-align:right;font-variant-numeric:tabular-nums}
@media (max-width:560px){
  .barrow{grid-template-columns:1fr;gap:3px}
  .barrow .bv{text-align:left}
}

/* ---------- details / tabs ---------- */
details{border:1px solid var(--border);border-radius:var(--radius);background:var(--bg-card);
  margin:16px 0;box-shadow:var(--shadow)}
details>summary{cursor:pointer;padding:13px 18px;font-weight:640;font-size:14.5px;
  list-style:none;display:flex;align-items:center;gap:10px}
details>summary::-webkit-details-marker{display:none}
details>summary::before{content:"▸";color:var(--accent);font-size:12px;transition:transform .15s}
details[open]>summary::before{transform:rotate(90deg)}
details>summary:hover{color:var(--accent)}
.dbody{padding:2px 18px 18px;border-top:1px solid var(--border-soft)}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:16px 0 0}
.tab{border:1px solid var(--border);background:var(--bg-card);color:var(--fg-soft);
  border-radius:8px;padding:7px 14px;font-size:13.5px;cursor:pointer;font-family:inherit}
.tab:hover{color:var(--accent);border-color:var(--accent)}
.tab[aria-selected="true"]{background:var(--accent);color:var(--on-accent);border-color:var(--accent)}
.panel[hidden]{display:none}

/* ---------- footer ---------- */
footer{border-top:1px solid var(--border);margin-top:72px;padding-top:26px;
  color:var(--fg-mute);font-size:13px}
footer ol{padding-left:20px;margin:8px 0}
footer li{margin-bottom:5px}
code{font-family:var(--mono);font-size:.88em;background:var(--bg-soft);
  padding:1px 5px;border-radius:5px;word-break:break-word}
.sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;
  clip:rect(0 0 0 0);white-space:nowrap;border:0}
@media (max-width:640px){
  .wrap{padding:0 16px 72px}
  .hero{padding:38px 0 4px}
  .masthead-in{padding:10px 16px}
  .brand{font-size:13.5px}
  th,td{padding:8px 11px}
}
@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  details>summary::before{transition:none}
}
@media print{
  .masthead,.theme-btn,.tabs{display:none}
  body{background:#fff}
  details{border:0}
  details>summary{font-size:16px;padding-left:0}
  .panel[hidden]{display:block}
  h2{page-break-after:avoid}
  table{page-break-inside:auto}
}
</style>
</head>
<body>
<header class="masthead">
  <div class="masthead-in">
    <div class="brand">Query Engine Comparison <span>· TPC-H / TPC-DS</span></div>
    <nav class="mast-nav" aria-label="Sections">
      <a href="#summary">Summary</a>
      <a href="#method">Method</a>
      <a href="#single">Single node</a>
      <a href="#tpch">TPC-H</a>
      <a href="#tpcds">TPC-DS</a>
      <a href="#queries">Per query</a>
      <a href="#cluster">Cluster</a>
      <a href="#caveats">Caveats</a>
    </nav>
    <button type="button" class="theme-btn" id="themeBtn" aria-label="Switch colour theme">◐ theme</button>
  </div>
</header>
<div class="wrap">
"""
)

# ---------------------------------------------------------------- hero
tpch_all = allrow["TPC-H"]
tpcds_all = allrow["TPC-DS"]
rust_d = tpch_all["Spark Rust 0.42.1 (default)"]
glu_h = tpch_all["Spark 4.1.1 Gluten"]
sp42_h = tpch_all["Spark 4.2"]
duck_ds = tpcds_all["DuckDB 1.5.5"]
rust_ds = tpcds_all["Spark Rust 0.42.1 (tuned)"]
glu_ds = tpcds_all["Spark 4.1.1 Gluten"]

A(
    f"""<section class="hero" aria-labelledby="title">
<div class="hero-grid">
  <div>
    <div class="eyebrow">Benchmark report · generated from engine-comparison-summary-data.json</div>
    <h1 id="title">Five query engines on TPC-H and TPC-DS,<br>from 1&nbsp;GB to 10&nbsp;TB</h1>
    <p class="lede">Two independent comparisons on the same Azure hardware: a five-engine
    single-node sweep across four scale factors, and a two-engine distributed run at
    SF&nbsp;100 / 1&nbsp;000 / 10&nbsp;000. Every number below is computed from the source
    JSON — nothing is estimated or carried over from elsewhere.</p>
    <p class="small muted" style="margin-top:18px">
      Source file <code>{e(D["source"])}</code><br>
      SHA-256 <code>{e(D["sha256"])}</code>
    </p>
  </div>
  <dl class="factlist">
    <div><dt class="k">Engines compared</dt><dd class="v">5 single-node · 2 distributed</dd></div>
    <div><dt class="k">Benchmarks</dt><dd class="v">TPC-H (22 queries) · TPC-DS (99 queries)</dd></div>
    <div><dt class="k">Single-node scale factors</dt><dd class="v">SF 1 · 10 · 100 · 1&nbsp;000</dd></div>
    <div><dt class="k">Cluster scale factors</dt><dd class="v">SF 100 · 1&nbsp;000 · 10&nbsp;000</dd></div>
    <div><dt class="k">Single-node hardware</dt><dd class="v">{e(HW["single_node"]["sku"])} · {HW["single_node"]["cores"]} vCPU · {HW["single_node"]["ram_gb"]} GB</dd></div>
    <div><dt class="k">Cluster hardware</dt><dd class="v">{HW["cluster_workers"]["count"]}× {e(HW["cluster_workers"]["sku"])} · {HW["cluster_workers"]["total_cores"]} vCPU · {HW["cluster_workers"]["total_ram_gb"]} GB</dd></div>
    <div><dt class="k">Hardware provenance</dt><dd class="v">{e(HW["provenance"])}</dd></div>
  </dl>
</div>
</section>
"""
)

# ---------------------------------------------------------------- KPIs
c100 = cluster_stats["100"]
A(
    f"""<section aria-label="Headline results">
<div class="kpis">
  <div class="kpi">
    <div class="n">{rust_d["ratio"]:.2f}&times;</div>
    <div class="l">Spark Rust 0.42.1 (default) total TPC-H time vs DuckDB 1.5.5, summed over SF 1–1000</div>
    <div class="sub">{dur(rust_d["time"])} vs {dur(tpch_all[BASE]["time"])}</div>
  </div>
  <div class="kpi">
    <div class="n">{glu_h["ratio"]:.2f}&times;</div>
    <div class="l">Spark 4.1.1 Gluten total TPC-H time vs DuckDB 1.5.5, summed over SF 1–1000</div>
    <div class="sub">{dur(glu_h["time"])} vs {dur(tpch_all[BASE]["time"])}</div>
  </div>
  <div class="kpi">
    <div class="n">{sp42_h["ratio"]:.2f}&times;</div>
    <div class="l">Spark 4.2 total TPC-H time vs DuckDB 1.5.5, summed over SF 1–1000</div>
    <div class="sub">{dur(sp42_h["time"])} vs {dur(tpch_all[BASE]["time"])}</div>
  </div>
  <div class="kpi">
    <div class="n">{rust_ds["ratio"]:.3f}&times;</div>
    <div class="l">Spark Rust 0.42.1 (tuned) total TPC-DS time vs DuckDB 1.5.5 — the only engine to beat DuckDB overall</div>
    <div class="sub">{dur(rust_ds["time"])} vs {dur(duck_ds["time"])}</div>
  </div>
  <div class="kpi">
    <div class="n">{c100["r_wins"]}–{c100["g_wins"]}</div>
    <div class="l">Query wins for Spark Rust 0.42.1 vs Spark 4.1.1 Gluten at cluster SF 100</div>
    <div class="sub">Wall clock {dur(c100["r_time"])} vs {dur(c100["g_time"])}</div>
  </div>
  <div class="kpi">
    <div class="n">{cluster_stats["10000"]["time_ratio"]:.2f}&times;</div>
    <div class="l">Cluster SF 10&nbsp;000 wall clock: Spark Rust slower than Gluten — the trend reverses at the top end</div>
    <div class="sub">{dur(cluster_stats["10000"]["r_time"])} vs {dur(cluster_stats["10000"]["g_time"])}</div>
  </div>
</div>
</section>
"""
)

# ---------------------------------------------------------------- summary
A(
    f"""<section id="summary">
<h2>Executive summary</h2>
<p class="muted">What the measurements support, stated at the level the data can carry.</p>
<div class="grid2">
  <div class="card">
    <h3>Single node: two performance tiers</h3>
    <p>The five engines split cleanly in two. <strong>DuckDB 1.5.5</strong> and
    <strong>Spark Rust 0.42.1</strong> (default and tuned) converge as data grows — within
    {(max(totals["TPC-H"]["100"][x]["ratio"] for x in ENGINES[:3]) - 1) * 100:.0f}% of each other at
    SF&nbsp;100 and {(max(totals["TPC-H"]["1000"][x]["ratio"] for x in ENGINES[:3]) - 1) * 100:.0f}% at
    SF&nbsp;1000 on TPC-H — though DuckDB is
    {(max(totals["TPC-H"]["1"][x]["ratio"] for x in ENGINES[:3]) - 1) * 100:.0f}% faster at SF&nbsp;1.
    <strong>Spark 4.1.1 Gluten</strong> and <strong>Spark 4.2</strong> carry a large fixed per-query
    cost — every query costs at least
    {min(min(r["times"][3] for r in single["TPC-H"]["1"]), min(r["times"][4] for r in single["TPC-H"]["1"])):.1f}&nbsp;s
    at SF&nbsp;1 regardless of the query — and are
    {min(totals["TPC-H"]["1"][x]["ratio"] for x in ENGINES[3:]):.0f}&times; to
    {max(totals["TPC-H"]["1"][x]["ratio"] for x in ENGINES[3:]):.0f}&times; slower on TPC-H at
    SF&nbsp;1.</p>
    <p class="small muted" style="margin-bottom:0">At SF&nbsp;1 the slowest TPC-H query for Spark 4.2
    takes {secs(max(r["times"][4] for r in single["TPC-H"]["1"]))}&nbsp;s; DuckDB's slowest takes
    {secs(max(r["times"][2] for r in single["TPC-H"]["1"]))}&nbsp;s.</p>
  </div>
  <div class="card">
    <h3>The gap closes as data grows</h3>
    <p>On TPC-H the slowest engine is
    {max(totals["TPC-H"]["1"][x]["ratio"] for x in ENGINES):.0f}&times; slower than DuckDB at
    SF&nbsp;1 but only {max(totals["TPC-H"]["1000"][x]["ratio"] for x in ENGINES):.2f}&times; slower at
    SF&nbsp;1000, because their cost is dominated by fixed per-query overhead rather than data volume.
    The convergence is not monotonic, though: the SF&nbsp;1000 gap
    ({max(totals["TPC-H"]["1000"][x]["ratio"] for x in ENGINES):.2f}&times;) is wider than the
    SF&nbsp;100 gap ({max(totals["TPC-H"]["100"][x]["ratio"] for x in ENGINES):.2f}&times;).</p>
    <p class="small muted" style="margin-bottom:0">TPC-DS narrows further: at SF&nbsp;1000 the
    fastest and slowest engines are within
    {max(totals["TPC-DS"]["1000"][x]["ratio"] for x in ENGINES) / min(totals["TPC-DS"]["1000"][x]["ratio"] for x in ENGINES):.2f}&times;
    of each other, against {max(totals["TPC-DS"]["1"][x]["ratio"] for x in ENGINES):.0f}&times; at SF&nbsp;1.</p>
  </div>
  <div class="card">
    <h3>TPC-DS is a genuine three-way contest</h3>
    <p>On TPC-DS the ranking is not stable. Spark Rust (tuned) is the only configuration to beat
    DuckDB on summed time ({rust_ds["ratio"]:.3f}&times;), Spark Rust (default) is effectively tied
    ({tpcds_all["Spark Rust 0.42.1 (default)"]["ratio"]:.3f}&times;), and DuckDB wins individual scale
    factors SF&nbsp;1 and SF&nbsp;10 while losing SF&nbsp;100 and SF&nbsp;1000. Treat TPC-DS as a tie
    between the Rust engine and DuckDB, not a DuckDB win.</p>
  </div>
  <div class="card">
    <h3>Cluster: Spark Rust leads until it doesn't</h3>
    <p>At SF&nbsp;100 Spark Rust 0.42.1 wins {c100["r_wins"]} of {c100["n"]} queries and the wall clock by
    {c100["g_time"] / c100["r_time"]:.2f}&times;, using {c100["cpu_ratio"]:.1f}&times; less CPU. The lead
    evaporates with scale: {cluster_stats["1000"]["r_wins"]}–{cluster_stats["1000"]["g_wins"]} at SF&nbsp;1000,
    and at SF&nbsp;10&nbsp;000 Gluten is {cluster_stats["10000"]["time_ratio"]:.2f}&times; <em>faster</em>
    overall while Spark Rust still wins {cluster_stats["10000"]["r_wins"]} queries.</p>
  </div>
</div>
<div class="callout">
  <p><strong>Bottom line.</strong> For single-node analytics up to SF&nbsp;1000, DuckDB 1.5.5 and
  Spark Rust 0.42.1 are interchangeable on TPC-H and effectively tied on TPC-DS; both are far ahead
  of Spark 4.1.1 Gluten and Spark 4.2, whose advantage is ecosystem compatibility rather than raw
  speed. For distributed runs, Spark Rust 0.42.1 is the better choice up to about SF&nbsp;1000, and
  Spark 4.1.1 Gluten takes over at SF&nbsp;10&nbsp;000.</p>
</div>
</section>
"""
)

# ---------------------------------------------------------------- method
A(
    f"""<section id="method">
<h2>Method and hardware</h2>
<p>All figures derive from <code>{e(SRC)}</code>. The file records wall-clock query times in seconds;
this report aggregates them and does not re-run or re-time anything.</p>
<div class="grid2">
  <div class="card">
    <h3>Single node</h3>
    <table class="kv">
      <tbody>
        <tr><th scope="row">Machine</th><td>{e(HW["single_node"]["sku"])}</td></tr>
        <tr><th scope="row">vCPU / RAM</th><td>{HW["single_node"]["cores"]} vCPU · {HW["single_node"]["ram_gb"]} GB</td></tr>
        <tr><th scope="row">Engines</th><td>{len(ENGINES)}</td></tr>
        <tr><th scope="row">Benchmarks</th><td>TPC-H (22 queries), TPC-DS (99 queries)</td></tr>
        <tr><th scope="row">Scale factors</th><td>SF 1, 10, 100, 1000</td></tr>
        <tr><th scope="row">Observations</th><td>{sum(len(v) for v in single["TPC-H"].values()) + sum(len(v) for v in single["TPC-DS"].values())} query rows</td></tr>
      </tbody>
    </table>
  </div>
  <div class="card">
    <h3>Distributed cluster</h3>
    <table class="kv">
      <tbody>
        <tr><th scope="row">Workers</th><td>{HW["cluster_workers"]["count"]}× {e(HW["cluster_workers"]["sku"])}</td></tr>
        <tr><th scope="row">Per worker</th><td>{HW["cluster_workers"]["cores_each"]} vCPU · {HW["cluster_workers"]["ram_gb_each"]} GB</td></tr>
        <tr><th scope="row">Totals</th><td>{HW["cluster_workers"]["total_cores"]} vCPU · {HW["cluster_workers"]["total_ram_gb"]} GB</td></tr>
        <tr><th scope="row">Head node</th><td>{e(HW["cluster_head_node"] or "not recorded")}</td></tr>
        <tr><th scope="row">Engines</th><td>Spark Rust 0.42.1, Spark 4.1.1 Gluten</td></tr>
        <tr><th scope="row">Scale factors</th><td>SF 100, 1000, 10000</td></tr>
      </tbody>
    </table>
  </div>
</div>
<div class="callout warn">
  <p><strong>Reading the ratios.</strong> Throughout, a ratio is
  <em>engine time ÷ DuckDB 1.5.5 time</em> for single-node tables and
  <em>Spark Rust ÷ Gluten</em> for cluster tables, so <strong>below 1.00&times; is faster</strong>.
  Single-node totals are sums of per-query times across the four scale factors, so large scale
  factors dominate them — that is stated wherever a total is shown. The source file also carries a
  <code>matched</code> field on its all-SF rows; its exact construction is not derivable from the JSON
  alone, so it is reproduced verbatim in <a href="#matched">Appendix A</a> rather than reinterpreted.</p>
</div>
</section>
"""
)

# ---------------------------------------------------------------- single node overview
A(
    """<section id="single">
<h2>Single-node results</h2>
<p class="muted">Five engines, two benchmarks, four scale factors. Times are wall clock in seconds.</p>
"""
)

for bench in ("TPC-H", "TPC-DS"):
    anchor = "tpch" if bench == "TPC-H" else "tpcds"
    nq = len(single[bench]["1"])
    A(f'<h3 id="{anchor}">{bench} — {nq} queries</h3>')
    A('<div class="table-scroll"><table>')
    A(
        "<caption>Total wall-clock seconds per scale factor (sum of all queries), "
        "with ratio against DuckDB 1.5.5. Lower is better.</caption>"
    )
    A("<thead><tr><th scope=\"col\">Engine</th>")
    for sf in SF_ORDER:
        A(f'<th scope="col">SF {sf}</th><th scope="col">vs DuckDB</th>')
    A('<th scope="col">All SF</th><th scope="col">vs DuckDB</th></tr></thead><tbody>')
    for eng in ENGINES:
        A(f'<tr><th scope="row">{e(SHORT[eng])}</th>')
        for sf in SF_ORDER:
            t = agg[(bench, sf, eng)]["total"]
            r = totals[bench][sf][eng]["ratio"]
            win = ' class="win"' if best[(bench, sf)] == eng else ""
            A(f'<td{win}>{secs(t, 2)}</td><td>{ratio_pill(r)}</td>')
        ta = totals[bench]["all"][eng]
        A(f'<td>{secs(ta["time"], 2)}</td><td>{ratio_pill(ta["ratio"])}</td></tr>')
    A("</tbody></table></div>")
    A(
        '<p class="tbl-note">Fastest engine per scale factor: '
        + ", ".join(
            f'SF&nbsp;{sf} → <strong>{e(SHORT[best[(bench, sf)]])}</strong>' for sf in SF_ORDER
        )
        + ". The “All SF” column sums the four scale factors, so SF&nbsp;1000 dominates it.</p>"
    )

    # Distribution chart: mean query time per engine per SF
    A('<h4>Mean query time by scale factor</h4>')
    A('<div class="legend">')
    for eng in ENGINES:
        A(f'<span><i style="background:{COLOR[eng]}"></i>{e(SHORT[eng])}</span>')
    A("</div>")
    for sf in SF_ORDER:
        mx = max(agg[(bench, sf, x)]["mean"] for x in ENGINES)
        A(f'<div style="margin-top:10px"><div class="small muted" style="margin-bottom:4px">SF {sf}</div>')
        for eng in ENGINES:
            v = agg[(bench, sf, eng)]["mean"]
            A(
                f'<div class="barrow"><span class="bl">{e(SHORT[eng])}</span>'
                f'{bar(v / mx * 100, COLOR[eng], f"{SHORT[eng]} SF {sf} mean {v:.3f} s")}'
                f'<span class="bv">{dur(v)}</span></div>'
            )
        A("</div>")

A("</section>")

# ---------------------------------------------------------------- per-query
A(
    """<section id="queries">
<h2>Per-query detail</h2>
<p class="muted">Every query row from the source file, grouped by benchmark and scale factor.
Times are seconds; the fastest engine in each row is highlighted.</p>
"""
)

for bench in ("TPC-H", "TPC-DS"):
    A(f"<h3>{bench}</h3>")
    A('<div class="tabs" role="tablist" aria-label="Scale factor">')
    for i, sf in enumerate(SF_ORDER):
        sel = "true" if i == 0 else "false"
        A(
            f'<button type="button" class="tab" role="tab" id="tab-{bench}-{sf}" '
            f'aria-selected="{sel}" aria-controls="panel-{bench}-{sf}" '
            f'data-tab="{bench}-{sf}">SF {sf}</button>'
        )
    A("</div>")
    for i, sf in enumerate(SF_ORDER):
        rows = single[bench][sf]
        hid = "" if i == 0 else " hidden"
        A(
            f'<div class="panel" id="panel-{bench}-{sf}" role="tabpanel" '
            f'aria-labelledby="tab-{bench}-{sf}"{hid}>'
        )
        A('<div class="table-scroll" style="margin-top:14px"><table>')
        A(f"<caption>{bench} SF {sf} — wall clock seconds per query.</caption>")
        A('<thead><tr><th scope="col">Query</th>')
        for eng in ENGINES:
            A(f'<th scope="col">{e(SHORT[eng])}</th>')
        A('<th scope="col">Fastest</th></tr></thead><tbody>')
        for r in rows:
            ts = r["times"]
            mn = min(ts)
            A(f'<tr><th scope="row">Q{r["q"]}</th>')
            for i2, eng in enumerate(ENGINES):
                cls = ' class="win"' if ts[i2] == mn else ""
                mk = r["markers"][i2]
                sup = f' <span class="pill plain" title="{e(MARKER_TEXT.get(mk, mk))}">{e(mk)}</span>' if mk else ""
                A(f"<td{cls}>{secs(ts[i2])}{sup}</td>")
            A(f'<td>{e(SHORT[ENGINES[ts.index(mn)]])}</td></tr>')
        A("</tbody></table></div></div>")
A("</section>")

# ---------------------------------------------------------------- cluster
A(
    """<section id="cluster">
<h2>Distributed cluster comparison</h2>
<p class="muted">Spark Rust 0.42.1 against Spark 4.1.1 Gluten on an 8-worker cluster, TPC-DS at
SF 100, 1&nbsp;000 and 10&nbsp;000. Ratios are Spark Rust ÷ Gluten, so below 1.00&times; favours
Spark Rust.</p>
"""
)

A('<div class="grid3">')
for sf in CLUSTER_SF:
    s = cluster_stats[sf]
    lead = "Spark Rust" if s["time_ratio"] < 1 else "Gluten"
    A(
        f"""<div class="card">
    <h3>SF {sf}</h3>
    <table class="kv">
      <tbody>
        <tr><th scope="row">Wall clock (Rust)</th><td>{dur(s["r_time"])}</td></tr>
        <tr><th scope="row">Wall clock (Gluten)</th><td>{dur(s["g_time"])}</td></tr>
        <tr><th scope="row">Overall</th><td>{ratio_pill(s["time_ratio"])} {e(lead)}</td></tr>
        <tr><th scope="row">Query wins</th><td>{s["r_wins"]} – {s["g_wins"]}</td></tr>
        <tr><th scope="row">CPU time</th><td>{s["cpu_ratio"]:.2f}&times; less for Rust</td></tr>
        <tr><th scope="row">Mean cores</th><td>{s["cores_r"]:.1f} vs {s["cores_g"]:.1f}</td></tr>
        <tr><th scope="row">Queries</th><td>{s["n_r"]} of {s["n"]}</td></tr>
      </tbody>
    </table>
  </div>"""
    )
A("</div>")

A('<h3>Resource totals</h3>')
A('<div class="table-scroll"><table>')
A(
    "<caption>Aggregate cost of the full run at each scale factor.</caption>"
)
A(
    '<thead><tr><th scope="col">SF</th><th scope="col">Engine</th>'
    '<th scope="col">Wall clock</th><th scope="col">CPU-hours</th><th scope="col">Mem-hours</th>'
    '<th scope="col">Mean cores</th><th scope="col">Mean query</th>'
    '<th scope="col">p50 query</th><th scope="col">p95 query</th><th scope="col">Max query</th>'
    "</tr></thead><tbody>"
)
for sf in CLUSTER_SF:
    s = cluster_stats[sf]
    rows = [
        ("Spark Rust 0.42.1", s["r_time"], s["cpu_hours_r"], s["mem_hours_r"], s["cores_r"], s["mean_r"], s["p50_r"], s["p95_r"], s["max_r"]),
        ("Spark 4.1.1 Gluten", s["g_time"], s["cpu_hours_g"], s["mem_hours_g"], s["cores_g"], s["mean_g"], s["p50_g"], s["p95_g"], s["max_g"]),
    ]
    for eng, t, ch, mh, co, mean, p50, p95, mx in rows:
        A(
            f'<tr><th scope="row">{sf}</th><td>{e(eng)}</td><td>{dur(t)}</td>'
            f'<td>{ch:,.2f}</td><td>{mh:,.2f}</td><td>{co:,.2f}</td>'
            f'<td>{secs(mean, 2)}</td><td>{secs(p50, 2)}</td><td>{secs(p95, 2)}</td>'
            f'<td>{secs(mx, 2)}</td></tr>'
        )
A("</tbody></table></div>")

A(
    f"""<div class="callout">
<p><strong>Efficiency versus end-to-end time.</strong> Spark Rust uses less CPU at every scale —
{cluster_stats["100"]["cpu_ratio"]:.1f}&times; less at SF&nbsp;100 and
{cluster_stats["1000"]["cpu_ratio"]:.1f}&times; at SF&nbsp;1000, though only
{cluster_stats["10000"]["cpu_ratio"]:.2f}&times; at SF&nbsp;10&nbsp;000 — yet loses the
SF&nbsp;10&nbsp;000 wall clock by {cluster_stats["10000"]["time_ratio"]:.2f}&times;. Lower CPU is not
the same as lower latency: Gluten keeps {cluster_stats["10000"]["cores_g"]:.1f} cores busy against
Spark Rust's {cluster_stats["10000"]["cores_r"]:.1f}, and buys back more wall clock than it spends.</p>
</div>"""
)

# per-SF query tables
for sf in CLUSTER_SF:
    s = cluster_stats[sf]
    rows = cq[sf]
    A(
        f"""<details>
<summary>SF {sf} — all {s["n"]} queries ({s["r_wins"]} Rust wins, {s["g_wins"]} Gluten wins)</summary>
<div class="dbody">"""
    )
    A('<div class="table-scroll" style="margin-top:14px"><table>')
    A(
        f"<caption>SF {sf}: r = Spark Rust 0.42.1, g = Spark 4.1.1 Gluten, both in seconds. "
        "Memory figures are GB.</caption>"
    )
    A(
        '<thead><tr><th scope="col">Q</th><th scope="col">Rust</th><th scope="col">Gluten</th>'
        '<th scope="col">Ratio</th><th scope="col">CPU r / g</th><th scope="col">Mem r / g</th>'
        '<th scope="col">p95 r / g</th><th scope="col">Status</th></tr></thead><tbody>'
    )
    for r in rows:
        stt = r["status"]
        cls = "good" if stt == "pass" else ("warn" if stt == "gap" else "plain")
        A(
            f'<tr><th scope="row">Q{r["q"]}</th>'
            f'<td>{secs(r["r"], 2)}</td><td>{secs(r["g"], 2)}</td>'
            f'<td>{ratio_pill(r["ratio"])}</td>'
            f'<td>{secs(r["cpu"][0], 1)} / {secs(r["cpu"][1], 1)}</td>'
            f'<td>{secs(r["memory"][0], 2)} / {secs(r["memory"][1], 2)}</td>'
            f'<td>{secs(r["p95"][0], 2)} / {secs(r["p95"][1], 2)}</td>'
            f'<td><span class="pill {cls}">{e(stt)}</span></td></tr>'
        )
    A("</tbody></table></div>")
    ex = exceptions.get(sf)
    if ex:
        A('<h4>Queries excluded from the win count</h4><ul class="small">')
        for r in ex:
            A(f'<li><strong>Q{r["q"]}</strong> — {e(r["status"])}</li>')
        A("</ul>")
    A("</div></details>")

A("</section>")

# ---------------------------------------------------------------- caveats
A('<section id="caveats"><h2>Caveats and data quality</h2>')
A(
    f"""<div class="grid2">
  <div class="card">
    <h3>Single-node flagged observations</h3>
    <p class="small muted">{len(marker_rows)} of
    {sum(len(v) for s in single.values() for v in s.values())} query rows carry a quality marker.
    They are included in every figure above and flagged inline in the per-query tables.</p>
    <div class="table-scroll"><table>
      <caption>Every flagged single-node observation, with the recorded time.</caption>
      <thead><tr><th scope="col">Benchmark</th><th scope="col">SF</th><th scope="col">Q</th>
      <th scope="col">Engine</th><th scope="col">Marker</th><th scope="col">Time (s)</th></tr></thead>
      <tbody>"""
)
for bench, sf, q, ms, ts in marker_rows:
    for i, m in ms:
        A(
            f'<tr><td>{bench}</td><td>{sf}</td><td>Q{q}</td><td>{e(SHORT[ENGINES[i]])}</td>'
            f'<td><span class="pill warn">{e(m)}</span></td><td>{secs(ts[i])}</td></tr>'
        )
A(
    """</tbody></table></div>
    <p class="tbl-note">Marker meanings are not defined in the source file; the codes are reproduced
    as-is. <code>B</code> appears on the slowest engine in rows where one engine is a large outlier,
    and <code>P</code> on two TPC-DS SF&nbsp;1000 rows.</p>
  </div>
  <div class="card">
    <h3>Cluster queries not counted as wins</h3>
    <p class="small muted">These rows have a status other than <code>pass</code> or <code>gap</code>
    and are excluded from the win tallies.</p>
    <div class="table-scroll"><table>
      <caption>Cluster rows excluded from the win tallies, with the reason recorded in the source.</caption>
      <thead><tr><th scope="col">SF</th><th scope="col">Q</th><th scope="col">Rust (s)</th>
      <th scope="col">Gluten (s)</th><th scope="col">Status</th></tr></thead><tbody>"""
)
for sf in CLUSTER_SF:
    for r in exceptions.get(sf, []):
        A(
            f'<tr><td>{sf}</td><td>Q{r["q"]}</td><td>{secs(r["r"], 2)}</td>'
            f'<td>{secs(r["g"], 2)}</td><td class="small">{e(r["status"])}</td></tr>'
        )
A(
    """</tbody></table></div>
    <p class="tbl-note">At SF&nbsp;10&nbsp;000 five queries have no comparable Gluten result, so the
    run covers 94 of 99 queries.</p>
  </div>
</div>
<div class="callout warn">
<p><strong>Limits of this report.</strong> The JSON records timings only — no repetitions, variance,
warm-up policy, or query-validation detail beyond the status strings, so no confidence intervals or
significance tests are possible. Cluster <code>pass</code>/<code>gap</code> labels are taken from the
source without reinterpretation. Hardware is user-provided specification, not measured inventory.
Cluster figures come from a single run per scale factor.</p>
</div>
</section>"""
)

# ---------------------------------------------------------------- appendix A
A(
    """<section id="matched">
<h2>Appendix A — source <code>matched</code> values</h2>
<p class="muted">The source file's all-scale-factor rows carry a <code>matched</code> field alongside
<code>ratio</code>. Its construction cannot be recovered from the JSON alone, so both are reproduced
verbatim rather than reinterpreted.</p>
"""
)
for bench in ("TPC-H", "TPC-DS"):
    A(f'<h3>{bench}</h3><div class="table-scroll"><table>')
    A(
        f"<caption>{bench}, sf = “all”, exactly as recorded in the source file.</caption>"
    )
    A(
        '<thead><tr><th scope="col">Engine</th><th scope="col">n</th>'
        '<th scope="col">time (s)</th><th scope="col">ratio</th><th scope="col">matched</th>'
        "</tr></thead><tbody>"
    )
    for eng in ENGINES:
        r = totals[bench]["all"][eng]
        A(
            f'<tr><th scope="row">{e(SHORT[eng])}</th><td>{r["n"]}</td>'
            f'<td>{secs(r["time"])}</td><td>{r["ratio"]:,.6f}</td>'
            f'<td>{r["matched"]:,.6f}</td></tr>'
        )
    A("</tbody></table></div>")
A("</section>")

# ---------------------------------------------------------------- footer
A(
    f"""<footer>
<p><strong>Provenance.</strong> Generated from <code>{e(SRC)}</code>
(sha256 <code>{e(D["sha256"][:16])}…</code>), originally derived from
<code>{e(D["source"])}</code>. This page is fully self-contained: no external fonts, scripts,
stylesheets, or network requests.</p>
<p><strong>How to read it.</strong></p>
<ol>
  <li>Ratios below 1.00&times; mean the engine was faster than the reference (DuckDB 1.5.5 for
  single node, Spark 4.1.1 Gluten for the cluster).</li>
  <li>“All SF” totals sum the four single-node scale factors, so SF&nbsp;1000 dominates them.</li>
  <li>Cluster win counts exclude queries whose status is neither <code>pass</code> nor
  <code>gap</code>; see <a href="#caveats">Caveats</a>.</li>
  <li>Every figure is an aggregation of the source timings — no measurement was repeated or
  inferred.</li>
</ol>
</footer>
</div>
<script>
(function () {{
  "use strict";
  var root = document.documentElement;

  // Theme toggle: explicit choice wins, otherwise follow the OS.
  var btn = document.getElementById("themeBtn");
  function current() {{
    var t = root.getAttribute("data-theme");
    if (t) return t;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }}
  btn.addEventListener("click", function () {{
    var next = current() === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    btn.setAttribute("aria-label", "Switch to " + (next === "dark" ? "light" : "dark") + " theme");
  }});

  // Scale-factor tabs within each benchmark block.
  document.querySelectorAll("[data-tab]").forEach(function (tab) {{
    tab.addEventListener("click", function () {{
      var group = tab.closest(".tabs");
      group.querySelectorAll(".tab").forEach(function (t) {{
        var on = t === tab;
        t.setAttribute("aria-selected", on ? "true" : "false");
        var p = document.getElementById(t.getAttribute("aria-controls"));
        if (p) p.hidden = !on;
      }});
    }});
    tab.addEventListener("keydown", function (ev) {{
      var tabs = Array.prototype.slice.call(tab.closest(".tabs").querySelectorAll(".tab"));
      var i = tabs.indexOf(tab);
      var d = ev.key === "ArrowRight" ? 1 : ev.key === "ArrowLeft" ? -1 : 0;
      if (!d) return;
      ev.preventDefault();
      var nxt = tabs[(i + d + tabs.length) % tabs.length];
      nxt.focus();
      nxt.click();
    }});
  }});
}})();
</script>
</body>
</html>
"""
)

with open(OUT, "w") as fh:
    fh.write("".join(parts))

print(f"wrote {OUT}")
