#!/usr/bin/env python3
"""Rigorous WCAG contrast audit of the rendered report.

For each representative text element, computes the *effective* background by
compositing every ancestor background (handling alpha and color-mix results),
then reports the contrast ratio and the AA/AAA verdict for that element's own
font size and weight.
"""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
TARGET = (HERE / "engine-comparison-report.html").resolve().as_uri()

# (label, selector, index) — index picks the nth match so we can target the
# active vs inactive TOC link, etc.
PROBES = [
    ("Body paragraph", ".prose p", 0),
    ("Lede text", ".lede", 0),
    ("Note block", ".note", 0),
    ("Inline content link", ".section p a", 0),
    ("Skip link (focused)", ".skip", 0),
    ("TOC link (inactive)", '.toc a[aria-current="false"]', 0),
    ("TOC link (active)", '.toc a[aria-current="true"]', 0),
    ("Theme button", ".theme-btn", 0),
    ("Stat big number", ".stat-big", 0),
    ("Stat label (small)", ".stat-label", 0),
    ("Stat sub-text", ".stat-sub", 0),
    ("Card heading", ".card h3", 0),
    ("Spec term", ".specs dt", 0),
    ("Spec value", ".specs dd", 0),
    ("Table caption", "table.data caption", 0),
    ("Table header", "table.data thead th", 1),
    ("Table row header", "table.data tbody th", 0),
    ("Numeric cell", "td.cell .val", 0),
    ("Cell sub-label", "td.cell .sub", 0),
    ("Ratio text", ".ratio", 0),
    ("As-reported cell", ".reported", 0),
    ("Win cell", ".win", 0),
    ("Marker flag", ".flag", 0),
    ("Status pill (pass)", ".pill", 0),
    ("Status pill (gap)", ".pill.gap", 0),
    ("Status pill (other)", ".pill.other", 0),
    ("Legend text", ".legend li", 0),
    ("Chart axis label", "svg .axis", 0),
    ("Chart axis title", "svg .axis-title", 0),
    ("Details summary", "details.fold summary", 0),
    ("Checklist item", "ul.checks li", 0),
    ("Warning checklist", "ul.checks.warn li", 0),
    ("Footer text", "footer span", 0),
    ("Empty-state text", ".empty", 0),
    ("Segmented (unpressed)", '.seg button[aria-pressed="false"]', 0),
    ("Segmented (pressed)", '.seg button[aria-pressed="true"]', 0),
    ("Search input", 'input[type="search"]', 0),
]

EFFECTIVE_BG_JS = r"""
(el) => {
  function parse(c) {
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[,\s\/]+/).map(Number).filter(n => !isNaN(n));
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  }
  // Walk from the element up, collecting non-transparent backgrounds.
  const layers = [];
  let node = el;
  while (node && node.nodeType === 1) {
    const bg = parse(getComputedStyle(node).backgroundColor);
    if (bg && bg.a > 0) layers.push(bg);
    if (bg && bg.a >= 1) break;
    node = node.parentElement;
  }
  // Composite top-down over an opaque canvas (the root background).
  const rootBg = parse(getComputedStyle(document.documentElement).backgroundColor)
              || parse(getComputedStyle(document.body).backgroundColor)
              || { r: 255, g: 255, b: 255, a: 1 };
  let acc = { r: rootBg.r, g: rootBg.g, b: rootBg.b };
  for (let i = layers.length - 1; i >= 0; i--) {
    const L = layers[i];
    acc = {
      r: L.r * L.a + acc.r * (1 - L.a),
      g: L.g * L.a + acc.g * (1 - L.a),
      b: L.b * L.a + acc.b * (1 - L.a),
    };
  }
  return `rgb(${Math.round(acc.r)}, ${Math.round(acc.g)}, ${Math.round(acc.b)})`;
}
"""

METRICS_JS = r"""
(el) => {
  const s = getComputedStyle(el);
  const px = parseFloat(s.fontSize);
  const w = parseInt(s.fontWeight, 10) || 400;
  return {
    color: s.color,
    fontSizePx: px,
    fontWeight: w,
    // WCAG "large text" = >=24px, or >=18.66px (14pt) and bold (>=700).
    large: px >= 24 || (px >= 18.66 && w >= 700),
  };
}
"""


