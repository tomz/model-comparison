#!/usr/bin/env python3
"""Rate the quality of each attempt's generated engine-comparison report.

Rubric (pre-registered, 100 points). Every point comes from a check that a
machine can repeat, so a score can be argued with by re-running this script:

    20  data fidelity    embeds the dataset, renders known figures, no errors
    18  coverage         both suites, all scale factors, cluster, per-query
    18  analysis depth   derived findings, ratios, win counts, multiple views
    14  caveats          limitations, canonical vs time, markers, nulls
    12  presentation     charts, tables, dark mode, print, responsive
    10  ease of use      navigation, sorting, filtering, drill-down
     8  provenance       builder, template, hashes, README, tests

What this deliberately does NOT score: visual taste, prose quality, or whether
the conclusions are *interesting*. Those need a human looking at the rendering.
The scores here are structural and factual, which is exactly why they are worth
computing over 36 reports.

    python3 rate_quality.py             # -> quality-ratings.json
    python3 rate_quality.py --dirs a b  # subset
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "quality-ratings.json"

sys.path.insert(0, str(ROOT))
from extract_metrics import ATTEMPT_EXCLUDES  # noqa: E402

# Figures from the frozen dataset, grouped so either display convention can
# satisfy a probe: a report may open on SF1 or on the "all scale factors" row,
# and may show raw seconds or a rounded ratio. Each group is satisfied by any
# one member, so the check tests "does this report render the benchmark data"
# rather than "did I guess its default view".
FACT_GROUPS = {
    "single-node figures": [
        # aggregate totals (any suite/scale factor, raw or rounded)
        r"6\.09", r"\b6\.1\b", r"5\.67", r"5\.68", r"4\.58", r"4\.59",
        r"\b1\.32[0-9]\b", r"\b1\.33\b", r"243\.0", r"\b243\.1\b", r"229\.0",
        r"33\.8[45]", r"31\.96", r"27\.13", r"79\.9[12]",
        r"5,?883", r"6,?05[0-9]", r"6,?14[0-9]", r"11,?369", r"10,?94[0-9]",
        r"11,?30[0-9]", r"24,?193", r"18,?284", r"13,?153",
        # per-query values (reports that show drill-down but no aggregate table)
        r"0\.20[89]", r"0\.21\b", r"0\.229", r"0\.169", r"0\.17\b", r"10\.41",
    ],
    "cluster figures": [
        r"\b807\b", r"\b808\b", r"1,?196", r"1,?197", r"2,?78[67]", r"2,?91[34]",
        r"18,?710", r"12,?76[23]",
        # CPU-hours / memory-hours at either precision
        r"4\.3[0-9]?", r"4\.4\b", r"11\.9[0-9]?", r"37\.1[0-9]?", r"37\.2\b",
        r"127\.6[0-9]?", r"127\.7\b", r"151\.3[0-9]?", r"151\.4\b", r"16\.7[0-9]?", r"16\.8\b",
    ],
}

# Kept for the evidence trail: what the probes above are looking for.
KNOWN_FACTS = {
    "single-node TPC-H or TPC-DS totals": FACT_GROUPS["single-node figures"],
    "cluster elapsed / CPU-hour figures": FACT_GROUPS["cluster figures"],
}

ENGINES = [
    "Spark Rust 0.42.1 (default)", "Spark Rust 0.42.1 (tuned)",
    "DuckDB 1.5.5", "Spark 4.1.1 Gluten", "Spark 4.2",
]

DOM_JS = r"""() => {
  const txt = document.body.innerText || '';
  const lower = txt.toLowerCase();
  const q = (s) => document.querySelectorAll(s).length;
  const cssText = Array.from(document.styleSheets).map(s => {
    try { return Array.from(s.cssRules).map(r => r.cssText).join('\n'); }
    catch (e) { return ''; }
  }).join('\n');
  return {
    text: txt,
    chars: txt.length,
    h2: q('h2'), h3: q('h3'),
    tables: q('table'), rows: q('table tr'), th: q('th'),
    svg: q('svg'), canvas: q('canvas'),
    buttons: q('button'), selects: q('select'), inputs: q('input'),
    details: q('details'),
    anchors: q('nav a, [role=navigation] a, a[href^="#"]'),
    sortable: q('th[data-key], th[data-sort], th[onclick], th[role=button]'),
    aria: q('[aria-label],[aria-labelledby],[role]'),
    cssbars: q('[class*=bar],[class*=meter],[class*=gauge]'),
    headers: Array.from(document.querySelectorAll('h1,h2,h3')).map(e => e.textContent.trim()),
    hasPrint: /@media[^{]*print/.test(cssText),
    hasDark: /prefers-color-scheme/.test(cssText),
    hasMono: /monospace|tabular-nums|sfmono|ui-monospace/i.test(cssText),
    hasResponsive: /@media[^{]*max-width/.test(cssText),
    hasTable: /<table|role=["']table/.test(document.body.innerHTML) || q('table') > 0,
    engines: __ENGINES__.filter(e => txt.includes(e)).length,
    tpch: txt.includes('TPC-H'), tpcds: txt.includes('TPC-DS'),
    facts: __FACTCOUNT__,
    sections: {
      summary: /(executive|summary|overview|key\s+finding|headline)/i.test(txt),
      single: /single[- ]node/i.test(txt),
      cluster: /cluster|8[- ]worker|worker node/i.test(txt),
      perquery: /per[- ]query|query[- ]level|by query|query detail/i.test(txt),
      method: /(method|methodology)/i.test(txt),
      provenance: /(sha-?256|hash|provenance|fingerprint)/i.test(txt),
    },
    terms: {
      canonical: /canonical/i.test(txt),
      matched: /matched/i.test(txt),
      markers: /(\bB\/P\b|ULP|Q39|\bmarker)/i.test(txt),
      nulls: /(\bnull\b|\bn\/a\b|not reported|no canonical|missing|-{2,}|—)/i.test(txt),
      limitations: /(limitation|caveat|unspecified|assumption|not official|not a controlled)/i.test(txt),
      units: /(seconds|assumed|timing unit|\bs\b\s*\))/i.test(txt),
      ratios: /(ratio|x faster|faster than|×|baseline|vs\.? DuckDB)/i.test(txt),
      wins: /(win|faster on \d+|passed \d+|\d+ of \d+)/i.test(txt),
    },
  };
}"""


def find_deliverable(directory: Path) -> Path | None:
    """The largest non-template HTML file in an attempt directory."""
    candidates = [
        p for p in directory.glob("*.html")
        if "template" not in p.name.lower()
        and "1st try" not in p.name.lower()
        and "2nd try" not in p.name.lower()
    ]
    if not candidates:
        candidates = [p for p in directory.glob("*.html") if "template" not in p.name.lower()]
    return max(candidates, key=lambda p: p.stat().st_size) if candidates else None


def source_evidence(path: Path) -> dict:
    """Checks that only need the file on disk, not a browser."""
    src = path.read_text(encoding="utf-8", errors="replace")
    external = re.findall(r'(?:src|href)\s*=\s*["\'](https?://[^"\']+)', src, re.I)
    return {
        "bytes": len(src),
        "embeds_dataset": "Spark Rust 0.42.1 (default)" in src,
        "placeholder_left": bool(re.search(r"__[A-Z_]{3,}__", src)),
        "external_refs": external[:5],
        "has_sha": bool(re.search(r"\b[0-9a-f]{64}\b", src)) or "sha256" in src.lower(),
    }


def dir_evidence(directory: Path) -> dict:
    py = [p for p in directory.glob("*.py")]
    return {
        "builder": bool([p for p in py if re.match(r"(build|generate|gen)", p.name, re.I)]),
        "template": bool(list(directory.glob("*template*"))),
        "readme": (directory / "README.md").exists() or bool(list(directory.glob("*.md"))),
        "tests": (directory / "tests").is_dir() or bool(list(directory.glob("test_*.py"))),
        "verify": bool(list(directory.glob("verify*"))),
    }


def render_evidence(path: Path, page) -> tuple[dict, list[str], list[str]]:
    errors: list[str] = []
    requests: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("request", lambda r: requests.append(r.url))
    page.goto(path.as_uri(), wait_until="load", timeout=25000)
    page.wait_for_timeout(700)
    js = (DOM_JS
          .replace("__ENGINES__", json.dumps(ENGINES))
          .replace("__FACTCOUNT__", str(len(KNOWN_FACTS))))
    dom = page.evaluate(js)
    text = dom.pop("text", "")
    hits = {name: bool(re.search("|".join(pats), text))
            for name, pats in FACT_GROUPS.items()}
    dom["fact_hits"] = sum(hits.values())
    dom["fact_detail"] = hits
    external = [u for u in requests if not u.startswith(("file://", "data:", "blob:"))]
    return dom, errors, external


def _band(value: int, bands: list[tuple[int, float]]) -> float:
    """Score a count against (threshold, points) bands, best first."""
    for threshold, points in bands:
        if value >= threshold:
            return points
    return 0.0


def score(dom: dict, src: dict, dirs: dict, errors: list[str], external: list[str]) -> dict:
    """Turn measured evidence into the 0-100 rubric score."""
    t = dom["terms"]
    s = dom["sections"]
    dims: dict[str, dict] = {}

    # 1. Data fidelity (20)
    checks = {
        "embeds the dataset": src["embeds_dataset"],
        "no unsubstituted placeholder": not src["placeholder_left"],
        "no page errors": not errors,
        "all 5 engine names preserved": dom["engines"] == 5,
        "both suites named": dom["tpch"] and dom["tpcds"],
        "renders single-node figures": dom["fact_detail"]["single-node figures"],
        "renders cluster figures": dom["fact_detail"]["cluster figures"],
    }
    dims["data_fidelity"] = {"max": 20, "checks": checks}

    # 2. Coverage (18)
    covers = {
        "single-node section": s["single"],
        "cluster section": s["cluster"],
        "per-query detail": s["perquery"],
        "bulk data shown (>=60 table rows)": dom["rows"] >= 60,
        "many columns (>=20 headers)": dom["th"] >= 20,
    }
    dims["coverage"] = {"max": 18, "checks": covers}

    # 3. Analysis depth (18)
    deep = {
        "summary / key findings": s["summary"],
        "ratio or baseline comparison": t["ratios"],
        "win counts / pass tallies": t["wins"],
        "methodology section": s["method"],
        ">=6 sections": (dom["h2"] + dom["h3"]) >= 6,
    }
    dims["analysis"] = {"max": 18, "checks": deep}

    # 4. Caveats and honesty (14)
    honest = {
        "limitations stated": t["limitations"],
        "canonical vs reported time": t["canonical"],
        "source markers / ULP flagged": t["markers"],
        "missing values not zeroed": t["nulls"],
        "timing unit addressed": t["units"],
    }
    dims["caveats"] = {"max": 14, "checks": honest}

    # 5. Presentation (12)
    visual = {
        "charts (svg/canvas)": (dom["svg"] + dom["canvas"]) >= 1,
        "css bars / gauges": dom["cssbars"] >= 3,
        "large tables": dom["rows"] >= 40,
        "dark mode": dom["hasDark"],
        "print styles": dom["hasPrint"],
        "responsive": dom["hasResponsive"],
        "monospaced numbers": dom["hasMono"],
    }
    dims["presentation"] = {"max": 12, "checks": visual}

    # 6. Ease of use (10)
    usable = {
        "navigation / TOC": dom["anchors"] >= 3,
        "interactive controls": (dom["buttons"] + dom["selects"] + dom["inputs"]) >= 2,
        "sortable columns": dom["sortable"] >= 3,
        "drill-down (details)": dom["details"] >= 1,
        "accessibility roles": dom["aria"] >= 5,
    }
    dims["usability"] = {"max": 10, "checks": usable}

    # 7. Provenance (8)
    prov = {
        "builder script kept": dirs["builder"],
        "template kept": dirs["template"],
        "hashes / source attribution": src["has_sha"] or s["provenance"],
        "README kept": dirs["readme"],
        "tests or verifier kept": dirs["tests"] or dirs["verify"],
    }
    dims["provenance"] = {"max": 8, "checks": prov}

    total = 0.0
    breakdown: dict[str, float] = {}
    for name, dim in dims.items():
        passed = sum(1 for v in dim["checks"].values() if v)
        score_value = round(dim["max"] * passed / len(dim["checks"]), 2)
        breakdown[name] = score_value
        total += score_value
        dim["passed"] = passed
        dim["of"] = len(dim["checks"])
        dim["score"] = score_value

    return {
        "score": round(total, 1),
        "breakdown": breakdown,
        "dimensions": {k: {"score": v["score"], "max": v["max"],
                           "passed": v["passed"], "of": v["of"],
                           "checks": v["checks"]} for k, v in dims.items()},
        "evidence": {
            "page_errors": errors[:3],
            "external_requests": external[:5],
            "fact_hits": dom["fact_hits"],
            "tables": dom["tables"], "rows": dom["rows"],
            "charts": dom["svg"] + dom["canvas"],
            "sections": dom["sections"], "terms": dom["terms"],
            "source_bytes": src["bytes"],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dirs", nargs="*", default=None)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    targets = ([ROOT / d for d in args.dirs] if args.dirs else
               sorted(p for p in ROOT.iterdir()
                      if p.is_dir() and not p.name.startswith(".")
                      and p.name not in ATTEMPT_EXCLUDES))
    results, skipped = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/usr/bin/google-chrome")
        for directory in targets:
            deliverable = find_deliverable(directory)
            if deliverable is None:
                skipped.append({"directory": directory.name, "reason": "no HTML deliverable"})
                continue
            page = browser.new_page(viewport={"width": 1400, "height": 1000})
            try:
                dom, errors, external = render_evidence(deliverable, page)
                rating = score(dom, source_evidence(deliverable), dir_evidence(directory),
                               errors, external)
            except Exception as exc:
                skipped.append({"directory": directory.name,
                                "reason": f"render failed: {type(exc).__name__}: {exc}"[:120]})
                page.close()
                continue
            page.close()
            rating.update({"directory": directory.name,
                           "deliverable": deliverable.name,
                           "deliverable_bytes": deliverable.stat().st_size})
            results.append(rating)
            print(f"{directory.name:30} {rating['score']:5.1f}/100  "
                  f"facts {rating['evidence']['fact_hits']}/{len(KNOWN_FACTS)}  "
                  f"tables {rating['evidence']['tables']:3}  "
                  f"charts {rating['evidence']['charts']:2}  "
                  + " ".join(f"{k[:4]}={rating['breakdown'][k]:g}" for k in
                             ("data_fidelity", "coverage", "analysis", "caveats",
                              "presentation", "usability", "provenance")))
        browser.close()

    payload = {
        "generated_by": "rate_quality.py",
        "rubric": {
            "data_fidelity": 20, "coverage": 18, "analysis": 18, "caveats": 14,
            "presentation": 12, "usability": 10, "provenance": 8,
        },
        "not_scored": ("visual taste, prose quality, and whether the conclusions are "
                       "interesting require human review; these scores are structural "
                       "and factual only"),
        "probe_limitations": (
            "The figure probes search the rendered text for dataset values at any "
            "rounding (raw, 1-2 decimals, thousands-separated). A report that presents "
            "cluster results only as ratios or deltas, without the cluster elapsed or "
            "CPU-hour figures, still loses that check. This is a deliberate but narrow "
            "penalty: the dataset supplies cluster cpu/cores/memtime/p95/max and the "
            "check rewards surfacing them."
        ),
        "known_facts": list(KNOWN_FACTS),
        "ratings": sorted(results, key=lambda r: -r["score"]),
        "skipped": skipped,
    }
    Path(args.out).write_text(json.dumps(payload, indent=1), encoding="utf-8")
    scores = [r["score"] for r in results]
    print(f"\n{len(results)} reports rated | median {sorted(scores)[len(scores)//2]:.1f} "
          f"| range {min(scores):.1f}-{max(scores):.1f} | skipped {len(skipped)}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
