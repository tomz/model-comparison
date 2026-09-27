#!/usr/bin/env python3
"""Build a self-contained HTML benchmark report.

Input : engine-comparison-summary-data.json  (the only data source)
Output: engine-comparison-report.html        (no external assets)

Run:  python3 build_report.py
"""

from __future__ import annotations

import html as html_mod
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "engine-comparison-summary-data.json"
OUT = ROOT / "engine-comparison-report.html"

data = json.loads(SRC.read_text(encoding="utf-8"))

ENGINES: list[str] = data["engines"]
SINGLE = data["single"]            # {suite: {sf: [{q, times, markers}]}}
CLUSTER = data["cluster"]          # {sf: [engine rows]}
CLUSTER_Q = data["clusterQueries"]  # {sf: [{q, r, g, diff, ratio, cpu, ...}]}
WINS = data["wins"]                # {sf: [rust_wins, gluten_wins]}
HW = data["hardware"]

SHORT = {
    "Spark Rust 0.42.1 (default)": ("Spark Rust", "0.42.1 · default"),
    "Spark Rust 0.42.1 (tuned)": ("Spark Rust", "0.42.1 · tuned"),
    "DuckDB 1.5.5": ("DuckDB", "1.5.5"),
    "Spark 4.1.1 Gluten": ("Spark 4.1.1 Gluten", "4.1.1 · Gluten"),
    "Spark 4.2": ("Spark 4.2", "4.2"),
}
COLOR = {
    "Spark Rust 0.42.1 (default)": "#2f6fd0",
    "Spark Rust 0.42.1 (tuned)": "#0e9c8b",
    "DuckDB 1.5.5": "#c07c0b",
    "Spark 4.1.1 Gluten": "#9a5cd6",
    "Spark 4.2": "#d94444",
}
C_RUST = "#2f6fd0"
C_GLUTEN = "#9a5cd6"
BENCHES = ["TPC-H", "TPC-DS"]
SF_SINGLE = ["1", "10", "100", "1000"]
SF_CLUSTER = ["100", "1000", "10000"]

totals_by: dict[str, dict[str, dict[str, dict]]] = {}
for bench, rows in data["totals"].items():
    for r in rows:
        totals_by.setdefault(bench, {}).setdefault(str(r["sf"]), {})[r["engine"]] = r


# ---------------------------------------------------------------- formatting
def esc(s) -> str:
    return html_mod.escape(str(s), quote=True)


def fmt_time(v) -> str:
    if v is None:
        return "—"
    if v >= 10000:
        return f"{v:,.0f}"
    if v >= 1000:
        return f"{v:,.1f}"
    if v >= 10:
        return f"{v:,.2f}"
    return f"{v:.3f}"


def fmt_ratio(v) -> str:
    return "—" if v is None else f"{v:.2f}\u00d7"


def fmt_signed(v) -> str:
    if v is None:
        return "—"
    if abs(v) < 1e-9:
        return "0"
    return ("+" if v > 0 else "\u2212") + fmt_time(abs(v))


def fmt_commas(v, dec: int = 1) -> str:
    return "—" if v is None else f"{v:,.{dec}f}"


def fmt_fixed(v, dec: int = 2) -> str:
    return "—" if v is None else f"{v:.{dec}f}"


def chip(color: str) -> str:
    return f'<span class="chip" style="--c:{color}"></span>'


def engine_th(eng: str) -> str:
    name, sub = SHORT[eng]
    return (
        f'<th scope="col" class="num" data-sort="num"><span class="eng">{chip(COLOR[eng])}{esc(name)}</span>'
        f'<span class="sub">{esc(sub)}</span></th>'
    )


# ------------------------------------------------------------------- charts
def svg_ratio_chart(bench: str) -> str:
    """Log-scale line chart: ratio vs DuckDB across scale factors."""
    w, h = 580, 330
    l, r, t, b = 46, 18, 16, 48
    pw, ph = w - l - r, h - t - b
    ymin, ymax = 0.85, 70

    def yy(v: float) -> float:
        return t + ph * (1 - (math.log10(v) - math.log10(ymin)) / (math.log10(ymax) - math.log10(ymin)))

    def xx(i: int) -> float:
        return l + pw * i / (len(SF_SINGLE) - 1)

    p = [
        f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="Runtime ratio versus DuckDB by scale factor for {esc(bench)}: '
        f'Spark Rust stays near 1.0x while Spark 4.x engines start 42-53 times slower at SF 1 '
        f'and converge to 1.3-3.1 times at SF 1000.">'
    ]
    for tick in (1, 2, 5, 10, 25, 50):
        y = yy(tick)
        p.append(f'<line class="grid" x1="{l}" y1="{y:.1f}" x2="{w - r}" y2="{y:.1f}"></line>')
        p.append(
            f'<text class="tick" x="{l - 8}" y="{y + 4:.1f}" text-anchor="end">{tick}\u00d7</text>'
        )
    for i, sf in enumerate(SF_SINGLE):
        p.append(
            f'<text class="tick" x="{xx(i):.1f}" y="{h - b + 24}" text-anchor="middle">SF {sf}</text>'
        )
    for eng in ENGINES:
        pts = []
        for i, sf in enumerate(SF_SINGLE):
            ratio = totals_by[bench][sf][eng]["ratio"]
            pts.append(f"{xx(i):.1f},{yy(ratio):.1f}")
        p.append(f'<polyline class="ln" points="{" ".join(pts)}" stroke="{COLOR[eng]}"></polyline>')
        for pt in pts:
            px, py = pt.split(",")
            p.append(f'<circle cx="{px}" cy="{py}" r="3.6" fill="{COLOR[eng]}"></circle>')
    p.append("</svg>")
    return "".join(p)


def legend(items: list[tuple[str, str]]) -> str:
    lis = "".join(
        f'<li>{chip(c)}{esc(label)}</li>' for c, label in items
    )
    return f'<ul class="legend">{lis}</ul>'


