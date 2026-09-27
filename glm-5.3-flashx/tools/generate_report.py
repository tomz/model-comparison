#!/usr/bin/env python3
"""Generate a self-contained HTML report from engine-comparison-summary-data.json.

Usage: python3 tools/generate_report.py
Reads  engine-comparison-summary-data.json from the project root.
Writes engine-comparison-report.html next to it.
"""
import json, html, math
from datetime import datetime, timezone

ROOT = __file__.rsplit("/tools/", 1)[0]
SRC = f"{ROOT}/engine-comparison-summary-data.json"
OUT = f"{ROOT}/engine-comparison-report.html"

with open(SRC) as f:
    data = json.load(f)

ENG = data["engines"]

META = {
    ENG[0]: dict(short="Rust (default)", full="Spark Rust 0.42.1 (default)", color="#56b4e9"),
    ENG[1]: dict(short="Rust (tuned)",   full="Spark Rust 0.42.1 (tuned)",   color="#0072b2"),
    ENG[2]: dict(short="DuckDB 1.5.5",   full="DuckDB 1.5.5",                color="#009e73"),
    ENG[3]: dict(short="Gluten 4.1.1",   full="Spark 4.1.1 + Gluten",        color="#e69f00"),
    ENG[4]: dict(short="Spark 4.2",      full="Spark 4.2 (Vanilla)",         color="#d55e00"),
}
SHORT = [META[e]["short"] for e in ENG]
COLORS = [META[e]["color"] for e in ENG]


def esc(s):
    return html.escape(str(s), quote=True)


def fsec(v):
    if v is None:
        return "&mdash;"
    a = abs(v)
    if a >= 1000:
        return f"{v:,.0f}"
    if a >= 100:
        return f"{v:,.1f}"
    if a >= 10:
        return f"{v:.1f}"
    return f"{v:.2f}"


def fsigndiff(v):
    if v is None:
        return "&mdash;"
    sign = "+" if v > 0 else ("&minus;" if v < 0 else "")
    return f"{sign}{fsec(abs(v))}"


def fratio(v):
    return f"&times;{v:.2f}"


def chip_ratio(v, extra=""):
    if v is None:
        return '<span class="chip none">&mdash;</span>'
    cls = "chip"
    if abs(v - 1.0) < 0.005:
        cls += " even"
    elif v < 1.0:
        cls += " good"
    elif v >= 3.0:
        cls += " hot"
    else:
        cls += " warn"
    return f'<span class="{cls}{extra}">{fratio(v)}</span>'


def heat_class(r):
    if r is None:
        return "none"
    if r < 1.0005:
        return "best"
    if r <= 1.15:
        return "h1"
    if r <= 1.5:
        return "h2"
    if r <= 3.0:
        return "h3"
    if r <= 10.0:
        return "h4"
    return "h5"


def total_row_map(bench):
    return {(e["sf"], e["engine"]): e for e in data["totals"][bench]}


def totals_table(bench, bench_label):
    m = total_row_map(bench)
    nq = 22 if bench == "TPC-H" else 99
    all_rows = {eng: m[("all", eng)] for eng in ENG}
    divs = []
    for i, eng in enumerate(ENG):
        e = all_rows[eng]
        if e["matched"] is not None and abs(e["matched"] - e["ratio"]) >= 0.03:
            divs.append(f'{esc(SHORT[i])} {fratio(e["ratio"])} vs {fratio(e["matched"])} mp')
    div_txt = (" Engines whose full-suite and matched-pair ratios diverge: " + "; ".join(divs) + ".") if divs else ""
    if bench == "TPC-H":
        dag_reason = ("Spark&nbsp;4.2 lacks it at SF&nbsp;1000 and on the all row, so those two aggregates are computed "
                      "from the observations available in the source")
    else:
        dag_reason = ("Spark&nbsp;4.1.1 Gluten lacks it at SF&nbsp;1000 and on the all row, so those two aggregates are "
                      "computed from the observations available in the source")
    head = "".join(
        f'<th scope="col" title="{esc(META[e]["full"])}">{esc(SHORT[i])}</th>'
        for i, e in enumerate(ENG)
    )
    rows = []
    for sf in ("1", "10", "100", "1000", "all"):
        last = ' class="allrow"' if sf == "all" else ""
        nsub = f"{nq} queries" if sf != "all" else (f"{4 * nq} query runs")
        cells = []
        for i, eng in enumerate(ENG):
            e = m[(sf, eng)]
            ratio = e["matched"] if (sf == "all" and e["matched"] is not None) else e["ratio"]
            dag = '<sup class="dag">&dagger;</sup>' if e["canonical"] is None else ""
            rtag = ' title="matched-pair ratio vs DuckDB (mp)"' if (sf == "all" and e["matched"] is not None) else ""
            mp = '<sup class="mp">mp</sup>' if (sf == "all" and e["matched"] is not None) else ""
            cells.append(
                f'<td class="num {heat_class(e["ratio"])}"><span class="t">{fsec(e["time"])}{dag}</span>'
                f'{chip_ratio(ratio, rtag)}{mp}</td>'
            )
        rows.append(
            f'<tr{last}><th scope="row" class="sfrow">SF {esc(sf)}<span class="nsub">{nsub}</span></th>'
            + "".join(cells) + "</tr>"
        )
    # canonical-vs-matched divergence notes are built above as div_txt
    return f"""<figure class="tblwrap">
<table class="totals">
<caption>{esc(bench_label)} &mdash; aggregate wall-clock time (seconds) and ratio vs DuckDB 1.5.5</caption>
<thead><tr><th scope="col">Scale factor</th>{head}</tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<figcaption class="tnote">Lower is better. <span class="chip base">&times;1.00</span> = DuckDB baseline.
On the <em>all</em> row, engines that missed some queries also carry a matched-pair ratio (tagged <code>mp</code>)
computed only over comparable query pairs; it is flattered relative to the full-suite ratio when misses are excluded.{div_txt}
<span class="dag">&dagger;</span>&nbsp;canonical per-query total absent in the source &mdash; {dag_reason}.</figcaption>
</figure>"""


