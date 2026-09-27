# Engine comparison report

Open **engine-comparison-summary.html** directly in a modern browser. It is a single, self-contained offline artifact with inline CSS, JavaScript and the complete supplied dataset. No server, CDN, font download, tracking or installation is needed to view it.

## Features

- Single-node TPC-H / TPC-DS comparisons by scale factor, with reported and canonical totals.
- Three cluster comparisons, CPU-hour reductions, coverage and timing wins.
- Searchable, sortable query tables with source markers and CSV export.
- Embedded JSON download, source fingerprints, hardware context and methodological caveats.
- Responsive layouts, keyboard-accessible controls and print / PDF styling. Printing includes the selected single-node chart and all cluster summaries; it omits the interactive explorer and collapsed detail tables.

The JSON does not define all field semantics or the complete benchmark protocol. Undefined markers and resource units are explicitly identified rather than invented. Timing values are interpreted as seconds. The displayed snapshot date is inferred from the named source document, which was not supplied.

## Rebuild

Python 3.10+; standard library only:

```bash
python3 generate_report.py
python3 -m unittest discover -s tests -v
```

The builder embeds `engine-comparison-summary-data.json` into `report.template.html` and writes `engine-comparison-summary.html`. Keep the template for edits; only the generated HTML needs to be shared. The narrative is specific to the supplied dataset, not a general-purpose report for unrelated inputs.

## Browser verification

With the already-installed Python Playwright package and Google Chrome:

```bash
python3 tests/browser_check.py
```

This checks offline loading, all single-node selections, query filters, mode switching, missing data, CSV/JSON downloads, print output and narrow-screen overflow. Screenshots and a test PDF are saved under `verification/` (not required for the report).
