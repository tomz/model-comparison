# Design brief — engine comparison report

**Audience:** engineers evaluating Spark Rust 0.42.1 against DuckDB 1.5.5,
Spark 4.1.1 Gluten, and Spark 4.2. They want headline conclusions fast, then
evidence tables and per-query drill-down.

**Purpose:** present the benchmark data honestly — including flagged runs,
missing canonical totals, and unvalidated cluster queries — without inventing
interpretations the dataset doesn't support.

**Delivery:** one self-contained HTML file, inline CSS/JS, system fonts, no
network requests. Works offline, printable.

**Content priority:**
1. Headline KPIs (all-SF ratios vs DuckDB; cluster wall-time + CPU-hours vs Gluten)
2. Key findings derived from the data (with the caveats attached)
3. Single-node totals per SF (table + bars)
4. Per-query single-node view (heatmap + sortable table)
5. Cluster section (wins, resources, per-query divergence chart + table)
6. Method & notes (field definitions, markers, limitations, provenance)

**Visual mood:** technical benchmark report. Calm, dense, data-first. No hero
imagery. Light + dark theme via `prefers-color-scheme` + toggle.

**Composition:** sticky top nav with section links; KPI card grid; sections
with numbered headings; tables in horizontal-scroll containers; pure-CSS bars
and inline SVG charts (no chart library).

**Type roles:** system sans for prose; monospace for numbers in tables and
query IDs. Numeric columns right-aligned, tabular-nums.

**Color roles:** accent blue for interactive/neutral data; green = faster/better;
red = slower/worse; amber = flagged/caveat. Heatmap: sequential blue scale for
ratio-to-best.

**Spacing rhythm:** 1080px max width, 56px section spacing, 18px card grid gap.

**Imagery:** none. Charts are data.

## Verified data semantics (do not contradict)

- `totals[].time` = sum of per-query wall-clock seconds (verified: equals sum of
  `single` times to 1e-6).
- `ratio` = engine time ÷ DuckDB time, same SF. Baseline: DuckDB 1.5.5.
- `canonical` = total over unflagged runs only; `null` where the source reports
  no canonical total (the raw total includes flagged runs). Verified: differs
  from `time` exactly on rows with B/P markers (TPC-DS tuned SF1000: canonical
  10082.33 vs time 10073.98, delta 8.35s = the two P-flagged runs).
- `matched` = source-provided all-SF aggregate ratio; **derivation not in this
  dataset** (not sum-ratio, not geomean — tested). Present as-is, labeled
  "as reported by source".
- `wins[sf]` = [Spark Rust passes (incl. ULP q39), Gluten gaps]. SF100: 89
  passes = 88 ratio<1 + q39 ULP pass (ratio 0.339<1 actually... verified 88
  ratio<1 + 1 ULP = 89). SF1000: 48/51. SF10000: 36/58 (over 94 validated).
- Cluster `time` = sum over mutually-validated queries (SF10000: 94 queries,
  verified sum matches). `n` = validated count.
- Cluster `mean/p50/p95/max` = source-provided per-query stats; do NOT match
  sums of `clusterQueries` (e.g. SF100 rust p50 2.434 vs computed 4.904) —
  present as-is, note the discrepancy is unexplained by this dataset.
- `status`: `pass` = Rust at least as fast; `gap` = Gluten faster; Q39 passes
  under ULP policy at SF100/1000; SF10000 has 5 one-sided/unvalidated queries
  (q23 both-failed, q39/q67/q78/q95 Rust-only).
- Markers: `B` (3× Spark 4.2 TPC-H SF1000 q8/q9/q21; 1× Gluten TPC-DS SF1000
  q23), `P` (2× tuned TPC-DS SF1000 q18/q69). Meanings not defined in dataset —
  copy from source, don't invent.
- `cpuHours`/`memHours` = CPU-seconds ÷ 3600; `memtime` = GB-seconds presumably;
  `cores` = average core utilization. Present with units, no invented claims.
- Hardware: single node D32ads v5 (32 cores, 128 GB); cluster 8× E16ads v5
  (16 cores, 128 GB each; 128 cores, 1 TB total). Provenance: user-provided.

## Key findings (derived, verifiable from data)

1. Single-node: Spark Rust (default & tuned) is within ~3–5% of DuckDB's total
   time at SF100–1000 on both benchmarks; at SF1 it's 18–33% slower. Spark 4.1.1
   Gluten and Spark 4.2 are 1.3–53× slower than DuckDB depending on SF.
2. TPC-DS SF100/1000: Spark Rust beats DuckDB on total time (ratios 0.96–0.99).
3. Cluster: Spark Rust wins 89/99 queries at SF100 but only 36/94 at SF10000;
   at SF10000 Gluten's wall time is 1.47× faster (12763s vs 18710s) while Rust
   uses 16% less CPU-hours (127.7 vs 151.4).
4. Rust's efficiency advantage: 2–2.7× less CPU-seconds and 5–7× less memory
   time at every cluster SF.
5. Caveats: 6 flagged single-node runs; 5 unvalidated SF10000 queries; cluster
   percentile stats don't reconcile with per-query data.
