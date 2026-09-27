#!/usr/bin/env python3
"""Generate a professional self-contained HTML report from engine-comparison-summary-data.json."""

import json

with open('engine-comparison-summary-data.json') as f:
    data = json.load(f)

# Engine colors (consistent, accessible palette)
engine_colors = {
    "Spark Rust 0.42.1 (default)": "#0d9488",
    "Spark Rust 0.42.1 (tuned)": "#14b8a6",
    "DuckDB 1.5.5": "#6366f1",
    "Spark 4.1.1 Gluten": "#f59e0b",
    "Spark 4.2": "#ef4444",
}
engine_colors_cluster = {
    "Spark Rust 0.42.1": "#0d9488",
    "Spark 4.1.1 Gluten": "#f59e0b",
}


def fmt_time(seconds):
    if seconds >= 3600:
        return f"{seconds/3600:.2f} h"
    elif seconds >= 60:
        return f"{seconds/60:.2f} min"
    else:
        return f"{seconds:.3f} s"


def fmt_time_short(seconds):
    if seconds >= 3600:
        return f"{seconds/3600:.1f}h"
    elif seconds >= 60:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds:.1f}s"


def build_totals_chart(bench_key):
    totals = data['totals'][bench_key]
    sfs = ['1', '10', '100', '1000']
    engines = data['engines']

    all_times = [t['time'] for t in totals if t['sf'] != 'all']
    max_time = max(all_times)

    chart_w = 900
    chart_h = 340
    margin_left = 120
    margin_right = 20
    margin_top = 20
    margin_bottom = 60
    plot_w = chart_w - margin_left - margin_right
    plot_h = chart_h - margin_top - margin_bottom

    group_w = plot_w / len(sfs)
    bar_w = min(28, group_w / (len(engines) + 1))

    svg = f'<svg class="chart-svg" viewBox="0 0 {chart_w} {chart_h}" preserveAspectRatio="xMidYMid meet">'

    # Grid lines
    for i in range(5):
        y = margin_top + plot_h * i / 4
        val = max_time * (1 - i / 4)
        svg += f'<line x1="{margin_left}" y1="{y}" x2="{chart_w - margin_right}" y2="{y}" stroke="var(--border)" stroke-width="0.5"/>'
        svg += f'<text x="{margin_left - 8}" y="{y + 4}" text-anchor="end" fill="var(--text-subtle)" font-size="10" font-family="monospace">{fmt_time_short(val)}</text>'

    # Bars
    for si, sf in enumerate(sfs):
        group_x = margin_left + si * group_w + group_w / 2
        sf_data = [t for t in totals if t['sf'] == sf]

        for ei, engine in enumerate(engines):
            ed = next((t for t in sf_data if t['engine'] == engine), None)
            if not ed:
                continue
            bar_h = (ed['time'] / max_time) * plot_h
            bar_x = group_x - (len(engines) * bar_w + (len(engines) - 1) * 3) / 2 + ei * (bar_w + 3)
            bar_y = margin_top + plot_h - bar_h
            color = engine_colors.get(engine, '#888')

            svg += f'<rect x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{color}" rx="2" ry="2">'
            svg += f'<title>{engine} · SF={sf} · {fmt_time(ed["time"])}</title>'
            svg += '</rect>'

        svg += f'<text x="{group_x}" y="{chart_h - margin_bottom + 20}" text-anchor="middle" fill="var(--text-muted)" font-size="12" font-weight="600">SF={sf}</text>'

    svg += '</svg>'
    return svg


