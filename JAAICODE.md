# model-comparison

## Overview

A side-by-side shoot-out of ~37 AI coding assistants, not a single application. Every
subdirectory is one model's independent attempt at the *same* prompt:

> generate a professional quality self contained html from the
> engine-comparison-summary-data.json, only use this file as the input

Each attempt delivers one self-contained, offline HTML report comparing Spark Rust / DuckDB /
Spark Gluten / Spark 4.2 over TPC-H and TPC-DS (single-node and 8-worker cluster). The repo is
a corpus for comparing output quality, not a product. The root also holds a pipeline: it reads
each run's time and cost from its screenshots, scores the generated report against a rubric, and
renders `comparison-report.html`.

## Tech Stack

- **Python 3** — attempt builders (stdlib only); the root pipeline adds Pillow + `tesseract`.
- **HTML + inline CSS + inline JS** — the graded artifact. Self-contained: no CDN, no network
  requests, no web fonts.
- **Node.js + Playwright / Chrome** — optional browser verification.
- **unittest** — the Python test framework (2 attempts, plus `tests/` at the root); **ruff**
  ran locally (`.ruff_cache/` in several directories).
- **graphify** — `graphify-out/` knowledge-graph artifacts (top level and per attempt).

## Project Structure

```
model-comparison/
├── engine-comparison-summary-data.json   # canonical input dataset (frozen, 324 KB)
├── comparison-report.html                # deliverable: root cost/time/quality/ROI report
├── extract_metrics.py                    # OCR screenshots -> screenshot-metrics.json
├── build_comparison.py                   # sessions + usage.jsonl -> comparison-data.json
├── report_template.py                    # root report HTML/CSS/JS, data inlined
├── verify_report.py, tests/test_parsers.py   # root browser checks, parser unit tests
├── screenshot-metrics.json / comparison-data.json / verification/   # generated
├── <model-name>/                         # one attempt per model, ~37 of them:
│   #   data copy, builder, template + deliverable (names vary), optional README,
│   #   tests/ and verification/, the evidence screenshot, graphify-out/
├── .jaaicode/                            # local prompt history (gitignored)
└── graphify-out/                         # repo-wide knowledge graph
```

Filenames vary by design (29 `engine-comparison-report.html`, 6 `…-summary.html`, `index.html`); `ls` first.

## Development

Each attempt builds from inside its own directory:

```bash
cd <model-name> && python3 build_report.py    # polished ones take --data/--template/--out
cd <model-name> && python3 -m unittest discover -s tests -v   # gpt-6-astra, -pro only
cd <model-name> && python3 tests/browser_check.py             # or: node verify_report.js
                                              # attempts need no install step or venv
```

```bash
python3 extract_metrics.py            # OCR every attempt directory
python3 rate_quality.py               # score each attempt's report -> quality-ratings.json
python3 build_comparison.py --report  # aggregate + render comparison-report.html
python3 -m unittest discover -s tests # 55 unit tests (no OCR or browser needed)
python3 verify_report.py              # Playwright checks + screenshots into verification/
```

## Coding Conventions

- `snake_case.py` entrypoints with `main() -> int`, guarded by
  `if __name__ == "__main__": sys.exit(main())`.
- `from __future__ import annotations`, modern hints (`list[str]`, `str | None`).
- `pathlib.Path` throughout, anchored at `ROOT = Path(__file__).resolve().parent`.
- Module docstring stating the contract, e.g. "no third-party packages".
- `argparse` for `--data` / `--template` / `--out`; `logging` or a bare status `print`.
- Builders string-replace a template token (`__DATA_JSON__`, `__SOURCE_JSON__`,
  `__JSON_SHA256__`, `__SRC_SHA256__`, `__SOURCE__`) rather than a template library.
- Table numbers are right-aligned and monospaced; report chrome uses system fonts only.

## Architecture

**Data flow.** dataset -> `json.load` -> re-serialized (`separators=(",", ":")`,
`ensure_ascii=False`) -> injected into the template -> one HTML file whose JS renders every
number at runtime. Nothing is hard-coded from the data.

**Escape the payload.** The JSON sits inside a `<script>` tag, so builders must neutralize the
sequence that would close it early: `payload.replace("</", "<\\/")` (glm-5.3) or escaping
`<`, `>`, `&` to `\u003c` (gpt-6-astra-pro). New builders must do one of these.