def cluster_walltime_bars() -> str:
    """Pure-CSS small multiples: wall time per engine, per scale factor."""
    panels = []
    for sf in SF_CLUSTER:
        rows = CLUSTER[sf]
        mx = max(r["time"] for r in rows)
        bars = []
        for r in rows:
            width = 100.0 * r["time"] / mx
            fill = "var(--fill-rust)" if "Rust" in r["engine"] else "var(--fill-gluten)"
            bars.append(
                f'<div class="bar-row"><span class="bl">{esc(SHORT.get(r["engine"], (r["engine"], ""))[0])}</span>'
                f'<div class="bar-track"><div class="bar" style="width:{width:.1f}%;background:{fill}"></div></div>'
                f'<span class="bv">{fmt_time(r["time"])} s</span></div>'
            )
        panels.append(f'<div class="sm"><h4>TPC-DS · SF {sf}</h4>{"".join(bars)}</div>')
    return f'<div class="sm-grid">{"".join(panels)}</div>'


def cluster_win_bars() -> str:
    rows = []
    for sf in SF_CLUSTER:
        rw, gw = WINS[sf]
        n = rw + gw
        rows.append(
            f'<div class="bar-row win-row">'
            f'<span class="bl">SF {sf}</span>'
            f'<div class="win-track">'
            f'<div class="win" style="width:{100.0 * rw / n:.1f}%;background:var(--fill-rust)">{rw}</div>'
            f'<div class="win" style="width:{100.0 * gw / n:.1f}%;background:var(--fill-gluten)">{gw}</div>'
            f'</div>'
            f'<span class="bv">{rw} – {gw}</span></div>'
        )
    return f'<div class="sm-grid single">{"".join(rows)}</div>'


# --------------------------------------------------------------- data tables
def totals_table(bench: str) -> str:
    heads = "".join(engine_th(e) for e in ENGINES)
    body = []
    for sf in SF_SINGLE + ["all"]:
        label = "All SF" if sf == "all" else f"SF {sf}"
        best = min(totals_by[bench][sf][e]["time"] for e in ENGINES)
        cells = []
        n = None
        for e in ENGINES:
            r = totals_by[bench][sf][e]
            n = r["n"]
            sub = f'<span class="sub">{fmt_ratio(r["ratio"])}'
            if sf == "all" and r["matched"] is not None:
                sub += f" · matched {fmt_ratio(r['matched'])}"
            sub += "</span>"
            dag = '<sup class="flag" title="The source records no canonical total for this row.">†</sup>' if r["canonical"] is None else ""
            is_best = abs(r["time"] - best) < 1e-9
            cls = "num best" if is_best else "num"
            cell_inner = f"<strong>{fmt_time(r['time'])}</strong>" if is_best else fmt_time(r["time"])
            cells.append(f'<td class="{cls}" data-v="{r["time"]}">{cell_inner}{dag}{sub}</td>')
        body.append(
            f'<tr><th scope="row" class="rowhead">{label}</th><td class="num">{n}</td>{"".join(cells)}</tr>'
        )
    return (
        f'<div class="table-scroll"><table class="data sortable">'
        f'<caption>Total wall time in seconds across all queries; ratio shown below each total '
        f'(engine ÷ DuckDB, same scale factor). Fastest total per row in bold.</caption>'
        f'<thead><tr><th scope="col" data-sort="text">Scale factor</th>'
        f'<th scope="col" class="num" data-sort="num">Queries</th>{heads}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>'
    )


def fastest_counts(rows: list[dict]) -> str:
    c: Counter[str] = Counter()
    for row in rows:
        best_i = min(range(len(ENGINES)), key=lambda i: row["times"][i])
        c[ENGINES[best_i]] += 1
    parts = []
    for e in ENGINES:
        if c[e]:
            parts.append(f'<span class="fc">{chip(COLOR[e])}{esc(SHORT[e][0] + " " + SHORT[e][1].replace("·", ""))} <b>{c[e]}</b></span>')
    return f'<p class="fc-strip">Fastest per query: {"".join(parts)}</p>'


def single_query_table(bench: str, sf: str) -> str:
    rows = SINGLE[bench][sf]
    heads = "".join(engine_th(e) for e in ENGINES)
    body = []
    for row in rows:
        times = row["times"]
        best = min(times)
        cells = []
        for i, e in enumerate(ENGINES):
            m = row["markers"][i]
            sup = (
                f'<sup class="flag" title="Run-quality flag carried from the source summary; '
                f'not defined in the data file.">{esc(m)}</sup>'
                if m
                else ""
            )
            is_best = abs(times[i] - best) < 1e-9
            cls = "num best" if is_best else "num"
            inner = f"<strong>{fmt_time(times[i])}</strong>" if is_best else fmt_time(times[i])
            cells.append(f'<td class="{cls}" data-v="{times[i]}">{inner}{sup}</td>')
        best_i = times.index(best)
        body.append(
            f'<tr><th scope="row" class="rowhead">Q{row["q"]}</th>{"".join(cells)}'
            f'<td class="fastest">{chip(COLOR[ENGINES[best_i]])}{esc(SHORT[ENGINES[best_i]][0])}</td></tr>'
        )
    heads_fastest = '<th scope="col" data-sort="text">Fastest</th>'
    return (
        f'{fastest_counts(rows)}'
        f'<div class="table-scroll"><table class="data sortable">'
        f'<caption>{esc(bench)} · SF {sf} — per-query wall time in seconds, {len(rows)} queries. '
        f'Best per row in bold. Superscript letters are source run flags.</caption>'
        f'<thead><tr><th scope="col" data-sort="num">Query</th>{heads}{heads_fastest}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>'
    )