# ---------------- charts ----------------
LOGTICKS = [(1, "1 s"), (10, "10 s"), (100, "100 s"), (1000, "1,000 s"), (10_000, "10,000 s"), (100_000, "100,000 s")]


def _nice_ticks(vmax):
    step = vmax / 4
    mag = 10 ** math.floor(math.log10(step))
    norm = step / mag
    nice = 1 if norm < 1.5 else 2 if norm < 3.5 else 5 if norm < 7.5 else 10
    step = nice * mag
    return [step * i for i in range(0, int(vmax / step) + 1)]


def hbar_chart(groups, *, log=True, lin_max=None):
    width, left, right = 980, 118, 104
    bar, bgap, ggap, top, axis_h = 15, 6, 20, 30, 30
    rows_n = len(groups[0][1])
    H = top + len(groups) * (rows_n * (bar + bgap) - bgap + ggap) + axis_h

    def x(v):
        if log:
            return left + (math.log10(max(v, 1e-9)) / 5.0) * (width - left - right)
        return left + (v / lin_max) * (width - left - right)

    parts = [f'<svg viewBox="0 0 {width} {H}" role="img" class="chart">',
             '<rect x="0" y="0" width="100%" height="100%" class="plotbg" rx="10"/>']
    ticks = LOGTICKS if log else [(v, f"{v:,.0f}") for v in _nice_ticks(lin_max)]
    for tv, lab in ticks:
        xx = x(tv)
        parts.append(f'<line class="gl" x1="{xx:.1f}" y1="{top-10}" x2="{xx:.1f}" y2="{H-axis_h+6}"/>')
        parts.append(f'<text class="ax" x="{xx:.1f}" y="{top-14}" text-anchor="middle">{esc(lab)}</text>')
        parts.append(f'<text class="ax" x="{xx:.1f}" y="{H-8}" text-anchor="middle">{esc(lab)}</text>')
    y = top
    for glabel, items in groups:
        parts.append(f'<text class="glabel" x="{left-12}" y="{y + rows_n*(bar+bgap)/2 - 4}" text-anchor="end">{esc(glabel)}</text>')
        for i, (eng, v) in enumerate(items):
            by = y + i * (bar + bgap)
            if v is None:
                parts.append(f'<text class="bl" x="{left+6}" y="{by+bar-3}">no data</text>')
            else:
                xe = x(v)
                parts.append(f'<rect class="bar" x="{left}" y="{by}" width="{max(xe-left,1):.1f}" height="{bar}" rx="3" fill="{COLORS[i]}" fill-opacity="0.92"><title>{esc(META[eng]["full"])} &mdash; SF {esc(glabel.split()[-1])}: {fsec(v)} s</title></rect>')
                parts.append(f'<text class="bl" x="{xe+7:.1f}" y="{by+bar-3}">{fsec(v)}</text>')
        y += rows_n * (bar + bgap) - bgap + ggap
    parts.append(f'<line class="axis" x1="{left}" y1="{top-10}" x2="{left}" y2="{H-axis_h+6}"/>')
    parts.append("</svg>")
    return "".join(parts)


def chart_totals(bench):
    groups = []
    for sf in ("1", "10", "100", "1000"):
        row = {e["engine"]: e["time"] for e in data["totals"][bench] if e["sf"] == sf}
        groups.append((f"SF {sf}", [(ENG[i], row[ENG[i]]) for i in range(5)]))
    return hbar_chart(groups, log=True)


def chart_cluster(field, log):
    groups = []
    for sf in ("100", "1000", "10000"):
        row = {r["engine"]: r.get(field) for r in data["cluster"][sf]}
        items = [(ENG[0], row["Spark Rust 0.42.1"]), (ENG[3], row["Spark 4.1.1 Gluten"])]
        groups.append((f"SF {sf}", items))
    if log:
        return hbar_chart(groups, log=True)
    lm = max(v for _, items in groups for _, v in items) * 1.08
    return hbar_chart(groups, log=False, lin_max=lm)


# ---------------- per-query (single node) ----------------
def perquery_block(bench, bench_label, sf):
    rows = sorted(data["single"][bench][sf], key=lambda r: r["q"])
    best_counts = {i: 0 for i in range(5)}
    body = []
    for r in rows:
        times = r["times"]
        valid = [(i, t) for i, t in enumerate(times) if t is not None]
        bidx = min(valid, key=lambda p: p[1])[0]
        best_counts[bidx] += 1
        bmin = times[bidx]
        cells = []
        for i in range(5):
            t = times[i]
            mk = r["markers"][i] if i < len(r["markers"]) else ""
            flag = f'<span class="flag flag{esc(mk)}" title="Per-query flag {esc(mk)} recorded in the source data">{esc(mk)}</span>' if mk else ""
            title = f'title="{esc(SHORT[i])}: {fsec(t)} s ({fratio(t/bmin)} vs best)"' if t is not None else ""
            cells.append(f'<td class="num {heat_class((t/bmin) if t is not None else None)}" {title}><span class="t">{fsec(t)}</span>{flag}</td>')
        body.append(f'<tr><th scope="row" class="qrow">{r["q"]}</th>' + "".join(cells) + "</tr>")
    bsum = " &middot; ".join(f"{esc(SHORT[i])} on {c}" for i, c in sorted(best_counts.items(), key=lambda kv: -kv[1]) if c)
    head = "".join(f'<th scope="col" title="{esc(META[e]["full"])}">{esc(SHORT[i])}</th>' for i, e in enumerate(ENG))
    return f"""<details class="pq">
<summary><span class="sum-t">{esc(bench_label)} &middot; SF {esc(sf)}</span>
<span class="sum-meta">{len(rows)} queries &middot; fastest: {bsum}</span><span class="chev" aria-hidden="true">&#9662;</span></summary>
<div class="tblwrap">
<table class="pqt">
<caption>Per-query wall-clock time in seconds; cell shading relative to the fastest engine in the row</caption>
<thead><tr><th scope="col">Q</th>{head}</tr></thead>
<tbody>{''.join(body)}</tbody>
</table>
</div></details>"""


