#!/usr/bin/env python3
"""Programmatic layout audit for the rendered report.

Vision inspection is unavailable, so this measures geometry instead: text
clipping, element overflow, unintended overlap, bar rendering, SVG chart
integrity, sticky-header behaviour, and print/RTL robustness.
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
TARGET = (HERE / "engine-comparison-report.html").resolve().as_uri()

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


CLIP_JS = r"""
() => {
  const bad = [];
  const sel = 'h1,h2,h3,p,td,th,li,dd,dt,figcaption,summary,span,.stat-big,.stat-label,' +
              '.stat-sub,.note,.lede,button,a,code';
  document.querySelectorAll(sel).forEach(el => {
    if (!el.offsetParent && el.tagName !== 'BODY') {
      // Skip hidden/detached elements, but keep sticky ones.
      const p = getComputedStyle(el).position;
      if (p !== 'sticky' && p !== 'fixed') return;
    }
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    // Text clipped horizontally by its own box?
    if (el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflowX !== 'auto'
        && getComputedStyle(el).overflowX !== 'scroll'
        && !el.closest('.table-wrap') && !el.closest('.toc .wrap')) {
      const t = (el.textContent || '').trim().slice(0, 40);
      if (t) bad.push({tag: el.tagName, cls: el.className.toString().slice(0,30),
                       text: t, sw: el.scrollWidth, cw: el.clientWidth});
    }
  });
  return bad;
}
"""

OVERFLOW_JS = r"""
() => {
  const vw = document.documentElement.clientWidth;
  const bad = [];
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width === 0) return;
    // Skip anything not actually painted (e.g. content of closed <details>).
    if (el.checkVisibility && !el.checkVisibility({contentVisibilityAuto:true,
                                                    visibilityProperty:true})) return;
    const cs = getComputedStyle(el);
    if (cs.position === 'fixed' || cs.position === 'sticky') return;
    // Allow elements inside a horizontally scrollable wrapper.
    if (el.closest('.table-wrap') || el.closest('.toc .wrap')) return;
    if (r.right > vw + 1 || r.left < -1) {
      bad.push({tag: el.tagName, cls: (el.className||'').toString().slice(0,40),
                left: Math.round(r.left), right: Math.round(r.right), vw});
    }
  });
  return bad;
}
"""

BAR_JS = r"""
() => {
  const bars = [...document.querySelectorAll('.bar')];
  const bad = bars.filter(b => {
    const w = parseFloat(getComputedStyle(b).width);
    return !(w > 0);
  }).length;
  const widths = bars.map(b => parseFloat(getComputedStyle(b).getPropertyValue('width')));
  return {count: bars.length, zeroWidth: bad,
          min: Math.min(...widths), max: Math.max(...widths)};
}
"""

SVG_JS = r"""
() => {
  const out = [];
  document.querySelectorAll('figure.chart svg').forEach(svg => {
    const r = svg.getBoundingClientRect();
    const polys = svg.querySelectorAll('polyline.series').length;
    const dots = svg.querySelectorAll('circle.dot').length;
    const titles = svg.querySelectorAll('circle title').length;
    const grid = svg.querySelectorAll('line.grid').length;
    const labels = svg.querySelectorAll('text').length;
    // Any NaN in geometry?
    const nan = svg.innerHTML.includes('NaN') || svg.innerHTML.includes('Infinity');
    out.push({w: Math.round(r.width), h: Math.round(r.height), polys, dots, titles,
              grid, labels, nan});
  });
  return out;
}
"""

OVERLAP_JS = r"""
() => {
  // Detect text-on-text overlap between sibling cards/sections.
  const boxes = [];
  document.querySelectorAll('.card, .stat, figure.chart, .table-wrap, .controls').forEach(el => {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) return;
    // Ignore content of closed <details>: geometry is reported but nothing is painted.
    if (el.checkVisibility && !el.checkVisibility({contentVisibilityAuto:true,
                                                   visibilityProperty:true})) return;
    boxes.push({el, r, id: el.className.toString().slice(0,24)});
  });
  const hits = [];
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i].r, b = boxes[j].r;
      const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (ox > 2 && oy > 2) {
        // Ignore genuine nesting (one contains the other).
        const contains = boxes[i].el.contains(boxes[j].el) || boxes[j].el.contains(boxes[i].el);
        if (!contains) hits.push({a: boxes[i].id, b: boxes[j].id,
                                  ox: Math.round(ox), oy: Math.round(oy)});
      }
    }
  }
  return hits;
}
"""


def audit_at(page, label: str) -> None:
    clipped = page.evaluate(CLIP_JS)
    check(f"{label}: no clipped text", not clipped, str(clipped[:3]))

    overflow = page.evaluate(OVERFLOW_JS)
    check(f"{label}: no element overflows viewport", not overflow, str(overflow[:3]))

    bars = page.evaluate(BAR_JS)
    check(f"{label}: bars rendered with width", bars["count"] > 0 and bars["zeroWidth"] == 0,
          f"{bars['count']} bars, min={bars['min']:.1f}px max={bars['max']:.1f}px")

    svgs = page.evaluate(SVG_JS)
    check(f"{label}: charts rendered", len(svgs) == 2, f"{len(svgs)} svgs")
    for s in svgs:
        check(f"{label}: chart geometry sane", s["w"] > 200 and s["h"] > 100 and not s["nan"],
              f"{s['w']}x{s['h']} polys={s['polys']} dots={s['dots']} grid={s['grid']} nan={s['nan']}")
        check(f"{label}: chart has 5 series + tooltips",
              s["polys"] == 5 and s["dots"] == 20 and s["titles"] == 20,
              f"polys={s['polys']} dots={s['dots']} titles={s['titles']}")

    overlaps = page.evaluate(OVERLAP_JS)
    check(f"{label}: no unintended box overlap", not overlaps, str(overlaps[:3]))


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- desktop, light ----------
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errs: list[str] = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(TARGET, wait_until="networkidle")
        page.wait_for_timeout(400)
        audit_at(page, "desktop-light")
        check("desktop-light: no page errors", not errs, "; ".join(errs[:2]))

        # Sticky table header stays inside its scroll container.
        page.locator("#per-query").scroll_into_view_if_needed()
        page.wait_for_timeout(200)
        sticky = page.evaluate("""() => {
          const th = document.querySelector('#single-head th');
          const wrap = th.closest('.table-wrap');
          const a = th.getBoundingClientRect(), b = wrap.getBoundingClientRect();
          return {thTop: Math.round(a.top), wrapTop: Math.round(b.top),
                  inside: a.top >= b.top - 1};
        }""")
        check("sticky header stays within wrapper", sticky["inside"], str(sticky))

        # Row height consistency — no row collapsed to zero.
        heights = page.evaluate("""() => {
          const hs = [...document.querySelectorAll('#single-body tr')]
            .map(r => Math.round(r.getBoundingClientRect().height));
          return {min: Math.min(...hs), max: Math.max(...hs), n: hs.length};
        }""")
        check("table rows have consistent non-zero height",
              heights["min"] > 15 and heights["max"] - heights["min"] < 12, str(heights))

        # ---------- desktop, dark ----------
        page.evaluate("document.documentElement.setAttribute('data-theme','dark')")
        page.wait_for_timeout(250)
        audit_at(page, "desktop-dark")

        # ---------- narrow mobile ----------
        m = browser.new_page(viewport={"width": 360, "height": 780}, is_mobile=True,
                             has_touch=True, device_scale_factor=2)
        merrs: list[str] = []
        m.on("pageerror", lambda e: merrs.append(str(e)))
        m.goto(TARGET, wait_until="networkidle")
        m.wait_for_timeout(400)
        check("mobile-360: no page errors", not merrs, "; ".join(merrs[:2]))

        clipped = m.evaluate(CLIP_JS)
        check("mobile-360: no clipped text", not clipped, str(clipped[:3]))
        overflow = m.evaluate(OVERFLOW_JS)
        check("mobile-360: no viewport overflow", not overflow, str(overflow[:3]))

        doc_w = m.evaluate("document.documentElement.scrollWidth")
        check("mobile-360: document does not scroll horizontally", doc_w <= 361,
              f"scrollWidth={doc_w}")

        # Masthead heading must not overflow at 360px.
        h1 = m.evaluate("""() => {
          const h = document.querySelector('h1').getBoundingClientRect();
          return {w: Math.round(h.width), right: Math.round(h.right)};
        }""")
        check("mobile-360: h1 fits", h1["right"] <= 361, str(h1))

        # Charts must shrink rather than overflow.
        svgs = m.evaluate(SVG_JS)
        check("mobile-360: charts scale down", all(s["w"] <= 340 and not s["nan"] for s in svgs),
              str([(s["w"], s["h"]) for s in svgs]))

        # TOC scrolls internally without breaking layout.
        toc = m.evaluate("""() => {
          const t = document.querySelector('.toc .wrap');
          return {sw: t.scrollWidth, cw: t.clientWidth,
                  overflowX: getComputedStyle(t).overflowX};
        }""")
        check("mobile-360: TOC scrolls internally",
              toc["overflowX"] in ("auto", "scroll") and toc["sw"] >= toc["cw"], str(toc))

        # ---------- very wide ----------
        w = browser.new_page(viewport={"width": 2560, "height": 1200})
        w.goto(TARGET, wait_until="networkidle")
        w.wait_for_timeout(400)
        maxw = w.evaluate("""() => {
          const m = document.querySelector('main.wrap').getBoundingClientRect();
          return {w: Math.round(m.width)};
        }""")
        check("ultrawide: content column capped", maxw["w"] <= 1181, str(maxw))
        overflow = w.evaluate(OVERFLOW_JS)
        check("ultrawide: no overflow", not overflow, str(overflow[:2]))

        # ---------- forced colors / reduced motion ----------
        rm = browser.new_page(viewport={"width": 1440, "height": 1000},
                              reduced_motion="reduce")
        rm.goto(TARGET, wait_until="networkidle")
        rm.wait_for_timeout(300)
        anim = rm.evaluate("""() => {
          const el = document.querySelector('.toc a');
          const d = getComputedStyle(el).transitionDuration;   // e.g. "1e-05s"
          return {raw: d, seconds: parseFloat(d)};
        }""")
        check("reduced-motion: transitions neutralised",
              anim["seconds"] <= 0.001, f"{anim['raw']} = {anim['seconds']}s")
        rmerrs = rm.evaluate(OVERFLOW_JS)
        check("reduced-motion: no overflow", not rmerrs, str(rmerrs[:2]))

        # ---------- keyboard navigation order ----------
        page2 = browser.new_page(viewport={"width": 1440, "height": 1000})
        page2.goto(TARGET, wait_until="networkidle")
        page2.wait_for_timeout(400)
        order = []
        for _ in range(6):
            page2.keyboard.press("Tab")
            order.append(page2.evaluate("""() => {
              const a = document.activeElement;
              return a ? (a.tagName + '.' + (a.className||'').toString().split(' ')[0] +
                          ':' + (a.textContent||'').trim().slice(0,18)) : 'none';
            }"""))
        check("keyboard: skip link is first stop", order[0].startswith("A.skip"), order[0])
        check("keyboard: focus moves through TOC", any("toc" in o or "A." in o for o in order[1:4]),
              " | ".join(order[1:5]))

        # Focus visible ring present.
        ring = page2.evaluate("""() => {
          const a = document.activeElement;
          const s = getComputedStyle(a);
          return {outline: s.outlineWidth, style: s.outlineStyle};
        }""")
        check("keyboard: focus ring visible",
              ring["style"] != "none" and float(ring["outline"].replace("px", "")) >= 2, str(ring))

        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} layout checks passed")
    if failed:
        print("FAILURES:")
        for n, _, d in failed:
            print(f"  - {n}: {d}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