def cluster_summary_table() -> str:
    heads = (
        '<th scope="col" data-sort="text">Scale factor</th>'
        '<th scope="col" data-sort="text">Engine</th>'
        '<th scope="col" class="num" data-sort="num">Queries</th>'
        '<th scope="col" class="num" data-sort="num">Total time (s)</th>'
        '<th scope="col" class="num" data-sort="num">CPU-hours</th>'
        '<th scope="col" class="num" data-sort="num">Mem-hours</th>'
        '<th scope="col" class="num" data-sort="num">Avg cores</th>'
        '<th scope="col" class="num" data-sort="num">Task mean (s)</th>'
        '<th scope="col" class="num" data-sort="num">p50</th>'
        '<th scope="col" class="num" data-sort="num">p95</th>'
        '<th scope="col" class="num" data-sort="num">max</th>'
    )
    body = []
    for sf in SF_CLUSTER:
        rows = CLUSTER[sf]
        best_time = min(r["time"] for r in rows)
        best_cpu = min(r["cpuHours"] for r in rows)
        for r in rows:
            name, sub = SHORT.get(r["engine"], (r["engine"], ""))
            color = C_RUST if "Rust" in r["engine"] else C_GLUTEN
            tcls = "num best" if abs(r["time"] - best_time) < 1e-9 else "num"
            ccls = "num best" if abs(r["cpuHours"] - best_cpu) < 1e-9 else "num"
            body.append(
                f'<tr><th scope="row" class="rowhead">SF {sf}</th>'
                f'<td><span class="eng">{chip(color)}{esc(name)}</span><span class="sub">{esc(sub)}</span></td>'
                f'<td class="num">{r["n"]}</td>'
                f'<td class="{tcls}" data-v="{r["time"]}">{fmt_time(r["time"])}</td>'
                f'<td class="{ccls}" data-v="{r["cpuHours"]}">{fmt_time(r["cpuHours"])}</td>'
                f'<td class="num" data-v="{r["memHours"]}">{fmt_time(r["memHours"])}</td>'
                f'<td class="num" data-v="{r["cores"]}">{fmt_fixed(r["cores"], 1)}</td>'
                f'<td class="num" data-v="{r["mean"]}">{fmt_fixed(r["mean"])}</td>'
                f'<td class="num" data-v="{r["p50"]}">{fmt_fixed(r["p50"])}</td>'
                f'<td class="num" data-v="{r["p95"]}">{fmt_fixed(r["p95"])}</td>'
                f'<td class="num" data-v="{r["max"]}">{fmt_fixed(r["max"])}</td></tr>'
            )
    return (
        f'<div class="table-scroll"><table class="data sortable">'
        f'<caption>TPC-DS on the 8-node cluster. Mem-hours = memory-time ÷ 3600. '
        f'Task mean/p50/p95/max are pooled task-runtime distribution statistics from the source. '
        f'Lowest total time and CPU-hours per scale factor in bold.</caption>'
        f'<thead><tr>{heads}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'
    )


def status_pill(status: str) -> str:
    if status == "pass":
        return '<span class="pill good">pass</span>'
    if status == "gap":
        return '<span class="pill warn">gap</span>'
    if status.startswith("pass"):
        note = status[len("pass"):].strip(" ()")
        return f'<span class="pill good">pass</span> <span class="s-note">{esc(note)}</span>'
    return f'<span class="pill bad">no pair</span> <span class="s-note">{esc(status)}</span>'


def cluster_resources(cq: dict) -> str:
    def pair(vals, fmt=fmt_time) -> str:
        return f"{fmt(vals[0])} / {fmt(vals[1])}"

    rows = [
        ("CPU-seconds", pair(cq["cpu"], lambda v: fmt_commas(v))),
        ("Avg cores", pair(cq["cores"], lambda v: fmt_fixed(v))),
        ("Peak memory (GB)", pair(cq["memory"], lambda v: fmt_fixed(v))),
        ("Task p50 (s)", pair(cq["p50"])),
        ("Task p95 (s)", pair(cq["p95"])),
        ("Task max (s)", pair(cq["max"])),
        ("Memory-time (GB·s)", pair(cq["memtime"], lambda v: fmt_commas(v))),
    ]
    lis = "".join(f"<li><span>{esc(k)}</span><b>{v}</b></li>" for k, v in rows)
    return (
        '<details class="res"><summary>Resources</summary>'
        '<p class="res-head">Spark Rust / Spark 4.1.1 Gluten</p>'
        f'<ul class="res-list">{lis}</ul></details>'
    )


def cluster_query_table(sf: str) -> str:
    rows = CLUSTER_Q[sf]
    rw, gw = WINS[sf]
    body = []
    for cq in rows:
        body.append(
            f'<tr><th scope="row" class="rowhead">Q{cq["q"]}</th>'
            f'<td class="num" data-v="{cq["r"]}">{fmt_time(cq["r"])}</td>'
            f'<td class="num" data-v="{cq["g"]}">{fmt_time(cq["g"])}</td>'
            f'<td class="num" data-v="{cq["diff"]}">{fmt_signed(cq["diff"])}</td>'
            f'<td class="num" data-v="{cq["ratio"]}">{fmt_ratio(cq["ratio"])}</td>'
            f'<td class="status">{status_pill(cq["status"])}</td>'
            f'<td class="res-cell">{cluster_resources(cq)}</td></tr>'
        )
    return (
        f'<p class="fc-strip">Query wins at SF {sf}: '
        f'<span class="fc">{chip(C_RUST)}Spark Rust <b>{rw}</b></span>'
        f'<span class="fc">{chip(C_GLUTEN)}Spark 4.1.1 Gluten <b>{gw}</b></span>'
        f'<span class="note">Ratio is Spark Rust ÷ Spark 4.1.1 Gluten (below 1.00× favours Spark Rust).</span></p>'
        f'<div class="table-scroll"><table class="data sortable sticky-first">'
        f'<caption>TPC-DS · SF {sf} — per-query wall time in seconds on the 8-node cluster. '
        f'Δ is Spark Rust minus Spark 4.1.1 Gluten.</caption>'
        f'<thead><tr>'
        f'<th scope="col" data-sort="num">Query</th>'
        f'<th scope="col" class="num" data-sort="num">Spark Rust (s)</th>'
        f'<th scope="col" class="num" data-sort="num">Spark 4.1.1 Gluten (s)</th>'
        f'<th scope="col" class="num" data-sort="num">Δ (s)</th>'
        f'<th scope="col" class="num" data-sort="num">Ratio</th>'
        f'<th scope="col" data-sort="text">Status</th>'
        f'<th scope="col">Resources</th>'
        f'</tr></thead><tbody>{"".join(body)}</tbody></table></div>'
    )