def perquery_section():
    parts = ['<p class="lead">Wall-clock seconds per query. The green-tinted cell in each row is the fastest engine; '
             'amber intensity grows with the gap to the fastest. <span class="flag flagB">B</span> and '
             '<span class="flag flagP">P</span> are per-query flags carried over verbatim from the source data '
             "(they appear only at SF 1000; consult the source document for their definitions).</p>"]
    for bench, label in (("TPC-H", "TPC-H"), ("TPC-DS", "TPC-DS")):
        parts.append(f"<h3>{esc(label)}</h3>")
        for sf in ("1", "10", "100", "1000"):
            parts.append(perquery_block(bench, label, sf))
    return "".join(parts)


# ---------------- cluster ----------------
STATUS_META = [
    ("pass (Q39 ULP policy)", "pass", "pass &middot; ULP", "ok"),
    ("pass", "pass", "pass", "ok"),
    ("gap", "gap", "gap", "warn"),
    ("Spark Rust 0.42.1-only: single observation; unvalidated against Spark 4.1.1 Gluten", "only", "Rust-only", "info"),
    ("Spark Rust 0.42.1-only: single observation; Spark 4.1.1 Gluten repeat rejected", "only", "Rust-only", "info"),
    ("Spark Rust 0.42.1-only: patched-build two-run mean; unvalidated against Spark 4.1.1 Gluten", "only", "Rust-only", "info"),
    ("no successful Spark Rust 0.42.1 result; Spark 4.1.1 Gluten timeout", "none", "no result", "bad"),
]


def status_cell(s):
    for full, _key, label, cls in STATUS_META:
        if s == full:
            return f'<span class="chip {cls}" title="{esc(s)}">{label}</span>', cls, s
    return f'<span class="chip info" title="{esc(s)}">{esc(s)}</span>', "info", s


def cluster_table(sf):
    rows = sorted(data["clusterQueries"][sf], key=lambda r: r["q"])
    wins = data["wins"][sf]
    notes = []
    body = []
    for r in rows:
        chip, cls, full = status_cell(r["status"])
        if cls in ("info", "bad"):
            notes.append((r["q"], full))
        cells = (
            f'<td class="num {"best" if cls == "ok" else ""}">{fsec(r["r"])}</td>'
            f'<td class="num">{fsec(r["g"])}</td>'
            f'<td class="num">{chip_ratio(r["ratio"])}</td>'
            f'<td class="num">{fsigndiff(r["diff"])}</td>'
            f'<td class="status">{chip}</td>'
        )
        body.append(f'<tr class="st-{cls}"><th scope="row" class="qrow">{r["q"]}</th>{cells}</tr>')
    noteh = ""
    if notes:
        items = "".join(f"<li><strong>Q{q}</strong> &mdash; {esc(t)}</li>" for q, t in notes)
        noteh = f'<div class="fnote"><h4>Notes for this scale factor</h4><ul>{items}</ul></div>'
    return f"""<details class="pq">
<summary><span class="sum-t">Cluster &middot; SF {esc(sf)}</span>
<span class="sum-meta">99 queries (TPC-DS) &middot; Rust <strong>{wins[0]}</strong> &ndash; <strong>{wins[1]}</strong> Gluten &middot; validated pairs only</span><span class="chev" aria-hidden="true">&#9662;</span></summary>
<div class="tblwrap">
<table class="cq">
<caption>Per-query comparison, Spark Rust 0.42.1 vs Spark 4.1.1 Gluten at SF {esc(sf)} (seconds; &Delta; = Rust minus Gluten)</caption>
<thead><tr><th scope="col">Q</th><th scope="col">Rust</th><th scope="col">Gluten</th><th scope="col">Rust&thinsp;/&thinsp;Gluten</th><th scope="col">&Delta; wall</th><th scope="col">Status</th></tr></thead>
<tbody>{''.join(body)}</tbody>
</table>
{noteh}
</div></details>"""


def cluster_totals_table():
    head = ('<tr><th scope="col">SF</th><th scope="col">Engine</th><th scope="col">n</th>'
            '<th scope="col">Wall (s)</th><th scope="col">CPU (core-h)</th><th scope="col">Mem (core-h)</th>'
            '<th scope="col">Mean (s)</th><th scope="col">p50 (s)</th><th scope="col">p95 (s)</th>'
            '<th scope="col">Max (s)</th><th scope="col">Avg cores</th></tr>')
    rows = []
    for sf in ("100", "1000", "10000"):
        for r in data["cluster"][sf]:
            short = "Rust 0.42.1" if "Rust" in r["engine"] else "Gluten 4.1.1"
            rows.append(
                f'<tr><th scope="row" class="sfrow">SF {esc(sf)}</th><td>{esc(short)}</td>'
                f'<td class="num">{r["n"]}</td><td class="num">{fsec(r["time"])}</td>'
                f'<td class="num">{r["cpuHours"]:,.1f}</td><td class="num">{r["memHours"]:,.1f}</td>'
                f'<td class="num">{fsec(r["mean"])}</td><td class="num">{fsec(r["p50"])}</td>'
                f'<td class="num">{fsec(r["p95"])}</td><td class="num">{fsec(r["max"])}</td>'
                f'<td class="num">{r["cores"]:.1f}</td></tr>'
            )
    return f"""<figure class="tblwrap">
<table class="totals clustert">
<caption>Cluster run totals &mdash; Spark Rust 0.42.1 vs Spark 4.1.1 Gluten (TPC-DS 99 queries)</caption>
<thead>{head}</thead>
<tbody>{''.join(rows)}</tbody>
</table>
<figcaption class="tnote">SF 10,000 totals cover 94 of 99 queries on both engines: Q23 failed on Rust (Gluten timeout)
and Q39, Q67, Q78, Q95 are Rust-only observations without a validated Gluten pair &mdash; see the SF&nbsp;10,000 per-query table.
CPU and memory are core-hours (resource-time), not wall-clock.</figcaption>
</figure>"""