def build_query_heatmap(bench, sf):
    queries = data['single'][bench][sf]
    engines = data['engines']
    n_queries = len(queries)

    chart_w = 900
    row_h = 28
    col_w = min(8, 800 / n_queries)
    margin_left = 180
    margin_top = 40
    chart_h = margin_top + len(engines) * row_h + 30

    svg = f'<svg class="chart-svg" viewBox="0 0 {chart_w} {chart_h}" preserveAspectRatio="xMidYMid meet">'

    # Query number labels (every 5th)
    for qi in range(0, n_queries, 5):
        x = margin_left + qi * col_w + col_w / 2
        qnum = queries[qi]['q']
        svg += f'<text x="{x:.1f}" y="{margin_top - 8}" text-anchor="middle" fill="var(--text-subtle)" font-size="9" font-family="monospace">{qnum}</text>'

    # Engine labels + heatmap cells
    for ei, eng in enumerate(engines):
        y = margin_top + ei * row_h
        svg += f'<text x="{margin_left - 10}" y="{y + row_h/2 + 4}" text-anchor="end" fill="var(--text-muted)" font-size="11">{eng}</text>'

        for qi in range(n_queries):
            t = queries[qi]['times'][ei]
            min_t = min(queries[qi]['times'])
            ratio = t / min_t if min_t > 0 else 1

            # Intensity: 0.3 at ratio=1, up to 1.0 at ratio=5+
            intensity = 0.3 + 0.7 * min(1, (ratio - 1) / 4)

            base_color = engine_colors.get(eng, '#888')

            x = margin_left + qi * col_w
            svg += f'<rect x="{x:.1f}" y="{y}" width="{col_w - 1:.1f}" height="{row_h - 2}" fill="{base_color}" opacity="{intensity:.2f}" rx="1">'
            svg += f'<title>Q{queries[qi]["q"]} · {eng} · {t:.3f}s · {ratio:.2f}×</title>'
            svg += '</rect>'

    svg += '</svg>'
    return svg


def build_cluster_query_chart(sf):
    queries = data['clusterQueries'][sf]
    n = len(queries)
    chart_w = 900
    chart_h = 300
    margin_left = 60
    margin_right = 20
    margin_top = 20
    margin_bottom = 50
    plot_w = chart_w - margin_left - margin_right
    plot_h = chart_h - margin_top - margin_bottom

    max_ratio = max(q['ratio'] for q in queries if q['ratio'] is not None)
    max_ratio = min(max_ratio, 5)

    svg = f'<svg class="chart-svg" viewBox="0 0 {chart_w} {chart_h}" preserveAspectRatio="xMidYMid meet">'

    # Grid lines
    for i in range(6):
        y = margin_top + plot_h * i / 5
        val = max_ratio * (1 - i / 5)
        svg += f'<line x1="{margin_left}" y1="{y}" x2="{chart_w - margin_right}" y2="{y}" stroke="var(--border)" stroke-width="0.5"/>'
        svg += f'<text x="{margin_left - 8}" y="{y + 4}" text-anchor="end" fill="var(--text-subtle)" font-size="10" font-family="monospace">{val:.1f}×</text>'

    # Parity line
    y_parity = margin_top + plot_h * (1 - 1 / max_ratio)
    svg += f'<line x1="{margin_left}" y1="{y_parity}" x2="{chart_w - margin_right}" y2="{y_parity}" stroke="var(--text-subtle)" stroke-width="1" stroke-dasharray="4,4"/>'
    svg += f'<text x="{chart_w - margin_right - 4}" y="{y_parity - 4}" text-anchor="end" fill="var(--text-subtle)" font-size="10">parity</text>'

    # Bars
    bar_w = plot_w / n * 0.7
    for qi, q in enumerate(queries):
        x = margin_left + qi * (plot_w / n) + (plot_w / n - bar_w) / 2
        ratio = q['ratio'] if q['ratio'] is not None else 0
        ratio_capped = min(ratio, max_ratio)

        y_val = margin_top + plot_h * (1 - ratio_capped / max_ratio)

        if ratio_capped < 1:
            bar_h_val = y_parity - y_val
            bar_y = y_val
        else:
            bar_h_val = y_val - y_parity
            bar_y = y_parity

        color = '#0d9488' if ratio <= 1 else '#f59e0b'

        svg += f'<rect x="{x:.1f}" y="{bar_y:.1f}" width="{bar_w:.1f}" height="{bar_h_val:.1f}" fill="{color}" opacity="0.75" rx="1">'
        svg += f'<title>Q{q["q"]} · ratio={ratio:.3f}× · Rust={q["r"]:.2f}s · Gluten={q["g"]:.2f}s</title>'
        svg += '</rect>'

    # X-axis labels
    for qi in range(0, n, 10):
        x = margin_left + qi * (plot_w / n) + (plot_w / n) / 2
        svg += f'<text x="{x:.1f}" y="{chart_h - margin_bottom + 20}" text-anchor="middle" fill="var(--text-subtle)" font-size="10" font-family="monospace">Q{queries[qi]["q"]}</text>'

    svg += f'<text x="{chart_w/2}" y="{chart_h - 8}" text-anchor="middle" fill="var(--text-muted)" font-size="11">Query</text>'
    svg += f'<text x="15" y="{chart_h/2}" text-anchor="middle" fill="var(--text-muted)" font-size="11" transform="rotate(-90 15 {chart_h/2})">Rust / Gluten ratio</text>'

    svg += '</svg>'
    return svg