# --------------------------------------------------------------- page pieces
def masthead() -> str:
    chips = [
        "Single node: D32ads v5 · 32 vCPU / 128 GB",
        "Cluster: 8 × E16ads v5 · 128 cores / 1,024 GB",
        "TPC-H 22 queries · TPC-DS 99 queries",
        "Scale factors 1 – 10,000",
        f"Source: {esc(data['source'])}",
    ]
    chips_html = "".join(f'<li>{esc(c)}</li>' for c in chips)
    return (
        '<header class="masthead">'
        '<p class="eyebrow">Benchmark report · TPC-H &amp; TPC-DS</p>'
        '<h1>Query Engine Comparison</h1>'
        '<p class="subtitle">Spark Rust 0.42.1 (default and tuned) against DuckDB 1.5.5, '
        'Spark 4.1.1 Gluten and Spark 4.2 — single-node totals, per-query timings, '
        'and an 8-node cluster comparison of Spark Rust versus Spark 4.1.1 Gluten.</p>'
        f'<ul class="meta-chips">{chips_html}</ul>'
        '</header>'
    )


NAV_ITEMS = [
    ("summary", "Executive summary"),
    ("totals", "Single-node totals"),
    ("query-detail", "Query detail"),
    ("cluster", "Cluster results"),
    ("cluster-detail", "Cluster queries"),
    ("method", "Methodology"),
]


def nav() -> str:
    lis = "".join(f'<li><a href="#{i}">{esc(t)}</a></li>' for i, t in NAV_ITEMS)
    return f'<nav class="topnav" aria-label="Report sections"><ul>{lis}</ul></nav>'


def section_summary() -> str:
    cards = [
        ("0.96×", "Spark Rust (tuned) versus DuckDB on TPC-DS SF 1000 — the best single-node result (10,074 s vs 10,497 s)."),
        ("1.03×", "Spark Rust (default) versus DuckDB across all single-node TPC-H runs (88 queries; matched-query ratio 1.02×)."),
        ("42–53×", "Spark 4.x slowdown versus DuckDB at SF 1 on a single node, across both suites."),
        ("89 → 36", "Spark Rust cluster query wins versus Spark 4.1.1 Gluten from SF 100 to SF 10,000 (Gluten wins: 10 → 58)."),
    ]
    cards_html = "".join(
        f'<div class="metric"><div class="num">{esc(n)}</div><div class="label">{esc(lab)}</div></div>'
        for n, lab in cards
    )
    findings = [
        "<strong>DuckDB is the single-node baseline and leads TPC-H at every scale factor.</strong> "
        "Spark Rust stays within 1–5% at SF ≥ 10 and overtakes it on TPC-DS at SF 100 and SF 1000 "
        "(0.99× and 0.96× for the tuned build).",
        "<strong>Tuning helps most on TPC-DS.</strong> The tuned Spark Rust build beats the default at every "
        "TPC-DS scale factor; on TPC-H SF 1000 the default build was slightly faster (1.03× vs 1.05×).",
        "<strong>Spark 4.x pays a heavy small-scale premium.</strong> At SF 1 the Spark engines are 42–53× slower "
        "than DuckDB, narrowing to 1.3–3.1× at SF 1000. Spark 4.2 leads Gluten at SF 1–10 on TPC-DS but falls "
        "behind at SF 100–1000, reaching 3.11× DuckDB on TPC-H SF 1000.",
        "<strong>The cluster race flips with scale.</strong> Spark Rust takes 89 of 99 TPC-DS queries at SF 100 "
        "(807.6 s vs 1,196.9 s total), the field narrows at SF 1000 (48–51), and Spark 4.1.1 Gluten wins 58 of 94 "
        "comparable queries at SF 10,000 (12,762.9 s vs 18,710.0 s).",
        "<strong>Resource efficiency diverges from wall time.</strong> Spark Rust uses 4.4 vs 11.9 CPU-hours at "
        "SF 100 and 16.8 vs 37.2 at SF 1000; at SF 10,000 Gluten consumes more CPU (151.4 vs 127.7 CPU-hours) "
        "yet still finishes first.",
        "<strong>Coverage notes.</strong> The SF 10,000 cluster runs cover 94 of 99 queries; the remaining five "
        "have no comparable pair and are marked in the per-query table.",
    ]
    lis = "".join(f"<li>{f}</li>" for f in findings)
    return (
        '<section id="summary"><h2><span class="sec-num">01</span> Executive summary</h2>'
        f'<div class="grid cards">{cards_html}</div>'
        f'<ol class="findings">{lis}</ol></section>'
    )


def section_totals() -> str:
    parts = []
    for bench in BENCHES:
        parts.append(
            f'<h3>{esc(bench)} totals</h3>'
            f'<div class="split">'
            f'<div class="split-table">{totals_table(bench)}</div>'
            f'<figure class="split-chart"><figcaption>Runtime ratio versus DuckDB '
            f'(log scale, lower is better)</figcaption>'
            f'{svg_ratio_chart(bench)}'
            f'{legend([(COLOR[e], SHORT[e][0] + " " + SHORT[e][1]) for e in ENGINES])}'
            f'</figure></div>'
        )
    return (
        '<section id="totals"><h2><span class="sec-num">02</span> Single-node totals</h2>'
        '<p class="lede">All five engines ran on one D32ads v5 node (32 vCPU, 128 GB). '
        'Ratio is the engine total divided by the DuckDB total at the same scale factor. '
        'The DuckDB line is the 1.00× baseline in both charts.</p>'
        f'{"".join(parts)}'
        '<p class="note">† The source records no canonical total for this row; the ratio shown is '
        'total ÷ DuckDB total as recorded. “All SF” rows also carry the source’s matched-query ratio '
        '(computed over the subset of queries matched across engines).</p>'
        '</section>'
    )


def section_query_detail() -> str:
    tabs, panels = [], []
    for bench in BENCHES:
        for sf in SF_SINGLE:
            key = f"{bench.lower().replace('-', '')}-{sf}"
            tabs.append(
                f'<button type="button" role="tab" id="tab-{key}" aria-controls="panel-{key}">'
                f'{esc(bench)} · SF {sf}</button>'
            )
            panels.append(
                f'<div role="tabpanel" id="panel-{key}" aria-labelledby="tab-{key}" tabindex="0">'
                f'<h3>{esc(bench)} · SF {sf}</h3>'
                f'{single_query_table(bench, sf)}</div>'
            )
    return (
        '<section id="query-detail"><h2><span class="sec-num">03</span> Single-node query detail</h2>'
        '<p class="lede">Per-query wall times in seconds for every engine. Column headers sort the table; '
        'without JavaScript all scale factors are listed in sequence.</p>'
        '<div class="tabset" data-tabset>'
        f'<div class="tablist" role="tablist" aria-label="Suite and scale factor">{"".join(tabs)}</div>'
        f'{"".join(panels)}'
        '</div></section>'
    )


