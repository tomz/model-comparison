#!/usr/bin/env python3
"""Verify comparison-report.html in a real browser and capture screenshots.

Checks that the file works offline (no network requests, no console errors),
that every section renders with real values, that sorting and filtering work,
and that there is no horizontal overflow at a phone width. Screenshots are
written to verification/ for human review.

Usage:
    python3 verify_report.py
"""
from __future__ import annotations

import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
REPORT = ROOT / "comparison-report.html"
SHOTS = ROOT / "verification"


def _dur(text: str) -> int:
    """Parse the report's '7m56s' / '1h02m' duration strings into seconds."""
    digits = "".join(c if c.isdigit() or c in "hms" else " " for c in text)
    total = 0
    for tok in digits.replace("h", "h ").replace("m", "m ").replace("s", "s ").split():
        if tok.endswith("h"):
            total += int(tok[:-1]) * 3600
        elif tok.endswith("m"):
            total += int(tok[:-1]) * 60
        elif tok.endswith("s"):
            total += int(tok[:-1])
    return total


def main() -> int:
    if not REPORT.exists():
        print("error: run build_comparison.py --report first", file=sys.stderr)
        return 1
    SHOTS.mkdir(exist_ok=True)
    failures: list[str] = []
    checks = 0

    def check(label: str, ok: bool, detail: str = "") -> None:
        nonlocal checks
        checks += 1
        print(f"{'PASS' if ok else 'FAIL'}  {label}{(' - ' + detail) if detail else ''}")
        if not ok:
            failures.append(label)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/usr/bin/google-chrome")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        console: list[str] = []
        requests: list[str] = []
        page.on("console", lambda m: console.append(f"{m.type}: {m.text}"))
        page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
        page.on("request", lambda r: requests.append(r.url))

        page.goto(REPORT.as_uri(), wait_until="load")
        page.wait_for_timeout(400)

        errors = [c for c in console if c.startswith(("error", "pageerror"))]
        check("no console errors", not errors, "; ".join(errors[:3]))

        external = [u for u in requests if not u.startswith(("file://", "data:"))]
        check("no network requests", not external, ", ".join(external[:3]))

        payload = json.loads(page.eval_on_selector("#data", "el => el.textContent"))
        n = len(payload["models"])

        kpis = page.eval_on_selector_all(".kpi .v", "els => els.map(e => e.textContent.trim())")
        check("KPI cards rendered", len(kpis) >= 6, f"{len(kpis)} cards: {kpis[:3]}")

        # The fastest/slowest cards must agree with the data, not with row order.
        kpi_map = dict(page.eval_on_selector_all(
            ".kpi", "els => els.map(e => [e.querySelector('.k').textContent, e.querySelector('.v').textContent])"))
        times = sorted(m["total_elapsed_s"] for m in payload["models"] if m.get("total_elapsed_s"))
        fastest_ok = kpi_map["Slowest run"].startswith(f"{times[-1] // 60}m")
        check("slowest KPI matches the data", fastest_ok,
              f"card={kpi_map['Slowest run']} expected about {times[-1]}s")
        check("slowest KPI is longer than fastest KPI",
              _dur(kpi_map["Slowest run"]) > _dur(kpi_map["Fastest run"]),
              f"{kpi_map['Fastest run']} vs {kpi_map['Slowest run']}")

        cost_rows = page.eval_on_selector_all("#chart-cost .row", "e => e.length")
        time_rows = page.eval_on_selector_all("#chart-time .row", "e => e.length")
        check("cost chart has a bar per model", cost_rows == n, f"{cost_rows} vs {n}")
        check("time chart has a bar per model", time_rows == n, f"{time_rows} vs {n}")

        lb_bars = page.eval_on_selector_all("#chart-time .bar.lb", "e => e.length")
        expected_lb = len([m for m in payload["models"] if m.get("time_is_lower_bound")])
        check("lower-bound bars marked", lb_bars == expected_lb, f"{lb_bars} vs {expected_lb}")

        # Bar length must be proportional to the value it encodes. The default axis is
        # zero-based and linear (the log view behind the toggle is not), so width/value
        # has to be constant across bars. Each chart is ranked by the quantity it draws,
        # longest first, so the two charts do not share one expected order.
        def ranked(key):
            return sorted((m for m in payload["models"] if m.get(key) is not None),
                          key=lambda m: m[key], reverse=True)

        def bar_widths(sel):
            return page.evaluate(
                """(sel) => [...document.querySelectorAll(sel + ' .row')].map((r) => {
                     const t = r.querySelector('.track').getBoundingClientRect().width;
                     return t ? r.querySelector('.bar').getBoundingClientRect().width / t : 0;
                   })""", sel)

        def proportional(sel, key, label):
            got = bar_widths(sel)
            vals = [m[key] for m in ranked(key)]
            peak = max(vals) or 1
            off = [round(g - v / peak, 4) for g, v in zip(got, vals)
                   if abs(g - v / peak) > 0.01]
            check(label, len(got) == len(vals) and not off,
                  f"{len(off)} of {len(vals)} off, first {off[:1]}")

        def longest_first(sel, label):
            widths = bar_widths(sel)
            rising = [round(b - a, 4) for a, b in zip(widths, widths[1:]) if b > a + 1e-3]
            check(label, not rising, f"{len(rising)} ascending steps, first {rising[:1]}")

        proportional("#chart-cost", "total_cost_usd",
                     "cost bar widths are proportional to spend")
        proportional("#chart-time", "total_elapsed_s",
                     "time bar widths are proportional to duration")
        longest_first("#chart-cost", "cost bars run longest first")
        longest_first("#chart-time", "time bars run longest first")

        lin = bar_widths("#chart-cost")
        page.click('#scale-cost button[data-scale="log"]')
        check("log toggle marks itself pressed",
              page.get_attribute('#scale-cost button[data-scale="log"]', "aria-pressed") == "true")
        logw = bar_widths("#chart-cost")
        check("log toggle rescales the cost bars",
              any(abs(a - b) > 0.02 for a, b in zip(lin, logw)),
              f"max delta {max(abs(a - b) for a, b in zip(lin, logw)):.3f}")
        page.click('#scale-cost button[data-scale="linear"]')

        dots = page.eval_on_selector_all("#scatter circle", "e => e.length")
        check("scatter has points", dots >= n - 2, f"{dots} points")

        body_rows = page.eval_on_selector_all("#tbody tr", "e => e.length")
        check("table lists every model", body_rows == n, f"{body_rows} vs {n}")

        # sorting: ascending then descending cost (column 7 after the quality column)
        page.click('#tbl th[data-k="total_cost_usd"]')
        page.wait_for_timeout(80)
        asc = page.eval_on_selector_all(
            "#tbody tr td:nth-child(7)", "els => els.map(e => e.textContent.trim())")
        page.click('#tbl th[data-k="total_cost_usd"]')
        page.wait_for_timeout(80)
        desc = page.eval_on_selector_all(
            "#tbody tr td:nth-child(7)", "els => els.map(e => e.textContent.trim())")
        check("sorting toggles direction", asc[0] != desc[0] or asc == desc[::-1],
              f"{asc[0]} then {desc[0]}")

        # quality: bars, rubric, and the sortable score column must agree
        ratings = json.loads(page.eval_on_selector("#data", "e => e.textContent")).get("quality", [])
        q_bars = page.eval_on_selector_all("#chart-quality .row", "e => e.length")
        check("quality bar per rated report", q_bars == len(ratings), f"{q_bars} vs {len(ratings)}")
        rubric = page.eval_on_selector_all("#rubric-body tr", "e => e.length")
        check("rubric lists every dimension", rubric == 7, f"{rubric} rows")
        page.click('#tbl th[data-k="quality_score"]')
        page.wait_for_timeout(80)
        qscores = page.eval_on_selector_all(
            "#tbody tr td:nth-child(4)", "els => els.map(e => parseFloat(e.textContent))")
        numeric = [q for q in qscores if not (q != q)]
        check("quality column is numeric", len(numeric) == len(qscores) and len(qscores) > 20,
              f"{len(numeric)}/{len(qscores)} numeric")
        check("quality sort is monotonic", numeric == sorted(numeric) or numeric == sorted(numeric, reverse=True),
              f"{numeric[:3]} ... {numeric[-3:]}")
        q_cav = page.eval_on_selector_all("#q-caveats li", "e => e.length")
        check("quality caveats populated", q_cav >= 4, f"{q_cav} caveats")
        stats = json.loads(page.eval_on_selector("#data", "e => e.textContent")).get("quality_stats", {})
        check("correlation exposed with n", stats.get("spearman_cost_quality") is not None and stats.get("n", 0) > 20,
              f"rho={stats.get('spearman_cost_quality')} n={stats.get('n')}")

        # ROI: bars, value table, scatter and the derived frontier claims
        payload2 = json.loads(page.eval_on_selector("#data", "e => e.textContent"))
        roi = payload2.get("roi", {})
        roi_rows = [m for m in payload2["models"]
                    if m.get("roi_score") is not None and m.get("quality_score") is not None]
        roi_bars = page.eval_on_selector_all("#chart-roi .row", "e => e.length")
        check("ROI bar per eligible run", roi_bars == len(roi_rows), f"{roi_bars} vs {len(roi_rows)}")
        # ROI bars are segmented, and the segments must add up to the score so the
        # colours explain the bar rather than mislead about its length.
        seg_sums = page.evaluate("""() => [...document.querySelectorAll('#chart-roi .stack')].map(
            (s) => [...s.children].reduce((a, c) => a + parseFloat(c.style.width || 0), 0))""")
        seg_vals = page.eval_on_selector_all("#chart-roi .val", "e => e.map(v => parseFloat(v.textContent))")
        mismatched = sum(1 for a, b in zip(seg_sums, seg_vals) if abs(a - b) > 0.6)
        check("ROI segments sum to the score", mismatched == 0, f"{mismatched} mismatched of {len(seg_vals)}")
        seg_counts = set(page.evaluate(
            "() => [...document.querySelectorAll('#chart-roi .stack')].map(s => s.children.length)"))
        check("ROI bars are segmented by factor", seg_counts == {3}, f"segment counts {seg_counts}")
        # Slice widths must track factor levels, not shortfall: a factor at full
        # marks has to be a wide slice, never an invisible one. Rows are matched to
        # data by position, because two directories can run the same model name.
        proportional = page.evaluate("""() => {
            const data = JSON.parse(document.getElementById('data').textContent);
            const by = Object.fromEntries(data.models.map((m) => [m.directory, m]));
            const order = (data.roi && data.roi.models) || [];
            const rows = [...document.querySelectorAll('#chart-roi .row')];
            let bad = [];
            rows.forEach((row, idx) => {
              const model = by[order[idx]];
              if (!model) return;
              const levels = [model.quality_attainment, model.cost_efficiency, model.time_efficiency];
              const sum = levels.reduce((a, b) => a + b, 0) || 1;
              const widths = [...row.querySelectorAll('.stack span')]
                .map((s) => parseFloat(s.style.width) || 0);
              levels.forEach((lv, i) => {
                const want = (lv / sum) * model.roi_score;
                if (Math.abs(want - widths[i]) > 0.5) bad.push([model.directory, i, widths[i], +want.toFixed(2)]);
              });
            });
            return bad;
        }""")
        check("ROI slice widths are proportional to factor levels", not proportional,
              f"{len(proportional)} mismatches, first {proportional[:1]}")

        # Two attempt directories ran the same model, so a model-name caption would
        # be ambiguous. Every chart/table row label must be distinct.
        dupes = page.evaluate("""() => {
            const grab = (sel) => [...document.querySelectorAll(sel)].map((n) => n.textContent.trim());
            const out = {};
            [['#chart-roi .lbl', 'roi chart'], ['#chart-cost .lbl', 'cost chart'],
             ['#value-body tr td:first-child', 'value table']].forEach(([sel, name]) => {
              const labels = grab(sel);
              const seen = new Set(), dup = new Set();
              labels.forEach((l) => (seen.has(l) ? dup.add(l) : seen.add(l)));
              if (dup.size) out[name] = [...dup];
            });
            return out;
        }""")
        check("chart and table row labels are unique", not dupes, str(dupes))
        check("ROI factor legend rendered",
              page.eval_on_selector("#roi-chart-legend", "e => e.innerText").count("Quality") == 1)
        check("ROI legend explains slice sizing",
              "slice" in page.eval_on_selector("#roi-chart-legend", "e => e.innerText").lower())
        vrows = page.eval_on_selector_all("#value-body tr", "e => e.length")
        check("value table lists eligible runs", vrows == len(roi_rows), f"{vrows} vs {len(roi_rows)}")
        dots2 = page.eval_on_selector_all("#roi-scatter circle", "e => e.length")
        check("ROI scatter has points", dots2 == len(roi_rows), f"{dots2} points")
        scores = [m["roi_score"] for m in roi_rows]
        check("ROI scores are within 0-100", all(0 <= s <= 100 for s in scores),
              f"min={min(scores)} max={max(scores)}")
        on_frontier = [m for m in roi_rows if m.get("on_frontier")]
        check("frontier is non-empty and smaller than the field", 0 < len(on_frontier) < len(roi_rows),
              f"{len(on_frontier)} of {len(roi_rows)}")
        # a frontier run must not be dominated: nothing cheaper scores at least as well
        undominated = all(
            m["quality_score"] > max((o["quality_score"] for o in roi_rows
                                      if o["total_cost_usd"] < m["total_cost_usd"]),
                                     default=-1)
            for m in on_frontier if m.get("pareto_cost"))
        check("cost-frontier runs are truly undominated", undominated)
        roi_cav = page.eval_on_selector_all("#roi-caveats li", "e => e.length")
        check("ROI caveats populated", roi_cav >= 4, f"{roi_cav} caveats")

        # The method section must actually explain the score the page computes.
        method = page.eval_on_selector_all(
            "#roi-method li", "e => e.map(x => x.textContent.replace(/\\s+/g, ' '))")
        formula = page.eval_on_selector(".formula", "e => e.textContent")
        check("ROI method section explains the calculation", len(method) >= 5,
              f"{len(method)} bullets")
        check("ROI formula block states the score",
              all(t in formula for t in ("attainment", "cost_efficiency", "time_efficiency",
                                         "ROI $+t")), formula[:60])
        # Numbers quoted in prose must match the data, or the section teaches the wrong thing.
        st = roi.get("stats", {})
        join = " ".join(method)
        check("ROI method frontier counts match the data",
              f"{st.get('frontier_union_size')} of {len(roi_rows)}" in join,
              f"union={st.get('frontier_union_size')} cost={st.get('frontier_size')} "
              f"time={st.get('time_frontier_size')}")
        check("ROI frontier note matches the data",
              f"{st.get('frontier_union_size')} of {roi.get('n')}" in page.text_content("#frontier-note"),
              page.text_content("#frontier-note"))
        # The overpayer figure must be attributed to the run that actually holds it,
        # not to whichever run topped the other (uncapped) multiple.
        worst = max(roi_rows, key=lambda m: m.get("cost_multiple_paid") or 0)
        kpi = page.eval_on_selector_all(
            "#roi-kpis .kpi", "e => e.map(x => x.textContent.replace(/\\s+/g, ' '))")
        overpay = next((k for k in kpi if "Overpaying" in k), "")
        best_in_data = [m for m in roi_rows if m["directory"] == st.get("best_roi")]
        win = best_in_data[0] if best_in_data else None
        check("overpayer stat names the run that holds it",
              worst["model"] in overpay or worst["directory"] in overpay, overpay)
        check("worked example quotes the winning run's own factors",
              bool(win) and all(str(win[k]).rstrip("0").rstrip(".") in join
                                for k in ("roi_score_cost", "roi_score_time", "roi_score")),
              f"winner={win['directory'] if win else None}")
        check("ROI stats expose sensitivity", bool(roi.get("stats", {}).get("sensitivity")),
              f"{list(roi.get('stats', {}).get('sensitivity', {}))}")
        # the money-only ranking must exist, differ-or-match, and be sortable
        check("money-only ROI ranking exposed",
              bool(roi.get("models_by_cost_roi")) and roi.get("stats", {}).get("best_roi_cost"),
              f"best={roi.get('stats', {}).get('best_roi_cost')} "
              f"vs combined={roi.get('stats', {}).get('best_roi')}")
        page.click('#tbl th[data-k="roi_score_cost"]')
        page.wait_for_timeout(100)
        rc = page.eval_on_selector_all(
            "#tbody tr", "els => els.map(r => parseFloat(r.children[4].textContent))")
        check("money-only ROI column sorts", rc == sorted(rc) or rc == sorted(rc, reverse=True),
              f"{rc[:4]}")
        page.click('#tbl th[data-k="roi_score"]')
        page.wait_for_timeout(100)
        rct = page.eval_on_selector_all(
            "#tbody tr", "els => els.map(r => parseFloat(r.children[5].textContent))")
        check("combined ROI column sorts", rct == sorted(rct) or rct == sorted(rct, reverse=True),
              f"{rct[:4]}")

        # filtering
        page.fill("#q", "opus")
        page.wait_for_timeout(120)
        filtered = page.eval_on_selector_all("#tbody tr", "e => e.length")
        check("text filter narrows the table", 0 < filtered < n, f"{filtered} rows for 'opus'")
        page.fill("#q", "")
        page.click("#f-multi")
        page.wait_for_timeout(120)
        multi = page.eval_on_selector_all("#tbody tr", "e => e.length")
        expected_multi = len([m for m in payload["models"] if m.get("prompts_at_least", 1) > 1])
        check("prompt filter matches data", multi == expected_multi, f"{multi} vs {expected_multi}")
        page.click("#f-all")
        page.wait_for_timeout(80)

        # provenance and caveats must carry real content
        cav = page.eval_on_selector_all("#caveats li", "e => e.length")
        check("caveats populated", cav >= 3, f"{cav} caveats")
        prov = page.eval_on_selector("#provenance", "e => e.textContent.trim()")
        check("provenance cites the sources", "usage.jsonl" in prov and "tesseract" in prov.lower())

        shots = [("desktop", 1280, 2200), ("mobile", 390, 1400)]
        for name, w, h in shots:
            page.set_viewport_size({"width": w, "height": h})
            page.wait_for_timeout(150)
            overflow = page.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"no page overflow at {w}px", overflow <= 2, f"overflow {overflow}px")
            page.screenshot(path=str(SHOTS / f"report-{name}.png"), full_page=True)

        # The results table must fit its panel on a desktop screen: no horizontal
        # scrollbar inside the table container. Below ~1280px internal scrolling is
        # correct behaviour, so this is asserted at the widths people actually use.
        for w in (1920, 1440, 1280):
            page.set_viewport_size({"width": w, "height": 1000})
            page.wait_for_timeout(120)
            worst = page.evaluate("""() => {
                let worst = 0;
                document.querySelectorAll('.scroll').forEach((s) => {
                  const t = s.querySelector('table');
                  if (t) worst = Math.max(worst, t.scrollWidth - s.clientWidth);
                });
                return Math.round(worst);
            }""")
            check(f"results table fits without scrolling at {w}px", worst <= 2,
                  f"{worst}px overflow")

        # dark theme
        page.set_viewport_size({"width": 1280, "height": 900})
        page.click("#theme")
        page.wait_for_timeout(150)
        theme = page.evaluate("() => document.documentElement.dataset.theme")
        check("theme toggle works", theme in ("dark", "light"), f"theme={theme}")
        page.screenshot(path=str(SHOTS / "report-dark.png"), full_page=True)
        browser.close()

    print(f"\n{checks - len(failures)}/{checks} checks passed")
    (SHOTS / "summary.json").write_text(json.dumps(
        {"checks": checks, "failures": failures}, indent=1), encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