def build_totals_table(bench_key):
    rows = []
    for sf in ['1', '10', '100', '1000', 'all']:
        sf_data = sorted(
            [t for t in data['totals'][bench_key] if t['sf'] == sf],
            key=lambda x: x['time']
        )
        if not sf_data:
            continue
        worst_time = sf_data[-1]['time']
        for i, row in enumerate(sf_data):
            sf_label = f"SF={sf}" if i == 0 else ""
            ratio = row['ratio']
            if ratio == 1:
                ratio_html = '<span class="badge badge-good">1.00×</span>'
            elif ratio < 1.5:
                ratio_html = f'<span class="badge badge-info">{ratio:.3f}×</span>'
            elif ratio < 5:
                ratio_html = f'<span class="badge badge-warn">{ratio:.2f}×</span>'
            else:
                ratio_html = f'<span class="badge badge-bad">{ratio:.1f}×</span>'

            bar_pct = row['time'] / worst_time * 100
            color = engine_colors.get(row['engine'], '#888')
            bar_html = f'<div class="bar-bg"><div class="bar-fill" style="width:{bar_pct:.1f}%;background:{color}"></div></div>'

            rows.append(
                f'<tr>'
                f'<td>{sf_label}</td>'
                f'<td>{row["engine"]}</td>'
                f'<td class="num">{row["n"]}</td>'
                f'<td class="num">{fmt_time(row["time"])}</td>'
                f'<td class="num">{ratio_html}</td>'
                f'<td class="bar-cell">{bar_html}</td>'
                f'</tr>'
            )
    return '\n'.join(rows)


# ---- Build HTML ----
parts = []

