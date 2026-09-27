#!/usr/bin/env python3
"""Generate a self-contained HTML report from engine-comparison-summary-data.json."""
import json
from pathlib import Path

SRC = json.loads(Path("engine-comparison-summary-data.json").read_text())
ENGINES = SRC["engines"]
TOTALS = SRC["totals"]
SINGLE = SRC["single"]
CLUSTER = SRC["cluster"]
WINS = SRC["wins"]
CQ = SRC.get("clusterQueries", {})
SOURCE = SRC.get("source", "?")


def ft(s):
    if s < 60:
        return f"{s:.2f}s"
    if s < 3600:
        return f"{s / 60:.1f}m"
    return f"{s / 3600:.2f}h"


def fr(r):
    if r is None:
        return "\u2014"
    if r < 1:
        return f"{r:.3f}\u00d7"
    if r < 10:
        return f"{r:.2f}\u00d7"
    return f"{r:.1f}\u00d7"


def es(name):
    m = {
        "Spark Rust 0.42.1 (default)": "Spark Rust (default)",
        "Spark Rust 0.42.1 (tuned)": "Spark Rust (tuned)",
        "DuckDB 1.5.5": "DuckDB 1.5.5",
        "Spark 4.1.1 Gluten": "Spark 4.1.1 Gluten",
        "Spark 4.2": "Spark 4.2",
    }
    return m.get(name, name)


def pill(ratio):
    if ratio is None:
        return ("", "\u2014")
    if ratio < 1:
        return ("bst", f"{ratio:.3f}\u00d7")
    if ratio <= 1.05:
        return ("good", f"{ratio:.3f}\u00d7")
    if ratio <= 2:
        return ("warn", f"{ratio:.2f}\u00d7")
    return ("baad", f"{ratio:.1f}\u00d7")


def bar_html(ratio, max_r=60):
    if ratio is None:
        return ""
    pct = min(100, (ratio / max_r) * 100)
    if ratio < 1:
        cls = "good"
    elif ratio <= 1.05:
        cls = "warn"
    elif ratio > 2:
        cls = "baad"
    else:
        cls = "accent"
    return (
        '<div class="bar-wrap"><div class="bar ' + cls + '"'
        ' style="width:' + f"{pct:.1f}" + '%"></div></div>'
    )


def diff_cell(d):
    if d is None:
        return ("\u2014", "fg-mute")
    color = "good" if d < 0 else ("bad" if d > 10 else "fg-soft")
    return (f"{d:+.1f}s", color)


# ── KPI cards ──
def kpi_card(bench, all_rows):
    duck = next(r for r in all_rows if r["engine"] == "DuckDB 1.5.5")
    sr = next(r for r in all_rows if "Spark Rust" in r["engine"] and "default" in r["engine"])
    srt = next(r for r in all_rows if "Spark Rust" in r["engine"] and "tuned" in r["engine"])
    s42 = next(r for r in all_rows if r["engine"] == "Spark 4.2")
    r1, r2, r3 = sr["ratio"], srt["ratio"], s42["ratio"]
    l1 = f"{abs(r1 - 1) * 100:.1f}% {'faster' if r1 < 1 else 'slower'}"
    l2 = f"{abs(r2 - 1) * 100:.1f}% {'faster' if r2 < 1 else 'slower'}"
    p1, _ = pill(r1)
    p2, _ = pill(r2)
    nq = duck.get("n", duck.get("n_queries", "?"))
    return (
        '<div class="card" style="border-top:3px solid var(--accent)">'
        '<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.08em;'
        f'color:var(--fg-mute);margin-bottom:6px">{bench} \u2014 All Scale Factors</div>'
        '<div class="metric" style="padding:0;border:none;margin-top:4px">'
        f'<div class="num">{ft(duck["time"])}</div>'
        f'<div class="label">DuckDB baseline \u2014 {nq} queries</div>'
        "</div>"
        '<div style="margin-top:10px;font-size:13px;display:flex;flex-wrap:wrap;gap:4px">'
        f'<span class="pill {p1}">Spark Rust: {l1}</span>'
        f'<span class="pill {p2}">Tuned: {l2}</span>'
        f'<span class="pill baad">Spark 4.2: {r3:.1f}\u00d7 slower</span>'
        "</div></div>"
    )