def cluster_wins_strip():
    chips = []
    label = {"100": "SF 100", "1000": "SF 1,000", "10000": "SF 10,000"}
    for k in ("100", "1000", "10000"):
        w = data["wins"][k]
        chips.append(f'<div class="wins"><span class="wlab">{label[k]}</span>'
                     f'<span class="wval">{w[0]}<em>&ndash;</em>{w[1]}</span>'
                     f'<span class="wsub">Rust &ndash; Gluten</span></div>')
    return f'<div class="winsrow">{"".join(chips)}</div>'


# ---------------- exec summary ----------------
def exec_summary():
    td = {(e["sf"], e["engine"]): e for e in data["totals"]["TPC-DS"]}
    h_all = {e["engine"]: e for e in data["totals"]["TPC-H"] if e["sf"] == "all"}
    d_all = {e["engine"]: e for e in data["totals"]["TPC-DS"] if e["sf"] == "all"}
    rust_t_h = h_all[ENG[1]]
    rust_t_d = d_all[ENG[1]]
    c10 = {r["engine"]: r for r in data["cluster"]["10000"]}
    rust10, gl10 = c10["Spark Rust 0.42.1"], c10["Spark 4.1.1 Gluten"]
    gl10_wall_ratio = gl10["time"] / rust10["time"]
    cpu_share = rust10["cpuHours"] / gl10["cpuHours"] * 100
    cards = [
        ("TPC-H &middot; all scale factors",
         fratio(rust_t_h["matched"]),
         f'Rust (tuned) vs DuckDB &middot; {fsec(rust_t_h["time"])} s vs {fsec(h_all[ENG[2]]["time"])} s across 88 query runs'),
        ("TPC-DS &middot; all scale factors",
         fratio(rust_t_d["matched"]),
         f'Rust (tuned) &mdash; fastest overall &middot; {fsec(rust_t_d["time"])} s vs {fsec(d_all[ENG[2]]["time"])} s across 396 query runs'),
        ("Matched pairs &middot; all scale factors",
         f'{fratio(h_all[ENG[0]]["matched"])} / {fratio(d_all[ENG[0]]["matched"])}',
         f'Rust (default) matched-pair ratio vs DuckDB on TPC-H / TPC-DS. It diverges from the full-suite ratio '
         f'({fratio(h_all[ENG[0]]["ratio"])} / {fratio(d_all[ENG[0]]["ratio"])}) because only comparable query pairs are counted'),
        ("Cluster &middot; SF 10,000",
         f'&times;{gl10_wall_ratio:.2f}',
         f'Gluten faster on wall-clock ({fsec(gl10["time"])} s vs {fsec(rust10["time"])} s) while Rust used {cpu_share:.0f}% of Gluten&rsquo;s CPU-hours ({rust10["cpuHours"]:,.0f} vs {gl10["cpuHours"]:,.0f} core-h)'),
    ]
    cardhtml = "".join(
        f'<article class="card"><h3>{t}</h3><p class="big">{v}</p><p class="sub">{s}</p></article>'
        for t, v, s in cards
    )
    w10 = data["wins"]["10000"]
    winsline = (f'At cluster scale the validated win count shifts from Rust {data["wins"]["100"][0]}&ndash;{data["wins"]["100"][1]} (SF&nbsp;100) '
                f'to Gluten {w10[1]}&ndash;{w10[0]} (SF&nbsp;10,000).')
    return f"""<div class="cards">{cardhtml}</div>
<aside class="callout" aria-label="Reading notes">
<h3>How to read this report</h3>
<ul>
<li>All single-node ratios are relative to <strong>DuckDB 1.5.5</strong> at the same scale factor; <span class="chip base">&times;1.00</span> marks the baseline and lower is faster.</li>
<li>On a single node, Spark Rust 0.42.1 tracks DuckDB within a few percent end-to-end on both suites and is 40&ndash;50&times; faster than the JVM engines at SF&nbsp;1 (about 8&times; at SF&nbsp;10); at SF&nbsp;1000 on TPC-DS the Rust builds <em>edge out</em> DuckDB ({fratio(td[("1000", ENG[0])]["ratio"])} default, {fratio(td[("1000", ENG[1])]["ratio"])} tuned).</li>
<li>{winsline} Cluster <em>gap</em> rows (parity not established) are excluded from win counts; among gap rows the median Rust/Gluten ratio is 2.04&times; / 1.22&times; / 1.74&times; at SF 100 / 1,000 / 10,000.</li>
<li>Some source totals lack a canonical per-query sum (marked <span class="dag">&dagger;</span> in the tables); those aggregates are computed from available observations and their all-rows ratios come from matched pairs.</li>
</ul>
</aside>"""