parts.append('''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Query Engine Performance Comparison</title>
<style>
:root {
  --bg: #f8fafc;
  --surface: #ffffff;
  --surface-alt: #f1f5f9;
  --border: #e2e8f0;
  --text: #0f172a;
  --text-muted: #64748b;
  --text-subtle: #94a3b8;
  --accent: #0d9488;
  --accent-soft: #ccfbf1;
  --warn: #f59e0b;
  --warn-soft: #fef3c7;
  --danger: #ef4444;
  --danger-soft: #fee2e2;
  --good: #10b981;
  --good-soft: #d1fae5;
  --indigo: #6366f1;
  --indigo-soft: #e0e7ff;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
  --radius: 8px;
  --radius-lg: 12px;
  --font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: "SF Mono", "JetBrains Mono", "Fira Code", Consolas, monospace;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f172a;
    --surface: #1e293b;
    --surface-alt: #334155;
    --border: #475569;
    --text: #f1f5f9;
    --text-muted: #94a3b8;
    --text-subtle: #64748b;
    --accent-soft: #134e4a;
    --warn-soft: #451a03;
    --danger-soft: #450a0a;
    --good-soft: #064e3b;
    --indigo-soft: #1e1b4b;
  }
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font-sans);
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  font-size: 14px;
  -webkit-font-smoothing: antialiased;
}

.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px 24px;
}

.header {
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border);
}
.header h1 {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 8px;
}
.header .subtitle {
  color: var(--text-muted);
  font-size: 15px;
}
.header .meta {
  margin-top: 12px;
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--text-subtle);
  font-family: var(--font-mono);
}

.section { margin-bottom: 48px; }
.section-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
  letter-spacing: -0.01em;
}
.section-subtitle {
  font-size: 15px;
  font-weight: 600;
  margin: 24px 0 12px;
  color: var(--text);
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}
.card .label {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
}
.card .value {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.card .detail {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
th, td {
  padding: 10px 14px;
  text-align: left;
  border-bottom: 1px solid var(--border);
}
th {
  background: var(--surface-alt);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  white-space: nowrap;
}
tr:last-child td { border-bottom: none; }
tr:hover td { background: var(--surface-alt); }
td.num { text-align: right; font-variant-numeric: tabular-nums; font-family: var(--font-mono); }

.bar-cell { min-width: 200px; }
.bar-bg {
  height: 20px;
  background: var(--surface-alt);
  border-radius: 4px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.chart-container {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: var(--shadow-sm);
}
.chart-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 16px;
}
.chart-svg { width: 100%; height: auto; }

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
}
.legend-swatch {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border);
}
.tab {
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all 0.15s;
  user-select: none;
}
.tab:hover { color: var(--text); }
.tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}
.tab-panel { display: none; }
.tab-panel.active { display: block; }

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}
@media (max-width: 900px) {
  .two-col { grid-template-columns: 1fr; }
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-mono);
}
.badge-good { background: var(--good-soft); color: var(--good); }
.badge-bad { background: var(--danger-soft); color: var(--danger); }
.badge-warn { background: var(--warn-soft); color: var(--warn); }
.badge-info { background: var(--indigo-soft); color: var(--indigo); }

.hw-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}
.hw-item {
  background: var(--surface-alt);
  border-radius: var(--radius);
  padding: 12px 16px;
}
.hw-item .hw-label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.hw-item .hw-value {
  font-size: 15px;
  font-weight: 600;
  margin-top: 4px;
}

.findings {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  box-shadow: var(--shadow-sm);
}
.findings ul {
  margin-left: 20px;
  line-height: 1.9;
  color: var(--text-muted);
}
.findings li strong { color: var(--text); }

.footer {
  margin-top: 48px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
  font-size: 12px;
  color: var(--text-subtle);
  font-family: var(--font-mono);
}

@media (max-width: 768px) {
  .container { padding: 16px 12px; }
  .header h1 { font-size: 22px; }
  .cards { grid-template-columns: 1fr 1fr; }
}
</style>
</head>
<body>
<div class="container">
''')

# ---- Header ----
hw = data['hardware']
parts.append(f'''
<div class="header">
  <h1>Query Engine Performance Comparison</h1>
  <div class="subtitle">TPC-H &amp; TPC-DS benchmark results across 5 engines at 4 scale factors</div>
  <div class="meta">
    <span>Source: {data['source']}</span>
    <span>Single-node: {hw['single_node']['sku']} · {hw['single_node']['cores']}c · {hw['single_node']['ram_gb']}GB</span>
    <span>Cluster: {hw['cluster_workers']['count']}× {hw['cluster_workers']['sku']} · {hw['cluster_workers']['total_cores']}c · {hw['cluster_workers']['total_ram_gb']}GB</span>
  </div>
</div>
''')

# ---- Executive Summary ----
parts.append('<div class="section"><div class="section-title">Executive Summary</div>')