**Provenance.** `data["sha256"]` hashes the *source document*
(`engine-comparison-20260925-clean.md`); the JSON file's own SHA-256 is computed at build
time. Different values, labelled distinctly. Share only the generated HTML.

**Root pipeline.** `extract_metrics.py` OCRs the bottom band of each screenshot (turn line plus
status bar) into `screenshot-metrics.json`; `rate_quality.py` renders each attempt's report in
headless Chrome and applies the rubric; `build_comparison.py` groups screenshots into sessions,
cross-checks `~/.jaaicode/usage.jsonl`, then writes `comparison-data.json` and the HTML.

## Invariants

- **Screenshot cost is cumulative, never additive.** The status bar shows a running session
  total and a turn line's `$` equals it at that moment. Take the maximum per session.
- **One session per directory unless the turn counter restarts.** Continuing turn numbers
  (2, 3) are consecutive prompts; a jump back to 1 is a restarted run with its own baseline.
- **A missing early turn means a lower-bound time.** If the lowest visible turn is not 1,
  earlier output scrolled off and the duration is a minimum — flag it, don't present a total.
- **`usage.jsonl` entries match by wall-clock overlap, not name or price.** Attempt directories
  were renamed after the runs, so recorded `cwd` no longer maps to a directory. `verification/`
  and `tests/` are tooling, not attempts (`extract_metrics.ATTEMPT_EXCLUDES`).
- **The dataset is frozen.** All 35 copies (root original + 34 in attempts) are byte-identical
  (md5 `9fac9460a60f3ffb404d9036e2addc1b`). Never edit a copy, and never "fix" a number in a
  report by changing the input.
- **Only that file is input.** The prompt forbids searching parent folders; reports must be
  derivable from the JSON alone. Needing a README to interpret the data violated the brief.
- **`totals[suite][].time` is the sum of the per-query `single` times** for that engine and
  scale factor (verified 40/40 rows, `diff` 0). Not independent.
- **`ratio` is engine time / DuckDB 1.5.5 time** at the same scale factor. DuckDB is the
  baseline and its own ratio is 1.
- **`canonical` may be `null`** (4 rows: TPC-H SF1000/`all` Spark 4.2, TPC-DS SF1000 Spark
  Gluten, …): no canonical total in the source. Render missing, never 0 or `time`. Raw `time`
  includes flagged runs, `canonical` excludes them, so they differ on `B`/`P` rows.
- **`matched` is `null` on every per-scale row**, set only on `sf: "all"` rows (40 nulls).
  Derivation absent from the dataset; if shown, label "as reported by source".
- **Preserve the vocabularies verbatim.** `engines` has exactly 5 entries and defines the column
  order of every `single[].times` / `.markers` array (length 5, index-aligned). `markers` is
  `""`/`"B"`/`"P"`; cluster `status` is free text (`pass`, `gap`, `pass (Q39 ULP policy)`,
  "Spark Rust-only: … unvalidated …") — pass it through, never collapse it to a boolean.
- **`cluster[*].mean/p50/p95/max` are source-reported and do not match sums over
  `clusterQueries`.** Present as-is and note the discrepancy; don't recompute.
- **Offline is a hard requirement.** No external assets, fonts or requests; the file must open
  correctly from `file://`.

## Patterns

- Verify claims against the JSON before writing them into prose; attach the caveat in the
  same sentence and flag undefined fields as unspecified rather than inventing an explanation.
- Prefer inline SVG or pure CSS bars over any chart library.
- Score reports against a pre-registered weighted rubric; keep per-check evidence in
  `quality-ratings.json`. Probe figures with tolerance; score structure, never prose.
- Express ROI as value per unit of investment with no invented weights: make quality a
  **multiplier** (attainment vs the best report), never merely a floor, or a cheap weak
  report out-ranks a cheap good one. Report money-only and money+time rankings separately;
  the combined score is their geometric mean. Cap efficiency at 1 (free tier).
- When a parsed value looks implausible (an OCR-lost decimal point), discard it and record the
  correction in the report's notes rather than silently trusting or dropping it.
- Leave `graphify-out/` and `.jaaicode/` alone; generated state, not sources.

## Avoid

- Hard-coding data values in HTML or JS instead of rendering from the embedded JSON.
- Editing or reformatting `engine-comparison-summary-data.json` anywhere.
- Assuming a fixed builder/deliverable filename.
- Adding a build-time third-party dependency to an attempt — stdlib only.