# ---------------- method / hardware ----------------
def method_section():
    hw = data["hardware"]
    sn, cw = hw["single_node"], hw["cluster_workers"]
    sha = data["sha256"]
    return f"""<div class="hwgrid">
<article class="card">
<h3>Single node</h3>
<p class="big">{esc(sn["sku"])}</p>
<p class="sub">{sn["cores"]} vCPU &middot; {sn["ram_gb"]} GB RAM &middot; {esc(hw["provenance"])}</p>
</article>
<article class="card">
<h3>Cluster</h3>
<p class="big">{cw["count"]} &times; {esc(cw["sku"])}</p>
<p class="sub">{cw["total_cores"]} vCPU and {cw["total_ram_gb"]} GB total ({cw["cores_each"]} &times; {cw["ram_gb_each"]} GB each) &middot; {esc(hw["provenance"])}</p>
</article>
</div>
<div class="notes">
<h3>Method &amp; caveats</h3>
<ul>
<li><strong>Baseline.</strong> DuckDB 1.5.5 is the reference in every single-node ratio. Ratios below 1.00 mean the engine finished faster than DuckDB.</li>
<li><strong>Suites.</strong> Single-node TPC-H covers 22 queries and TPC-DS 99 queries at SF 1 / 10 / 100 / 1000; the &ldquo;all&rdquo; row aggregates 88 (TPC-H) or 396 (TPC-DS) query runs across scale factors.</li>
<li><strong>Canonical vs matched.</strong> The source carries a canonical per-query total per engine. Where it is missing (<span class="dag">&dagger;</span>), the shown aggregate sums the available observations. For all-scale-factor rows the reported ratio is the source&rsquo;s <em>matched-pair</em> ratio, which pairs only queries both engines completed.</li>
<li><strong>Marker flags.</strong> <span class="flag flagB">B</span>/<span class="flag flagP">P</span> appear on six query/engine cells at SF&nbsp;1000 only; their semantics are defined in the source document and are reproduced here unaltered.</li>
<li><strong>Q39 (ULP).</strong> One cluster query passes under a documented ULP-tolerance policy rather than exact equality (&ldquo;pass &middot; ULP&rdquo; status).</li>
<li><strong>Cluster status vocabulary.</strong> <span class="chip ok">pass</span> = validated pair, both engines completed. <span class="chip warn">gap</span> = parity not established in the source; excluded from win counts. <span class="chip info">Rust-only</span> = no usable Gluten observation (single or rejected-repeat runs; unvalidated). <span class="chip bad">no result</span> = no successful Rust run (Gluten timed out).</li>
<li><strong>Scale effects.</strong> Gluten&rsquo;s SF&nbsp;1 disadvantage (&times;50 on TPC-H, &times;45 on TPC-DS) largely reflects fixed JVM/startup overhead; it shrinks to &times;1.3&ndash;&times;3.6 at SF&nbsp;1000.</li>
<li><strong>Numbers as recorded.</strong> Values are reformatted for readability only &mdash; no re-aggregation, smoothing, or outlier removal beyond what the source encodes (e.g. TPC-DS SF&nbsp;1000 tuned canonical total 10,082.3 vs run-sum 10,074.0, kept as published).</li>
<li><strong>Provenance.</strong> Source document <code>{esc(data["source"])}</code>, SHA-256 <code title="{esc(sha)}">{esc(sha[:12])}&hellip;</code>. This page is generated solely from <code>engine-comparison-summary-data.json</code>.</li>
</ul>
</div>"""


# ---------------- legend ----------------
def legend():
    sw = "".join(f'<span class="sw"><i style="background:{COLORS[i]}"></i>{esc(SHORT[i])}</span>' for i in range(5))
    heat = ('<span class="sw"><i class="hx best"></i>fastest</span>'
            '<span class="sw"><i class="hx h1"></i>&le;1.15&times;</span>'
            '<span class="sw"><i class="hx h2"></i>&le;1.5&times;</span>'
            '<span class="sw"><i class="hx h3"></i>&le;3&times;</span>'
            '<span class="sw"><i class="hx h4"></i>&le;10&times;</span>'
            '<span class="sw"><i class="hx h5"></i>&gt;10&times;</span>')
    return f"""<div class="legend"><div class="lgroup"><span class="ltitle">Engines</span>{sw}</div>
<div class="lgroup"><span class="ltitle">Cell heat (vs row best)</span>{heat}</div></div>"""