tpch_all = [t for t in data['totals']['TPC-H'] if t['sf'] == 'all']
tpds_all = [t for t in data['totals']['TPC-DS'] if t['sf'] == 'all']
tpch_best = min(tpch_all, key=lambda x: x['time'])
tpch_worst = max(tpch_all, key=lambda x: x['time'])
tpds_best = min(tpds_all, key=lambda x: x['time'])
tpds_worst = max(tpds_all, key=lambda x: x['time'])

parts.append(f'''
<div class="cards">
  <div class="card">
    <div class="label">Engines Compared</div>
    <div class="value">{len(data['engines'])}</div>
    <div class="detail">Single-node benchmarks</div>
  </div>
  <div class="card">
    <div class="label">TPC-H Best (all SF)</div>
    <div class="value" style="color: var(--good)">{tpch_best['engine'].split(' (')[0]}</div>
    <div class="detail">{fmt_time(tpch_best['time'])} total · {tpch_best['n']} queries</div>
  </div>
  <div class="card">
    <div class="label">TPC-DS Best (all SF)</div>
    <div class="value" style="color: var(--good)">{tpds_best['engine'].split(' (')[0]}</div>
    <div class="detail">{fmt_time(tpds_best['time'])} total · {tpds_best['n']} queries</div>
  </div>
  <div class="card">
    <div class="label">TPC-H Speed Range</div>
    <div class="value">{tpch_worst['ratio']:.1f}×</div>
    <div class="detail">fastest to slowest ratio</div>
  </div>
</div>
''')

# Key findings
tpch_sf1 = [t for t in data['totals']['TPC-H'] if t['sf'] == '1']
tpch_sf1000 = [t for t in data['totals']['TPC-H'] if t['sf'] == '1000']
tpds_sf1 = [t for t in data['totals']['TPC-DS'] if t['sf'] == '1']
tpds_sf1000 = [t for t in data['totals']['TPC-DS'] if t['sf'] == '1000']

duckdb_sf1_tpch = next(t for t in tpch_sf1 if 'DuckDB' in t['engine'])
sparkrust_sf1_tpch = next(t for t in tpch_sf1 if 'default' in t['engine'])
duckdb_sf1000_tpch = next(t for t in tpch_sf1000 if 'DuckDB' in t['engine'])
sparkrust_sf1000_tpch = next(t for t in tpch_sf1000 if 'default' in t['engine'])
sparkrust_tuned_sf1000_tpds = next(t for t in tpds_sf1000 if 'tuned' in t['engine'])
duckdb_sf1000_tpds = next(t for t in tpds_sf1000 if 'DuckDB' in t['engine'])
spark42_sf1_tpch = next(t for t in tpch_sf1 if t['engine'] == 'Spark 4.2')

cluster_100 = data['cluster']['100']
sr_cluster = next(c for c in cluster_100 if 'Spark Rust' in c['engine'])
gl_cluster = next(c for c in cluster_100 if 'Gluten' in c['engine'])

findings = [
    f"<strong>Small scales favor DuckDB.</strong> At SF=1 TPC-H, DuckDB finishes in {fmt_time(duckdb_sf1_tpch['time'])} — Spark Rust default is {sparkrust_sf1_tpch['ratio']:.2f}× slower, and Spark 4.2 is {spark42_sf1_tpch['ratio']:.0f}× slower (JVM overhead dominates).",
    f"<strong>Convergence at scale.</strong> At SF=1000 TPC-H, DuckDB and Spark Rust are nearly tied ({duckdb_sf1000_tpch['time']/60:.0f} vs {sparkrust_sf1000_tpch['time']/60:.0f} min, {sparkrust_sf1000_tpch['ratio']:.3f}× ratio).",
    f"<strong>Spark Rust leads TPC-DS at large scale.</strong> At SF=1000 TPC-DS, Spark Rust tuned is fastest at {fmt_time(sparkrust_tuned_sf1000_tpds['time'])}, beating DuckDB by {(1/sparkrust_tuned_sf1000_tpds['ratio'] - 1)*100:.1f}%.",
    f"<strong>Cluster: Spark Rust vs Gluten.</strong> At SF=100 on 8 workers, Spark Rust runs in {fmt_time(sr_cluster['time'])} vs Gluten {fmt_time(gl_cluster['time'])} — a {gl_cluster['time']/sr_cluster['time']:.2f}× advantage.",
    "<strong>Query-level variance is high.</strong> Some queries show 10–50× differences between engines, while others are within 10%. See per-query heatmaps below.",
]

