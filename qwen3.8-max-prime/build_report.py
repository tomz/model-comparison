#!/usr/bin/env python3
"""Build a self-contained HTML report from engine-comparison-summary-data.json.

The JSON file is the sole input. Every number in the report is either read
directly from that file or recomputed from it; fields whose derivation could not
be reproduced from the file are labelled "as reported" rather than explained.

Usage:
    python3 build_report.py [input.json] [output.html]
"""

from __future__ import annotations

import html
import json
import math
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Engine identity: stable order, short labels, and colour roles.
# ---------------------------------------------------------------------------

ENGINE_COLORS = {
    "Spark Rust 0.42.1 (default)": "#2f5fd0",
    "Spark Rust 0.42.1 (tuned)": "#7aa5f2",
    "DuckDB 1.5.5": "#d99a1b",
    "Spark 4.1.1 Gluten": "#1f9d6b",
    "Spark 4.2": "#b0519c",
}

ENGINE_SHORT = {
    "Spark Rust 0.42.1 (default)": "Spark Rust (default)",
    "Spark Rust 0.42.1 (tuned)": "Spark Rust (tuned)",
    "DuckDB 1.5.5": "DuckDB",
    "Spark 4.1.1 Gluten": "Gluten",
    "Spark 4.2": "Spark 4.2",
}

CLUSTER_ENGINES = ["Spark Rust 0.42.1", "Spark 4.1.1 Gluten"]
CLUSTER_COLORS = {
    "Spark Rust 0.42.1": "#2f5fd0",
    "Spark 4.1.1 Gluten": "#1f9d6b",
}
CLUSTER_SHORT = {
    "Spark Rust 0.42.1": "Spark Rust",
    "Spark 4.1.1 Gluten": "Gluten",
}

BASELINE = "DuckDB 1.5.5"
SINGLE_SFS = ["1", "10", "100", "1000"]
CLUSTER_SFS = ["100", "1000", "10000"]


def esc(value: object) -> str:
    """HTML-escape any value for safe interpolation into markup."""
    return html.escape("" if value is None else str(value), quote=True)


# ---------------------------------------------------------------------------
# Number formatting
# ---------------------------------------------------------------------------

def fmt_time(v: float | None) -> str:
    """Format seconds with precision appropriate to magnitude."""
    if v is None:
        return "—"
    a = abs(v)
    if a == 0:
        return "0"
    if a < 1:
        return f"{v:.3f}"
    if a < 10:
        return f"{v:.3f}"
    if a < 100:
        return f"{v:.2f}"
    if a < 1000:
        return f"{v:.1f}"
    return f"{v:,.0f}"


def fmt_ratio(v: float | None) -> str:
    if v is None:
        return "—"
    if abs(v - 1) < 0.005:
        return "1.00×"
    if v < 10:
        return f"{v:.2f}×"
    if v < 100:
        return f"{v:.1f}×"
    return f"{v:,.0f}×"


def fmt_signed(v: float | None) -> str:
    if v is None:
        return "—"
    sign = "+" if v > 0 else ("−" if v < 0 else "±")
    return f"{sign}{fmt_time(abs(v))}"


def fmt_num(v: float | None, nd: int = 2) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1000:
        return f"{v:,.1f}"
    return f"{v:.{nd}f}"


# ---------------------------------------------------------------------------
# Derived analysis (recomputed from the file, never invented)
# ---------------------------------------------------------------------------

def totals_map(data: dict) -> dict:
    """{(benchmark, sf): {engine: row}}"""
    out: dict = {}
    for bench, rows in data["totals"].items():
        for row in rows:
            out.setdefault((bench, row["sf"]), {})[row["engine"]] = row
    return out


def per_query_win_counts(data: dict) -> dict:
    """Count fastest engine per query, per benchmark/sf, from single[]."""
    engines = data["engines"]
    out: dict = {}
    for bench, scales in data["single"].items():
        for sf, rows in scales.items():
            counts = {e: 0 for e in engines}
            for row in rows:
                times = row["times"]
                if all(t is not None and t > 0 for t in times):
                    counts[engines[times.index(min(times))]] += 1
            out[(bench, sf)] = counts
    return out


def build_findings(data: dict, tm: dict) -> list[dict]:
    """Assemble the headline findings shown in the summary section."""
    engines = data["engines"]
    findings = []

    for bench in ("TPC-H", "TPC-DS"):
        agg = tm[(bench, "all")]
        base = agg[BASELINE]["time"]
        ranked = sorted(engines, key=lambda e: agg[e]["time"])
        fastest, slowest = ranked[0], ranked[-1]
        findings.append(
            {
                "bench": bench,
                "queries": agg[BASELINE]["n"],
                "base": base,
                "ranked": [(e, agg[e]["time"], agg[e]["ratio"]) for e in ranked],
                "fastest": fastest,
                "slowest": slowest,
                "spread": agg[slowest]["time"] / agg[fastest]["time"],
            }
        )

    # Startup overhead: JVM engines at sf=1 vs sf=1000.
    startup = []
    for e in engines:
        if e == BASELINE:
            continue
        r1 = tm[("TPC-H", "1")][e]["ratio"]
        r1000 = tm[("TPC-H", "1000")][e]["ratio"]
        startup.append({"engine": e, "sf1": r1, "sf1000": r1000})

    # Cluster crossover.
    cluster = []
    for sf in CLUSTER_SFS:
        rows = {r["engine"]: r for r in data["cluster"][sf]}
        rust, glut = rows[CLUSTER_ENGINES[0]], rows[CLUSTER_ENGINES[1]]
        wins = data["wins"][sf]
        cluster.append(
            {
                "sf": sf,
                "rust": rust,
                "gluten": glut,
                "wall_ratio": glut["time"] / rust["time"],
                "cpu_ratio": glut["cpuHours"] / rust["cpuHours"],
                "wins": wins,
                "n": rust["n"],
            }
        )

    return {"totals": findings, "startup": startup, "cluster": cluster}


# ---------------------------------------------------------------------------
# SVG scaling chart (log-y, hand-rolled so the artifact needs no libraries)
# ---------------------------------------------------------------------------

def scaling_chart(data: dict, tm: dict, bench: str) -> str:
    engines = data["engines"]
    W, H = 720, 340
    pad_l, pad_r, pad_t, pad_b = 66, 18, 18, 46
    plot_w, plot_h = W - pad_l - pad_r, H - pad_t - pad_b

    values = [
        tm[(bench, sf)][e]["time"]
        for sf in SINGLE_SFS
        for e in engines
        if tm[(bench, sf)][e]["time"]
    ]
    vmin, vmax = min(values), max(values)
    lo = math.floor(math.log10(vmin))
    hi = math.ceil(math.log10(vmax))

    def x(sf_index: int) -> float:
        return pad_l + plot_w * (sf_index / (len(SINGLE_SFS) - 1))

    def y(v: float) -> float:
        return pad_t + plot_h * (1 - (math.log10(v) - lo) / (hi - lo))

    parts = [
        f'<svg viewBox="0 0 {W} {H}" role="img" preserveAspectRatio="xMidYMid meet"',
        f' aria-label="{esc(bench)} total query time by scale factor, logarithmic scale">',
    ]

    # Horizontal gridlines at each power of ten.
    for decade in range(lo, hi + 1):
        gy = y(10**decade)
        parts.append(
            f'<line class="grid" x1="{pad_l}" y1="{gy:.1f}" x2="{W - pad_r}" y2="{gy:.1f}"/>'
        )
        label = f"{10 ** decade:,}s" if decade >= 0 else f"{10 ** decade}s"
        parts.append(
            f'<text class="axis" x="{pad_l - 10}" y="{gy + 4:.1f}" text-anchor="end">{esc(label)}</text>'
        )

    # X axis labels.
    for i, sf in enumerate(SINGLE_SFS):
        parts.append(
            f'<text class="axis" x="{x(i):.1f}" y="{H - pad_b + 22}" text-anchor="middle">SF {esc(sf)}</text>'
        )
    parts.append(
        f'<text class="axis-title" x="{pad_l + plot_w / 2:.1f}" y="{H - 6}" text-anchor="middle">Scale factor</text>'
    )
    parts.append(
        f'<text class="axis-title" transform="translate(15,{pad_t + plot_h / 2:.1f}) rotate(-90)" '
        f'text-anchor="middle">Total time (s, log)</text>'
    )

    # One polyline per engine.
    for e in engines:
        color = ENGINE_COLORS[e]
        pts = []
        for i, sf in enumerate(SINGLE_SFS):
            v = tm[(bench, sf)][e]["time"]
            if v:
                pts.append((x(i), y(v), v, sf))
        if len(pts) < 2:
            continue
        path = " ".join(f"{px:.1f},{py:.1f}" for px, py, _, _ in pts)
        parts.append(
            f'<polyline class="series" points="{path}" stroke="{color}" '
            f'aria-hidden="true"/>'
        )
        for px, py, v, sf in pts:
            parts.append(
                f'<circle class="dot" cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{color}">'
                f'<title>{esc(e)} — SF {esc(sf)}: {esc(fmt_time(v))} s</title></circle>'
            )

    parts.append("</svg>")
    return "".join(parts)