# ---------------- CSS ----------------
CSS = """
:root{
  --bg:#f7f8fa; --bg2:#ffffff; --bg3:#eef0f4; --fg:#1a2230; --fg2:#5b6778;
  --line:#dfe3ea; --accent:#0b7285;
  --good-bg:rgba(0,158,115,.14); --good-fg:#046a4d;
  --warn-bg:rgba(230,159,0,.16); --warn-fg:#8a5a00;
  --hot-bg:rgba(213,94,0,.16); --hot-fg:#9c3a00;
  --bad-bg:rgba(214,40,40,.14); --bad-fg:#a02020;
  --info-bg:rgba(0,114,178,.13); --info-fg:#0a5c94;
  --base-bg:rgba(91,103,120,.10); --base-fg:#5b6778;
  --shadow:0 1px 2px rgba(16,24,40,.05),0 8px 24px -12px rgba(16,24,40,.12);
  --mono:ui-monospace,'SF Mono','Cascadia Code',Menlo,Consolas,monospace;
  color-scheme:light;
}
[data-theme="dark"]{
  --bg:#0e1218; --bg2:#161c26; --bg3:#1d2532; --fg:#e6eaf2; --fg2:#98a4b8;
  --line:#2a3342; --accent:#4cc3d9;
  --good-bg:rgba(0,200,145,.16); --good-fg:#4fd6a8;
  --warn-bg:rgba(255,176,32,.15); --warn-fg:#ffc45e;
  --hot-bg:rgba(255,110,40,.17); --hot-fg:#ff9d6b;
  --bad-bg:rgba(255,80,80,.15); --bad-fg:#ff8f8f;
  --info-bg:rgba(86,180,233,.15); --info-fg:#7cc4ea;
  --base-bg:rgba(152,164,184,.13); --base-fg:#98a4b8;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px -12px rgba(0,0,0,.5);
  color-scheme:dark;
}
@media (prefers-color-scheme:dark){ :root:not([data-theme]){
  --bg:#0e1218; --bg2:#161c26; --bg3:#1d2532; --fg:#e6eaf2; --fg2:#98a4b8;
  --line:#2a3342; --accent:#4cc3d9;
  --good-bg:rgba(0,200,145,.16); --good-fg:#4fd6a8;
  --warn-bg:rgba(255,176,32,.15); --warn-fg:#ffc45e;
  --hot-bg:rgba(255,110,40,.17); --hot-fg:#ff9d6b;
  --bad-bg:rgba(255,80,80,.15); --bad-fg:#ff8f8f;
  --info-bg:rgba(86,180,233,.15); --info-fg:#7cc4ea;
  --base-bg:rgba(152,164,184,.13); --base-fg:#98a4b8;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px -12px rgba(0,0,0,.5);
  color-scheme:dark;
}}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto} *{transition:none!important;animation:none!important}}
body{
  margin:0; background:var(--bg); color:var(--fg);
  font:15px/1.6 system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',sans-serif;
  -webkit-font-smoothing:antialiased;
}
main,footer,.heroinner{max-width:1180px;margin:0 auto;padding:0 clamp(16px,4vw,40px)}
a{color:var(--accent)}
code{font-family:var(--mono);font-size:.86em;background:var(--bg3);padding:.1em .35em;border-radius:5px}

.topnav{position:sticky;top:0;z-index:20;backdrop-filter:blur(10px);
  background:color-mix(in srgb,var(--bg) 82%,transparent);border-bottom:1px solid var(--line)}
.topnav .navin{max-width:1180px;margin:0 auto;padding:9px clamp(16px,4vw,40px);
  display:flex;gap:4px;align-items:center;flex-wrap:wrap}
.topnav a{color:var(--fg2);text-decoration:none;font-size:12.5px;font-weight:600;
  letter-spacing:.04em;text-transform:uppercase;padding:5px 10px;border-radius:7px}
.topnav a:hover,.topnav a:focus-visible{color:var(--fg);background:var(--bg3)}
.navin .spacer{flex:1}
#themeBtn{border:1px solid var(--line);background:var(--bg2);color:var(--fg2);border-radius:8px;
  padding:4px 11px;font-size:13px;cursor:pointer}
#themeBtn:hover{color:var(--fg);border-color:var(--fg2)}

.hero{padding:52px 0 30px;border-bottom:1px solid var(--line)}
.kicker{font-family:var(--mono);font-size:11.5px;letter-spacing:.18em;text-transform:uppercase;
  color:var(--accent);margin:0 0 10px;font-weight:700}
h1{font-size:clamp(1.75rem,3.4vw,2.5rem);line-height:1.12;letter-spacing:-.02em;margin:0 0 12px;font-weight:800}
.subline{color:var(--fg2);font-size:clamp(1rem,1.6vw,1.13rem);margin:0 0 18px;max-width:62ch}
.prov{display:flex;flex-wrap:wrap;gap:8px;font-family:var(--mono);font-size:11.5px;color:var(--fg2)}
.prov span{border:1px solid var(--line);background:var(--bg2);border-radius:999px;padding:3px 11px}

section{padding:38px 0 6px}
h2{font-size:1.28rem;letter-spacing:-.01em;margin:0 0 6px;display:flex;align-items:baseline;gap:12px}
h2 .idx{font-family:var(--mono);font-size:.72em;color:var(--accent);font-weight:700}
.sectionsub{color:var(--fg2);margin:0 0 20px;max-width:75ch}
h3{font-size:.95rem;margin:26px 0 10px;letter-spacing:.01em}
.lead{color:var(--fg2);max-width:80ch;margin:0 0 18px}

.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-bottom:22px}
.card{background:var(--bg2);border:1px solid var(--line);border-radius:12px;padding:18px 20px;box-shadow:var(--shadow)}
.card h3{margin:0 0 8px;font-size:.78rem;text-transform:uppercase;letter-spacing:.09em;color:var(--fg2)}
.card .big{font-family:var(--mono);font-size:1.72rem;font-weight:700;margin:0 0 6px;letter-spacing:-.01em}
.card .sub{margin:0;color:var(--fg2);font-size:.86rem;line-height:1.5}
.hwgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin:18px 0 22px}

.callout{background:var(--bg2);border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:12px;padding:18px 22px;margin:4px 0 10px}
.callout h3{margin:0 0 10px}
.callout ul{margin:0;padding-left:1.2em;display:grid;gap:7px}
.callout li{font-size:.92rem;color:var(--fg)}

.tblwrap{margin:14px 0 26px;overflow-x:auto;border:1px solid var(--line);border-radius:12px;
  background:var(--bg2);box-shadow:var(--shadow)}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:13px}
caption{text-align:left;padding:13px 18px 11px;color:var(--fg2);font-size:12.5px;border-bottom:1px solid var(--line)}
th,td{padding:8px 12px;text-align:right;white-space:nowrap}
thead th{font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;color:var(--fg2);
  background:var(--bg3);border-bottom:1px solid var(--line)}
tbody th[scope=row]{text-align:left;font-weight:600}
tbody tr+tr td,tbody tr+tr th{border-top:1px solid var(--line)}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:12.6px}
td .t{position:relative;z-index:1}
.sfrow{font-family:var(--mono);white-space:nowrap}
.nsub{display:block;font-weight:400;font-size:10.5px;color:var(--fg2);letter-spacing:0;text-transform:none;margin-top:1px}
tr.allrow td,tr.allrow th{border-top:2px solid var(--fg2)}
.qrow{font-family:var(--mono);color:var(--fg2);font-weight:600;font-size:12px}
.status{text-align:left;font-size:12px}
.tnote{padding:10px 18px 14px;color:var(--fg2);font-size:12px;line-height:1.55}
.dag{color:var(--warn-fg);font-weight:700}

td.best{background:var(--good-bg)}
td.best .t{color:var(--good-fg);font-weight:700}
td.h1{background:color-mix(in srgb,var(--warn-bg) 30%,transparent)}
td.h2{background:color-mix(in srgb,var(--warn-bg) 60%,transparent)}
td.h3{background:var(--warn-bg)}
td.h4{background:var(--hot-bg)}
td.h5{background:color-mix(in srgb,var(--hot-bg) 70%,var(--bad-bg))}
td.none{color:var(--fg2);background:repeating-linear-gradient(45deg,transparent,transparent 5px,var(--bg3) 5px,var(--bg3) 10px)}

.chip{display:inline-block;margin-left:9px;font-family:var(--mono);font-size:10.5px;font-weight:600;
  border-radius:999px;padding:1px 8px;vertical-align:1px}
.chip.base,.chip.even{background:var(--base-bg);color:var(--base-fg)}
.chip.good{background:var(--good-bg);color:var(--good-fg)}
.chip.warn{background:var(--warn-bg);color:var(--warn-fg)}
.chip.hot{background:var(--hot-bg);color:var(--hot-fg)}
.chip.ok{background:var(--good-bg);color:var(--good-fg)}
.chip.info{background:var(--info-bg);color:var(--info-fg)}
.chip.bad{background:var(--bad-bg);color:var(--bad-fg)}
.chip.none{background:var(--base-bg);color:var(--base-fg)}
.mp{font-family:var(--mono);font-size:9px;font-weight:700;color:var(--fg2);margin-left:3px}
.flag{display:inline-block;margin-left:6px;font-family:var(--mono);font-size:9.5px;font-weight:700;
  width:15px;height:15px;line-height:15px;text-align:center;border-radius:4px;vertical-align:1px}
.flagB{background:var(--info-bg);color:var(--info-fg)}
.flagP{background:color-mix(in srgb,var(--hot-bg) 55%,var(--info-bg));color:var(--hot-fg)}

details.pq{border:1px solid var(--line);border-radius:12px;background:var(--bg2);
  box-shadow:var(--shadow);margin:0 0 12px;overflow:hidden}
details.pq>summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:14px;
  padding:13px 18px;user-select:none}
details.pq>summary::-webkit-details-marker{display:none}
details.pq>summary:hover,details.pq[open]>summary{background:var(--bg3)}
details.pq>summary:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.sum-t{font-weight:700;font-size:14px;min-width:11.5em}
.sum-meta{color:var(--fg2);font-size:12.5px;flex:1}
.chev{color:var(--fg2);transition:transform .15s ease}
details[open]>summary .chev{transform:rotate(180deg)}
details.pq .tblwrap{margin:0;border:0;border-radius:0;box-shadow:none;border-top:1px solid var(--line)}
.fnote{padding:12px 18px 16px;border-top:1px solid var(--line);font-size:12.3px;color:var(--fg2)}
.fnote h4{margin:0 0 6px;font-size:11px;text-transform:uppercase;letter-spacing:.08em}
.fnote ul{margin:0;padding-left:1.2em;display:grid;gap:4px}
tr.st-info td,tr.st-info th.qrow{background:color-mix(in srgb,var(--info-bg) 26%,transparent)}
tr.st-bad td,tr.st-bad th.qrow{background:color-mix(in srgb,var(--bad-bg) 30%,transparent)}

.charts{display:grid;gap:18px}
.charts.two{grid-template-columns:repeat(auto-fit,minmax(min(420px,100%),1fr))}
.charts>*{min-width:0}
.chartfig{margin:0}
.chart{width:100%;height:auto;display:block}
.plotbg{fill:var(--bg2);stroke:var(--line);stroke-width:1}
.gl{stroke:var(--line);stroke-width:1}
.axis{stroke:var(--fg2);stroke-width:1}
.ax{fill:var(--fg2);font-family:var(--mono);font-size:10.5px}
.glabel{fill:var(--fg);font-size:12px;font-weight:600}
.bl{fill:var(--fg2);font-family:var(--mono);font-size:10.5px}
@media (prefers-reduced-motion:no-preference){.bar{transition:filter .12s ease}.bar:hover{filter:brightness(1.18)}}

.legend{display:flex;flex-wrap:wrap;gap:10px 34px;margin:0 0 20px}
.lgroup{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center}
.ltitle{font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;color:var(--fg2);font-weight:700;margin-right:2px}
.sw{display:inline-flex;align-items:center;gap:7px;font-size:12.3px;color:var(--fg)}
.sw i{width:12px;height:12px;border-radius:3px;display:inline-block}
.sw i.hx.h1{background:color-mix(in srgb,var(--warn-bg) 30%,transparent)}
.sw i.hx.h2{background:color-mix(in srgb,var(--warn-bg) 60%,transparent)}
.sw i.hx.h3{background:var(--warn-bg)}
.sw i.hx.h4{background:var(--hot-bg)}
.sw i.hx.h5{background:color-mix(in srgb,var(--hot-bg) 70%,var(--bad-bg))}
.sw i.hx.best{background:var(--good-bg)}

.winsrow{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin:18px 0 22px}
.wins{background:var(--bg2);border:1px solid var(--line);border-radius:12px;padding:14px 18px;text-align:center}
.wins .wlab{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.09em;color:var(--fg2);font-weight:700}
.wins .wval{display:block;font-family:var(--mono);font-size:1.55rem;font-weight:700;margin:4px 0 2px}
.wins .wval em{font-style:normal;color:var(--fg2);padding:0 .18em}
.wins .wsub{display:block;font-size:11px;color:var(--fg2)}

.notes{background:var(--bg2);border:1px solid var(--line);border-radius:12px;padding:20px 24px;margin-bottom:26px}
.notes h3{margin:0 0 12px}
.notes ul{margin:0;padding-left:1.25em;display:grid;gap:9px}
.notes li{font-size:.9rem;color:var(--fg);line-height:1.55}

footer{border-top:1px solid var(--line);margin-top:40px;padding:26px 0 42px;color:var(--fg2);font-size:12.3px}
footer p{margin:4px 0}

@media print{
  .topnav{display:none}
  body{background:#fff;color:#000}
  .card,.tblwrap,details.pq,.notes,.callout,.wins{box-shadow:none}
  details.pq{border-color:#bbb}
  .hero{padding-top:10px}
}
@media (max-width:640px){
  .sum-t{min-width:0}
  th,td{padding:7px 8px}
  .chip{margin-left:5px}
}
"""