parts.append('<div class="findings"><div class="section-subtitle" style="margin-top:0;">Key Findings</div><ul>')
for f in findings:
    parts.append(f'<li>{f}</li>')
parts.append('</ul></div></div>')

# ---- Single-Node Total Time ----
parts.append('<div class="section"><div class="section-title">Single-Node Total Time</div>')

parts.append('''
<div class="tabs" id="bench-tabs">
  <div class="tab active" data-tab="tpch">TPC-H</div>
  <div class="tab" data-tab="tpds">TPC-DS</div>
</div>
''')

# Legend HTML
def legend_html(engines_list, color_map):
    items = []
    for eng in engines_list:
        items.append(f'<div class="legend-item"><span class="legend-swatch" style="background:{color_map[eng]}"></span>{eng}</div>')
    return '<div class="legend">' + ''.join(items) + '</div>'

# TPC-H panel
parts.append('<div class="tab-panel active" id="panel-tpch">')
parts.append('<div class="chart-container">')
parts.append('<div class="chart-title">TPC-H Total Execution Time by Scale Factor</div>')
parts.append(legend_html(data['engines'], engine_colors))
parts.append(build_totals_chart('TPC-H'))
parts.append('</div>')

parts.append('<div class="section-subtitle">Detailed Results</div>')
parts.append('<div class="table-wrap"><table>')
parts.append('<thead><tr><th>Scale Factor</th><th>Engine</th><th class="num">Queries</th><th class="num">Total Time</th><th class="num">vs Best</th><th>Relative Speed</th></tr></thead><tbody>')
parts.append(build_totals_table('TPC-H'))
parts.append('</tbody></table></div>')
parts.append('</div>')

# TPC-DS panel
parts.append('<div class="tab-panel" id="panel-tpds">')
parts.append('<div class="chart-container">')
parts.append('<div class="chart-title">TPC-DS Total Execution Time by Scale Factor</div>')
parts.append(legend_html(data['engines'], engine_colors))
parts.append(build_totals_chart('TPC-DS'))
parts.append('</div>')

parts.append('<div class="section-subtitle">Detailed Results</div>')
parts.append('<div class="table-wrap"><table>')
parts.append('<thead><tr><th>Scale Factor</th><th>Engine</th><th class="num">Queries</th><th class="num">Total Time</th><th class="num">vs Best</th><th>Relative Speed</th></tr></thead><tbody>')
parts.append(build_totals_table('TPC-DS'))
parts.append('</tbody></table></div>')
parts.append('</div>')

parts.append('</div>')  # end section

# ---- Per-Query Heatmaps ----
parts.append('<div class="section"><div class="section-title">Per-Query Performance Heatmaps</div>')
parts.append('<p style="color: var(--text-muted); margin-bottom: 16px;">Each row is an engine, each column is a query. Color intensity = time relative to the fastest engine for that query (darker = slower). Hover for exact values.</p>')

parts.append('<div class="section-subtitle">TPC-H — SF=100</div>')
parts.append('<div class="chart-container">')
parts.append(build_query_heatmap('TPC-H', '100'))
parts.append('</div>')

parts.append('<div class="section-subtitle">TPC-DS — SF=100</div>')
parts.append('<div class="chart-container">')
parts.append(build_query_heatmap('TPC-DS', '100'))
parts.append('</div>')

parts.append('</div>')  # end per-query section

