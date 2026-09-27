# Engine comparison report

Self-contained HTML report built from `../engine-comparison-summary-data.json`
(Spark Rust 0.42.1, DuckDB 1.5.5, Spark 4.1.1 Gluten and Spark 4.2 on TPC-H and
TPC-DS, single-node and 8-worker cluster).

## Files

| File | Purpose |
|---|---|
| `engine-comparison-report.html` | The deliverable. One file, inline CSS/JS, system fonts, no network requests. |
| `report_template.html` | Source template; the `__DATA_JSON__` placeholder is replaced at build time. |
| `build_report.py` | Embeds the JSON into the template and records its SHA-256 in the footer. |

## Build

```bash
python3 build_report.py            # defaults: ../engine-comparison-summary-data.json -> engine-comparison-report.html
python3 build_report.py --data path/to/data.json --out report.html
```

Requires Python 3.8+ and no third-party packages.

## Report contents

- Overview KPIs (all-scale-factor ratios vs DuckDB; cluster ratios vs Gluten) and derived key findings.
- Setup: engines, hardware, workloads.
- Single-node suite totals per scale factor (table with ratio pills and canonical/matched flags, plus bar panels).
- Single-node per-query heatmap with benchmark / scale-factor selectors and run markers (`B`, `P`).
- Cluster section: win stacks per scale factor, resource table (CPU-hours, GB·h, memory percentiles),
  a log₂ divergence chart of per-query speed ratios, and a collapsible per-query detail table.
- Method and notes: field definitions, marker legend, limitations, source hashes.

All numbers are rendered directly from the JSON; nothing is hard-coded.
