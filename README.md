# Model comparison — cost, time and value per report

How long did each model take, what did it cost, and what was the resulting
report worth — to build the same self-contained HTML report?

Every subdirectory here is one model's attempt at an identical prompt:

> generate a professional quality self contained html from the
> engine-comparison-summary-data.json, only use this file as the input

This project reads the evidence that the runs left behind — the TUI screenshots
in each directory — and turns it into one comparison report. It covers three
things: what each run **cost**, how long it **took**, and how good its
**report** was, combined into a value-per-investment (ROI) score.

**Deliverable:** [`comparison-report.html`](comparison-report.html) — a single
self-contained file, no network requests, opens from `file://`.

## Headline

| | |
|---|---|
| Runs compared | 35 (one excluded for having no screenshot) |
| Combined cost | **$73.77** (median $0.43 per run) |
| Combined model time | **7h06m** (median 7m56s per run) |
| Spread among paid runs | **582×** — $0.03 to $14.54 |
| Single-prompt runs | 27 of 35; 8 needed another prompt |

The two things the data supports:

1. **Cost is dominated by the model, not the job.** Every run produced a report
   from the same 324 KB input, yet the bill ranges from $0.03 to $14.54 — and
   one free-tier run cost $0.0009. The dearest models are not visibly faster.
2. **Time does not track price either.** The cheapest run finished in 58s; the
   most expensive took 25m54s. The scatter plot in the report shows a broad
   cloud, not a downward band: you cannot buy speed here.

## Report quality

Each of the 36 generated reports was also scored 0–100 on how well it does the
job of a benchmark report. The rubric is pre-registered and every point traces
to a check recorded in `quality-ratings.json`:

| Dimension | Weight | Rewards |
|---|---:|---|
| Correctness | 20 | Embeds the dataset, renders known figures unchanged, no console errors |
| Completeness | 18 | Both suites, single-node and cluster, per-query detail |
| Analysis | 18 | Key findings, ratios/baseline, win counts, a method section |
| Caveats | 14 | Limitations; canonical vs reported time; source markers flagged |
| Presentation | 12 | Charts, large tables, dark mode, print styles, responsive |
| Ease of use | 10 | Navigation, sorting, filtering, drill-down, accessible controls |
| Provenance | 8 | Builder, template, hashes, README and tests kept alongside |

**Median 81.4, range 32.3–96.8.** Best reports:

| report | score | correctness | completeness | caveats |
|---|---:|---:|---:|---:|
| `mimo-2.6-pro` | 96.8 | 20.0 | 18.0 | 14.0 |
| `fable-5.1` | 96.4 | 20.0 | 18.0 | 14.0 |
| `glm-5.3` | 93.4 | 17.1 | 18.0 | 14.0 |
| `gpt-6-astra` | 91.7 | 17.1 | 18.0 | 14.0 |
| `gpt-6-astra-pro` | 91.0 | 20.0 | 14.4 | 14.0 |

Weakest: `gemini-3.1-pro-preview` (32.3 — two tables, no charts, no caveats, no
cluster view), `nemotron-3.5-ligtening` (45.9), `somemodel_unknown` (48.5).

**Spend and quality move together, weakly.** Spearman rank correlation between a
run's cost and its report quality is **0.486** (n=35), and between time and
quality **0.689** — runs that cost more and ran longer *tended* to produce better
reports. But the relationship is loose and partly definitional (a fuller report
takes more turns): the cheapest third still reached a median 77.8 against 87.5
for the dearest third, and `deepseek-v4.1-flash` scored 81.4 — above median — for
$0.09. This is correlational, on sequential runs, and cost largely reflects the
provider's price list.

**Where the corpus is weakest.** Averaged per dimension the reports are strong on
correctness (18.6/20) and completeness (16.0/18) but weak on **provenance**
(2.8/8 — most attempts delete the builder, template, README or tests) and **ease
of use** (5.0/10 — no navigation or filtering). Caveats average 9.5/14: many
reports state no limitations at all.

What the rubric deliberately does **not** score: visual taste, prose quality, and
whether the conclusions are *interesting*. Those need a human looking at the
rendering. The scores are structural and factual, which is why they are worth
computing across 36 reports.

## Return on investment

ROI combines all three signals — quality (the return), cost and time (the
investment) — without inventing weights. Quality points are not currency, so
rather than fabricate a dollar figure the analysis asks the only question a buyer
can act on: **at the quality this run achieved, what was the best deal
available?** Each run's cost is divided by the cheapest run that reached at least
its quality, and its time by the fastest such run.

```
roi_score = 100 x quality_attainment x sqrt(cost_efficiency x time_efficiency)
```

where *attainment* is the run's quality score divided by the best score achieved,
and each efficiency is the run's cost/time measured against the cheapest (and
fastest) run that reached at least its quality, capped at 1.