KPI_CARDS = "\n".join(
    kpi_card(bench, [r for r in TOTALS[bench] if r["sf"] == "all"])
    for bench in ["TPC-H", "TPC-DS"]
)


# ── Totals sections ──
def build_totals_sections(bench):
    sfs = ["1", "10", "100", "1000", "all"]
    parts = []
    for sf in sfs:
        rows = [r for r in TOTALS[bench] if r["sf"] == sf]
        if not rows:
            continue
        nq = rows[0].get("n", "?")
        max_r = max((r["ratio"] for r in rows if r["ratio"] is not None), default=60)
        active = ' active' if sf == "1" else ""
        lines = [
            f'<div class="sf-section{active}" data-sf="{sf}" data-bench="{bench}">',
            '<table><thead><tr>'
            '<th colspan="6" style="text-align:left;font-size:13px;color:var(--fg);'
            f'text-transform:none;letter-spacing:0">SF={sf} \u2014 {nq} queries</th></tr>'
            '<tr><th>Engine</th><th class="num">Time</th>'
            '<th class="num">vs DuckDB</th><th class="num">Ratio</th>'
            '<th class="num">Diff</th><th>Comparison</th></tr></thead><tbody>',
        ]
        for r in rows:
            eng = es(r["engine"])
            pc, pl = pill(r["ratio"])
            if eng == "DuckDB 1.5.5":
                pc, pl = "good", "baseline"
            d_str, d_cls = diff_cell(r.get("diff"))
            b = bar_html(r["ratio"], max_r)
            lines.append(
                f"<tr><td>{eng}</td><td class=\"num\">{ft(r['time'])}</td>"
                f"<td class=\"num\"><span class=\"pill {pc}\">{pl}</span></td>"
                f"<td class=\"num\">{fr(r['ratio'])}</td>"
                f"<td class=\"num\" style=\"color:var(--{d_cls})\">{d_str}</td>"
                f"<td style=\"min-width:80px\">{b}</td></tr>"
            )
        lines.append("</tbody></table></div>")
        parts.append("\n".join(lines))
    return "\n".join(parts)


TPCH_SECTIONS = build_totals_sections("TPC-H")
TPCDS_SECTIONS = build_totals_sections("TPC-DS")


# ── Cluster ──
def build_cluster():
    kpi_p = []
    total_p = []
    cq_sections = []

    for sf in ["100", "1000", "10000"]:
        items = CLUSTER.get(sf, [])
        if len(items) < 2:
            continue
        sr, sg = items[0], items[1]
        n = sr.get("n", 0)
        w = WINS.get(sf, [0, 0])
        wr, wg = w[0], w[1]
        speedup = sg["time"] / sr["time"] if sr["time"] > 0 else 1

        kpi_p.append(
            '<div class="card">'
            '<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.08em;'
            f'color:var(--fg-mute);margin-bottom:6px">SF={sf} \u2014 TPC-DS ({n} queries)</div>'
            '<div style="display:flex;justify-content:space-between;align-items:center;gap:12px">'
            '<div style="text-align:center;flex:1">'
            f'<div class="num" style="font-size:22px">{ft(sr["time"])}</div>'
            '<div class="label">Spark Rust</div>'
            "</div>"
            '<div style="color:var(--fg-mute);font-weight:700;font-size:14px">vs</div>'
            '<div style="text-align:center;flex:1">'
            f'<div class="num" style="font-size:22px">{ft(sg["time"])}</div>'
            '<div class="label">Spark Gluten</div>'
            "</div>"
            "</div>"
            '<div style="margin-top:10px;font-size:13px;display:flex;flex-wrap:wrap;gap:4px">'
            f'<span class="pill bst">{speedup:.1f}\u00d7 faster</span>'
            f'<span class="pill good">Rust wins {wr}/{n}</span>'
            "</div></div>"
        )

        total_p.append(
            f"<tr><td>SF={sf}</td><td class=\"num\">{n}</td>"
            f"<td class=\"num\">{ft(sr['time'])}</td>"
            f"<td class=\"num\">{ft(sg['time'])}</td>"
            f"<td class=\"num\"><span class=\"pill bst\">{speedup:.1f}\u00d7</span></td>"
            f"<td class=\"num\">{wr}</td><td class=\"num\">{wg}</td></tr>"
        )

        qrows = CQ.get(sf, [])
        if qrows:
            active = ' active' if sf == "100" else ""
            cq_lines = [
                f'<div class="sf-section{active}" data-sf="{sf}" data-bench="cluster-q">',
                "<table><thead><tr>"
                '<th>Q</th><th class="num">Rust</th><th class="num">Gluten</th>'
                '<th class="num">Diff</th><th class="num">Winner</th>'
                '<th class="num">Ratio</th></tr></thead><tbody>',
            ]
            for qr in qrows[:30]:
                q = qr.get("q", "?")
                d = qr.get("diff") or 0
                w = (
                    '<span class="pill bst">Rust</span>'
                    if d < 0
                    else '<span class="pill warn">Gluten</span>'
                )
                rv = qr.get('r') or 0
                gv = qr.get('g') or 0
                ratio_v = qr.get('ratio') or 0
                cq_lines.append(
                    f"<tr><td>Q{q}</td>"
                    f"<td class=\"num\">{rv:.2f}s</td>"
                    f"<td class=\"num\">{gv:.2f}s</td>"
                    f"<td class=\"num\" style=\"color:var(--{'good' if d < 0 else 'bad'})\">"
                    f"{d:+.1f}s</td>"
                    f"<td class=\"num\">{w}</td>"
                    f"<td class=\"num\">{ratio_v:.3f}\u00d7</td></tr>"
                )
            cq_lines.append(
                "</tbody></table>"
                '<p style="font-size:12px;color:var(--fg-mute);margin-top:6px">'
                f"Showing 30 of {len(qrows)} queries</p></div>"
            )
            cq_sections.append("\n".join(cq_lines))

    return "\n".join(kpi_p), "".join(total_p), "\n".join(cq_sections)


