#!/usr/bin/env python3
"""Generate a self-contained HTML report from engine-comparison-summary-data.json."""

import json
from pathlib import Path

DATA = json.loads(Path("engine-comparison-summary-data.json").read_text())

ENGINES = DATA["engines"]
TOTALS = DATA["totals"]
SINGLE = DATA["single"]
CLUSTER = DATA["cluster"]
WINS = DATA["wins"]
CQ = DATA.get("clusterQueries", {})


def fmt_time(s):
    if s < 60:
        return f"{s:.2f}s"
    elif s < 3600:
        return f"{s / 60:.1f}m"
    else:
        return f"{s / 3600:.2f}h"


def fmt_ratio(r):
    if r is None:
        return "—"
    if r < 1:
        return f"{r:.3f}×"
    elif r < 10:
        return f"{r:.2f}×"
    else:
        return f"{r:.1f}×"


def engine_short(name):
    m = {
        "Spark Rust 0.42.1 (default)": "Spark Rust (default)",
        "Spark Rust 0.42.1 (tuned)": "Spark Rust (tuned)",
        "DuckDB 1.5.5": "DuckDB 1.5.5",
        "Spark 4.1.1 Gluten": "Spark 4.1.1 Gluten",
        "Spark 4.2": "Spark 4.2",
    }
    return m.get(name, name)


