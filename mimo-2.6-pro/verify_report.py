#!/usr/bin/env python3
"""Behavioral + accessibility verification for engine-comparison-report.html.

Usage: python3 verify_report.py   (requires the report to be served on :8741)
"""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "http://localhost:8741/engine-comparison-report.html"
OUT = Path(__file__).resolve().parent / "verify-shots"
OUT.mkdir(exist_ok=True)

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


CONTRAST_JS = """
() => {
  const cs = getComputedStyle(document.documentElement);
  const v = n => cs.getPropertyValue(n).trim();
  const pairs = [
    ['ink on bg', '--ink', '--bg'],
    ['ink-soft on bg', '--ink-soft', '--bg'],
    ['ink-mute on card', '--ink-mute', '--card'],
    ['accent on card', '--accent', '--card'],
    ['accent on accent-soft', '--accent', '--accent-soft'],
    ['good on good-soft', '--good', '--good-soft'],
    ['warn on warn-soft', '--warn', '--warn-soft'],
    ['bad on bad-soft', '--bad', '--bad-soft'],
    ['ink on bg-soft', '--ink', '--bg-soft'],
    ['ink-soft on card', '--ink-soft', '--card'],
    ['ink-mute on bg', '--ink-mute', '--bg'],
    ['ink-mute on bg-soft', '--ink-mute', '--bg-soft'],
    ['on-accent text on accent', '--on-accent', '--accent'],
    ['fill-ink text on fill-rust', '--fill-ink', '--fill-rust'],
    ['fill-ink text on fill-gluten', '--fill-ink', '--fill-gluten'],
    ['duckdb chip on card', '#c07c0b', '--card'],
    ['rust chip on card', '#2f6fd0', '--card'],
    ['gluten chip on card', '#9a5cd6', '--card'],
    ['teal chip on card', '#0e9c8b', '--card'],
    ['red chip on card', '#d94444', '--card'],
  ];
  const parse = (s) => {
    if (s.startsWith('#')) {
      const h = s.slice(1);
      const f = h.length === 3 ? h.split('').map(c => c + c).join('') : h;
      return [parseInt(f.slice(0,2),16), parseInt(f.slice(2,4),16), parseInt(f.slice(4,6),16)];
    }
    const m = s.match(/\\d+/g);
    return [+m[0], +m[1], +m[2]];
  };
  const lum = (rgb) => {
    const [r,g,b] = rgb.map(x => { x /= 255; return x <= .03928 ? x/12.92 : Math.pow((x+.055)/1.055, 2.4); });
    return .2126*r + .7152*g + .0722*b;
  };
  const ratio = (a, b) => {
    const la = lum(parse(a)), lb = lum(parse(b));
    return (Math.max(la, lb) + .05) / (Math.min(la, lb) + .05);
  };
  return pairs.map(([name, fg, bg]) => {
    const f = fg.startsWith('#') ? fg : v(fg);
    const b = bg.startsWith('#') ? bg : v(bg);
    return {name, ratio: +ratio(f, b).toFixed(2)};
  });
}
"""


def overflow_report(page):
    return page.evaluate("""
      () => {
        const de = document.documentElement;
        const offenders = [];
        for (const el of document.querySelectorAll('body *')) {
          const r = el.getBoundingClientRect();
          if (r.width === 0) continue;
          const inScroller = el.closest('.table-scroll');
          if (!inScroller && (r.right > de.clientWidth + 2 || r.left < -2)) {
            offenders.push(el.tagName.toLowerCase() + '.' + (el.className || '') + ' right=' + Math.round(r.right));
          }
        }
        return {scrollW: de.scrollWidth, clientW: de.clientWidth, offenders: offenders.slice(0, 8)};
      }
    """)