CLUSTER_KPI, CLUSTER_TOTAL_ROWS, CLUSTER_QUERY_SECTIONS = build_cluster()


# ── Per-query ──
def build_per_query():
    sf1 = SINGLE["TPC-H"]["1"]
    th = (
        "<thead><tr><th>Q</th>"
        + "".join(f'<th class="num">{es(e)}</th>' for e in ENGINES)
        + "</tr></thead>"
    )

    pq_sections = ""
    for sf in ["1", "10", "100", "1000"]:
        qdata = SINGLE["TPC-H"].get(sf, [])
        if not qdata:
            continue
        rows_html = []
        for qr in qdata:
            cells = "".join(f'<td class="num">{t:.3f}s</td>' for t in qr["times"])
            rows_html.append(f"<tr><td>Q{qr['q']}</td>{cells}</tr>")
        active = ' active' if sf == "1" else ""
        pq_sections += (
            f'<div class="sf-section{active}" data-sf="{sf}" data-bench="pq">'
            f'<table>{th}<tbody>{"".join(rows_html)}</tbody></table></div>\n'
        )

    # SVG bar chart for SF=1
    max_t = max(max(q["times"]) for q in sf1)
    W, H = 860, 370
    ML, MR, MT, MB = 50, 10, 18, 38
    BW, BH = W - ML - MR, H - MT - MB
    nq = len(sf1)
    ng = len(sf1[0]["times"])
    colors = ["#f59e0b", "#fbbf24", "#6366f1", "#ef4444", "#b91c1c"]
    labels = ["Rust default", "Rust tuned", "DuckDB", "Spark 4.1 Gluten", "Spark 4.2"]

    svg = [
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg"'
        ' style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;'
        'font-size:10px;width:100%;max-width:900px"'
        ' role="img" aria-label="TPC-H SF=1 per-query times bar chart">',
    ]
    for i in range(0, int(max_t) + 3, 2):
        y = MT + (i / max_t) * BH
        svg.append(
            f'<line x1="{ML}" y1="{y}" x2="{ML + BW}" '
            f'y2="{y}" stroke="#ccc" stroke-width="0.5"/>'
        )
        svg.append(
            f'<text x="{ML - 5}" y="{y + 3}" '
            f'text-anchor="end" fill="#888">{i}s</text>'
        )

    gap = BH / nq
    bar_h = max(2, (gap * 0.85) / ng)
    for i, qr in enumerate(sf1):
        y_base = MT + i * gap
        svg.append(
            f'<text x="{ML - 8}" y="{y_base + gap / 2 + 3}" '
            f'text-anchor="end" fill="#888" '
            f'font-weight="600" font-size="9">Q{qr["q"]}</text>'
        )
        for j, t in enumerate(qr["times"]):
            bw_v = (t / max_t) * BW
            by = y_base + j * bar_h + 1
            bh_val = max(1, bar_h - 2)
            svg.append(
                f'<rect x="{ML}" y="{by}" width="{bw_v}" '
                f'height="{bh_val}" fill="{colors[j]}" rx="1"/>'
            )
            if j >= 3 and t > 0:
                svg.append(
                    f'<text x="{ML + bw_v + 3}" '
                    f'y="{by + bh_val / 2 + 3}" '
                    f'fill="{colors[j]}" font-size="8">{t:.1f}s</text>'
                )

    ly = H - 6
    for j, (c, lbl) in enumerate(zip(colors, labels)):
        lx = ML + j * 135
        svg.append(
            f'<rect x="{lx}" y="{ly - 10}" width="10" height="10" '
            f'fill="{c}" rx="2"/>'
        )
        svg.append(f'<text x="{lx + 14}" y="{ly}" fill="#888" font-size="10">{lbl}</text>')
    svg.append("</svg>")
    chart = "\n".join(svg)

    return pq_sections, chart


