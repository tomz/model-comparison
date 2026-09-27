# SQL engine comparison report

Open **`engine-comparison-report.html`** directly in a modern browser. It is a complete offline artifact: all source data, styles, scripts, and charts are inline. Only this HTML file is needed for sharing.

## Features

- Executive findings, single-node suite/scale selectors, reported/canonical timing views, and cross-scale ratios.
- Query search, flag/coverage filters, pagination, and full filtered CSV exports.
- Cluster elapsed-time, CPU-hour, memory-time, and query-level comparisons.
- Embedded JSON download, hardware context, provenance hashes, and explicit limitations.
- Responsive layouts, keyboard controls, reduced-motion support, and print/PDF styles. Printing captures current selections and the current query-table pages, not every query.

## Rebuild

Python 3.10+; no third-party build dependencies:

```sh
python3 build_report.py
python3 -m unittest discover -s tests -v
```

The builder reads `engine-comparison-summary-data.json` and `report-template.html`, then writes `engine-comparison-report.html`. The report narrative is specific to this dataset; review it if replacing the input with different results.

Optional browser acceptance checks use an already-installed Playwright/Chromium:

```sh
python3 tests/browser_check.py
```

Screenshots and a browser-check summary are saved under `verification/`.

## Interpretation

The report preserves the input data without silently replacing missing values. Seconds are an explicit timing-unit assumption, supported by the cluster CPU/CPU-hour relationship. Memory units, B/P markers, source status semantics, matched-ratio methodology, and some experimental details are unspecified. The cluster suite name is not explicit in the JSON. The report does not claim official TPC results, verified correctness, or statistical significance.
