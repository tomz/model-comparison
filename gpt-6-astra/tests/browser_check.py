"""Exercise the report in the installed Chrome browser, offline."""
from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Verify interactive behavior and capture desktop, mobile and print evidence."""
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    output = ROOT / 'verification'
    output.mkdir(exist_ok=True)
    source = json.loads((ROOT / 'engine-comparison-summary-data.json').read_text())
    errors: list[str] = []
    requests: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1, offline=True)
        page = context.new_page()
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.on('request', lambda req: requests.append(req.url))
        page.goto((ROOT / 'engine-comparison-summary.html').as_uri())
        page.wait_for_selector('.bar-row')
        assert page.locator('.bar-row').count() == 5
        assert page.locator('.cluster-card').count() == 3
        page.screenshot(path=str(output / 'desktop.png'), full_page=True)
        for suite in ['TPC-H', 'TPC-DS']:
            for sf in ['1', '10', '100', '1000', 'all']:
                for basis in ['time', 'canonical']:
                    page.select_option('#suite', suite)
                    page.select_option('#scale', sf)
                    page.select_option('#basis', basis)
                    rows = [r for r in source['totals'][suite] if r['sf'] == sf]
                    available = [r for r in rows if r[basis] is not None]
                    leader = min(available, key=lambda r: r[basis])
                    assert f'{leader[basis]:,.2f} s' in page.locator('#single-reading').inner_text()
                    assert page.locator('.bar-row').count() == 5
        page.select_option('#suite', 'TPC-DS')
        page.select_option('#scale', '1000')
        page.select_option('#basis', 'time')
        page.fill('#query-search', 'Q18')
        assert page.locator('#query-body tr').count() == 1
        assert page.locator('#query-body .badge').inner_text() == 'P'
        with page.expect_download() as event:
            page.click('#export-csv')
        rows = list(csv.reader(io.StringIO(Path(event.value.path()).read_text())))
        assert rows[1][0] == 'Q18' and len(rows) == 2
        assert rows[1][4] == 'P'
        page.fill('#query-search', 'nothing')
        assert 'No matching query' in page.locator('#query-body').inner_text()
        assert page.locator('#export-csv').is_disabled()
        page.fill('#query-search', '')
        page.select_option('#query-mode', 'cluster')
        page.select_option('#query-scale', '10000')
        assert page.locator('#query-body tr').count() == 99
        assert page.locator('#query-suite-field').is_hidden()
        page.fill('#query-search', '23')
        assert 'timeout' in page.locator('#query-body').inner_text()
        assert page.locator('#query-body td').nth(0).inner_text() == '—'
        page.fill('#query-search', '')
        page.select_option('#query-sort', 'slowest')
        timed = [r for r in source['clusterQueries']['10000'] if r['r'] is not None or r['g'] is not None]
        slowest = max(timed, key=lambda r: max(v for v in [r['r'], r['g']] if v is not None))
        assert page.locator('#query-body th').first.inner_text() == f'Q{slowest["q"]}'
        with page.expect_download() as event:
            page.click('#download-json')
        assert json.loads(Path(event.value.path()).read_text()) == source
        page.select_option('#query-mode', 'single')
        assert page.locator('#query-scale').input_value() == '1000'
        page.select_option('#query-sort', 'query')
        for width in [1440, 768, 390, 320]:
            page.set_viewport_size({'width': width, 'height': 900})
            page.evaluate('window.scrollTo(0,0)')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow at {width}px'
            for selector in ['#single', '#cluster', '#queries', '#method']:
                page.locator(selector).scroll_into_view_if_needed()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.evaluate('window.scrollTo(0,0)')
            if width == 390:
                page.screenshot(path=str(output / 'mobile.png'), full_page=True)
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.locator('#single').screenshot(path=str(output / 'single-node.png'))
        page.locator('#cluster').screenshot(path=str(output / 'cluster.png'))
        page.evaluate('window.scrollTo(0,0)')
        page.reload()
        page.keyboard.press('Tab')
        assert page.locator('.skip').evaluate('(el) => el === document.activeElement')
        page.keyboard.press('Enter')
        page.pdf(path=str(output / 'report.pdf'), format='A4', print_background=True)
        assert not errors, errors
        assert not [url for url in requests if url.startswith(('http:', 'https:'))], requests
        browser.close()
    logging.info('PASS: 20 single-node views, query search/sort, missing results, mode switching, CSV/JSON exports, keyboard skip link, four viewport widths, offline requests and PDF generation.')


if __name__ == '__main__':
    main()