def section_cluster() -> str:
    return (
        '<section id="cluster"><h2><span class="sec-num">04</span> Cluster results</h2>'
        '<p class="lede">TPC-DS on eight E16ads v5 workers (128 cores, 1,024 GB total) comparing '
        'Spark Rust 0.42.1 with Spark 4.1.1 Gluten. At SF 10,000 only 94 of 99 queries produced a '
        'comparable pair.</p>'
        '<h3>Query wins by scale factor</h3>'
        f'{cluster_win_bars()}'
        f'{legend([(C_RUST, "Spark Rust 0.42.1"), (C_GLUTEN, "Spark 4.1.1 Gluten")])}'
        '<h3>Total wall time by scale factor</h3>'
        f'{cluster_walltime_bars()}'
        '<h3>Cluster summary</h3>'
        f'{cluster_summary_table()}'
        '</section>'
    )


def section_cluster_detail() -> str:
    tabs, panels = [], []
    for sf in SF_CLUSTER:
        tabs.append(
            f'<button type="button" role="tab" id="tab-cl-{sf}" aria-controls="panel-cl-{sf}">SF {sf}</button>'
        )
        panels.append(
            f'<div role="tabpanel" id="panel-cl-{sf}" aria-labelledby="tab-cl-{sf}" tabindex="0">'
            f'<h3>TPC-DS · SF {sf}</h3>{cluster_query_table(sf)}</div>'
        )
    return (
        '<section id="cluster-detail"><h2><span class="sec-num">05</span> Cluster query detail</h2>'
        '<p class="lede">Per-query comparison on the cluster. “Resources” expands per-query CPU, core, '
        'memory and task-runtime figures. Query wins follow the source tally; at SF 100, Q56 ties at '
        '10.16 s and is counted as a Spark Rust win there.</p>'
        '<div class="tabset" data-tabset>'
        f'<div class="tablist" role="tablist" aria-label="Cluster scale factor">{"".join(tabs)}</div>'
        f'{"".join(panels)}'
        '</div></section>'
    )


def section_method() -> str:
    sn = HW["single_node"]
    cw = HW["cluster_workers"]
    hw_rows = [
        ("Single test node", sn["sku"], f"{sn['cores']} vCPU", f"{sn['ram_gb']} GB"),
        ("Cluster workers", f"{cw['sku']} × {cw['count']}",
         f"{cw['cores_each']} each ({cw['total_cores']} total)",
         f"{cw['ram_gb_each']} GB each ({cw['total_ram_gb']:,} GB total)"),
        ("Cluster head node", "not specified in source", "—", "—"),
    ]
    hw_html = "".join(
        f'<tr><th scope="row" class="rowhead">{esc(a)}</th><td>{esc(b)}</td><td>{esc(c)}</td><td>{esc(d)}</td></tr>'
        for a, b, c, d in hw_rows
    )
    glossary = [
        ("Total time", "Sum of per-query wall times, seconds."),
        ("Ratio (single node)", "Engine total ÷ DuckDB total at the same scale factor; 1.00× is parity."),
        ("Diff (single node)", "Engine total − DuckDB total, seconds."),
        ("Ratio (cluster)", "Spark Rust ÷ Spark 4.1.1 Gluten; below 1.00× favours Spark Rust."),
        ("CPU-hours", "Total CPU-seconds ÷ 3,600."),
        ("Mem-hours", "Total memory-time in GB·seconds ÷ 3,600."),
        ("Avg cores", "CPU-seconds ÷ wall seconds (average parallelism)."),
        ("Task mean / p50 / p95 / max", "Pooled task-runtime distribution statistics, seconds, as recorded in the source summary."),
        ("Canonical / matched", "Additional source aggregates: the canonical total (blank where the source records none) and the matched-query ratio, reported on “All SF” rows only."),
    ]
    gl_html = "".join(
        f'<tr><th scope="row" class="rowhead">{esc(k)}</th><td>{esc(v)}</td></tr>' for k, v in glossary
    )
    limits = [
        "One recorded run per configuration; the data carries no repeat-run variance or confidence intervals.",
        "Six single-node query results carry source run flags (<sup class=\"flag\">B</sup> / <sup class=\"flag\">P</sup>); "
        "the JSON does not define their semantics.",
        "Canonical totals are missing for Spark 4.2 (TPC-H SF 1000) and Spark 4.1.1 Gluten (TPC-DS SF 1000); "
        "those rows are marked † in the totals tables.",
        "Cluster SF 10,000 covers 94 of 99 queries; five queries have no comparable pair and carry explanatory "
        "status text in the per-query table.",
        "The cluster comparison covers Spark Rust 0.42.1 and Spark 4.1.1 Gluten only — there is no DuckDB cluster data.",
        "Hardware figures are user-provided specifications; no cluster head-node specification is present in the data.",
    ]
    lim_html = "".join(f"<li>{x}</li>" for x in limits)
    return (
        '<section id="method"><h2><span class="sec-num">06</span> Methodology &amp; provenance</h2>'
        '<h3>Hardware</h3>'
        '<div class="table-scroll"><table class="data">'
        '<caption>Test hardware, as specified in the source data '
        f'({esc(HW["provenance"])}).</caption>'
        '<thead><tr><th scope="col">Component</th><th scope="col">SKU</th>'
        '<th scope="col">Cores</th><th scope="col">Memory</th></tr></thead>'
        f'<tbody>{hw_html}</tbody></table></div>'
        '<h3>Field glossary</h3>'
        '<div class="table-scroll"><table class="data">'
        '<caption>How to read the figures in this report.</caption>'
        '<thead><tr><th scope="col">Field</th><th scope="col">Meaning</th></tr></thead>'
        f'<tbody>{gl_html}</tbody></table></div>'
        '<h3>Provenance</h3>'
        '<div class="card prov">'
        f'<p><b>Source summary</b><br><code>{esc(data["source"])}</code></p>'
        f'<p><b>SHA-256 of source data</b><br><code class="hash">{esc(data["sha256"])}</code></p>'
        f'<p><b>Hardware provenance</b><br>{esc(HW["provenance"])}</p>'
        '<p><b>Engines</b><br>' + " · ".join(esc(e) for e in ENGINES) + "</p>"
        '</div>'
        '<h3>Limitations</h3>'
        f'<ul class="limits">{lim_html}</ul>'
        '</section>'
    )