TEMPLATE = """<!DOCTYPE html>
<html lang="en" data-theme="">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Query Engine Comparison — TPC-H &amp; TPC-DS Benchmarks</title>
  <style>
    :root {
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
    }
    :root[data-theme="dark"] {
      --fg: #e6e7e9; --fg-soft: #b6bac3; --fg-mute: #8a8f99;
      --bg: #0f1117; --bg-soft: #1a1d27; --bg-card: #1e2130;
      --accent: #60a5fa; --accent-soft: #1e293b;
      --good: #4ade80; --good-soft: #14532d;
      --warn: #fbbf24; --warn-soft: #422006;
      --bad: #f87171; --bad-soft: #450a0a;
      --border: #2e333c; --border-soft: #232832;
    }
    @media (prefers-color-scheme: dark) {
      :root:not([data-theme="light"]) {
        --fg: #e6e7e9; --fg-soft: #b6bac3; --fg-mute: #8a8f99;
        --bg: #0f1117; --bg-soft: #1a1d27; --bg-card: #1e2130;
        --accent: #60a5fa; --accent-soft: #1e293b;
        --good: #4ade80; --good-soft: #14532d;
        --warn: #fbbf24; --warn-soft: #422006;
        --bad: #f87171; --bad-soft: #450a0a;
        --border: #2e333c; --border-soft: #232832;
      }
    }
    * { box-sizing: border-box; }
    html { -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }
    body {
      margin: 0; color: var(--fg); background: var(--bg);
      font-family: var(--sans); font-size: 15px; line-height: 1.65;
      -webkit-font-smoothing: antialiased;
    }
    .wrap { max-width: 1120px; margin: 0 auto; padding: 48px 28px 96px; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    :focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
    .table-scroll { max-width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
    h1 { font-size: 30px; font-weight: 700; letter-spacing: -0.015em; line-height: 1.18; margin: 0 0 8px; }
    h2 { font-size: 21px; font-weight: 700; margin: 48px 0 14px; padding-bottom: 6px;
         border-bottom: 2px solid var(--border-soft); scroll-margin-top: 20px; }
    h3 { font-size: 17px; font-weight: 650; margin: 32px 0 8px; }
    p { margin: 0 0 14px; }
    .eyebrow { font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em;
               color: var(--accent); font-weight: 600; margin-bottom: 8px; }
    .subtitle { color: var(--fg-soft); font-sze: 16px; max-width: 820px; }
    .meta { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 16px;
            color: var(--fg-mute); font-size: 13px; align-items: center; }
    .card { background: var(--bg-card); border: 1px solid var(--border);
            border-radius: var(--radius); padding: 20px 22px; }
    .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr)); }
    .pill { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 12px;
            font-weight: 600; background: var(--accent-soft); color: var(--accent); }
    .pill.bst { background: var(--good-soft); color: var(--good); }
    .pill.good { background: var(--good-soft); color: var(--good); }
    .pill.warn { background: var(--warn-soft); color: var(--warn); }
    .pill.baad { background: var(--bad-soft); color: var(--bad); }
    .callout { border-left: 3px solid var(--accent); background: var(--accent-soft);
               padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 16px 0; font-size: 14px; }
    .callout.good { border-color: var(--good); background: var(--good-soft); }
    .callout.warn { border-color: var(--warn); background: var(--warn-soft); }
    table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 13.5px; }
    th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--border-soft); white-space: nowrap; }
    thead th { font-size: 11 px; text-transform: uppercase; letter-spacing: 0.04em;
               color: var(--fg-mute); border-bo ttom: 2px solid var(--border);
               position: sticky; top: 0; background: var(--bg); z-index: 1; }
    tbody tr:hover { background: var(--bg-soft); }
    td.num { text-align: right; font-variant-numeric: tabular-nums; }
    code { font-family: var(--mono); font-size: 0.88em; background: var(--bg-soft);
           padding: 1px 4px; border-radius: 4px; }
    .metric { background: var(--bg-card); border: 1px solid var(--border);
              border-radius: var(--radius); padding: 16px 18px; }
    .metric .num { font-size: 28px; font-weight: 700; letter-spacing: -0.02em; line-height: 1.15; }
    .metric .label { color: var(--fg-mute); font-size: 12.5px; margin-top: 4px; }
    .toc { background: var(--bg-soft); border: 1px solid var(--border-soft);
           border-radius: var(--radius); padding: 16px 20px; margin: 22px 0; }
    .toc a { display: block; paddng: 3px 0; color: var(--fg-soft); text-decoration: none; font-sze: 13.5px; }
    .toc a:hover { color: var(--accent); }
    .theme-toggle { position: fixed; top: 12px; right: 12px; border: 1px solid var(--border);
                    background: var(--bg-card); color: var(--fg-soft); border-radius: 6px;
                    padding: 5px 10px; font-size: 12px; cursor: pointer; z-index: 10; }
    .bar-wrap { position: relative; height: 8px; background: var(--bg-soft); border-radius: 4px;
                min-width: 60px; margin-top: 2px; }
    .bar { height: 100%; border-radius: 4px; transition: width 0.3s ease; }
    .bar.accent { background: var(--accent); }
    .bar.good { background: var(--good); }
    .bar.warn { background: var(--warn); }
    .bar.baad { background: var(--bad); }
    .bar.duck { background: #6366f1; }
    .sf-nav { display: flex; gap: 6px; flex-wrap: wrap; margin: 10px 0 16px; }
    .sf-btn { border: 1px solid var(--border); background: var(--bg-card); color: var(--fg-soft);
              border-radius: 6px; padding: 5px 14px; font-size: 13px; cursor: pointer; font-family: inherit; }
    .sf-btn:hover, .sf-btn.active { background: var(--accent-soft); color: var(--accent);
                                      border-color: var(--accent); }
    .sf-section { display: none; }
    .sf-section.active { display: block; }
    .highlight { background: var(--accent-soft); font-weight: 600; }
    .engine-tag { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 4px; }
    .engine-tag.c0 { background: #f59e0b; }
    .engine-tag.c1 { background: #fbbf24; }
    .engine-tag.c2 { background: #6366f1; }
    .engine-tag.c3 { background: #ef4444; }
    .engine-tag.c4 { background: #b91c1c; }
    @media (max-width: 680px) {
      .wrap { padding: 32px 16px 64px; }
      h1 { font-size: 25px; }
      .grid { grid-template-columns: 1fr 1fr; }
    }
    @media (prefers-reduced-motion: reduce) {
      html { scroll-behavior: auto; scroll-snap-type: none; }
    }
  </style>
</head>
<body>

<button type="button" class="theme-toggle" aria-label="Toggle color theme"
 onclick="(function(){var r=document.documentElement;var d=r.getAttribute('data-theme')==='dark'||(!r.getAttribute('data-theme')&&window.matchMedia('(prefers-color-scheme: dark)').matches);r.setAttribute('data-theme',d?'light':'dark');})()">&#9680;&nbsp;theme</button>

<div class="wrap">

<header>
  <div class="eyebrow">Query Engine Benchmark &middot; September 2025</div>
  <h1>Spark Rust vs DuckDB vs JVM Spark</h1>
  <p class="subtitle">
    TPC-H and TPC-DS performance comparision across five engines on a</p>
</header>
</div>
</body>
</html>"""

# This approach of hand-writing the full HTML inline is too error-prone.
# Let me use a proper string building approach.

print("placeholder")