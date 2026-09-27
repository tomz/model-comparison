# Engine Comparison Report

A self-contained HTML benchmark report generated exclusively from
`engine-comparison-summary-data.json` (TPC-H / TPC-DS engine comparison:
Spark Rust 0.42.1 default & tuned, DuckDB 1.5.5, Spark 4.1.1 Gluten, Spark 4.2).

## Build

```bash
python3 -c "import json, pathlib; p = pathlib.Path('engine-comparison-summary-data.json'); t = pathlib.Path('report_template.html').read_text(); d = p.read_text().replace('</', '<\\/'); pathlib.Path('engine-comparison-report.html').write_text(t.replace('__DATA_JSON__', d))"
```

The generated `engine-comparison-report.html` embeds the full dataset and needs
no network access — open it directly in any modern browser.

## Contents

- Overview scoreboard (suite totals, matched ratios, cluster win counts)
- Single-node totals per scale factor (ratio-to-DuckDB and log-absolute charts)
- Per-query detail for both suites at SF 1–1000
- Cluster comparison and per-query detail for SF 100 / 1,000 / 10,000
- Method & hardware appendix with field glossary