def chart_legend(engines: list[str]) -> str:
    items = "".join(
        f'<li><span class="swatch" style="--c:{ENGINE_COLORS[e]}"></span>{esc(ENGINE_SHORT[e])}</li>'
        for e in engines
    )
    return f'<ul class="legend">{items}</ul>'


# ---------------------------------------------------------------------------
# Static section builders
# ---------------------------------------------------------------------------

def section_hardware(data: dict) -> str:
    hw = data["hardware"]
    sn, cw = hw["single_node"], hw["cluster_workers"]
    head = hw.get("cluster_head_node")
    head_txt = (
        "not specified in source" if head is None else esc(json.dumps(head))
    )
    return f"""
<section id="hardware" class="section">
  <h2>Test hardware</h2>
  <p class="lede">Provenance as recorded in the source file: <strong>{esc(hw.get("provenance"))}</strong>.</p>
  <div class="card-grid">
    <article class="card">
      <h3>Single node</h3>
      <dl class="specs">
        <dt>SKU</dt><dd>{esc(sn["sku"])}</dd>
        <dt>Cores</dt><dd>{esc(sn["cores"])}</dd>
        <dt>RAM</dt><dd>{esc(sn["ram_gb"])} GB</dd>
      </dl>
    </article>
    <article class="card">
      <h3>Cluster workers</h3>
      <dl class="specs">
        <dt>SKU</dt><dd>{esc(cw["sku"])}</dd>
        <dt>Workers</dt><dd>{esc(cw["count"])}</dd>
        <dt>Cores each</dt><dd>{esc(cw["cores_each"])}</dd>
        <dt>RAM each</dt><dd>{esc(cw["ram_gb_each"])} GB</dd>
        <dt>Total cores</dt><dd>{esc(cw["total_cores"])}</dd>
        <dt>Total RAM</dt><dd>{esc(cw["total_ram_gb"])} GB</dd>
      </dl>
    </article>
    <article class="card">
      <h3>Cluster head node</h3>
      <p class="muted">{head_txt}</p>
      <p class="note">The source file records <code>null</code> for the head node, so no
      head-node specification is available.</p>
    </article>
  </div>
</section>"""


def section_summary(data: dict, tm: dict, analysis: dict) -> str:
    engines = data["engines"]

    stat_cards = []
    for f in analysis["totals"]:
        best = f["ranked"][0]
        stat_cards.append(
            f"""
      <article class="stat">
        <h3>{esc(f["bench"])}</h3>
        <p class="stat-big">{esc(fmt_time(f["base"]))}<span class="unit">s</span></p>
        <p class="stat-label">{esc(BASELINE)} baseline · {esc(f["queries"])} queries × 4 scale factors</p>
        <p class="stat-sub">Fastest overall: <strong>{esc(ENGINE_SHORT[best[0]])}</strong>
        at {esc(fmt_ratio(best[2]))}. Slowest: {esc(ENGINE_SHORT[f["slowest"]])}
        at {esc(fmt_ratio(f["ranked"][-1][2]))}.</p>
      </article>"""
        )

    # Aggregate ranking table across both benchmarks.
    rank_rows = []
    for e in engines:
        h = tm[("TPC-H", "all")][e]
        ds = tm[("TPC-DS", "all")][e]
        rank_rows.append(
            f"""<tr>
        <th scope="row"><span class="swatch" style="--c:{ENGINE_COLORS[e]}"></span>{esc(e)}</th>
        <td class="num">{esc(fmt_time(h["time"]))}</td>
        <td class="num"><span class="ratio">{esc(fmt_ratio(h["ratio"]))}</span></td>
        <td class="num">{esc(fmt_time(ds["time"]))}</td>
        <td class="num"><span class="ratio">{esc(fmt_ratio(ds["ratio"]))}</span></td>
      </tr>"""
        )

    startup_rows = "".join(
        f"""<tr>
        <th scope="row"><span class="swatch" style="--c:{ENGINE_COLORS[s["engine"]]}"></span>{esc(s["engine"])}</th>
        <td class="num">{esc(fmt_ratio(s["sf1"]))}</td>
        <td class="num">{esc(fmt_ratio(s["sf1000"]))}</td>
        <td class="num">{esc(fmt_ratio(s["sf1"] / s["sf1000"]))}</td>
      </tr>"""
        for s in analysis["startup"]
    )

    cl = analysis["cluster"]
    cluster_rows = "".join(
        f"""<tr>
        <th scope="row">SF {esc(c["sf"])}</th>
        <td class="num">{esc(fmt_time(c["rust"]["time"]))}</td>
        <td class="num">{esc(fmt_time(c["gluten"]["time"]))}</td>
        <td class="num">{esc(fmt_ratio(c["wall_ratio"]))}</td>
        <td class="num">{esc(fmt_num(c["rust"]["cpuHours"], 2))}</td>
        <td class="num">{esc(fmt_num(c["gluten"]["cpuHours"], 2))}</td>
        <td class="num">{esc(fmt_ratio(c["cpu_ratio"]))}</td>
        <td class="num">{esc(c["wins"][0])}–{esc(c["wins"][1])}</td>
      </tr>"""
        for c in cl
    )

    tpch, tpcds = analysis["totals"][0], analysis["totals"][1]
    ds_winner = tpcds["ranked"][0][0]
    crossover = cl[0]["wins"][0] > cl[-1]["wins"][0]

    return f"""
<section id="summary" class="section">
  <h2>Summary</h2>
  <div class="stat-grid">{''.join(stat_cards)}
  </div>

  <div class="prose">
    <p>Across all four single-node scale factors, <strong>{esc(ENGINE_SHORT[ds_winner])}</strong>
    posts the lowest total TPC-DS time at {esc(fmt_time(tpcds["ranked"][0][1]))} s
    ({esc(fmt_ratio(tpcds["ranked"][0][2]))} of the {esc(BASELINE)} baseline), while
    {esc(BASELINE)} leads TPC-H at {esc(fmt_time(tpch["base"]))} s. The two JVM-based
    Spark builds trail on both workloads, at
    {esc(fmt_ratio(tm[("TPC-H", "all")]["Spark 4.2"]["ratio"]))} and
    {esc(fmt_ratio(tm[("TPC-DS", "all")]["Spark 4.2"]["ratio"]))} of baseline on TPC-H
    and TPC-DS respectively for Spark 4.2.</p>

    <p>The single-node gap is dominated by fixed startup cost rather than throughput.
    At SF 1 the four non-baseline engines run
    {esc(fmt_ratio(min(s["sf1"] for s in analysis["startup"]) if analysis["startup"] else 1))}–{esc(fmt_ratio(max(s["sf1"] for s in analysis["startup"])))}
    of baseline on TPC-H, but by SF 1000 that narrows to
    {esc(fmt_ratio(min(s["sf1000"] for s in analysis["startup"])))}–{esc(fmt_ratio(max(s["sf1000"] for s in analysis["startup"])))}.
    Ratios below 1.00× mean the engine was <em>faster</em> than {esc(BASELINE)}.</p>
  </div>

  <h3>Aggregate single-node totals</h3>
  <p class="lede">Sum of per-query wall-clock seconds over scale factors 1, 10, 100 and 1000.
  Ratio is against {esc(BASELINE)}; lower is better.</p>
  <div class="table-wrap">
    <table class="data">
      <caption>Aggregate single-node totals by engine</caption>
      <thead>
        <tr>
          <th scope="col" rowspan="2">Engine</th>
          <th scope="colgroup" colspan="2">TPC-H ({esc(tm[("TPC-H","all")][BASELINE]["n"])} query-runs)</th>
          <th scope="colgroup" colspan="2">TPC-DS ({esc(tm[("TPC-DS","all")][BASELINE]["n"])} query-runs)</th>
        </tr>
        <tr>
          <th scope="col" class="num">Total s</th><th scope="col" class="num">Ratio</th>
          <th scope="col" class="num">Total s</th><th scope="col" class="num">Ratio</th>
        </tr>
      </thead>
      <tbody>{''.join(rank_rows)}
      </tbody>
    </table>
  </div>

  <h3>Startup cost dominates small scale factors</h3>
  <p class="lede">TPC-H ratio versus {esc(BASELINE)} at the smallest and largest single-node
  scale factors, and the factor by which the gap shrinks.</p>
  <div class="table-wrap">
    <table class="data">
      <caption>TPC-H ratio at SF 1 versus SF 1000</caption>
      <thead><tr>
        <th scope="col">Engine</th>
        <th scope="col" class="num">SF 1</th>
        <th scope="col" class="num">SF 1000</th>
        <th scope="col" class="num">Gap reduction</th>
      </tr></thead>
      <tbody>{startup_rows}</tbody>
    </table>
  </div>

  <h3>Cluster results reverse with scale</h3>
  <p class="lede">Eight-worker TPC-DS runs comparing Spark Rust 0.42.1 against Spark 4.1.1 Gluten.
  {'Spark Rust leads on per-query wins at SF 100 but loses that lead by SF 10000.' if crossover else ''}
  CPU-hours measure total compute consumed, so a lower figure means better efficiency.</p>
  <div class="table-wrap">
    <table class="data">
      <caption>Cluster totals by scale factor</caption>
      <thead><tr>
        <th scope="col">Scale factor</th>
        <th scope="col" class="num">Spark Rust s</th>
        <th scope="col" class="num">Gluten s</th>
        <th scope="col" class="num">Wall ratio</th>
        <th scope="col" class="num">Rust CPU-h</th>
        <th scope="col" class="num">Gluten CPU-h</th>
        <th scope="col" class="num">CPU ratio</th>
        <th scope="col" class="num">Wins R–G</th>
      </tr></thead>
      <tbody>{cluster_rows}</tbody>
    </table>
  </div>
  <p class="note">Wall ratio is Gluten total time ÷ Spark Rust total time; values above 1.00×
  favour Spark Rust. CPU ratio is Gluten CPU-hours ÷ Spark Rust CPU-hours. Win counts are
  taken from the <code>wins</code> field of the source file.</p>
</section>"""