def build() -> str:
    body = "".join([
        '<a class="skip" href="#summary">Skip to report</a>',
        masthead(),
        nav(),
        "<main>",
        section_summary(),
        section_totals(),
        section_query_detail(),
        section_cluster(),
        section_cluster_detail(),
        section_method(),
        "</main>",
        '<footer><p>Self-contained HTML report generated from '
        f'<code>{esc(SRC.name)}</code> — no external assets, fonts or scripts. '
        'Charts are inline SVG and CSS.</p></footer>',
    ])
    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>Query Engine Comparison — TPC-H &amp; TPC-DS Benchmark Report</title>\n'
        '<meta name="description" content="Benchmark comparison of Spark Rust 0.42.1, DuckDB 1.5.5, '
        'Spark 4.1.1 Gluten and Spark 4.2 on TPC-H and TPC-DS, single node and 8-node cluster.">\n'
        f'<style>\n{CSS}\n</style>\n'
        '<script>document.documentElement.classList.add("js");</script>\n'
        '</head>\n<body>\n'
        f'{body}\n'
        f'<script>\n{JS}\n</script>\n'
        '</body>\n</html>\n'
    )


CSS = r"""
:root {
  --bg: #f7f6f2;
  --bg-soft: #efeee8;
  --card: #ffffff;
  --ink: #1b1e24;
  --ink-soft: #4b525e;
  --ink-mute: #646c7a;
  --line: #dcd8d0;
  --line-soft: #e9e5dd;
  --accent: #1e4fa3;
  --accent-soft: #e8eef8;
  --on-accent: #ffffff;
  --fill-rust: #2f6fd0;
  --fill-gluten: #8544cc;
  --fill-ink: #ffffff;
  --good: #156b45;  --good-soft: #e3f1e9;
  --warn: #8a5316;  --warn-soft: #f8eeda;
  --bad:  #a52b42;  --bad-soft:  #f8e6ea;
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --serif: Georgia, "Times New Roman", "Songti SC", serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #14161a;
    --bg-soft: #1b1e24;
    --card: #1e222a;
    --ink: #e8eaee;
    --ink-soft: #b4bac6;
    --ink-mute: #8b93a1;
    --line: #2e333d;
    --line-soft: #252a33;
    --accent: #86aaf2;
    --accent-soft: #1d2a44;
    --on-accent: #10203c;
    --fill-rust: #7fa7f2;
    --fill-gluten: #b78ef0;
    --fill-ink: #12141c;
    --good: #6fcf9e;  --good-soft: #143023;
    --warn: #e0b072;  --warn-soft: #33240f;
    --bad:  #ee8fa2;  --bad-soft:  #3a1a22;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font-family: var(--sans); font-size: 15.5px; line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}
.skip {
  position: absolute; width: 1px; height: 1px; overflow: hidden;
  clip-path: inset(50%); white-space: nowrap;
  background: var(--card); color: var(--ink);
  border: 2px solid var(--accent); z-index: 20;
}
.skip:focus {
  position: fixed; left: 12px; top: 12px;
  width: auto; height: auto; overflow: visible; clip-path: none;
  padding: 10px 16px;
}
main, .masthead, .topnav ul, footer {
  max-width: 1180px; margin-left: auto; margin-right: auto;
}
.masthead { padding: 56px 28px 8px; }
.topnav {
  position: sticky; top: 0; z-index: 10;
  background: color-mix(in srgb, var(--bg) 92%, transparent);
  backdrop-filter: blur(6px);
  border-bottom: 1px solid var(--line);
}
.topnav ul {
  display: flex; flex-wrap: wrap; gap: 4px 22px;
  list-style: none; margin: 0; padding: 10px 28px;
  font-size: 13.5px;
}
.topnav a { color: var(--ink-soft); text-decoration: none; padding: 4px 2px; display: inline-block; }
.topnav a:hover { color: var(--accent); text-decoration: underline; }
h1 {
  font-family: var(--serif);
  font-size: clamp(30px, 5vw, 44px);
  line-height: 1.12; letter-spacing: -0.015em;
  margin: 6px 0 14px; font-weight: 700;
}
h2 {
  font-family: var(--serif); font-size: clamp(23px, 3vw, 29px);
  margin: 76px 0 6px; padding-bottom: 10px;
  border-bottom: 2px solid var(--line);
  letter-spacing: -0.01em; scroll-margin-top: 64px;
}
h3 { font-size: 18px; font-weight: 650; margin: 38px 0 8px; }
h4 { font-size: 13.5px; font-weight: 650; margin: 0 0 10px; color: var(--ink-soft); }
.sec-num { color: var(--accent); font-size: 0.72em; letter-spacing: 0.08em; margin-right: 12px; }
.eyebrow {
  font-size: 12px; text-transform: uppercase; letter-spacing: 0.14em;
  color: var(--accent); font-weight: 650; margin: 0 0 6px;
}
.subtitle { font-size: 17.5px; color: var(--ink-soft); max-width: 880px; margin: 0; }
.lede { color: var(--ink-soft); max-width: 900px; margin: 10px 0 22px; }
.note, .s-note { color: var(--ink-mute); font-size: 13px; }
.meta-chips {
  display: flex; flex-wrap: wrap; gap: 8px; list-style: none;
  padding: 0; margin: 26px 0 8px;
}
.meta-chips li {
  background: var(--bg-soft); border: 1px solid var(--line-soft);
  border-radius: 999px; padding: 5px 13px; font-size: 12.5px; color: var(--ink-soft);
}
.cards { margin: 22px 0 10px; }
.grid.cards {
  display: grid; gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 235px), 1fr));
}
.metric {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 12px; padding: 18px 20px;
}
.metric .num {
  font-family: var(--serif); font-size: 32px; font-weight: 700;
  letter-spacing: -0.02em; line-height: 1.15; color: var(--accent);
  font-variant-numeric: tabular-nums;
}
.metric .label { color: var(--ink-soft); font-size: 13.5px; margin-top: 6px; line-height: 1.5; }
.findings { margin: 20px 0 0; padding-left: 22px; max-width: 980px; }
.findings li { margin: 0 0 12px; }
.card {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 12px; padding: 20px 24px;
}
.prov code { word-break: break-all; }
.hash { font-size: 12.5px; }
code {
  font-family: var(--mono); font-size: 0.88em;
  background: var(--bg-soft); padding: 1px 6px; border-radius: 5px;
}
/* tables */
.table-scroll { max-width: 100%; overflow-x: auto; margin: 16px 0 6px; }
table.data {
  width: 100%; border-collapse: collapse; font-size: 14px;
  background: var(--card); border: 1px solid var(--line);
  border-radius: 10px;
}
table.data caption {
  caption-side: top; text-align: left; color: var(--ink-mute);
  font-size: 12.5px; padding: 10px 14px 2px; line-height: 1.5;
}
table.data th, table.data td {
  padding: 9px 13px; border-bottom: 1px solid var(--line-soft);
  vertical-align: top; white-space: nowrap;
}
table.data thead th {
  font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.04em;
  color: var(--ink-mute); font-weight: 650;
  border-bottom: 2px solid var(--line); background: var(--card);
  position: sticky; top: 42px; z-index: 1;
}
table.data thead th.num { text-align: right; }
table.data tbody tr:hover { background: var(--bg-soft); }
table.data tbody tr:last-child th, table.data tbody tr:last-child td { border-bottom: none; }
th.rowhead { font-weight: 650; color: var(--ink); text-align: left; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
td.best { background: var(--accent-soft); }
td.best strong { color: var(--accent); }
.sub {
  display: block; font-size: 11.5px; color: var(--ink-mute);
  font-weight: 400; text-transform: none; letter-spacing: 0;
  margin-top: 1px;
}
.eng { display: inline-flex; align-items: center; gap: 7px; font-weight: 650; color: var(--ink); }
thead th .eng { color: var(--ink-soft); }
.chip {
  width: 10px; height: 10px; border-radius: 3px; display: inline-block;
  background: var(--c, var(--accent)); flex: none;
}
.flag { color: var(--warn); font-size: 10px; font-weight: 700; margin-left: 1px; }
td.fastest { white-space: nowrap; }
td.fastest .chip { margin-right: 6px; }
/* sortable headers */
table.sortable thead th[data-sort] { cursor: pointer; user-select: none; }
table.sortable thead th[data-sort]::after {
  content: " \2195"; color: var(--line); font-size: 11px;
}
table.sortable thead th[aria-sort="ascending"]::after { content: " \2191"; color: var(--accent); }
table.sortable thead th[aria-sort="descending"]::after { content: " \2193"; color: var(--accent); }
table.sortable thead th[data-sort]:hover { color: var(--accent); }
/* tabs */
.tablist { display: none; flex-wrap: wrap; gap: 6px; margin: 20px 0 4px; }
.js .tablist { display: flex; }
.tablist [role="tab"] {
  font: inherit; font-size: 13.5px; cursor: pointer;
  padding: 7px 14px; border-radius: 8px;
  border: 1px solid var(--line); background: var(--card); color: var(--ink-soft);
}
.tablist [role="tab"][aria-selected="true"] {
  background: var(--accent); border-color: var(--accent); color: var(--on-accent); font-weight: 600;
}
.tablist [role="tab"]:hover { border-color: var(--accent); }
[role="tabpanel"] { outline: none; }
[role="tabpanel"]:focus-visible { outline: 3px solid var(--accent); outline-offset: 4px; }
[role="tabpanel"] > h3 { margin-top: 22px; }
/* charts + bars */
.split {
  display: grid; gap: 26px;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  align-items: start;
}
.split > * { min-width: 0; }
@media (max-width: 980px) { .split { grid-template-columns: minmax(0, 1fr); } }
figure.split-chart { margin: 16px 0 0; }
figure.split-chart figcaption {
  font-size: 12.5px; color: var(--ink-mute); margin-bottom: 8px;
}
svg.chart {
  width: 100%; height: auto; display: block;
  background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  padding: 8px;
}
svg.chart .grid { stroke: var(--line-soft); stroke-width: 1; }
svg.chart .tick {
  fill: var(--ink-mute); font-size: 11.5px;
  font-family: var(--sans); font-variant-numeric: tabular-nums;
}
svg.chart .ln { fill: none; stroke-width: 2.4; stroke-linejoin: round; stroke-linecap: round; }
.legend {
  display: flex; flex-wrap: wrap; gap: 6px 18px;
  list-style: none; padding: 0; margin: 12px 0 0;
  font-size: 12.5px; color: var(--ink-soft);
}
.legend li { display: inline-flex; align-items: center; gap: 7px; }
.sm-grid {
  display: grid; gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
}
.sm-grid.single { grid-template-columns: 1fr; max-width: 920px; }
.sm {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 12px; padding: 16px 18px;
}
.bar-row {
  display: grid; grid-template-columns: 118px 1fr 86px;
  align-items: center; gap: 10px; margin: 9px 0;
  font-size: 12.5px;
}
.win-row { grid-template-columns: 64px 1fr 72px; }
.bl { color: var(--ink-soft); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bv { text-align: right; font-variant-numeric: tabular-nums; color: var(--ink); font-weight: 600; }
.bar-track { background: var(--bg-soft); border-radius: 6px; height: 14px; overflow: hidden; }
.bar { height: 100%; border-radius: 6px; }
.win-track {
  display: flex; height: 26px; border-radius: 6px; overflow: hidden;
  background: var(--bg-soft);
}
.win {
  color: var(--fill-ink); font-size: 12px; font-weight: 650;
  display: flex; align-items: center; justify-content: center;
  font-variant-numeric: tabular-nums; min-width: 22px;
}
/* fastest-count strip */
.fc-strip {
  display: flex; flex-wrap: wrap; gap: 8px 18px; align-items: center;
  margin: 18px 0 2px; font-size: 13px; color: var(--ink-soft);
}
.fc { display: inline-flex; align-items: center; gap: 7px; }
.fc b { font-variant-numeric: tabular-nums; }
.fc-strip .note { width: 100%; }
/* status pills */
.pill {
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 11.5px; font-weight: 650; white-space: nowrap;
}
.pill.good { background: var(--good-soft); color: var(--good); }
.pill.warn { background: var(--warn-soft); color: var(--warn); }
.pill.bad  { background: var(--bad-soft);  color: var(--bad); }
td.status { white-space: normal; min-width: 220px; }
td.status .s-note { display: block; margin-top: 3px; }
/* resource disclosure */
td.res-cell { white-space: normal; min-width: 130px; }
details.res summary {
  cursor: pointer; color: var(--accent); font-size: 12.5px; font-weight: 600;
  list-style: none;
  display: inline-block; padding: 6px 2px; margin: -6px -2px;
}
details.res summary::before { content: "\25B8 "; display: inline-block; transition: none; }
details.res[open] summary::before { content: "\25BE "; }
details.res summary::-webkit-details-marker { display: none; }
.res-head { font-size: 11px; color: var(--ink-mute); margin: 8px 0 2px; }
.res-list {
  list-style: none; padding: 0; margin: 0; min-width: 180px;
  font-size: 11.5px; color: var(--ink-soft);
}
.res-list li {
  display: flex; justify-content: space-between; gap: 12px;
  padding: 2px 0; border-bottom: 1px dotted var(--line-soft);
}
.res-list b { font-variant-numeric: tabular-nums; font-weight: 600; color: var(--ink); }
/* sticky first column on wide cluster tables */
.sticky-first tbody th.rowhead, .sticky-first thead th:first-child {
  position: sticky; left: 0; background: var(--card); z-index: 2;
}
.sticky-first tbody tr:hover th.rowhead { background: var(--bg-soft); }
table.sortable thead th:first-child { z-index: 3; }
/* footer */
footer {
  margin-top: 90px; padding: 26px 28px 60px;
  border-top: 1px solid var(--line); color: var(--ink-mute); font-size: 13px;
}
footer p { margin: 0; }
/* responsive */
@media (max-width: 640px) {
  .masthead { padding: 38px 18px 4px; }
  .topnav ul { padding: 10px 18px; gap: 4px 16px; }
  main { padding: 0 2px; }
  .metric .num { font-size: 28px; }
  table.data thead th { position: static; }
  .bar-row { grid-template-columns: 96px 1fr 76px; }
}
@media print {
  .topnav, .skip { display: none; }
  [role="tabpanel"][hidden] { display: block !important; }
  .tablist { display: none !important; }
  body { background: #fff; }
  .metric, .card, .sm, svg.chart, table.data { border-color: #bbb; }
  h2 { break-after: avoid; }
  table.data tr, .sm, svg.chart { break-inside: avoid; }
}
"""

