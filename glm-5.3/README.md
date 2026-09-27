# Engine comparison report

Self-contained HTML report built from `engine-comparison-summary-data.json`
(Spark Rust 0.42.1 default/tuned, DuckDB 1.5.5, Spark 4.1.1 Gluten and
Spark 4.2 on TPC-H and TPC-DS; single-node and 8-worker cluster).

## Files

| File | Purpose |
|---|---|
| `engine-comparison-report.html` | The deliverable. One file, inline CSS/JS, system fonts, no network requests. |
| `report_template.html` | Source template; `__DATA_JSON__` and hash placeholders are replaced at build time. |
| `build_report.py` | Embeds the JSON into the template; records both the source-document SHA-256 (from the dataset) and the JSON file's own SHA-256. |
| `verify_report.js` | DOM-level verification (rendering, interactions, overflow, focus) run with Playwright. |
| `design-brief.md` | Design direction and the verified data-semantics notes the report is built on. |

## Build

```bash
python3 build_report.py            # engine-comparison-summary-data.json -> engine-comparison-report.html
python3 build_report.py --data path/to/data.json --out report.html
```

Requires Python 3.8+ and no third-party packages.

## Verify

```bash
python3 -m http.server 8477 &      # serve, then:
node verify_report.js              # 21 rendering/interaction checks
```

## Report contents

- Overview: KPI cards (all-SF ratios vs DuckDB, cluster wall/CPU vs Gluten,
  win rates) and derived key findings with caveats attached.
- Setup: engines, hardware (single node + cluster), workloads.
- Single-node totals per scale factor: log-scale bar panels plus a full table
  with ratio pills, canonical-total status, and source-reported matched ratios.
- Per-query single-node heatmap with benchmark/scale-factor selectors; fastest
  engine outlined; B/P run flags carried through; sortable detail table.
- Cluster: win stacks per scale factor, resource accounting table, log₂
  divergence charts of per-query Rust/Gluten ratios, collapsible per-query
  detail tables with pass/gap/unvalidated status.
- Method & notes: field definitions (verified against the data), limitations,
  provenance with both hashes.

All numbers are rendered from the JSON at runtime; nothing is hard-coded.

## Verification notes

- 21/21 DOM checks pass (desktop + mobile): no console errors, all sections
  render, controls work, no page-level horizontal overflow at 390 px,
  focus-visible outline present, theme toggle functional.
- Content spot-checks pass: rendered values match the source JSON (totals,
  cluster CPU-hours, hashes); heading hierarchy and accessible names valid;
  light-theme body contrast 16.4:1, muted 5.5:1; dark theme 14.5:1 via
  `prefers-color-scheme`.
- Not performed: pixel-level visual inspection (this client cannot view
  images). Screenshots are saved under `.verify/` for human review.