# ---- Cluster Results ----
parts.append('<div class="section"><div class="section-title">Cluster Results (TPC-DS)</div>')
parts.append('<p style="color: var(--text-muted); margin-bottom: 16px;">8-worker cluster comparing Spark Rust vs Spark 4.1.1 Gluten at three scale factors.</p>')

parts.append('<div class="cards">')
for sf in ['100', '1000', '10000']:
    cl = data['cluster'][sf]
    sr = next(c for c in cl if 'Spark Rust' in c['engine'])
    gl = next(c for c in cl if 'Gluten' in c['engine'])
    speedup = gl['time'] / sr['time']
    parts.append(f'''
  <div class="card">
    <div class="label">SF={sf} Speedup</div>
    <div class="value" style="color: var(--good)">{speedup:.2f}×</div>
    <div class="detail">Spark Rust faster than Gluten</div>
    <div class="detail" style="margin-top:8px;">
      <span style="color:var(--good);font-weight:600;">{fmt_time(sr['time'])}</span>
      <span style="color:var(--text-subtle)"> · </span>
      <span style="color:var(--warn)">{fmt_time(gl['time'])}</span>
    </div>
  </div>
''')
parts.append('</div>')

# Cluster detailed table
parts.append('<div class="section-subtitle">Detailed Cluster Results</div>')
parts.append('<div class="table-wrap"><table>')
parts.append('<thead><tr><th>SF</th><th>Engine</th><th class="num">Queries</th><th class="num">Wall Time</th><th class="num">CPU Time</th><th class="num">Avg Cores</th><th class="num">CPU Hours</th><th class="num">Mean</th><th class="num">p50</th><th class="num">p95</th><th class="num">Max</th></tr></thead><tbody>')

for sf in ['100', '1000', '10000']:
    for i, row in enumerate(data['cluster'][sf]):
        sf_label = sf if i == 0 else ''
        color = engine_colors_cluster.get(row['engine'], '#888')
        parts.append(
            f'<tr>'
            f'<td>{sf_label}</td>'
            f'<td><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:{color};margin-right:8px;"></span>{row["engine"]}</td>'
            f'<td class="num">{row["n"]}</td>'
            f'<td class="num">{fmt_time(row["time"])}</td>'
            f'<td class="num">{fmt_time(row["cpu"])}</td>'
            f'<td class="num">{row["cores"]:.1f}</td>'
            f'<td class="num">{row["cpuHours"]:.2f}</td>'
            f'<td class="num">{row["mean"]:.2f}s</td>'
            f'<td class="num">{row["p50"]:.2f}s</td>'
            f'<td class="num">{row["p95"]:.2f}s</td>'
            f'<td class="num">{row["max"]:.2f}s</td>'
            f'</tr>'
        )

parts.append('</tbody></table></div>')

# Query wins
parts.append('<div class="section-subtitle">Query Wins</div>')
parts.append('<div class="cards">')
for sf in ['100', '1000', '10000']:
    w = data['wins'][sf]
    total = w[0] + w[1]
    parts.append(f'''
  <div class="card">
    <div class="label">SF={sf} Query Wins</div>
    <div class="value" style="font-size:20px;">
      <span style="color:var(--good)">{w[0]}</span>
      <span style="color:var(--text-subtle);font-weight:400;font-size:14px;"> — </span>
      <span style="color:var(--warn)">{w[1]}</span>
    </div>
    <div class="detail">Spark Rust · Gluten (of {total} queries)</div>
  </div>
''')
parts.append('</div>')

# Per-query cluster chart
parts.append('<div class="section-subtitle">SF=1000 Query-by-Query Ratio (Spark Rust / Gluten)</div>')
parts.append('<div class="chart-container">')
parts.append('<div class="legend">')
parts.append('<div class="legend-item"><span class="legend-swatch" style="background:#0d9488"></span>Spark Rust faster</div>')
parts.append('<div class="legend-item"><span class="legend-swatch" style="background:#f59e0b"></span>Gluten faster</div>')
parts.append('<div class="legend-item"><span style="display:inline-block;width:20px;border-top:1px dashed var(--text-subtle);"></span> parity</div>')
parts.append('</div>')
parts.append(build_cluster_query_chart('1000'))
parts.append('</div>')