JS = r"""
(function () {
  /* Tabs */
  document.querySelectorAll("[data-tabset]").forEach(function (set) {
    var tabs = Array.prototype.slice.call(set.querySelectorAll('[role="tab"]'));
    var panels = tabs.map(function (t) {
      return document.getElementById(t.getAttribute("aria-controls"));
    });
    function select(i) {
      tabs.forEach(function (t, j) {
        var on = i === j;
        t.setAttribute("aria-selected", on ? "true" : "false");
        t.tabIndex = on ? 0 : -1;
        if (panels[j]) panels[j].hidden = !on;
      });
    }
    tabs.forEach(function (t, i) {
      t.addEventListener("click", function () { select(i); });
      t.addEventListener("keydown", function (e) {
        var n = null;
        if (e.key === "ArrowRight" || e.key === "ArrowDown") n = (i + 1) % tabs.length;
        else if (e.key === "ArrowLeft" || e.key === "ArrowUp") n = (i - 1 + tabs.length) % tabs.length;
        else if (e.key === "Home") n = 0;
        else if (e.key === "End") n = tabs.length - 1;
        if (n !== null) { e.preventDefault(); select(n); tabs[n].focus(); }
      });
    });
    select(0);
  });

  /* Column sorting */
  document.querySelectorAll("table.sortable").forEach(function (table) {
    var tbody = table.tBodies[0];
    if (!tbody) return;
    var ths = Array.prototype.slice.call(table.querySelectorAll("th[data-sort]"));
    ths.forEach(function (th) {
      th.setAttribute("aria-sort", "none");
      th.setAttribute("title", "Click to sort");
      th.addEventListener("click", function () {
        var dir = th.getAttribute("aria-sort") === "ascending" ? -1 : 1;
        ths.forEach(function (o) { o.setAttribute("aria-sort", "none"); });
        th.setAttribute("aria-sort", dir === 1 ? "ascending" : "descending");
        var col = th.cellIndex;
        var numeric = th.getAttribute("data-sort") === "num";
        var rows = Array.prototype.slice.call(tbody.rows);
        rows.sort(function (a, b) {
          var ca = a.cells[col], cb = b.cells[col];
          if (!ca || !cb) return 0;
          if (numeric) {
            var va = parseFloat(ca.getAttribute("data-v"));
            if (isNaN(va)) va = parseFloat(ca.textContent.replace(/[^0-9.\-]/g, ""));
            var vb = parseFloat(cb.getAttribute("data-v"));
            if (isNaN(vb)) vb = parseFloat(cb.textContent.replace(/[^0-9.\-]/g, ""));
            if (isNaN(va)) va = -Infinity;
            if (isNaN(vb)) vb = -Infinity;
            return (va - vb) * dir;
          }
          return ca.textContent.trim().localeCompare(cb.textContent.trim()) * dir;
        });
        rows.forEach(function (r) { tbody.appendChild(r); });
      });
    });
  });
})();
"""


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.name}: {OUT.stat().st_size / 1024:.0f} KB")