def channel(v: float) -> float:
    v /= 255.0
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def luminance(rgb: str) -> float:
    nums = [float(x) for x in rgb.replace("rgba", "").replace("rgb", "").strip("()").split(",")]
    r, g, b = nums[0], nums[1], nums[2]
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def ratio(fg: str, bg: str) -> float:
    l1, l2 = sorted([luminance(fg), luminance(bg)], reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def audit(theme: str) -> list[dict]:
    rows: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(TARGET, wait_until="networkidle")
        page.wait_for_timeout(400)
        page.evaluate(f"document.documentElement.setAttribute('data-theme','{theme}')")
        page.wait_for_timeout(200)

        # Reveal the skip link the way a keyboard user would, so it can be measured.
        page.evaluate("document.querySelector('.skip').focus()")
        page.wait_for_timeout(120)
        # Ensure an active TOC link exists.
        page.evaluate("""() => {
          const a = document.querySelectorAll('.toc a');
          if (a.length) {
            a.forEach(x => x.setAttribute('aria-current','false'));
            a[0].setAttribute('aria-current','true');
          }
        }""")
        # Ensure the empty state is measurable.
        page.evaluate("document.getElementById('single-empty').hidden=false")
        # Put the single-node explorer into TPC-DS SF 1000 so marker flags render.
        page.evaluate("""() => {
          const b = document.querySelector('#seg-sbench button[data-v="TPC-DS"]');
          if (b) b.click();
          const s = document.querySelector('#seg-ssf button[data-v="1000"]');
          if (s) s.click();
        }""")
        # Put the cluster explorer on SF 10000 so single-engine pills render.
        page.evaluate("""() => {
          const s = document.querySelector('#seg-csf button[data-v="10000"]');
          if (s) s.click();
          const f = document.querySelector('#seg-cfilter button[data-v="other"]');
          if (f) f.click();
        }""")
        page.wait_for_timeout(250)

        for label, selector, idx in PROBES:
            handle = page.query_selector_all(selector)
            if len(handle) <= idx:
                rows.append({"theme": theme, "label": label, "selector": selector,
                             "missing": True})
                continue
            el = handle[idx]
            metrics = el.evaluate(METRICS_JS)
            bg = el.evaluate(EFFECTIVE_BG_JS)
            r = ratio(metrics["color"], bg)
            need = 3.0 if metrics["large"] else 4.5
            rows.append({
                "theme": theme, "label": label, "selector": selector,
                "fg": metrics["color"], "bg": bg, "ratio": round(r, 2),
                "px": round(metrics["fontSizePx"], 1), "weight": metrics["fontWeight"],
                "large": metrics["large"], "need": need,
                "pass": r >= need, "aaa": r >= (4.5 if metrics["large"] else 7.0),
                "missing": False,
            })
        browser.close()
    return rows


def main() -> int:
    all_rows = audit("light") + audit("dark")
    Path(HERE / "shots" / "contrast-audit.json").write_text(json.dumps(all_rows, indent=2))

    failures = [r for r in all_rows if not r.get("missing") and not r["pass"]]
    missing = [r for r in all_rows if r.get("missing")]

    for theme in ("light", "dark"):
        print(f"\n=== {theme} ===")
        for r in all_rows:
            if r["theme"] != theme:
                continue
            if r.get("missing"):
                print(f"  {'n/a':<24} {r['label']} (no element matched)")
                continue
            mark = "ok " if r["pass"] else "FAIL"
            aaa = " AAA" if r["aaa"] else ""
            size = f"{r['px']}px/{r['weight']}" + (" large" if r["large"] else "")
            print(f"  {mark} {r['ratio']:5.2f}:1 (need {r['need']}){aaa:<4} "
                  f"{r['label']:<24} {size:<16} {r['fg']} on {r['bg']}")

    print(f"\n{len(all_rows) - len(failures) - len(missing)}/{len(all_rows) - len(missing)} "
          f"measurable pairs meet WCAG AA")
    if failures:
        print("\nCONTRAST FAILURES:")
        for r in failures:
            print(f"  [{r['theme']}] {r['label']}: {r['ratio']}:1 "
                  f"(needs {r['need']}) {r['fg']} on {r['bg']}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