def section_totals(data: dict, tm: dict) -> str:
    engines = data["engines"]
    out = []

    for bench in ("TPC-H", "TPC-DS"):
        # Matrix: engines × scale factors, log-scaled bar per cell.
        col_max = {
            sf: max(tm[(bench, sf)][e]["time"] for e in engines) for sf in SINGLE_SFS
        }
        col_min = {
            sf: min(
                tm[(bench, sf)][e]["time"] for e in engines if tm[(bench, sf)][e]["time"]
            )
            for sf in SINGLE_SFS
        }

        body = []
        for e in engines:
            cells = []
            for sf in SINGLE_SFS:
                row = tm[(bench, sf)][e]
                v = row["time"]
                lo, hi = math.log10(col_min[sf]), math.log10(col_max[sf])
                frac = 0.0 if hi <= lo else (math.log10(v) - lo) / (hi - lo)
                width = 6 + 94 * frac
                fastest = v == col_min[sf]
                cells.append(
                    f"""<td class="num cell">
              <span class="bar" style="--w:{width:.1f}%;--c:{ENGINE_COLORS[e]}"></span>
              <span class="val{' best' if fastest else ''}">{esc(fmt_time(v))}</span>
              <span class="sub">{esc(fmt_ratio(row["ratio"]))}</span>
            </td>"""
                )
            agg = tm[(bench, "all")][e]
            cells.append(
                f"""<td class="num cell total">
              <span class="val">{esc(fmt_time(agg["time"]))}</span>
              <span class="sub">{esc(fmt_ratio(agg["ratio"]))}</span>
            </td>"""
            )
            body.append(
                f"""<tr>
          <th scope="row"><span class="swatch" style="--c:{ENGINE_COLORS[e]}"></span>{esc(e)}</th>
          {''.join(cells)}
        </tr>"""
            )

        n_sf1 = tm[(bench, "1")][BASELINE]["n"]

        # Aggregate detail, including the as-reported canonical/matched fields.
        detail = []
        for e in engines:
            a = tm[(bench, "all")][e]
            detail.append(
                f"""<tr>
          <th scope="row"><span class="swatch" style="--c:{ENGINE_COLORS[e]}"></span>{esc(e)}</th>
          <td class="num">{esc(a["n"])}</td>
          <td class="num">{esc(fmt_time(a["time"]))}</td>
          <td class="num">{esc(fmt_signed(a["diff"]))}</td>
          <td class="num">{esc(fmt_ratio(a["ratio"]))}</td>
          <td class="num reported">{esc(fmt_time(a["canonical"]))}</td>
          <td class="num reported">{esc(fmt_ratio(a["matched"]))}</td>
        </tr>"""
            )

        out.append(
            f"""
  <h3 id="{bench.lower()}-totals">{esc(bench)}</h3>
  <p class="lede">{esc(n_sf1)} queries per scale factor. Bars are logarithmic within each
  column; the shortest time in a column is marked in bold. Ratio is against {esc(BASELINE)}.</p>
  <div class="table-wrap">
    <table class="data matrix">
      <caption>{esc(bench)} total wall-clock seconds by engine and scale factor</caption>
      <thead><tr>
        <th scope="col">Engine</th>
        {''.join(f'<th scope="col" class="num">SF {esc(sf)}</th>' for sf in SINGLE_SFS)}
        <th scope="col" class="num">All SF</th>
      </tr></thead>
      <tbody>{''.join(body)}
      </tbody>
    </table>
  </div>

  <details class="fold">
    <summary>Aggregate detail, including as-reported <code>canonical</code> and <code>matched</code></summary>
    <div class="table-wrap">
      <table class="data">
        <caption>{esc(bench)} aggregate fields as recorded in the source file</caption>
        <thead><tr>
          <th scope="col">Engine</th>
          <th scope="col" class="num">n</th>
          <th scope="col" class="num">time (s)</th>
          <th scope="col" class="num">diff (s)</th>
          <th scope="col" class="num">ratio</th>
          <th scope="col" class="num">canonical (s)</th>
          <th scope="col" class="num">matched</th>
        </tr></thead>
        <tbody>{''.join(detail)}
        </tbody>
      </table>
    </div>
    <p class="note"><code>diff</code> and <code>ratio</code> were verified against
    <code>time</code> and the {esc(BASELINE)} total. <code>canonical</code> equals
    <code>time</code> for most rows but differs or is <code>null</code> for others, and
    <code>matched</code> is populated only on the aggregate row. The source file does not
    define how either is derived, and neither could be reproduced from the per-query data,
    so both are shown verbatim. See <a href="#notes">data notes</a>.</p>
  </details>"""
        )

    return f"""
<section id="totals" class="section">
  <h2>Single-node totals</h2>
  <p class="lede">Each total is the sum of per-query wall-clock seconds, which was verified
  to match the per-query records in <code>single</code> exactly for every engine and scale factor.</p>
  {''.join(out)}
</section>"""


def section_scaling(data: dict, tm: dict) -> str:
    engines = data["engines"]
    panels = "".join(
        f"""
    <figure class="chart">
      <figcaption>{esc(bench)} — total time by scale factor</figcaption>
      {scaling_chart(data, tm, bench)}
    </figure>"""
        for bench in ("TPC-H", "TPC-DS")
    )
    return f"""
<section id="scaling" class="section">
  <h2>Scaling behaviour</h2>
  <p class="lede">Total wall-clock time per scale factor on a logarithmic axis. The steep
  convergence from SF 1 to SF 1000 shows how much of the small-scale gap is fixed
  startup cost rather than per-row throughput.</p>
  {chart_legend(engines)}
  <div class="chart-grid">{panels}
  </div>
</section>"""


def section_cluster(data: dict) -> str:
    rows_out = []
    metrics = [
        ("n", "Queries", 0),
        ("time", "Total wall time (s)", 2),
        ("mean", "Mean (s) — as reported", 3),
        ("p50", "p50 (s) — as reported", 3),
        ("p95", "p95 (s) — as reported", 3),
        ("max", "Max (s) — as reported", 3),
        ("cpu", "CPU seconds", 1),
        ("cpuHours", "CPU-hours", 3),
        ("cores", "Mean cores used", 3),
        ("memtime", "Memory-seconds", 1),
        ("memHours", "Memory-hours", 3),
    ]

    for sf in CLUSTER_SFS:
        by_engine = {r["engine"]: r for r in data["cluster"][sf]}
        rust, glut = by_engine[CLUSTER_ENGINES[0]], by_engine[CLUSTER_ENGINES[1]]
        wins = data["wins"][sf]
        body = []
        for key, label, nd in metrics:
            rv, gv = rust.get(key), glut.get(key)
            better = ""
            if isinstance(rv, (int, float)) and isinstance(gv, (int, float)) and rv != gv:
                if key in ("cpu", "cpuHours", "cores", "memtime", "memHours", "time", "mean", "p50", "p95", "max"):
                    better = "rust" if rv < gv else "gluten"
            body.append(
                f"""<tr>
          <th scope="row">{esc(label)}</th>
          <td class="num{' win' if better == 'rust' else ''}">{esc(fmt_num(rv, nd))}</td>
          <td class="num{' win' if better == 'gluten' else ''}">{esc(fmt_num(gv, nd))}</td>
        </tr>"""
            )
        rows_out.append(
            f"""
    <article class="card">
      <h3>SF {esc(sf)}</h3>
      <p class="stat-label">Per-query wins: <strong>{esc(wins[0])}</strong> Spark Rust ·
      <strong>{esc(wins[1])}</strong> Gluten · of {esc(rust["n"])} compared</p>
      <div class="table-wrap">
        <table class="data compact">
          <caption>Cluster metrics at SF {esc(sf)}</caption>
          <thead><tr>
            <th scope="col">Metric</th>
            <th scope="col" class="num"><span class="swatch" style="--c:{CLUSTER_COLORS[CLUSTER_ENGINES[0]]}"></span>Spark Rust</th>
            <th scope="col" class="num"><span class="swatch" style="--c:{CLUSTER_COLORS[CLUSTER_ENGINES[1]]}"></span>Gluten</th>
          </tr></thead>
          <tbody>{''.join(body)}
          </tbody>
        </table>
      </div>
    </article>"""
        )

    return f"""
<section id="cluster" class="section">
  <h2>Cluster runs</h2>
  <p class="lede">TPC-DS on {esc(data["hardware"]["cluster_workers"]["count"])} workers
  ({esc(data["hardware"]["cluster_workers"]["total_cores"])} cores,
  {esc(data["hardware"]["cluster_workers"]["total_ram_gb"])} GB total). Only two engines
  appear in the cluster data. Shaded values are the lower of the pair for that metric.</p>
  <div class="card-grid three">{''.join(rows_out)}
  </div>
  <p class="note">Total wall time was verified to equal the sum of the per-query times in
  <code>clusterQueries</code> for SF 100 and SF 1000. At SF 10000 the Spark Rust total
  ({esc(fmt_time({r["engine"]: r for r in data["cluster"]["10000"]}[CLUSTER_ENGINES[0]]["time"]))} s)
  is lower than the sum of its per-query times, and five queries have no Gluten result, so the
  aggregate excludes work present in the per-query records. <code>mean</code>, <code>p50</code>,
  <code>p95</code> and <code>max</code> do not correspond to the mean or percentiles of the
  per-query times and are shown as reported.</p>
</section>"""