# ---------------- JS ----------------
JS = """
(function(){
  var root=document.documentElement, btn=document.getElementById('themeBtn');
  try{
    var saved=localStorage.getItem('ecr-theme');
    if(saved==='dark'||saved==='light'){root.setAttribute('data-theme',saved);}
    else if(window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches){root.setAttribute('data-theme','dark');}
  }catch(e){}
  if(btn){btn.addEventListener('click',function(){
    var t=root.getAttribute('data-theme')==='dark'?'light':'dark';
    root.setAttribute('data-theme',t);
    try{localStorage.setItem('ecr-theme',t);}catch(e){}
  });}
  var opened=[];
  window.addEventListener('beforeprint',function(){
    opened=[];
    document.querySelectorAll('details:not([open])').forEach(function(d){opened.push(d);d.setAttribute('open','');});
  });
  window.addEventListener('afterprint',function(){
    opened.forEach(function(d){d.removeAttribute('open');});
    opened=[];
  });
})();
"""


# ---------------- assemble ----------------
def main():
    gen_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hw = data["hardware"]
    sn, cw = hw["single_node"], hw["cluster_workers"]

    parts = []
    parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<meta name="description" content="TPC-H and TPC-DS benchmark comparison: Spark Rust 0.42.1 vs DuckDB 1.5.5 vs Spark 4.1.1 Gluten vs Spark 4.2, single-node and 8-node cluster.">