**Quality multiplies; it is not merely a bar to clear.** An earlier version of
this analysis treated quality as a floor, which let a cheap 45.9-quality report
out-rank a cheap 86.9-quality one — that is a low price, not a return on
investment. Now a run's ceiling is set by how good its report was: **half the best
quality can never score above 50**, however little it cost. This is asserted by
unit test.

100 means the best report at the best available price; 10 means roughly ten times
the going rate in money-and-time for the quality delivered. The score is reported
three ways:

- **ROI $+t** — money and time together (the headline number).
- **ROI $** — money alone; what matters if you pay per token but waiting is free.
- **`$ / quality pt`** — the raw ratio, for readers who distrust indices.

The factors are consistent by construction: `roi_score = sqrt(roi_score_cost x
roi_score_time)`, so each is readable as "how much of the score came from money
versus speed". The ROI chart's bars are **segmented by factor** (quality, money,
speed) to show which one cost each run the most.

**The best report is also the best deal.**

| run | quality | cost | ROI $ | ROI $+t | why |
|---|---:|---:|---:|---:|---|
| `mimo-2.6-pro` | **96.8** | $0.12 | **100** | **100** | best report at a frontier price |
| `gpt-6-luna` | 75.0 | $0.03 | 77.5 | 77.5 | cheapest paid run; capped by its own quality |
| `glm-5.3-flash` | 86.9 | $0.043 | 89.8 | 31.9 | cheaper per quality point, 8x slower |
| `openrouter-free` | 61.1 | $0.0009 | 63.1 | 51.3 | free, but capped near 63 by quality |
| `opus-5` | 87.5 | $14.54 | 0.8 | 3.7 | 119x the going rate for its quality |
| `grok-4.7` | 83.9 | $6.03 | 0.6 | 3.0 | 140x — worst in the corpus |

**Every expensive run is dominated.** The Pareto frontier holds just **4 runs** by
cost (7 by time, 9 on one or the other), the dearest costing **$0.12** against a
median run cost of **$0.40** — no run at or above the median cost is on it.
**18 of 35 runs** spent at least ten times the going rate for the quality they
reached; the worst, `grok-4.7`, paid **140x** the cheapest run at equal-or-better
quality.

**Recommendation.** `mimo-2.6-pro` is the pick: it produced the highest-scoring
report in the corpus for $0.12 — one percent of what `opus-5` cost for a lower
score — and it tops both ROI rankings. `gpt-6-luna` at $0.03 remains the choice if
a merely adequate report (75.0/100) is all you need.

**The recommendation is robust to weighting.** Re-weighting money against time
from 1:3 to 3:1 selects `mimo-2.6-pro` at every setting. On money alone the
runner-up is `glm-5.3-flash` (86.9 quality for $0.043): cheaper per quality point,
but 8x slower, so it drops out of contention once time is charged.



### Most expensive runs

| model | time | cost | prompts |
|---|---:|---:|---:|
| `anthropic/claude-opus-5` | 25m54s | $14.5400 | 1 |
| `openai/gpt-6-astra-pro` | 16m34s | $13.7900 | 1 |
| `anthropic/claude-fable-5.1` | 22m29s | $13.7000 | 1 |
| `x-ai/grok-4.7` | 27m10s | $6.0300 | 1 |
| `qwen/qwen3.8-max-prime` | ≥18m48s | $5.2500 | 2 |
| `anthropic/claude-opus-5.5` | 7m07s | $3.8200 | 1 |
| `anthropic/claude-sonnet-5` | 9m22s | $2.2900 | 1 |
| `openai/gpt-6-astra` | 5m54s | $2.2800 | 1 |

`≥` marks a lower bound (see caveats). Full results for all 35 runs are in the
report's table, sortable and filterable.

## Pipeline

Three stages, each a separate script so a failure is easy to localise:

```
screenshots (*.png)
      │  extract_metrics.py         OCR the bottom band of each image
      ▼
screenshot-metrics.json              raw per-turn and status-bar readings
      │  build_comparison.py         group into sessions, cross-check usage log
      ▼
comparison-data.json                 per-model aggregates
      │  build_comparison.py --report
      ▼
comparison-report.html               the deliverable

<model-name>/*.html
      │  rate_quality.py             render in headless Chrome, apply the rubric
      ▼
quality-ratings.json                 per-report scores + per-check evidence
```

**OCR.** Each screenshot's bottom band holds the turn line
(`Turn 1 done 00:41:34 → 00:48:41 in 7m07s … $3.82`) and the status bar
(`folder | provider | model (effort) | tokens | … | $cost | ctx`). Both are read
with tesseract using two crops (`--psm 4` over a tall band to catch earlier
turns, `--psm 6` over a tight band for the newest), because a single crop misses
turns that have scrolled up.