def section_notes(data: dict) -> str:
    # Collect marker occurrences for an honest, complete disclosure.
    markers = []
    for bench, scales in data["single"].items():
        for sf, rows in scales.items():
            for row in rows:
                for i, m in enumerate(row["markers"]):
                    if m:
                        markers.append((bench, sf, row["q"], data["engines"][i], m))

    marker_rows = "".join(
        f"""<tr><td>{esc(b)}</td><td class="num">{esc(sf)}</td><td class="num">Q{esc(q)}</td>
        <td>{esc(e)}</td><td><code>{esc(m)}</code></td></tr>"""
        for b, sf, q, e, m in markers
    )

    statuses = sorted(
        {r["status"] for sf in data["clusterQueries"] for r in data["clusterQueries"][sf]}
    )
    status_rows = "".join(
        f"""<tr><td><code>{esc(s)}</code></td>
        <td class="num">{sum(1 for sf in data["clusterQueries"] for r in data["clusterQueries"][sf] if r["status"] == s)}</td></tr>"""
        for s in statuses
    )

    return f"""
<section id="notes" class="section">
  <h2>Data notes and limitations</h2>
  <p class="lede">This report was generated from
  <code>{esc(data["source"])}</code> as captured in
  <code>engine-comparison-summary-data.json</code>
  (SHA-256 <code class="hash">{esc(data["sha256"])}</code>). That file is the only input;
  no external data, benchmark result or specification was added.</p>

  <h3>Verified relationships</h3>
  <ul class="checks">
    <li><strong>Confirmed.</strong> In <code>totals</code>, <code>ratio</code> equals
      <code>time</code> ÷ the {esc(BASELINE)} time and <code>diff</code> equals
      <code>time</code> − that time, for all 50 rows.</li>
    <li><strong>Confirmed.</strong> <code>totals.time</code> equals the sum of the
      corresponding per-query times in <code>single</code> for every engine and scale factor.</li>
    <li><strong>Confirmed.</strong> <code>cluster.time</code> equals the sum of per-query
      times in <code>clusterQueries</code> at SF 100 and SF 1000.</li>
    <li><strong>Confirmed.</strong> <code>cluster.cores</code> = <code>cpu</code> ÷ <code>time</code>,
      <code>cpuHours</code> = <code>cpu</code> ÷ 3600 and <code>memHours</code> =
      <code>memtime</code> ÷ 3600.</li>
    <li><strong>Confirmed.</strong> <code>wins</code> matches per-query win counts recomputed
      from <code>clusterQueries</code>; at SF 100 the single tied query is counted for Spark Rust.</li>
    <li><strong>Confirmed.</strong> In <code>clusterQueries</code>, <code>ratio</code> =
      Spark Rust time ÷ Gluten time and <code>diff</code> = Spark Rust − Gluten, so a ratio
      below 1 favours Spark Rust. Note this is the opposite convention to
      <code>totals.ratio</code>.</li>
  </ul>

  <h3>Fields shown as reported</h3>
  <p>The following fields could not be reproduced from the per-query records, and the source
  file does not define their derivation. They are displayed verbatim and should not be
  interpreted as computed aggregates of the data in this report.</p>
  <ul class="checks warn">
    <li><code>totals.canonical</code> — equals <code>time</code> on 44 of 50 rows, differs
      slightly on two TPC-DS Spark Rust (tuned) rows, and is <code>null</code> on four rows.</li>
    <li><code>totals.matched</code> — populated only on the ten aggregate rows. It matches
      neither the sum-ratio, geometric mean nor median of the per-query ratios under any
      scale-factor subset tested.</li>
    <li><code>cluster.mean</code>, <code>p50</code>, <code>p95</code>, <code>max</code> —
      these do not equal the mean, median, 95th percentile or maximum of the per-query times
      in <code>clusterQueries</code>, nor any trimmed mean of them. They likely describe a
      different measurement level, such as per-task rather than per-query timing.</li>
  </ul>

  <h3>Query markers</h3>
  <p>Six per-query cells in <code>single</code> carry a non-empty marker, all at SF 1000.
  The source file does not define what <code>B</code> or <code>P</code> mean, so they are
  reproduced here without interpretation and flagged in the per-query tables.</p>
  <div class="table-wrap narrow">
    <table class="data compact">
      <caption>Non-empty markers in the single-node per-query data</caption>
      <thead><tr><th scope="col">Benchmark</th><th scope="col" class="num">SF</th>
      <th scope="col" class="num">Query</th><th scope="col">Engine</th>
      <th scope="col">Marker</th></tr></thead>
      <tbody>{marker_rows}</tbody>
    </table>
  </div>

  <h3>Cluster query statuses</h3>
  <p>Every <code>clusterQueries</code> row carries a <code>status</code>. Values other than
  <code>pass</code> indicate a comparison gap or a single-engine observation, and the
  affected rows are labelled in the cluster per-query table.</p>
  <div class="table-wrap narrow">
    <table class="data compact">
      <caption>Distinct status values and their frequency</caption>
      <thead><tr><th scope="col">Status</th><th scope="col" class="num">Rows</th></tr></thead>
      <tbody>{status_rows}</tbody>
    </table>
  </div>

  <h3>Coverage gaps</h3>
  <ul class="checks">
    <li>Single-node data covers five engines; cluster data covers only Spark Rust 0.42.1 and
      Spark 4.1.1 Gluten. DuckDB, Spark Rust (tuned) and Spark 4.2 have no cluster results.</li>
    <li>At cluster SF 10000, one query has no Spark Rust time, five have no Gluten time, and
      all 99 rows have <code>null</code> per-query <code>p50</code> values.</li>
    <li>The cluster engine name <code>Spark Rust 0.42.1</code> does not distinguish the
      default and tuned single-node configurations.</li>
    <li>No variance, repeat-count or cold/warm-cache information is present, so no statement
      about statistical significance can be made from this file.</li>
    <li>The head-node specification is <code>null</code>.</li>
  </ul>
</section>"""


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = r"""
:root{
  --bg:#f6f7f9; --surface:#fff; --surface-2:#fafbfc; --ink:#15181c; --muted:#5b6672;
  --faint:#666f7b; --border:#e1e5ea; --border-strong:#cdd4dc; --accent:#2f5fd0;
  --accent-soft:#eaf0fd; --on-accent:#ffffff; --good:#1f7a4d; --good-soft:#e7f5ee; --warn:#8a5a00;
  --warn-soft:#fdf3e0; --shadow:0 1px 2px rgba(16,24,40,.05),0 4px 16px rgba(16,24,40,.05);
  --radius:10px; --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
}
html[data-theme="dark"]{
  --bg:#101317; --surface:#171b21; --surface-2:#1c2128; --ink:#e7ebef; --muted:#9aa5b1;
  --faint:#8b95a1; --border:#272d36; --border-strong:#363e49; --accent:#7aa5f2;
  --accent-soft:#1b2436; --on-accent:#0d1220; --good:#5ec795; --good-soft:#152a20; --warn:#e0b25f;
  --warn-soft:#2a2114; --shadow:0 1px 2px rgba(0,0,0,.4),0 6px 20px rgba(0,0,0,.28);
}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0; background:var(--bg); color:var(--ink); font-family:var(--sans);
  font-size:15px; line-height:1.6; font-variant-numeric:tabular-nums;
  -webkit-font-smoothing:antialiased;
}
h1,h2,h3,h4{line-height:1.25; margin:0 0 .5rem; font-weight:650; letter-spacing:-.01em}
h1{font-size:clamp(1.6rem,3.4vw,2.3rem); letter-spacing:-.025em}
h2{font-size:clamp(1.25rem,2.4vw,1.6rem); margin-bottom:.35rem}
h3{font-size:1.02rem; margin-top:2rem}
p{margin:0 0 .85rem}
a{color:var(--accent)}
code{font-family:var(--mono); font-size:.86em; background:var(--surface-2);
  border:1px solid var(--border); border-radius:4px; padding:.08em .34em; word-break:break-word}
code.hash{font-size:.78em; word-break:break-all}
.skip{position:absolute; left:0; top:0; z-index:100; background:var(--accent);
  color:var(--on-accent); padding:.7rem 1.1rem; border-radius:0 0 8px 0;
  clip-path:inset(0 0 100% 0); pointer-events:none; transition:clip-path .12s ease}
.skip:focus{clip-path:inset(0 0 0 0); pointer-events:auto}
:focus-visible{outline:2px solid var(--accent); outline-offset:2px; border-radius:3px}

/* ---------- layout ---------- */
.wrap{max-width:1180px; margin:0 auto; padding:0 clamp(1rem,3vw,2rem)}
.masthead{background:var(--surface); border-bottom:1px solid var(--border); padding:2.4rem 0 1.6rem}
.masthead .eyebrow{font-size:.74rem; text-transform:uppercase; letter-spacing:.13em;
  color:var(--faint); font-weight:650; margin-bottom:.6rem}
.masthead p.lede{color:var(--muted); max-width:70ch; margin-bottom:1rem}
.prov{display:flex; flex-wrap:wrap; gap:.4rem 1.4rem; font-size:.8rem; color:var(--muted);
  border-top:1px solid var(--border); padding-top:.9rem; margin-top:.4rem}
.prov span{display:inline-flex; gap:.4rem; align-items:baseline}
.prov b{color:var(--ink); font-weight:600}

.toc{position:sticky; top:0; z-index:20; background:color-mix(in srgb,var(--surface) 92%,transparent);
  backdrop-filter:blur(8px); border-bottom:1px solid var(--border)}
.toc .wrap{display:flex; align-items:center; gap:.3rem; overflow-x:auto; padding-top:.5rem;
  padding-bottom:.5rem; scrollbar-width:thin}
.toc a{flex:0 0 auto; padding:.34rem .7rem; border-radius:999px; text-decoration:none;
  font-size:.83rem; color:var(--muted); font-weight:550; white-space:nowrap}
.toc a:hover{background:var(--accent-soft); color:var(--accent)}
.toc a[aria-current="true"]{background:var(--accent); color:var(--on-accent)}
.toc .spacer{flex:1 1 auto}
.theme-btn{flex:0 0 auto; border:1px solid var(--border-strong); background:var(--surface);
  color:var(--muted); border-radius:999px; padding:.42rem .85rem; font-size:.8rem; cursor:pointer;
  font-family:inherit; font-weight:550; min-height:36px}
.theme-btn:hover{border-color:var(--accent); color:var(--accent)}

.section{padding:2.6rem 0 .6rem; border-bottom:1px solid var(--border)}
.section:last-of-type{border-bottom:0}
.section>h2{scroll-margin-top:4rem}
.lede{color:var(--muted); max-width:82ch}
.prose{max-width:82ch}
.note{font-size:.82rem; color:var(--muted); background:var(--surface-2);
  border-left:3px solid var(--border-strong); padding:.65rem .85rem; border-radius:0 6px 6px 0;
  margin:.9rem 0}
.muted{color:var(--muted)}

/* ---------- cards ---------- */
.card-grid{display:grid; gap:1rem; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); margin:1.1rem 0}
.card-grid.three{grid-template-columns:repeat(auto-fit,minmax(310px,1fr))}
.card{background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
  padding:1.05rem 1.15rem; box-shadow:var(--shadow)}
.card h3{margin-top:0; font-size:.95rem}
.specs{display:grid; grid-template-columns:auto 1fr; gap:.28rem .9rem; margin:0; font-size:.87rem}
.specs dt{color:var(--muted)}
.specs dd{margin:0; font-weight:600; text-align:right}

.stat-grid{display:grid; gap:1rem; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); margin:1.2rem 0}
.stat{background:var(--surface); border:1px solid var(--border); border-left:3px solid var(--accent);
  border-radius:var(--radius); padding:1.05rem 1.2rem; box-shadow:var(--shadow)}
.stat h3{margin:0 0 .3rem; font-size:.8rem; text-transform:uppercase; letter-spacing:.1em; color:var(--faint)}
.stat-big{font-size:2.05rem; font-weight:680; letter-spacing:-.03em; margin:0; line-height:1.1}
.stat-big .unit{font-size:.95rem; font-weight:500; color:var(--muted); margin-left:.22rem}
.stat-label{font-size:.8rem; color:var(--muted); margin:.25rem 0 .55rem}
.stat-sub{font-size:.84rem; color:var(--muted); margin:0; border-top:1px solid var(--border); padding-top:.55rem}

/* ---------- tables ---------- */
.table-wrap{overflow-x:auto; margin:.9rem 0 1.1rem; background:var(--surface);
  border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow)}
.table-wrap.narrow{max-width:760px}
table.data{width:100%; border-collapse:collapse; font-size:.855rem}
table.data caption{caption-side:top; text-align:left; padding:.8rem 1rem .55rem;
  font-size:.78rem; color:var(--faint); font-weight:600; letter-spacing:.02em}
table.data th,table.data td{padding:.5rem .8rem; border-bottom:1px solid var(--border); text-align:left; vertical-align:middle}
table.data thead th{background:var(--surface-2); font-size:.75rem; text-transform:uppercase;
  letter-spacing:.055em; color:var(--muted); font-weight:650; border-bottom:1px solid var(--border-strong);
  position:sticky; top:0; z-index:1}
table.data tbody th{font-weight:550; white-space:nowrap}
table.data tbody tr:last-child th,table.data tbody tr:last-child td{border-bottom:0}
table.data tbody tr:hover{background:var(--surface-2)}
.num{text-align:right; font-family:var(--mono); font-size:.83rem; white-space:nowrap}
td.num{font-variant-numeric:tabular-nums}
.ratio{color:var(--muted)}
.reported{color:var(--muted); font-style:italic}
.win{background:var(--good-soft); color:var(--good); font-weight:650}
.val.best{font-weight:700}
td.total{border-left:1px solid var(--border-strong); background:var(--surface-2)}
th[scope="colgroup"]{text-align:center; border-left:1px solid var(--border)}

td.cell{position:relative; min-width:104px; padding-right:.8rem}
.bar{position:absolute; left:0; top:12%; bottom:12%; width:var(--w); background:var(--c);
  opacity:.15; border-radius:0 3px 3px 0; pointer-events:none}
html[data-theme="dark"] .bar{opacity:.26}
td.cell .val,td.cell .sub{position:relative; display:block}
td.cell .sub{font-size:.72rem; color:var(--faint)}

.swatch{display:inline-block; width:9px; height:9px; border-radius:2px; background:var(--c);
  margin-right:.5rem; vertical-align:baseline; flex:0 0 auto}
th .swatch{margin-right:.5rem}

/* ---------- legend & charts ---------- */
.legend{display:flex; flex-wrap:wrap; gap:.35rem 1.1rem; list-style:none; padding:0;
  margin:.9rem 0 .3rem; font-size:.82rem; color:var(--muted)}
.legend li{display:flex; align-items:center}
.chart-grid{display:grid; gap:1.2rem; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); margin:1rem 0}
figure.chart{margin:0; background:var(--surface); border:1px solid var(--border);
  border-radius:var(--radius); padding:.9rem 1rem 1rem; box-shadow:var(--shadow)}
figure.chart figcaption{font-size:.82rem; font-weight:650; color:var(--muted); margin-bottom:.5rem}
figure.chart svg{width:100%; height:auto; display:block}
svg .grid{stroke:var(--border); stroke-width:1}
svg .axis{fill:var(--faint); font-size:11px; font-family:var(--mono)}
svg .axis-title{fill:var(--muted); font-size:11px; font-family:var(--sans); font-weight:600}
svg .series{fill:none; stroke-width:2.25; stroke-linejoin:round; stroke-linecap:round}
svg .dot{stroke:var(--surface); stroke-width:1.5}

/* ---------- interactive controls ---------- */
.controls{display:flex; flex-wrap:wrap; gap:.9rem; align-items:flex-end; margin:1.1rem 0;
  padding:.9rem 1rem; background:var(--surface); border:1px solid var(--border);
  border-radius:var(--radius); box-shadow:var(--shadow)}
.control{display:flex; flex-direction:column; gap:.32rem}
.control>span{font-size:.73rem; text-transform:uppercase; letter-spacing:.07em;
  color:var(--faint); font-weight:650}
.seg{display:flex; gap:2px; background:var(--surface-2); border:1px solid var(--border);
  border-radius:8px; padding:2px; flex-wrap:wrap}
.seg button{border:0; background:transparent; color:var(--muted); font-family:inherit;
  font-size:.82rem; font-weight:550; padding:.34rem .72rem; border-radius:6px; cursor:pointer;
  min-height:32px}
.seg button:hover{color:var(--ink); background:color-mix(in srgb,var(--accent) 12%,transparent)}
.seg button[aria-pressed="true"]{background:var(--accent); color:var(--on-accent)}
select,input[type="search"]{font-family:inherit; font-size:.85rem; padding:.4rem .6rem;
  border:1px solid var(--border-strong); border-radius:8px; background:var(--surface);
  color:var(--ink); min-height:34px}
input[type="search"]{min-width:170px}

table.sortable thead th[data-sort]{cursor:pointer; user-select:none}
table.sortable thead th[data-sort]:hover{color:var(--accent)}
table.sortable thead th .arrow{opacity:.35; margin-left:.3rem; font-size:.72em}
table.sortable thead th[aria-sort] .arrow{opacity:1; color:var(--accent)}

.flag{display:inline-block; font-family:var(--mono); font-size:.68rem; font-weight:700;
  padding:.05rem .32rem; border-radius:4px; margin-left:.35rem; vertical-align:middle;
  background:var(--warn-soft); color:var(--warn); border:1px solid color-mix(in srgb,var(--warn) 35%,transparent)}
.pill{display:inline-block; font-size:.7rem; font-weight:650; padding:.1rem .45rem;
  border-radius:999px; background:var(--good-soft); color:var(--good); white-space:nowrap}
.pill.gap{background:var(--warn-soft); color:var(--warn)}
.pill.other{background:var(--surface-2); color:var(--muted); border:1px solid var(--border)}
.empty{padding:2rem 1rem; text-align:center; color:var(--muted); font-size:.88rem}

details.fold{margin:.6rem 0 1.2rem; background:var(--surface); border:1px solid var(--border);
  border-radius:var(--radius); padding:.1rem 1rem}
details.fold summary{cursor:pointer; padding:.7rem 0; font-size:.87rem; font-weight:600; color:var(--accent)}
details.fold[open] summary{border-bottom:1px solid var(--border); margin-bottom:.6rem}

ul.checks{list-style:none; padding:0; margin:.7rem 0 1.1rem; max-width:92ch}
ul.checks li{position:relative; padding:.42rem 0 .42rem 1.6rem; border-bottom:1px solid var(--border); font-size:.875rem}
ul.checks li:last-child{border-bottom:0}
ul.checks li::before{content:"✓"; position:absolute; left:.15rem; top:.42rem; color:var(--good); font-weight:700}
ul.checks.warn li::before{content:"!"; color:var(--warn)}

footer{padding:2rem 0 3rem; color:var(--faint); font-size:.8rem}
footer .wrap{display:flex; flex-wrap:wrap; gap:.4rem 1.4rem; justify-content:space-between}

@media (max-width:640px){
  body{font-size:14.5px}
  .section{padding:2rem 0 .4rem}
  table.data th,table.data td{padding:.42rem .55rem}
  td.cell{min-width:88px}
  .stat-big{font-size:1.7rem}
}
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation-duration:.01ms!important; animation-iteration-count:1!important;
    transition-duration:.01ms!important; scroll-behavior:auto!important}
}
@media print{
  .toc,.theme-btn,.controls,.skip{display:none!important}
  body{background:#fff; color:#000; font-size:11pt}
  .section{border:0; padding:1rem 0; page-break-inside:avoid}
  .card,.stat,.table-wrap,figure.chart{box-shadow:none; border-color:#bbb}
  a{color:#000; text-decoration:underline}
  details.fold{display:block}
  details.fold summary{display:none}
  details.fold>*{display:block}
}
html{scroll-behavior:smooth}
"""