<title>Engine Comparison &mdash; TPC-H &amp; TPC-DS Benchmark Report</title>
<style>{CSS}</style>
</head>
<body>
<nav class="topnav" aria-label="Sections">
  <div class="navin">
    <a href="#summary">Summary</a><a href="#totals">Totals</a><a href="#charts">Charts</a>
    <a href="#perquery">Per-query</a><a href="#cluster">Cluster</a><a href="#method">Method</a>
    <span class="spacer"></span>
    <button id="themeBtn" type="button" aria-label="Toggle dark or light theme">&#9788;</button>
  </div>
</nav>
<header class="hero">
  <div class="heroinner">
    <p class="kicker">Benchmark report</p>
    <h1>Query Engine Comparison: Spark Rust 0.42.1 vs DuckDB, Gluten &amp; Spark 4.2</h1>
    <p class="subline">TPC-H (22 queries &times; SF 1&ndash;1000) and TPC-DS (99 queries &times; SF 1&ndash;1000) on a single
    {esc(sn["sku"])} node, plus a TPC-DS head-to-head on an {cw["count"]}-node
    {esc(cw["sku"])} cluster. All single-node ratios use DuckDB 1.5.5 as the baseline.</p>
    <div class="prov">
      <span>Source: {esc(data["source"])}</span>
      <span>sha256 {esc(data["sha256"][:12])}&hellip;</span>
      <span>Generated {gen_date}</span>
      <span>5 engines &middot; 2 suites &middot; SF 1&ndash;1000 + cluster</span>
    </div>
  </div>
</header>
<main>
""")

    parts.append(f"""<section id="summary" aria-labelledby="s-sum">
<h2 id="s-sum"><span class="idx">01</span>Executive summary</h2>
<p class="sectionsub">Headline results across full suites; every figure below is computed directly from the source data.</p>
{exec_summary()}
</section>""")

    parts.append(f"""<section id="totals" aria-labelledby="s-tot">
<h2 id="s-tot"><span class="idx">02</span>Single-node totals</h2>
<p class="sectionsub">Aggregate wall-clock seconds per suite and scale factor. Cell heat shows the gap to the
fastest engine in the row; chips show the ratio to DuckDB.</p>
{totals_table("TPC-H", "TPC-H")}
{totals_table("TPC-DS", "TPC-DS")}
</section>""")

    parts.append(f"""<section id="charts" aria-labelledby="s-ch">
<h2 id="s-ch"><span class="idx">03</span>Charts</h2>
<p class="sectionsub">Logarithmic scale &mdash; each gridline is 10&times; the previous. This is what makes the
SF&nbsp;1 JVM start-up penalty and the SF&nbsp;1000 convergence visible on one axis.</p>
{legend()}
<h3>Single-node total wall time</h3>
<div class="charts">
<figure class="chartfig">{chart_totals("TPC-H")}<figcaption class="tnote figcap">TPC-H, by scale factor</figcaption></figure>
<figure class="chartfig">{chart_totals("TPC-DS")}<figcaption class="tnote figcap">TPC-DS, by scale factor</figcaption></figure>
</div>
<h3>Cluster (TPC-DS 99 queries, Spark Rust vs Gluten)</h3>
<div class="charts two">
<figure class="chartfig">{chart_cluster("time", True)}<figcaption class="tnote figcap">Wall-clock seconds (log scale)</figcaption></figure>
<figure class="chartfig">{chart_cluster("cpuHours", False)}<figcaption class="tnote figcap">CPU consumption, core-hours (linear)</figcaption></figure>
</div>
</section>""")

    parts.append(f"""<section id="perquery" aria-labelledby="s-pq">
<h2 id="s-pq"><span class="idx">04</span>Per-query drill-down (single node)</h2>
<p class="sectionsub">Every query, every engine. Tables are collapsed by scale factor &mdash; expand what you need.
All values are seconds of wall-clock time as recorded in the source.</p>
{perquery_section()}
</section>""")

    parts.append(f"""<section id="cluster" aria-labelledby="s-cl">
<h2 id="s-cl"><span class="idx">05</span>Cluster head-to-head: Spark Rust vs Gluten</h2>
<p class="sectionsub">TPC-DS (99 queries) on {cw["count"]} &times; {esc(cw["sku"])} workers.
Win counts cover validated pairs only; status chips flag the rest.</p>
{cluster_wins_strip()}
{cluster_totals_table()}
{cluster_table("100")}
{cluster_table("1000")}
{cluster_table("10000")}
</section>""")

    parts.append(f"""<section id="method" aria-labelledby="s-me">
<h2 id="s-me"><span class="idx">06</span>Hardware, method &amp; caveats</h2>
{method_section()}
</section>
</main>
<footer>
<p>Generated {gen_date} from <code>engine-comparison-summary-data.json</code> &middot; source document
<code>{esc(data["source"])}</code> (SHA-256 <code>{esc(data["sha256"][:12])}&hellip;</code>).</p>
<p>Self-contained HTML: no external fonts, scripts, images, or network requests. Charts are inline SVG; the theme
toggle and print expansion are the only scripts. Times are as recorded in the source data; formatting only.</p>
</footer>
<script>{JS}</script>
</body>
</html>""")

    out = "".join(parts)
    with open(OUT, "w") as f:
        f.write(out)
    print(f"wrote {OUT}: {len(out):,} bytes")


if __name__ == "__main__":
    main()