**Session grouping.** A directory's screenshots are split into sessions when the
turn counter restarts. Cost is read as the **maximum** cumulative value per
session, never a sum — the status bar shows a running total.

**Cross-check.** Every run is matched to its entry in the assistant's own
`~/.jaaicode/usage.jsonl` by the wall-clock overlap of its turn window, not by
name or price. The directories were renamed after the runs, so their recorded
`cwd` no longer identifies them; the timestamps do, and 33 of 35 runs reconcile
to within $0.01.

**Quality rating.** `rate_quality.py` opens each attempt's deliverable in
headless Chrome, applies the rubric above, and writes `quality-ratings.json`
with the per-check evidence. Figure probes search the rendered text for dataset
values at any legitimate rounding (raw, 1–2 decimals, thousands-separated) and
accept either display convention (SF1 or all-scale-factor rows), so a report is
not penalised for a rounding or default-view choice.

## Usage

Requires Python 3.9+, Pillow, and the `tesseract` binary
(`sudo apt-get install tesseract-ocr`).

```bash
python3 extract_metrics.py            # OCR every attempt directory
python3 rate_quality.py               # score each attempt's report -> quality-ratings.json
python3 build_comparison.py --report  # aggregate + render comparison-report.html
python3 -m unittest discover -s tests # 39 unit tests, no OCR or browser needed
python3 verify_report.py              # browser checks + screenshots
```

Useful flags:

```bash
python3 extract_metrics.py --dirs glm-5.3 opus-5.5   # subset
python3 extract_metrics.py --dump-raw                # keep OCR text in the JSON
```

## Method and caveats

Stated plainly, because the numbers are only as good as these limits:

- **Cost is cumulative, not additive.** Summing several screenshots of one run
  would overcount, so the maximum per session is used.
- **9 runs have lower-bound times.** Their earliest visible turn is not turn 1
  — earlier output scrolled off screen — so the reported time is a minimum. The
  report marks these with a striped bar and `≥`.
- **Two runs share a session with another model.** The operator switched models
  mid-session, so the `usage.jsonl` total covers more than the one artifact and
  exceeds the screenshot figure. The screenshot value is the better estimate for
  that run alone; both are shown.
- **One OCR misread was corrected.** A status bar rendered `$0.860` as `860`
  (decimal point lost); the implausible value was discarded rather than reported.
- **One directory was excluded.** `somemodel_unknown` has no screenshot, so
  there is no time or cost evidence to read.
- **The quality score is structural, not aesthetic.** It checks data fidelity,
  coverage, analysis, caveats, presentation, usability and provenance — all
  measurable. It does not read prose, so a confidently wrong sentence scores the
  same as a correct one unless it changes a number or drops a section. A report
  that shows cluster results only as ratios still loses that figure check.
- **The cost–quality link is correlational.** Runs are sequential on one machine,
  all at medium effort, and cost largely reflects the provider's price list.
  Spearman ρ = 0.49 (cost) and 0.69 (time) describe this corpus; they are not a
  claim that spending more causes a better report.
- **ROI multiplies by quality; it does not treat quality as a bar to clear.** A
  run's ceiling is set by how good its report was, so cheap-and-weak cannot top
  the ranking. What remains a modelling choice is that value is assumed *linear*
  in the quality score: if all you need is "good enough to publish", read the
  table by quality first and price second rather than by ROI alone.
- **ROI fixes the money:time trade-off at 1:1.** Sensitivity is reported at 1:3
  and 3:1 and picks the same winner, but a buyer who values speed far above cost
  should re-derive with their own weights.
- **Not a controlled experiment.** Runs are sequential on one machine, all at
  medium effort, and the harness changed between attempts. Treat differences as
  indicative, not causal. Costs come from one gateway's price list at the time
  of the run and are not directly comparable across providers in general.

## Files

| File | Purpose |
|---|---|
| `comparison-report.html` | The deliverable. Self-contained, offline. |
| `extract_metrics.py` | OCR the screenshots into `screenshot-metrics.json`. |
| `rate_quality.py` | Score each attempt's report against the rubric. |
| `build_comparison.py` | Aggregate sessions + ratings, render the report. |
| `report_template.py` | HTML/CSS/JS template with the data inlined. |
| `verify_report.py` | Browser checks (Playwright) and screenshots. |
| `tests/test_parsers.py` | Unit tests for the OCR parsers and session logic. |
| `tests/test_scoring.py` | Unit tests for the rank correlation and rubric. |
| `screenshot-metrics.json` | Generated: raw per-screenshot readings. |
| `quality-ratings.json` | Generated: per-report scores + per-check evidence. |
| `comparison-data.json` | Generated: per-model aggregates (incl. quality). |
| `verification/` | Generated: screenshots and check summary. |