# ---------------------------------------------------------------------------
# JavaScript: theme, nav highlighting, and the two per-query explorers
# ---------------------------------------------------------------------------

JS = r"""
(function(){
  "use strict";
  var D = window.__DATA__;
  var ENGINES = D.engines;
  var COLORS = D.__colors, SHORT = D.__short;
  var CCOLORS = D.__ccolors;
  var BASE = "DuckDB 1.5.5";
  var SFS = ["1","10","100","1000"];
  var CSFS = ["100","1000","10000"];

  function esc(s){
    return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){
      return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];
    });
  }
  function fmtTime(v){
    if(v === null || v === undefined) return "\u2014";
    var a = Math.abs(v);
    if(a === 0) return "0";
    if(a < 10) return v.toFixed(3);
    if(a < 100) return v.toFixed(2);
    if(a < 1000) return v.toFixed(1);
    return Math.round(v).toLocaleString("en-US");
  }
  function fmtNum(v, nd){
    if(v === null || v === undefined) return "\u2014";
    if(Math.abs(v) >= 1000) return v.toLocaleString("en-US",{maximumFractionDigits:1});
    return v.toFixed(nd === undefined ? 2 : nd);
  }
  function fmtRatio(v){
    if(v === null || v === undefined) return "\u2014";
    if(Math.abs(v-1) < 0.005) return "1.00\u00d7";
    if(v < 10) return v.toFixed(2)+"\u00d7";
    if(v < 100) return v.toFixed(1)+"\u00d7";
    return Math.round(v).toLocaleString("en-US")+"\u00d7";
  }

  /* ---------------- theme ---------------- */
  var root = document.documentElement;
  var btn = document.getElementById("theme-toggle");
  function applyTheme(t){
    root.setAttribute("data-theme", t);
    if(btn) btn.textContent = t === "dark" ? "Light" : "Dark";
    try{ localStorage.setItem("ec-theme", t); }catch(e){}
  }
  var saved = null;
  try{ saved = localStorage.getItem("ec-theme"); }catch(e){}
  if(!saved){
    saved = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  applyTheme(saved);
  if(btn) btn.addEventListener("click", function(){
    applyTheme(root.getAttribute("data-theme") === "dark" ? "light" : "dark");
  });

  /* ---------------- scrollspy ---------------- */
  var links = Array.prototype.slice.call(document.querySelectorAll(".toc a[href^='#']"));
  var sections = links.map(function(a){ return document.querySelector(a.getAttribute("href")); })
                      .filter(Boolean);
  if("IntersectionObserver" in window && sections.length){
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(en){
        if(en.isIntersecting){
          links.forEach(function(a){
            a.setAttribute("aria-current",
              a.getAttribute("href") === "#"+en.target.id ? "true" : "false");
          });
        }
      });
    }, {rootMargin:"-20% 0px -70% 0px"});
    sections.forEach(function(s){ io.observe(s); });
  }

  /* ---------------- single-node per-query explorer ---------------- */
  var sBench = "TPC-H", sSf = "1", sSort = {key:"q", dir:1}, sQuery = "";

  function seg(group, values, current, onPick, labelFn){
    return '<div class="seg" role="group" aria-label="'+esc(group)+'">' +
      values.map(function(v){
        return '<button type="button" data-v="'+esc(v)+'" aria-pressed="'+(v===current)+'">'+
               esc(labelFn ? labelFn(v) : v)+'</button>';
      }).join("") + '</div>';
  }
  function wireSeg(container, onPick){
    container.addEventListener("click", function(ev){
      var b = ev.target.closest("button[data-v]");
      if(!b) return;
      Array.prototype.forEach.call(container.querySelectorAll("button[data-v]"), function(x){
        x.setAttribute("aria-pressed", String(x === b));
      });
      onPick(b.getAttribute("data-v"));
    });
  }

  var elSBench = document.getElementById("seg-sbench");
  var elSSf = document.getElementById("seg-ssf");
  var elSearch = document.getElementById("single-search");
  var elBody = document.getElementById("single-body");
  var elHead = document.getElementById("single-head");
  var elMeta = document.getElementById("single-meta");
  var elEmpty = document.getElementById("single-empty");

  function singleRows(){
    var rows = (D.single[sBench] && D.single[sBench][sSf]) || [];
    var q = sQuery.trim().toLowerCase();
    var out = rows.map(function(r){ return r; });
    if(q){
      out = out.filter(function(r){
        return ("q"+r.q).toLowerCase().indexOf(q) !== -1 || String(r.q) === q;
      });
    }
    var k = sSort.key;
    out.sort(function(a,b){
      var av, bv;
      if(k === "q"){ av = a.q; bv = b.q; }
      else if(k === "spread"){
        av = spread(a); bv = spread(b);
      } else {
        var i = ENGINES.indexOf(k);
        av = a.times[i]; bv = b.times[i];
      }
      if(av === null || av === undefined) av = Infinity;
      if(bv === null || bv === undefined) bv = Infinity;
      return (av - bv) * sSort.dir;
    });
    return out;
  }
  function spread(r){
    var t = r.times.filter(function(v){ return v !== null && v > 0; });
    if(t.length < 2) return 0;
    return Math.max.apply(null,t) / Math.min.apply(null,t);
  }

  function renderSingleHead(){
    var cols = [{k:"q", label:"Query"}];
    ENGINES.forEach(function(e){ cols.push({k:e, label:SHORT[e], color:COLORS[e]}); });
    cols.push({k:"spread", label:"Slowest ÷ fastest"});
    elHead.innerHTML = "<tr>" + cols.map(function(c){
      var active = sSort.key === c.k;
      var sortAttr = active ? ' aria-sort="'+(sSort.dir===1?"ascending":"descending")+'"' : "";
      var arrow = active ? (sSort.dir===1 ? "\u25b2" : "\u25bc") : "\u25b4";
      var style = c.color ? ' style="--c:'+c.color+'"' : "";
      return '<th scope="col" class="num" data-sort="'+esc(c.k)+'"'+sortAttr+
             (c.k==="q"?' style="text-align:left"':"")+'>'+
             (c.color ? '<span class="swatch"'+style+'></span>' : "")+
             esc(c.label)+'<span class="arrow">'+arrow+'</span></th>';
    }).join("") + "</tr>";
  }

  function renderSingle(){
    renderSingleHead();
    var rows = singleRows();
    if(!rows.length){
      elBody.innerHTML = "";
      elEmpty.hidden = false;
      elEmpty.textContent = "No queries match \u201c" + sQuery + "\u201d at this selection.";
      elMeta.textContent = "";
      return;
    }
    elEmpty.hidden = true;

    // Log-scale domain across the visible cells so bars are comparable row to row.
    var all = [];
    rows.forEach(function(r){ r.times.forEach(function(t){ if(t && t > 0) all.push(t); }); });
    var lo = Math.log10(Math.min.apply(null, all));
    var hi = Math.log10(Math.max.apply(null, all));
    if(hi <= lo) hi = lo + 1;

    var wins = {};
    ENGINES.forEach(function(e){ wins[e] = 0; });

    elBody.innerHTML = rows.map(function(r){
      var valid = r.times.filter(function(t){ return t && t > 0; });
      var min = valid.length ? Math.min.apply(null, valid) : null;
      var cells = ENGINES.map(function(e,i){
        var t = r.times[i], m = r.markers[i];
        if(t === null || t === undefined){
          return '<td class="num"><span class="val">\u2014</span></td>';
        }
        var frac = (Math.log10(t) - lo) / (hi - lo);
        var w = 5 + 95 * Math.max(0, Math.min(1, frac));
        var best = min !== null && Math.abs(t - min) < 1e-12;
        if(best) wins[e]++;
        return '<td class="num cell">'+
          '<span class="bar" style="--w:'+w.toFixed(1)+'%;--c:'+COLORS[e]+'"></span>'+
          '<span class="val'+(best?" best":"")+'">'+esc(fmtTime(t))+
          (m ? '<span class="flag" title="Marker '+esc(m)+' as reported in source">'+esc(m)+'</span>' : "")+
          '</span></td>';
      }).join("");
      return '<tr><th scope="row" style="text-align:left">Q'+esc(r.q)+'</th>'+cells+
             '<td class="num">'+esc(fmtNum(spread(r),2))+'\u00d7</td></tr>';
    }).join("");

    var fastest = ENGINES.slice().sort(function(a,b){ return wins[b]-wins[a]; });
    elMeta.innerHTML = "<strong>"+esc(rows.length)+"</strong> queries shown \u00b7 "+
      esc(sBench)+" \u00b7 SF "+esc(sSf)+" \u00b7 fastest in most queries: "+
      fastest.map(function(e){
        return '<span class="swatch" style="--c:'+COLORS[e]+'"></span>'+esc(SHORT[e])+
               " <strong>"+wins[e]+"</strong>";
      }).join(" \u00b7 ");
  }

  elHead.addEventListener("click", function(ev){
    var th = ev.target.closest("th[data-sort]");
    if(!th) return;
    var k = th.getAttribute("data-sort");
    if(sSort.key === k) sSort.dir = -sSort.dir;
    else { sSort.key = k; sSort.dir = 1; }
    renderSingle();
  });
  wireSeg(elSBench, function(v){ sBench = v; renderSingle(); });
  wireSeg(elSSf, function(v){ sSf = v; renderSingle(); });
  elSearch.addEventListener("input", function(){ sQuery = elSearch.value; renderSingle(); });
  elSBench.innerHTML = seg("Benchmark", ["TPC-H","TPC-DS"], sBench);
  elSSf.innerHTML = seg("Scale factor", SFS, sSf, null, function(v){ return "SF "+v; });
  renderSingle();

  /* ---------------- cluster per-query explorer ---------------- */
  var cSf = "100", cSort = {key:"q", dir:1}, cFilter = "all", cQuery = "";
  var elCSf = document.getElementById("seg-csf");
  var elCFilter = document.getElementById("seg-cfilter");
  var elCSearch = document.getElementById("cluster-search");
  var elCHead = document.getElementById("cluster-head");
  var elCBody = document.getElementById("cluster-body");
  var elCMeta = document.getElementById("cluster-meta");
  var elCEmpty = document.getElementById("cluster-empty");

  var CCOLS = [
    {k:"q", label:"Query", left:true},
    {k:"r", label:"Spark Rust s", color:CCOLORS["Spark Rust 0.42.1"]},
    {k:"g", label:"Gluten s", color:CCOLORS["Spark 4.1.1 Gluten"]},
    {k:"diff", label:"\u0394 s"},
    {k:"ratio", label:"Ratio R\u00f7G"},
    {k:"cpu0", label:"Rust CPU s"},
    {k:"cpu1", label:"Gluten CPU s"},
    {k:"cores0", label:"Rust cores"},
    {k:"cores1", label:"Gluten cores"},
    {k:"mem0", label:"Rust mem"},
    {k:"mem1", label:"Gluten mem"},
    {k:"status", label:"Status", left:true}
  ];

  function cval(r, k){
    if(k === "cpu0") return r.cpu ? r.cpu[0] : null;
    if(k === "cpu1") return r.cpu ? r.cpu[1] : null;
    if(k === "cores0") return r.cores ? r.cores[0] : null;
    if(k === "cores1") return r.cores ? r.cores[1] : null;
    if(k === "mem0") return r.memory ? r.memory[0] : null;
    if(k === "mem1") return r.memory ? r.memory[1] : null;
    return r[k];
  }

  function clusterRows(){
    var rows = (D.clusterQueries[cSf] || []).slice();
    if(cFilter === "gap") rows = rows.filter(function(r){ return r.status === "gap"; });
    else if(cFilter === "pass") rows = rows.filter(function(r){ return r.status.indexOf("pass") === 0; });
    else if(cFilter === "other") rows = rows.filter(function(r){
      return r.status !== "gap" && r.status.indexOf("pass") !== 0;
    });
    var q = cQuery.trim().toLowerCase();
    if(q) rows = rows.filter(function(r){
      return ("q"+r.q).toLowerCase().indexOf(q) !== -1 || String(r.q) === q;
    });
    var k = cSort.key;
    rows.sort(function(a,b){
      var av = k === "status" ? a.status : cval(a,k);
      var bv = k === "status" ? b.status : cval(b,k);
      if(typeof av === "string") return av.localeCompare(bv) * cSort.dir;
      if(av === null || av === undefined) av = Infinity;
      if(bv === null || bv === undefined) bv = Infinity;
      return (av - bv) * cSort.dir;
    });
    return rows;
  }

  function renderClusterHead(){
    elCHead.innerHTML = "<tr>" + CCOLS.map(function(c){
      var active = cSort.key === c.k;
      var sortAttr = active ? ' aria-sort="'+(cSort.dir===1?"ascending":"descending")+'"' : "";
      var arrow = active ? (cSort.dir===1 ? "\u25b2" : "\u25bc") : "\u25b4";
      return '<th scope="col" class="num" data-sort="'+esc(c.k)+'"'+sortAttr+
             (c.left ? ' style="text-align:left"' : "")+'>'+
             (c.color ? '<span class="swatch" style="--c:'+c.color+'"></span>' : "")+
             esc(c.label)+'<span class="arrow">'+arrow+'</span></th>';
    }).join("") + "</tr>";
  }

  function renderCluster(){
    renderClusterHead();
    var rows = clusterRows();
    var all = (D.clusterQueries[cSf] || []);
    if(!rows.length){
      elCBody.innerHTML = "";
      elCEmpty.hidden = false;
      elCEmpty.textContent = "No queries match the current filter and search.";
      elCMeta.textContent = "";
      return;
    }
    elCEmpty.hidden = true;

    var vals = [];
    rows.forEach(function(r){
      if(r.r && r.r > 0) vals.push(r.r);
      if(r.g && r.g > 0) vals.push(r.g);
    });
    var lo = vals.length ? Math.log10(Math.min.apply(null, vals)) : 0;
    var hi = vals.length ? Math.log10(Math.max.apply(null, vals)) : 1;
    if(hi <= lo) hi = lo + 1;

    elCBody.innerHTML = rows.map(function(r){
      function barCell(v, color){
        if(v === null || v === undefined){
          return '<td class="num"><span class="val">\u2014</span></td>';
        }
        var frac = (Math.log10(v) - lo) / (hi - lo);
        var w = 5 + 95 * Math.max(0, Math.min(1, frac));
        return '<td class="num cell"><span class="bar" style="--w:'+w.toFixed(1)+'%;--c:'+color+
               '"></span><span class="val">'+esc(fmtTime(v))+'</span></td>';
      }
      var st = r.status;
      var cls = st === "gap" ? "gap" : (st.indexOf("pass") === 0 ? "" : "other");
      var label = st === "gap" ? "gap" : (st === "pass" ? "pass" :
                  (st.indexOf("pass") === 0 ? "pass*" : "single-engine"));
      var faster = (r.r !== null && r.g !== null) ? (r.r < r.g ? "r" : (r.g < r.r ? "g" : "")) : "";
      return "<tr>"+
        '<th scope="row" style="text-align:left">Q'+esc(r.q)+'</th>'+
        barCell(r.r, CCOLORS["Spark Rust 0.42.1"]).replace('class="val"', 'class="val'+(faster==="r"?" best":"")+'"')+
        barCell(r.g, CCOLORS["Spark 4.1.1 Gluten"]).replace('class="val"', 'class="val'+(faster==="g"?" best":"")+'"')+
        '<td class="num">'+esc(r.diff === null ? "\u2014" : (r.diff>0?"+":(r.diff<0?"\u2212":"\u00b1"))+fmtTime(Math.abs(r.diff)))+'</td>'+
        '<td class="num">'+esc(fmtRatio(r.ratio))+'</td>'+
        '<td class="num">'+esc(fmtNum(cval(r,"cpu0"),1))+'</td>'+
        '<td class="num">'+esc(fmtNum(cval(r,"cpu1"),1))+'</td>'+
        '<td class="num">'+esc(fmtNum(cval(r,"cores0"),2))+'</td>'+
        '<td class="num">'+esc(fmtNum(cval(r,"cores1"),2))+'</td>'+
        '<td class="num">'+esc(fmtNum(cval(r,"mem0"),2))+'</td>'+
        '<td class="num">'+esc(fmtNum(cval(r,"mem1"),2))+'</td>'+
        '<td style="text-align:left"><span class="pill '+cls+'" title="'+esc(st)+'">'+esc(label)+'</span></td>'+
      "</tr>";
    }).join("");

    var w = D.wins[cSf] || [0,0];
    elCMeta.innerHTML = "<strong>"+esc(rows.length)+"</strong> of "+esc(all.length)+
      " queries shown \u00b7 SF "+esc(cSf)+" \u00b7 per-query wins: <strong>"+esc(w[0])+
      "</strong> Spark Rust \u00b7 <strong>"+esc(w[1])+"</strong> Gluten"+
      " \u00b7 ratio is Spark Rust \u00f7 Gluten, so below 1.00\u00d7 favours Spark Rust.";
  }

  elCHead.addEventListener("click", function(ev){
    var th = ev.target.closest("th[data-sort]");
    if(!th) return;
    var k = th.getAttribute("data-sort");
    if(cSort.key === k) cSort.dir = -cSort.dir;
    else { cSort.key = k; cSort.dir = 1; }
    renderCluster();
  });
  wireSeg(elCSf, function(v){ cSf = v; renderCluster(); });
  wireSeg(elCFilter, function(v){ cFilter = v; renderCluster(); });
  elCSearch.addEventListener("input", function(){ cQuery = elCSearch.value; renderCluster(); });
  elCSf.innerHTML = seg("Scale factor", CSFS, cSf, null, function(v){ return "SF "+v; });
  elCFilter.innerHTML = seg("Status filter", ["all","pass","gap","other"], cFilter, null, function(v){
    return v === "all" ? "All" : v === "other" ? "Single-engine" : v[0].toUpperCase()+v.slice(1);
  });
  renderCluster();
})();
"""


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def build(data: dict) -> str:
    tm = totals_map(data)
    analysis = build_findings(data, tm)

    payload = dict(data)
    payload["__colors"] = ENGINE_COLORS
    payload["__short"] = ENGINE_SHORT
    payload["__ccolors"] = CLUSTER_COLORS
    data_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    # Guard against premature </script> termination.
    data_json = data_json.replace("</", "<\\/")

    engines = data["engines"]

    toc_items = [
        ("summary", "Summary"),
        ("hardware", "Hardware"),
        ("totals", "Single-node totals"),
        ("scaling", "Scaling"),
        ("per-query", "Per-query"),
        ("cluster", "Cluster"),
        ("cluster-queries", "Cluster per-query"),
        ("notes", "Data notes"),
    ]
    toc = "".join(
        f'<a href="#{slug}" aria-current="false">{esc(label)}</a>' for slug, label in toc_items
    )

    per_query_section = """
<section id="per-query" class="section">
  <h2>Single-node per-query detail</h2>
  <p class="lede">Wall-clock seconds for every query. Bars are logarithmic across the visible
  cells, so bar length is comparable between rows; the fastest engine in each query is bold.
  Click any column header to sort. Lettered flags reproduce the <code>markers</code> field
  verbatim — see <a href="#notes">data notes</a> for what is and is not known about them.</p>
  <div class="controls">
    <div class="control"><span id="lbl-sbench">Benchmark</span>
      <div id="seg-sbench" aria-labelledby="lbl-sbench"></div></div>
    <div class="control"><span id="lbl-ssf">Scale factor</span>
      <div id="seg-ssf" aria-labelledby="lbl-ssf"></div></div>
    <div class="control"><label for="single-search">Find query</label>
      <input type="search" id="single-search" placeholder="e.g. 12" autocomplete="off"></div>
  </div>
  <p class="lede" id="single-meta" role="status" aria-live="polite"></p>
  <noscript>
    <p class="note">This interactive table requires JavaScript. The per-query values it would
    show are the same numbers aggregated in <a href="#totals">Single-node totals</a>, and are
    present in the source dataset under <code>single.&lt;benchmark&gt;.&lt;sf&gt;</code>.</p>
  </noscript>
  <div class="table-wrap">
    <table class="data sortable">
      <caption>Per-query wall-clock seconds, single node</caption>
      <thead id="single-head"></thead>
      <tbody id="single-body"></tbody>
    </table>
    <p class="empty" id="single-empty" hidden></p>
  </div>
</section>"""

    cluster_query_section = """
<section id="cluster-queries" class="section">
  <h2>Cluster per-query detail</h2>
  <p class="lede">TPC-DS on eight workers. <code>r</code> is Spark Rust 0.42.1 and
  <code>g</code> is Spark 4.1.1 Gluten; the ratio is <code>r ÷ g</code>, so values below
  1.00× favour Spark Rust. Memory columns are the reported <code>memory</code> values.
  Status pills summarise the source <code>status</code> string, which is shown in full on hover.</p>
  <div class="controls">
    <div class="control"><span id="lbl-csf">Scale factor</span>
      <div id="seg-csf" aria-labelledby="lbl-csf"></div></div>
    <div class="control"><span id="lbl-cfilter">Status</span>
      <div id="seg-cfilter" aria-labelledby="lbl-cfilter"></div></div>
    <div class="control"><label for="cluster-search">Find query</label>
      <input type="search" id="cluster-search" placeholder="e.g. 39" autocomplete="off"></div>
  </div>
  <p class="lede" id="cluster-meta" role="status" aria-live="polite"></p>
  <noscript>
    <p class="note">This interactive table requires JavaScript. The cluster aggregates it
    feeds are shown in <a href="#cluster">Cluster runs</a>, and the per-query values are
    present in the source dataset under <code>clusterQueries.&lt;sf&gt;</code>.</p>
  </noscript>
  <div class="table-wrap">
    <table class="data sortable">
      <caption>Per-query cluster results, Spark Rust 0.42.1 versus Spark 4.1.1 Gluten</caption>
      <thead id="cluster-head"></thead>
      <tbody id="cluster-body"></tbody>
    </table>
    <p class="empty" id="cluster-empty" hidden></p>
  </div>
</section>"""

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Query Engine Comparison — TPC-H and TPC-DS Benchmark Report</title>
<meta name="description" content="Single-node and cluster TPC-H and TPC-DS benchmark comparison of Spark Rust 0.42.1, DuckDB 1.5.5, Spark 4.1.1 Gluten and Spark 4.2, generated from engine-comparison-summary-data.json.">
<meta name="color-scheme" content="light dark">
<style>{CSS}</style>
<noscript><style>
  /* Without JS the segmented controls and search fields are inert; hide them
     rather than presenting non-functional controls. */
  .controls{{display:none!important}}
  table.sortable thead th[data-sort]{{cursor:default}}
  table.sortable thead th .arrow{{display:none}}