def run_scheme(pw, scheme, label):
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, color_scheme=scheme)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(URL, wait_until="networkidle")

    if scheme == "light":
        check("h1 count == 1", page.locator("h1").count() == 1)
        check("lang + title + viewport",
              page.evaluate("document.documentElement.lang") == "en"
              and "Comparison" in page.title()
              and page.locator('meta[name="viewport"]').count() == 1)
        page.keyboard.press("Tab")
        first_focus = page.evaluate("document.activeElement.className")
        check("skip link is first tab stop", "skip" in first_focus, first_focus)
        ids = page.evaluate("[...document.querySelectorAll('[id]')].map(e => e.id)")
        check("no duplicate ids", len(ids) == len(set(ids)))
        anchors = page.evaluate("[...document.querySelectorAll('a[href^=\"#\"]')].map(a => a.getAttribute('href').slice(1))")
        missing = [a for a in anchors if a not in ids]
        check("all nav anchors resolve", not missing, str(missing))
        check("main + nav + header + footer",
              all(page.locator(t).count() >= 1 for t in ("main", "nav", "header", "footer")))
        bad_tables = page.evaluate("""
          [...document.querySelectorAll('table')].filter(t =>
            !t.querySelector('caption') || !t.querySelector('thead th[scope="col"]')).length
        """)
        check("every table has caption + column headers", bad_tables == 0, f"{bad_tables} bad")

        tabs = page.locator('[data-tabset]').first.locator('[role="tab"]')
        panels = page.locator('[data-tabset]').first.locator('[role="tabpanel"]')
        check("tab counts (8 single-node panels)", tabs.count() == 8 and panels.count() == 8)
        vis0 = page.evaluate("[...document.querySelectorAll('[data-tabset]')].map(s => [...s.querySelectorAll('[role=tabpanel]')].filter(p => !p.hidden).length)")
        check("one panel visible per tabset initially", vis0 == [1, 1], str(vis0))
        tabs.nth(2).click()
        vis = page.locator('[data-tabset]').first.evaluate("s => [...s.querySelectorAll('[role=tabpanel]')].map(p => !p.hidden)")
        check("clicking tab 3 switches panel", vis[2] and sum(vis) == 1, str(vis))
        tabs.nth(2).focus()
        page.keyboard.press("ArrowRight")
        vis = page.locator('[data-tabset]').first.evaluate("s => [...s.querySelectorAll('[role=tabpanel]')].map(p => !p.hidden)")
        check("ArrowRight moves to tab 4", vis[3] and sum(vis) == 1, str(vis))
        selected = page.evaluate("document.activeElement.getAttribute('aria-selected')")
        check("focus follows keyboard selection", selected == "true")

        first_table = page.locator("table.sortable").first
        first_table.locator("th[data-sort]").first.click()
        sort_state = first_table.locator("th[data-sort]").first.get_attribute("aria-sort")
        check("sort state toggles on click", sort_state in ("ascending", "descending"), sort_state)
        first_table.locator("th[data-sort]").first.click()
        sort_state2 = first_table.locator("th[data-sort]").first.get_attribute("aria-sort")
        check("sort direction toggles", sort_state2 != sort_state, f"{sort_state}->{sort_state2}")

        det = page.locator("details.res").first
        det.locator("summary").click()
        check("resource disclosure opens", det.evaluate("d => d.open"))

    doc_over = overflow_report(page)
    check(f"[{label}] no page-level horizontal overflow",
          doc_over["scrollW"] <= doc_over["clientW"] + 2 and not doc_over["offenders"],
          json.dumps(doc_over))

    scrolls = page.evaluate("""
      [...document.querySelectorAll('.table-scroll')]
        .filter(e => e.scrollWidth > e.clientWidth + 2).length
    """)
    print(f"INFO  [{label}] local table scrollers active: {scrolls}")

    for c in page.evaluate(CONTRAST_JS):
        need = 4.5 if any(k in c["name"] for k in ("ink", "good", "warn", "bad", "text")) else 3.0
        check(f"[{label}] contrast {c['name']}", c["ratio"] >= need, f"{c['ratio']}:1 (need {need})")

    page.screenshot(path=str(OUT / f"viewport-{label}.png"), full_page=False)
    page.screenshot(path=str(OUT / f"full-{label}.png"), full_page=True)
    check(f"[{label}] no JS/page errors", not errors, str(errors[:3]))
    ctx.close()
    browser.close()


with sync_playwright() as pw:
    run_scheme(pw, "light", "desktop")

    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, color_scheme="light")
    page = ctx.new_page()
    page.goto(URL, wait_until="networkidle")
    doc_over = overflow_report(page)
    check("[mobile] no page-level horizontal overflow",
          doc_over["scrollW"] <= doc_over["clientW"] + 2 and not doc_over["offenders"], json.dumps(doc_over))
    small = page.evaluate("""
      () => {
        const out = [];
        for (const el of document.querySelectorAll('a, button, summary')) {
          const r = el.getBoundingClientRect();
          const st = getComputedStyle(el);
          const hidden = st.clipPath === 'inset(50%)' || st.overflow === 'hidden';
          if (r.width === 0 || hidden) continue;
          if (r.height < 24 || r.width < 24) out.push((el.textContent || el.tagName).trim().slice(0, 24) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
        }
        return out.slice(0, 10);
      }
    """)
    check("[mobile] interactive targets >= 24px", not small, str(small))
    page.screenshot(path=str(OUT / "viewport-mobile.png"), full_page=False)
    page.screenshot(path=str(OUT / "full-mobile.png"), full_page=True)
    ctx.close()
    browser.close()

    run_scheme(pw, "dark", "dark")

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} checks passed")
sys.exit(1 if fails else 0)
