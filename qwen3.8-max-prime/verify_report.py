#!/usr/bin/env python3
"""Render engine-comparison-report.html in headless Chromium and verify it.

Checks: console errors, JS-populated table row counts, theme toggle, sorting,
filtering, search, and captures desktop + narrow screenshots for visual review.
"""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
TARGET = (HERE / "engine-comparison-report.html").resolve().as_uri()
SHOTS = HERE / "shots"
SHOTS.mkdir(exist_ok=True)

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def main() -> int:
    console_errors: list[str] = []
    page_errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        page.goto(TARGET, wait_until="networkidle")
        page.wait_for_timeout(400)

        check("no page errors", not page_errors, "; ".join(page_errors[:3]))
        check("no console errors", not console_errors, "; ".join(console_errors[:3]))

        # --- JS-populated tables ---
        single_rows = page.locator("#single-body tr").count()
        check("single-node table populated", single_rows == 22, f"{single_rows} rows")

        single_cols = page.locator("#single-head th").count()
        check("single-node header columns", single_cols == 7, f"{single_cols} cols (expect 1+5+1)")

        cluster_rows = page.locator("#cluster-body tr").count()
        check("cluster table populated", cluster_rows == 99, f"{cluster_rows} rows")

        cluster_cols = page.locator("#cluster-head th").count()
        check("cluster header columns", cluster_cols == 12, f"{cluster_cols} cols")

        # --- controls rendered by JS ---
        check("benchmark segmented control", page.locator("#seg-sbench button").count() == 2)
        check("sf segmented control", page.locator("#seg-ssf button").count() == 4)
        check("cluster sf control", page.locator("#seg-csf button").count() == 3)
        check("cluster status filter", page.locator("#seg-cfilter button").count() == 4)

        # --- meta/status text populated ---
        smeta = page.inner_text("#single-meta")
        check("single meta text", "queries shown" in smeta, smeta[:70])
        cmeta = page.inner_text("#cluster-meta")
        check("cluster meta text", "per-query wins" in cmeta, cmeta[:70])

        # --- switching benchmark + scale factor ---
        page.click('#seg-sbench button[data-v="TPC-DS"]')
        page.wait_for_timeout(150)
        check("switch to TPC-DS gives 99 rows", page.locator("#single-body tr").count() == 99)
        page.click('#seg-ssf button[data-v="1000"]')
        page.wait_for_timeout(150)
        marker_flags = page.locator("#single-body .flag").count()
        check("markers flagged at TPC-DS SF1000", marker_flags == 3, f"{marker_flags} flags")

        # --- search ---
        page.fill("#single-search", "23")
        page.wait_for_timeout(150)
        found = page.locator("#single-body tr").count()
        check("search narrows rows", 0 < found < 99, f"{found} rows for '23'")
        page.fill("#single-search", "zzzz")
        page.wait_for_timeout(150)
        check("empty state shown", page.locator("#single-empty").is_visible())
        page.fill("#single-search", "")
        page.wait_for_timeout(150)

        # --- sorting: initial state is query ascending; clicks toggle direction ---
        aria0 = page.get_attribute('#single-head th[data-sort="q"]', "aria-sort")
        check("initial aria-sort is ascending", aria0 == "ascending", str(aria0))
        first0 = page.inner_text("#single-body tr:first-child th").strip()
        check("initial order starts at Q1", first0 == "Q1", first0)

        page.click('#single-head th[data-sort="q"]')
        page.wait_for_timeout(120)
        aria1 = page.get_attribute('#single-head th[data-sort="q"]', "aria-sort")
        first1 = page.inner_text("#single-body tr:first-child th").strip()
        check("one click sorts descending", aria1 == "descending" and first1 == "Q99",
              f"{aria1} / {first1}")

        page.click('#single-head th[data-sort="q"]')
        page.wait_for_timeout(120)
        aria2 = page.get_attribute('#single-head th[data-sort="q"]', "aria-sort")
        first2 = page.inner_text("#single-body tr:first-child th").strip()
        check("second click returns to ascending", aria2 == "ascending" and first2 == "Q1",
              f"{aria2} / {first2}")

        # Sorting by a numeric engine column, descending-ish by magnitude.
        page.click('#single-head th[data-sort="DuckDB 1.5.5"]')
        page.wait_for_timeout(150)
        aria3 = page.get_attribute('#single-head th[data-sort="DuckDB 1.5.5"]', "aria-sort")
        check("numeric column sortable", aria3 == "ascending", str(aria3))
        duck_col = page.eval_on_selector_all(
            "#single-body tr td:nth-child(4) .val",
            "els => els.map(e => parseFloat(e.textContent.replace(/,/g,'')))"
        )
        check("numeric sort is monotonic", duck_col == sorted(duck_col), str(duck_col[:6]))
        page.click('#single-head th[data-sort="q"]')
        page.wait_for_timeout(120)

        # --- cluster status filter ---
        page.click('#seg-csf button[data-v="1000"]')
        page.wait_for_timeout(150)
        page.click('#seg-cfilter button[data-v="gap"]')
        page.wait_for_timeout(150)
        gap_rows = page.locator("#cluster-body tr").count()
        check("gap filter yields 51 rows at SF1000", gap_rows == 51, f"{gap_rows} rows")
        page.click('#seg-cfilter button[data-v="all"]')
        page.wait_for_timeout(150)

        # --- cluster SF 10000 nulls render as em dash, not 'null'/'undefined' ---
        page.click('#seg-csf button[data-v="10000"]')
        page.wait_for_timeout(200)
        body_txt = page.inner_text("#cluster-body")
        check("no literal null/undefined in cluster table",
              "null" not in body_txt and "undefined" not in body_txt and "NaN" not in body_txt)
        check("em dash used for missing values", "—" in body_txt)
        single_engine_pills = page.locator("#cluster-body .pill.other").count()
        check("single-engine statuses pill-marked", single_engine_pills == 5,
              f"{single_engine_pills} pills")

        # --- whole-document text sanity ---
        full = page.inner_text("body")
        for bad in ("None", "undefined", "NaN", "[object Object]"):
            check(f"no stray '{bad}' in rendered text", bad not in full)

        # --- theme toggle ---
        initial = page.get_attribute("html", "data-theme")
        page.click("#theme-toggle")
        page.wait_for_timeout(200)
        toggled = page.get_attribute("html", "data-theme")
        check("theme toggle switches", initial != toggled, f"{initial} -> {toggled}")

        # --- screenshots: light desktop ---
        page.click("#theme-toggle")
        page.wait_for_timeout(200)
        page.screenshot(path=str(SHOTS / "01-desktop-light-top.png"))
        page.locator("#totals").scroll_into_view_if_needed()
        page.wait_for_timeout(250)
        page.screenshot(path=str(SHOTS / "02-desktop-totals.png"))
        page.locator("#scaling").scroll_into_view_if_needed()
        page.wait_for_timeout(250)
        page.screenshot(path=str(SHOTS / "03-desktop-scaling.png"))
        page.locator("#per-query").scroll_into_view_if_needed()
        page.wait_for_timeout(250)
        page.screenshot(path=str(SHOTS / "04-desktop-perquery.png"))
        page.locator("#cluster").scroll_into_view_if_needed()
        page.wait_for_timeout(250)
        page.screenshot(path=str(SHOTS / "05-desktop-cluster.png"))
        page.locator("#notes").scroll_into_view_if_needed()
        page.wait_for_timeout(250)
        page.screenshot(path=str(SHOTS / "06-desktop-notes.png"))

        # --- dark theme ---
        page.click("#theme-toggle")
        page.wait_for_timeout(250)
        page.evaluate("window.scrollTo(0,0)")
        page.wait_for_timeout(200)
        page.screenshot(path=str(SHOTS / "07-desktop-dark-top.png"))
        page.locator("#per-query").scroll_into_view_if_needed()
        page.wait_for_timeout(250)
        page.screenshot(path=str(SHOTS / "08-desktop-dark-perquery.png"))

        # --- contrast sampling in both themes ---
        contrast = {}
        for theme in ("light", "dark"):
            page.evaluate(f"document.documentElement.setAttribute('data-theme','{theme}')")
            page.wait_for_timeout(150)
            contrast[theme] = page.evaluate("""() => {
              const g = (s, p) => {
                const el = document.querySelector(s);
                if (!el) return null;
                return getComputedStyle(el)[p];
              };
              return {
                bodyFg: g('body','color'), bodyBg: g('body','backgroundColor'),
                mutedFg: g('.lede','color'),
                noteFg: g('.note','color'), noteBg: g('.note','backgroundColor'),
                faintFg: g('.stat-label','color'),
                thFg: g('table.data thead th','color'), thBg: g('table.data thead th','backgroundColor'),
                subFg: g('td.cell .sub','color'),
                tocFg: g('.toc a','color'), tocBg: g('.toc','backgroundColor'),
                legendFg: g('.legend','color'),
                captionFg: g('table.data caption','color'),
                cardBg: g('.card','backgroundColor'),
                statBg: g('.stat','backgroundColor'),
                winFg: g('.win','color'), winBg: g('.win','backgroundColor'),
                flagFg: g('.flag','color'), flagBg: g('.flag','backgroundColor'),
                pillFg: g('.pill','color'), pillBg: g('.pill','backgroundColor'),
                linkFg: g('a','color'),
              };
            }""")
        check("contrast samples collected", all(contrast.values()), json.dumps(contrast)[:120])

        browser.close()

        # --- narrow mobile pass ---
        browser = p.chromium.launch()
        m = browser.new_page(viewport={"width": 390, "height": 844},
                             device_scale_factor=2, is_mobile=True, has_touch=True)
        merr: list[str] = []
        m.on("pageerror", lambda e: merr.append(str(e)))
        m.goto(TARGET, wait_until="networkidle")
        m.wait_for_timeout(400)
        check("mobile: no page errors", not merr, "; ".join(merr[:2]))

        doc_w = m.evaluate("document.documentElement.scrollWidth")
        win_w = m.evaluate("window.innerWidth")
        check("mobile: no page-level horizontal overflow", doc_w <= win_w + 1,
              f"scrollWidth={doc_w} innerWidth={win_w}")

        # Tables may scroll internally; that is intended.
        wrap_w = m.evaluate("document.querySelector('#per-query .table-wrap').scrollWidth")
        check("mobile: wide table scrolls inside its wrapper", wrap_w > win_w,
              f"table scrollWidth={wrap_w}")

        m.screenshot(path=str(SHOTS / "09-mobile-top.png"))
        m.locator("#summary").scroll_into_view_if_needed()
        m.wait_for_timeout(200)
        m.screenshot(path=str(SHOTS / "10-mobile-summary.png"))
        m.locator("#scaling").scroll_into_view_if_needed()
        m.wait_for_timeout(200)
        m.screenshot(path=str(SHOTS / "11-mobile-scaling.png"))
        m.locator("#per-query").scroll_into_view_if_needed()
        m.wait_for_timeout(200)
        m.screenshot(path=str(SHOTS / "12-mobile-perquery.png"))

        # Touch target sizing on the segmented controls.
        sizes = m.evaluate("""() => {
          const out = [];
          document.querySelectorAll('#seg-sbench button, #seg-ssf button, .theme-btn').forEach(b => {
            const r = b.getBoundingClientRect();
            out.push({t: b.textContent.trim(), w: Math.round(r.width), h: Math.round(r.height)});
          });
          return out;
        }""")
        small = [s for s in sizes if s["h"] < 30 or s["w"] < 34]
        check("mobile: touch targets >= 30px tall", not small, json.dumps(small[:6]))

        browser.close()

    Path(SHOTS / "contrast.json").write_text(json.dumps(contrast, indent=2))

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILURES:")
        for name, _, detail in failed:
            print(f"  - {name}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