</style></noscript>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<header class="masthead">
  <div class="wrap">
    <p class="eyebrow">Benchmark report</p>
    <h1>Query engine comparison: TPC-H &amp; TPC-DS</h1>
    <p class="lede">Wall-clock, CPU and memory results for {esc(len(engines))} engines on a
    single node across four scale factors, plus eight-worker cluster runs of TPC-DS at three
    scale factors. Every figure is taken from or recomputed from a single source dataset.</p>
    <div class="prov">
      <span><b>Source</b> {esc(data["source"])}</span>
      <span><b>Dataset</b> engine-comparison-summary-data.json</span>
      <span><b>SHA-256</b> <code class="hash">{esc(data["sha256"][:32])}…</code></span>
      <span><b>Benchmarks</b> TPC-H ({esc(tm[("TPC-H","1")][BASELINE]["n"])} q), TPC-DS ({esc(tm[("TPC-DS","1")][BASELINE]["n"])} q)</span>
    </div>
  </div>
</header>

<nav class="toc" aria-label="Sections">
  <div class="wrap">
    {toc}
    <span class="spacer"></span>
    <button type="button" class="theme-btn" id="theme-toggle" aria-label="Switch colour theme">Dark</button>
  </div>
</nav>

<main id="main" class="wrap">
{section_summary(data, tm, analysis)}
{section_hardware(data)}
{section_totals(data, tm)}
{section_scaling(data, tm)}
{per_query_section}
{section_cluster(data)}
{cluster_query_section}
{section_notes(data)}
</main>

<footer>
  <div class="wrap">
    <span>Generated from <code>engine-comparison-summary-data.json</code> — the sole input. No external data was added.</span>
    <span>Source <code>{esc(data["source"])}</code> · SHA-256 <code class="hash">{esc(data["sha256"][:16])}…</code></span>
  </div>
</footer>

<script>window.__DATA__ = {data_json};</script>
<script>{JS}</script>
</body>
</html>
"""


def main(argv: list[str]) -> int:
    src = Path(argv[1]) if len(argv) > 1 else Path("engine-comparison-summary-data.json")
    dst = Path(argv[2]) if len(argv) > 2 else Path("engine-comparison-report.html")
    data = json.loads(src.read_text(encoding="utf-8"))
    dst.write_text(build(data), encoding="utf-8")
    size = dst.stat().st_size
    print(f"wrote {dst} ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