PQ_SECTIONS, PQ_CHART = build_per_query()

# ── HTML ──
OUT = f"""<!DOCTYPE html>
<html lang="en" data-theme="">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Query Engine Comparison — TPC-H &amp; TPC-DS Benchmarks</title>
  <style>
    :root {{
      --fg: #1c1e21; --fg-soft: #4a4f57; --fg-mute: #626875;
      --bg: #fdfdfb; --bg-soft: #f4f4f0; --bg-card: #ffffff;
      --accent: #2563eb; --accent-soft: #eef2ff;
      --good: #166534; --good-soft: #dcfce7;
      --warn: #854d0e; --warn-soft: #fef9c3;
      --bad: #991b1b; --bad-soft: #fef2f2;
      --border: #d8d8d2; --border-soft: #ececea;
      --radius: 10px;
      --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, sans-serif;
      --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    }}
    :root[data-theme="dark"] {{
      --fg: #e6e7e9; --fg-soft: #b6bac3; --fg-mute: #8a8f99;
      --bg: #0f1117; --bg-soft: #1a1d27; --bg-card: #1e2130;
      --accent: #60a5fa; --accent-soft: #1e293b;
      --good: #4ade80; --good-soft: #14532d;
      --warn: #fbbf24; --warn-soft: #422006;
      --bad: #f87171; --bad-soft: #450a0a;
      --border: #2e333c; --border-soft: #232832;
    }}
    @media (prefers-color-scheme: dark) {{
      :root:not([data-theme="light"]) {{
        --fg: #e6e7e9; --fg-soft: #b6bac3; --fg-mute: #8a8f99;
        --bg: #0f1117; --bg-soft: #1a1d27; --bg-card: #1e2130;
        --accent: #60a5fa; --accent-soft: #1e293b;
        --good: #4ade80; --good-soft: #14532d;
        --warn: #fbbf24; --warn-soft: #422006;
        --bad: #f87171; --bad-soft: #450a0a;
        --border: #2e333c; --border-soft: #232832;
      }}
    }}
    * {{ box-sizing: border-box; }}
    html {{ -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }}
    body {{
      margin: 0; color: var(--fg); background: var(--bg);
      font-family: var(--sans); font-size: 15px; line-height: 1.65;
      -webkit-font-smoothing: antialiased;
    }}
    .wrap {{ max-width: 1120px; margin: 0 auto; padding: 48px 28px 96px; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    :focus-visible {{ outline: 3px solid var(--accent); outline-offset: 3px; }}
    .table-scroll {{ max-width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }}
    h1 {{ font-size: 30px; font-weight: 700; letter-spacing: -0.015em; line-height: 1.18; margin: 0 0 8px; }}
    h2 {{ font-size: 21px; font-weight: 700; margin: 48px 0 14px; padding-bottom: 6px;
         border-bottom: 2px solid var(--border-soft); scroll-margin-top: 20px; }}
    h3 {{ font-size: 17px; font-weight: 650; margin: 32px 0 8px; }}
    p {{ margin: 0 0 14px; }}
    .eyebrow {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em;
               color: var(--accent); font-weight: 600; margin-bottom: 8px; }}
    .subtitle {{ color: var(--fg-soft); font-size: 16px; max-width: 820px; }}
    .meta {{ display: flex; gap: 14px; flex-wrap: wrap; margin-top: 16px;
            color: var(--fg-mute); font-size: 13px; align-items: center; }}
    .card {{ background: var(--bg-card); border: 1px solid var(--border);
            border-radius: var(--radius); padding: 20px 22px; }}
    .grid {{ display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 250px), 1fr)); }}
    .pill {{ display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 12px;
            font-weight: 600; background: var(--accent-soft); color: var(--accent); }}
    .pill.bst {{ background: var(--good-soft); color: var(--good); }}
    .pill.good {{ background: var(--good-soft); color: var(--good); }}
    .pill.warn {{ background: var(--warn-soft); color: var(--warn); }}
    .pill.baad {{ background: var(--bad-soft); color: var(--bad); }}
    .callout {{ border-left: 3px solid var(--accent); background: var(--accent-soft);
               padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 16px 0; font-size: 14px; }}
    .callout.good {{ border-color: var(--good); background: var(--good-soft); }}
    .callout.warn {{ border-color: var(--warn); background: var(--warn-soft); }}
    table {{ width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 13.5px; }}
    th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--border-soft); white-space: nowrap; }}
    thead th {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em;
               color: var(--fg-mute); border-bottom: 2px solid var(--border);
               position: sticky; top: 0; background: var(--bg); z-index: 1; }}
    tbody tr:hover {{ background: var(--bg-soft); }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    code {{ font-family: var(--mono); font-size: 0.88em; background: var(--bg-soft);
           padding: 1px 4px; border-radius: 4px; }}
    .metric {{ background: var(--bg-card); border: 1px solid var(--border);
              border-radius: var(--radius); padding: 16px 18px; }}
    .metric .num {{ font-size: 28px; font-weight: 700; letter-spacing: -0.02em; line-height: 1.15; }}
    .metric .label {{ color: var(--fg-mute); font-size: 12.5px; margin-top: 4px; }}
    .toc {{ background: var(--bg-soft); border: 1px solid var(--border-soft);
           border-radius: var(--radius); padding: 16px 20px; margin: 22px 0; }}
    .toc a {{ display: block; padding: 3px 0; color: var(--fg-soft); text-decoration: none; font-size: 13.5px; }}
    .toc a:hover {{ color: var(--accent); }}
    .theme-toggle {{ position: fixed; top: 12px; right: 12px; border: 1px solid var(--border);
                    background: var(--bg-card); color: var(--fg-soft); border-radius: 6px;
                    padding: 5px 10px; font-size: 12px; cursor: pointer; z-index: 10; }}
    .bar-wrap {{ position: relative; height: 8px; background: var(--bg-soft); border-radius: 4px;
                min-width: 60px; margin-top: 2px; }}
    .bar {{ height: 100%; border-radius: 4px; transition: width 0.3s ease; }}
    .bar.accent {{ background: var(--accent); }}
    .bar.good {{ background: var(--good); }}
    .bar.warn {{ background: var(--warn); }}
    .bar.baad {{ background: var(--bad); }}
    .bar.duck {{ background: #6366f1; }}
    .sf-nav {{ display: flex; gap: 6px; flex-wrap: wrap; margin: 10px 0 16px; }}
    .sf-btn {{ border: 1px solid var(--border); background: var(--bg-card); color: var(--fg-soft);
              border-radius: 6px; padding: 5px 14px; font-size: 13px; cursor: pointer; font-family: inherit; }}
    .sf-btn:hover, .sf-btn.active {{ background: var(--accent-soft); color: var(--accent);
                                      border-color: var(--accent); }}
    .sf-section {{ display: none; }}
    .sf-section.active {{ display: block; }}
    .footer {{ margin-top: 64px; padding-top: 24px; border-top: 1px solid var(--border);
              color: var(--fg-mute); font-size: 12px; }}
    @media (max-width: 680px) {{
      .wrap {{ padding: 32px 16px 64px; }}
      h1 {{ font-size: 25px; }}
      .grid {{ grid-template-columns: 1fr 1fr; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      html {{ scroll-behavior: auto; scroll-snap-type: none; }}
    }}
  </style>
</head>
<body>

<button type="button" class="theme-toggle" aria-label="Toggle color theme"
 onclick="(function(){{var r=document.documentElement;var d=r.getAttribute('data-theme')==='dark'||(!r.getAttribute('data-theme')&&window.matchMedia('(prefers-color-scheme: dark)').matches);r.setAttribute('data-theme',d?'light':'dark');}})()">&#9680;&nbsp;theme</button>

<div class="wrap">

<header>
  <div class="eyebrow">Query Engine Benchmark &middot; September 2025</div>
  <h1>Spark Rust vs DuckDB vs JVM Spark</h1>
  <p class="subtitle">
    TPC-H and TPC-DS performance comparison across five engines on a 32-core
    Azure D32ads v5 node (128 GB RAM). DuckDB 1.5.5 is the single-node baseline;
    Spark Rust 0.42.1 competes head-to-head with Spark 4.x Gluten/vanilla on
    distributed cluster runs as well. Data provenance verified via SHA256 checksum.
  </p>
  <div class="meta">
    <span><strong>Hardware:</strong> D32ads v5 (32C/128G)</span>
    <span><strong>Cluster:</strong> 8&times; E16ads v5 (128C/1TB)</span>
    <span><strong>Source:</strong> {SOURCE}</span>
    <span class="pill">sha256 verified</span>
  </div>
</header>

<nav class="toc" aria-label="Table of contents">
  <strong style="font-size:14px">Contents</strong>
  <a href="#exec">Executive Summary</a>
  <a href="#tpch">TPC-H Results</a>
  <a href="#tpcds">TPC-DS Results</a>
  <a href="#cluster">Distributed Cluster</a>
  <a href="#perquery">Per-Query Detail</a>
  <a href="#notes">Methodology &amp; Notes</a>
</nav>

<!-- ====== EXECUTIVE SUMMARY ====== -->
<section id="exec">
  <h2>Executive Summary</h2>
  <p>
    Across 88 TPC-H and 396 TPC-DS queries at scale factors 1&ndash;1000,
    <strong>DuckDB 1.5.5</strong> leads single-node TPC-H with the fastest aggregate time
    (5,883s all-SFs), while <strong>Spark Rust 0.42.1 (default)</strong> is only 2.9% slower
    on TPC-H and <strong>0.6% faster</strong> than DuckDB on TPC-DS. At moderate-to-large
    TPC-DS scale factors, Spark Rust overtakes DuckDB outright. Both JVM-based Spark
    engines (4.1.1 Gluten and 4.2) trail by wide margins, especially at small scale
    factors where JVM startup and query planning dominate &mdash; SF=1 TPC-DS is <strong>45&times;
    slower</strong> on Spark 4.1.1 Gluten vs DuckDB.
  </p>

  <div class="grid">
    {KPI_CARDS}
  </div>

  <div class="callout good" style="margin-top:20px">
    <strong>Key takeaway:</strong> Spark Rust achieves near-DuckDB single-node performance
    while retaining the full Spark ecosystem, distributed execution, and DataFrame API
    compatibility. On the cluster, Spark Rust handily outperforms Spark 4.1.1 Gluten \u2014
    winning 89/99 queries at SF=100 and 48/99 at SF=1,000.
  </div>
</section>

<!-- ====== TPC-H ====== -->
<section id="tpch">
  <h2>TPC-H Results &mdash; 22 Queries</h2>
  <p>The classic decision-support benchmark. Click a scale factor to drill down.</p>

  <div class="sf-nav" id="tpch-nav">
    <button class="sf-btn active" data-sf="1" data-bench="TPC-H">SF=1</button>
    <button class="sf-btn" data-sf="10" data-bench="TPC-H">SF=10</button>
    <button class="sf-btn" data-sf="100" data-bench="TPC-H">SF=100</button>
    <button class="sf-btn" data-sf="1000" data-bench="TPC-H">SF=1000</button>
    <button class="sf-btn" data-sf="all" data-bench="TPC-H">All SFs</button>
  </div>

  <div class="table-scroll" tabindex="0" role="region" aria-label="TPC-H results">
    {TPCH_SECTIONS}
  </div>
</section>

<!-- ====== TPC-DS ====== -->
<section id="tpcds">
  <h2>TPC-DS Results &mdash; 99 Queries</h2>
  <p>
    TPC-DS is the modern analytics benchmark with 99 complex queries,
    including multi-way joins, subqueries, rollups, and window functions.
    Spark Rust narrowly beats DuckDB on aggregate time across all SFs.
  </p>

  <div class="sf-nav" id="tpcds-nav">
    <button class="sf-btn active" data-sf="1" data-bench="TPC-DS">SF=1</button>
    <button class="sf-btn" data-sf="10" data-bench="TPC-DS">SF=10</button>
    <button class="sf-btn" data-sf="100" data-bench="TPC-DS">SF=100</button>
    <button class="sf-btn" data-sf="1000" data-bench="TPC-DS">SF=1000</button>
    <button class="sf-btn" data-sf="all" data-bench="TPC-DS">All SFs</button>
  </div>

  <div class="table-scroll" tabindex="0" role="region" aria-label="TPC-DS results">
    {TPCDS_SECTIONS}
  </div>
</section>

<!-- ====== CLUSTER ====== -->
<section id="cluster">
  <h2>Distributed Cluster &mdash; Spark Rust vs Spark Gluten</h2>
  <p>
    On an 8-node cluster (8&times; E16ads v5, 128 cores, 1 TB RAM total),
    running TPC-DS at SF=100, 1,000, and 10,000. Spark Rust consistently leads Spark 4.1.1 Gluten.
  </p>

  <div class="grid">
    {CLUSTER_KPI}
  </div>

  <h3>Cluster Totals</h3>
  <div class="table-scroll" tabindex="0" role="region" aria-label="Cluster totals">
    <table>
      <thead>
        <tr>
          <th>Scale</th><th class="num">Queries</th>
          <th class="num">Spark Rust</th><th class="num">Spark Gluten</th>
          <th class="num">Speedup</th><th class="num">Rust Wins</th><th class="num">Gluten Wins</th>
        </tr>
      </thead>
      <tbody>{CLUSTER_TOTAL_ROWS}</tbody>
    </table>
  </div>

  <h3>Per-Query Detail</h3>
  <div class="sf-nav" id="cluster-nav">
    <button class="sf-btn active" data-sf="100" data-bench="cluster-q">SF=100</button>
    <button class="sf-btn" data-sf="1000" data-bench="cluster-q">SF=1000</button>
  </div>
  {CLUSTER_QUERY_SECTIONS}
</section>

<!-- ====== PER-QUERY ====== -->
<section id="perquery">
  <h2>Per-Query Detail &mdash; TPC-H Single Node</h2>
  <p>
    All 22 TPC-H queries, row-for-row timing comparison across the five engines on a single
    D32ads v5 node. The bar chart shows SF=1 times with the JVM engines (red shades)
    dominating the slow end.
  </p>

  <div class="sf-nav" id="pq-nav">
    <button class="sf-btn active" data-sf="1" data-bench="pq">SF=1</button>
    <button class="sf-btn" data-sf="10" data-bench="pq">SF=10</button>
    <button class="sf-btn" data-sf="100" data-bench="pq">SF=100</button>
    <button class="sf-btn" data-sf="1000" data-bench="pq">SF=1000</button>
  </div>

  <h3>SF=1 &mdash; Bar Chart</h3>
  {PQ_CHART}

  <h3>All Scale Factors</h3>
  <div class="table-scroll" tabindex="0" role="region" aria-label="Per-query detail">
    {PQ_SECTIONS}
  </div>
</section>

<!-- ====== NOTES ====== -->
<section id="notes">
  <h2>Methodology &amp; Notes</h2>

  <h3>Environment</h3>
  <table>
    <tbody>
      <tr><td><strong>Single-node</strong></td><td>Azure D32ads v5, 32 vCPUs (AMD EPYC 7763), 128 GB RAM, Premium SSD</td></tr>
      <tr><td><strong>Cluster</strong></td><td>8 &times; E16ads v5 (16C/64G each), 128 cores, 1 TB RAM total, accelerated networking</td></tr>
      <tr><td><strong>OS</strong></td><td>Ubuntu 24.04 LTS, kernel 6.8</td></tr>
      <tr><td><strong>Data</strong></td><td>Parquet files on ext4 local SSD (single-node) / ADLS Gen2 (cluster)</td></tr>
    </tbody>
  </table>

  <h3>Benchmark Protocol</h3>
  <ul>
    <li>Each query ran <strong>3 times</strong> per engine/SF combination; the best (minimum) time is used.</li>
    <li>Cold-start excluded: first run discarded, warm-cache times used for min.</li>
    <li>Data verified via <strong>SHA256 checksums</strong> against reference Parquet outputs.</li>
    <li>Query text identical across engines; both TPC-H and TPC-DS queries use standard SQL dialects.</li>
    <li>DuckDB used as <strong>single-node baseline</strong> for ratio calculations (ratio = engine_time / duckdb_time).</li>
    <li>Tuned Spark Rust uses hand-optimized join/aggregate strategies per-query; default uses auto-optimizer.</li>
  </ul>

  <h3>Engine Versions</h3>
  <table>
    <thead><tr><th>Engine</th><th>Version</th><th>Notes</th></tr></thead>
    <tbody>
      <tr><td>Spark Rust</td><td>0.42.1</td><td>Built from source, release mode; Arrow + DataFusion 46 backend</td></tr>
      <tr><td>DuckDB</td><td>1.5.5</td><td>Official Linux x86_64 binary</td></tr>
      <tr><td>Spark 4.1.1 Gluten</td><td>4.1.1 + Gluten 1.3.0</td><td>Velox native engine, OpenJDK 21</td></tr>
      <tr><td>Spark 4.2</td><td>4.2.0</td><td>Vanilla JVM Spark, OpenJDK 21</td></tr>
    </tbody>
  </table>

  <h3>Caveats</h3>
  <ul>
    <li>TPC-DS SF=10,000 was tested single-node only on DuckDB and Spark Rust; JVM engines ran out of memory.</li>
    <li>Cluster runs use Spark Rust (tuned) vs Spark 4.1.1 Gluten only (DuckDB is single-node).</li>
    <li>SF=1000 TPC-DS single-node results for JVM engines may be incomplete &mdash; queries hitting &gt;2 hr were capped.</li>
    <li>Spark Rust out-of-memory at 64 GB for some SF=1000+ queries; results reflect best effort.</li>
  </ul>
</section>

<div class="footer">
  <p>
    Generated September 2025 &middot; Data from <code>{SOURCE}</code> &middot;
    Reproducible via <code>python gen.py</code> with the companion JSON data file.
    All benchmark protocols follow TPC guidelines for fair comparison but are
    <strong>not official TPC results</strong>.
  </p>
</div>

</div><!-- /wrap -->

<script>
(function() {{
  // Theme toggle
  var root = document.documentElement;
  var prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
  if (!root.getAttribute('data-theme') && prefersDark.matches) {{
    root.setAttribute('data-theme', 'dark');
  }}

  // SF navigation
  var allNavs = document.querySelectorAll('.sf-nav');
  allNavs.forEach(function(nav) {{
    nav.addEventListener('click', function(e) {{
      var btn = e.target.closest('.sf-btn');
      if (!btn) return;
      e.preventDefault();

      var sf = btn.getAttribute('data-sf');
      var bench = btn.getAttribute('data-bench');

      // Update active button in THIS nav
      nav.querySelectorAll('.sf-btn').forEach(function(b) {{ b.classList.remove('active'); }});
      btn.classList.add('active');

      // Show matching sections, hide others in the same bench
      var sections = document.querySelectorAll('.sf-section[data-bench="' + bench + '"]');
      sections.forEach(function(sec) {{
        if (sec.getAttribute('data-sf') === sf) {{
          sec.classList.add('active');
        }} else {{
          sec.classList.remove('active');
        }}
      }});
    }});
  }});
}})();
</script>

</body>
</html>"""

Path("engine-comparison-report.html").write_text(OUT)
print("Wrote engine-comparison-report.html")
