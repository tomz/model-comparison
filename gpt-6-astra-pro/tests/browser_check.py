"""Run local Chromium acceptance checks and capture representative report views."""
from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "verification"


def main() -> None:
    """Exercise the self-contained report without a web server or network access."""
    OUTPUT.mkdir(exist_ok=True)
    source = json.loads((ROOT / "engine-comparison-summary-data.json").read_text())
    errors: list[str] = []
    requests: list[str] = []
    checks: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1050}, offline=True)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url) if request.url.startswith(("http:", "https:")) else None)
        page.goto((ROOT / "engine-comparison-report.html").as_uri())
        expect(page.locator("#app-error")).to_be_hidden()
        expect(page.locator(".bar-row")).to_have_count(5)
        expect(page.locator("#finding-h")).to_have_text("2.9%")
        expect(page.locator("#finding-ds")).to_have_text("3.7%")
        expect(page.locator("#finding-cluster")).to_have_text("31.8%")
        checks.append("Offline file:// load; findings match source-derived calculations")
        page.screenshot(path=str(OUTPUT / "desktop-overview.png"))
        page.evaluate("window.scrollTo({top: document.querySelector('#single').offsetTop - 72, behavior: 'instant'})")
        page.screenshot(path=str(OUTPUT / "desktop-single.png"))
        for suite in source["totals"]:
            page.get_by_label("Benchmark suite", exact=True).select_option(suite)
            for scale in ("all", "1", "10", "100", "1000"):
                page.get_by_label("Scale factor", exact=True).select_option(scale)
                for basis in ("time", "canonical"):
                    page.get_by_label("Timing basis").select_option(basis)
                    rows = [r for r in source["totals"][suite] if r["sf"] == scale]
                    actual = page.locator(".bar-number").all_text_contents()
                    for text, row in zip(actual, rows, strict=True):
                        assert ("Not supplied" in text) == (row[basis] is None), (suite, scale, basis, text)
                        if row[basis] is not None:
                            assert f"{row[basis]:,.2f} s" in text, (suite, scale, basis, text)
                    expect(page.locator("#scale-body tr")).to_have_count(5)
        checks.append("All 20 suite/scale/basis combinations render source values and preserve nulls")
        page.get_by_label("Benchmark suite", exact=True).select_option("TPC-DS")
        page.get_by_label("Scale factor", exact=True).select_option("1000")
        page.get_by_label("Timing basis").select_option("time")
        page.get_by_label("Show", exact=True).select_option("flagged")
        expected_flags = sum(any(r["markers"]) for r in source["single"]["TPC-DS"]["1000"])
        expect(page.locator("#query-body tr")).to_have_count(expected_flags)
        with page.expect_download() as event:
            page.get_by_role("button", name="Export filtered CSV ↓", exact=True).nth(0).click()
        download = event.value
        csv_rows = list(csv.reader(io.StringIO(Path(download.path()).read_text(encoding="utf-8-sig"))))
        assert len(csv_rows) == expected_flags + 1
        checks.append("Source-flag filter and full-precision filtered single-node CSV download")
        page.locator("#query-search").fill("Q999")
        expect(page.locator("#query-body")).to_contain_text("No matching queries")
        expect(page.locator("#query-next")).to_be_disabled()
        page.locator("#query-search").fill("Q18")
        expect(page.locator("#query-body tr")).to_have_count(1)
        expect(page.locator("#query-body")).to_contain_text("P")
        page.locator("#query-search").fill("")
        page.get_by_label("Show", exact=True).select_option("all")
        page.get_by_label("Scale factor", exact=True).select_option("all")
        page.locator("#query-next").click()
        expect(page.locator("#query-count")).to_contain_text("21–40 of 396")
        page.locator("#query-prev").click()
        page.get_by_label("Order by").select_option("spread")
        spreads = []
        for sf, rows in source["single"]["TPC-DS"].items():
            spreads.extend((max(r["times"])-min(r["times"]), r["q"]) for r in rows)
        assert f"Q{max(spreads)[1]} " in page.locator("#query-body tr").first.inner_text()
        checks.append("Search, empty state, pagination, and largest-spread sorting")
        for scale in source["cluster"]:
            page.get_by_label("Cluster scale factor").select_option(scale)
            expect(page.locator(".metric-card")).to_have_count(3)
            for metric in ("time", "cpu", "cores", "memory", "p50", "p95", "max", "memtime"):
                page.get_by_label("Values to compare").select_option(metric)
                expect(page.locator("#cluster-query-body tr")).to_have_count(20)
        checks.append("All 24 cluster scale/metric views render without runtime errors")
        page.get_by_label("Cluster scale factor").select_option("10000")
        page.get_by_label("Values to compare").select_option("time")
        page.get_by_label("Coverage", exact=True).select_option("unpaired")
        expect(page.locator("#cluster-query-body tr")).to_have_count(5)
        expect(page.locator("#cluster-query-body")).to_contain_text("Q23")
        expect(page.locator("#cluster-query-body")).to_contain_text("unvalidated")
        with page.expect_download() as event:
            page.locator("#export-cluster").click()
        csv_rows = list(csv.reader(io.StringIO(Path(event.value.path()).read_text(encoding="utf-8-sig"))))
        assert len(csv_rows) == 6
        assert csv_rows[1][1:4] == ["23", "", ""]
        checks.append("SF 10,000 unpaired coverage, verbatim statuses, and missing-value CSV export")
        with page.expect_download() as event:
            page.get_by_role("button", name="Download embedded dataset ↓").click()
        assert json.loads(Path(event.value.path()).read_text()) == source
        checks.append("Downloaded embedded JSON preserves every source value")
        # Reset to the default presentation before layout captures.
        page.reload()
        page.evaluate("window.scrollTo({top: document.querySelector('#cluster').offsetTop - 72, behavior: 'instant'})")
        page.screenshot(path=str(OUTPUT / "desktop-cluster.png"))
        page.get_by_label("Cluster scale factor").select_option("10000")
        page.evaluate("window.scrollTo({top: document.querySelector('#cluster').offsetTop - 72, behavior: 'instant'})")
        page.screenshot(path=str(OUTPUT / "desktop-cluster-10000.png"))
        for width in (1440, 1024, 768, 390, 320):
            page.set_viewport_size({"width": width, "height": 900})
            overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
            assert not overflow, f"Page-wide overflow at {width}px"
            # Data tables are intentionally scrollable locally, not page-wide.
            for element in page.locator("select,input,button:visible").all():
                box = element.bounding_box()
                assert box and box["x"] >= 0 and box["x"]+box["width"] <= width+1, (width, box)
        checks.append("No page-wide horizontal overflow or offscreen controls at 1440/1024/768/390/320px")
        page.set_viewport_size({"width": 390, "height": 844})
        page.evaluate("window.scrollTo(0,0)")
        page.screenshot(path=str(OUTPUT / "mobile-overview.png"))
        page.evaluate("window.scrollTo({top: document.querySelector('#single').offsetTop - 72, behavior: 'instant'})")
        page.screenshot(path=str(OUTPUT / "mobile-single.png"))
        page.evaluate("window.scrollTo({top: document.querySelector('#cluster').offsetTop - 72, behavior: 'instant'})")
        page.screenshot(path=str(OUTPUT / "mobile-cluster.png"))
        page.set_viewport_size({"width": 1440, "height": 1050})
        page.reload()
        page.keyboard.press("Tab")
        expect(page.get_by_role("link", name="Skip to report")).to_be_focused()
        assert page.get_by_role("link", name="Skip to report").evaluate("e => getComputedStyle(e).outlineStyle") != "none"
        page.keyboard.press("Enter")
        assert page.evaluate("location.hash") == "#main"
        checks.append("Keyboard skip link and visible focus ring")
        page.emulate_media(reduced_motion="reduce")
        assert page.evaluate("getComputedStyle(document.documentElement).scrollBehavior") == "auto"
        page.emulate_media(media="print")
        expect(page.locator(".nav")).to_be_hidden()
        page.pdf(path=str(OUTPUT / "print-preview.pdf"), format="A4", print_background=True, margin={"top":"12mm","right":"10mm","bottom":"12mm","left":"10mm"})
        checks.append("Reduced-motion behavior and printable PDF generation")
        assert not errors, errors
        assert not requests, requests
        checks.append("No browser runtime errors and zero HTTP(S) requests")
        summary = {"browser": browser.version, "checks": checks, "errors": errors, "network_requests": requests, "limitations": ["No manual screen-reader audit", "Automated checks are not full accessibility certification"]}
        (OUTPUT / "browser-checks.json").write_text(json.dumps(summary, indent=2)+"\n")
        browser.close()
    for check in checks:
        logging.info("PASS %s", check)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