parts.append('</div>')  # end cluster section

# ---- Hardware & Methodology ----
parts.append('<div class="section"><div class="section-title">Hardware &amp; Methodology</div>')

parts.append('<div class="two-col">')
parts.append('<div>')
parts.append('<div class="section-subtitle">Single Node</div>')
parts.append('<div class="hw-grid">')
sn = hw['single_node']
parts.append(f'''
  <div class="hw-item">
    <div class="hw-label">Instance</div>
    <div class="hw-value">{sn['sku']}</div>
  </div>
  <div class="hw-item">
    <div class="hw-label">Cores</div>
    <div class="hw-value">{sn['cores']}</div>
  </div>
  <div class="hw-item">
    <div class="hw-label">RAM</div>
    <div class="hw-value">{sn['ram_gb']} GB</div>
  </div>
''')
parts.append('</div></div>')

parts.append('<div>')
parts.append('<div class="section-subtitle">Cluster Workers</div>')
parts.append('<div class="hw-grid">')
cw = hw['cluster_workers']
parts.append(f'''
  <div class="hw-item">
    <div class="hw-label">Workers</div>
    <div class="hw-value">{cw['count']} × {cw['sku']}</div>
  </div>
  <div class="hw-item">
    <div class="hw-label">Total Cores</div>
    <div class="hw-value">{cw['total_cores']}</div>
  </div>
  <div class="hw-item">
    <div class="hw-label">Total RAM</div>
    <div class="hw-value">{cw['total_ram_gb']} GB</div>
  </div>
  <div class="hw-item">
    <div class="hw-label">Cores/Worker</div>
    <div class="hw-value">{cw['cores_each']}</div>
  </div>
''')
parts.append('</div></div>')
parts.append('</div>')

parts.append(f'''
<div style="margin-top: 24px; padding: 16px 20px; background: var(--surface-alt); border-radius: var(--radius); font-size: 12px; color: var(--text-muted); line-height: 1.8;">
  <strong style="color: var(--text);">Provenance:</strong> {hw['provenance']}<br>
  <strong style="color: var(--text);">Data source:</strong> {data['source']}<br>
  <strong style="color: var(--text);">SHA-256:</strong> <code style="font-family: var(--font-mono); font-size: 11px; word-break: break-all;">{data['sha256']}</code>
</div>
''')

parts.append('</div>')  # end hardware section

# ---- Footer ----
n_tpch_q = len(data['single']['TPC-H']['1'])
n_tpch_sf = len(data['single']['TPC-H'])
n_tpds_q = len(data['single']['TPC-DS']['1'])
n_tpds_sf = len(data['single']['TPC-DS'])

parts.append(f'''
<div class="footer">
  Generated from engine-comparison-summary-data.json · {len(data['engines'])} engines ·
  TPC-H: {n_tpch_q} queries × {n_tpch_sf} scale factors ·
  TPC-DS: {n_tpds_q} queries × {n_tpds_sf} scale factors ·
  Cluster: {len(data['cluster'])} scale factors × 2 engines
</div>
''')

# ---- JavaScript ----
parts.append('''
<script>
// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.tab;
    const parent = tab.closest('.tabs');
    const panelId = 'panel-' + target;
    // Find sibling panels within the same section
    const section = tab.closest('.section');
    section.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    section.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(panelId).classList.add('active');
  });
});
</script>
''')

parts.append('</div></body></html>')

# Write output
output = '\n'.join(parts)
with open('engine-comparison-report.html', 'w') as f:
    f.write(output)

print(f"Done! Wrote engine-comparison-report.html ({len(output):,} bytes)")
