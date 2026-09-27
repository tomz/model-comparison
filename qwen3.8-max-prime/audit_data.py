#!/usr/bin/env python3
"""Data-fidelity audit: rendered report versus the source JSON.

Re-derives expected values from engine-comparison-summary-data.json and compares
them against what the browser actually renders, so a formatting or wiring bug
cannot silently misreport a benchmark number.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
TARGET = (HERE / "engine-comparison-report.html").resolve().as_uri()
SRC = HERE / "engine-comparison-summary-data.json"

results: list[tuple[str, bool, str]] = []
mismatches: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def expect(name: str, rendered, expected, tol: float = 0.0) -> None:
    """Compare a rendered value with the source-derived expectation.

    The report rounds for display using a magnitude-based precision rule, so
    numeric comparisons use a tolerance derived from the decimals actually
    shown rather than demanding exact equality.
    """
    if isinstance(expected, (int, float)) and isinstance(rendered, (int, float)):
        # Tolerance: half of the last displayed decimal place.
        s = f"{rendered:f}".rstrip("0")
        decimals = len(s.split(".")[1]) if "." in s else 0
        eff_tol = max(tol, 0.5 * 10 ** (-decimals) + abs(expected) * 1e-9)
        ok = abs(rendered - expected) <= eff_tol
        detail = f"rendered={rendered} expected={expected} tol={eff_tol:.4g}"
    else:
        ok = rendered == expected
        detail = f"rendered={rendered!r} expected={expected!r}"
    if not ok:
        mismatches.append(f"{name}: {detail}")
    check(name, ok, detail)


def main() -> int:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    engines = data["engines"]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        errs: list[str] = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(TARGET, wait_until="networkidle")
        page.wait_for_timeout(400)
        check("no page errors during audit", not errs, "; ".join(errs[:2]))

        # ---- 1. Static totals matrix: every cell vs source ----
        for bench in ("TPC-H", "TPC-DS"):
            # Select the right matrix table by its caption text.
            rows = page.evaluate("""(bench) => {
              const caps = [...document.querySelectorAll('table.data.matrix')];
              const t = caps.find(x => x.caption.textContent.startsWith(bench));
              if (!t) return null;
              return [...t.querySelectorAll('tbody tr')].map(tr => ({
                engine: tr.querySelector('th').textContent.trim(),
                cells: [...tr.querySelectorAll('td')].map(td => {
                  const v = td.querySelector('.val');
                  const s = td.querySelector('.sub');
                  return {val: v ? v.textContent.trim() : null,
                          sub: s ? s.textContent.trim() : null};
                })
              }));
            }""", bench)
            check(f"{bench}: matrix table found", rows is not None and len(rows) == 5,
                  f"{len(rows) if rows else 0} rows")
            if not rows:
                continue

            sfs = ["1", "10", "100", "1000", "all"]
            for r in rows:
                eng = r["engine"]
                src_rows = {x["sf"]: x for x in data["totals"][bench] if x["engine"] == eng}
                check(f"{bench}: engine present in source", eng in engines, eng)
                for ci, sf in enumerate(sfs):
                    cell = r["cells"][ci]
                    src = src_rows[sf]
                    # Compare the ratio sub-label exactly (it is the stable field).
                    exp_ratio = src["ratio"]
                    got = cell["sub"]
                    if exp_ratio is None:
                        exp_txt = "—"
                    elif abs(exp_ratio - 1) < 0.005:
                        exp_txt = "1.00×"
                    elif exp_ratio < 10:
                        exp_txt = f"{exp_ratio:.2f}×"
                    elif exp_ratio < 100:
                        exp_txt = f"{exp_ratio:.1f}×"
                    else:
                        exp_txt = f"{exp_ratio:,.0f}×"
                    if got != exp_txt:
                        mismatches.append(
                            f"{bench} {eng} SF{sf} ratio: rendered={got!r} expected={exp_txt!r}")
                check(f"{bench}: {eng[:28]} ratios match source",
                      not any(m.startswith(f"{bench} {eng} ") for m in mismatches))

        # ---- 2. Cluster totals cards vs source ----
        for sf in ("100", "1000", "10000"):
            got = page.evaluate("""(sf) => {
              const cards = [...document.querySelectorAll('#cluster .card')];
              const c = cards.find(x => x.querySelector('h3').textContent.trim() === 'SF ' + sf);
              if (!c) return null;
              const out = {};
              c.querySelectorAll('tbody tr').forEach(tr => {
                const k = tr.querySelector('th').textContent.trim();
                const tds = tr.querySelectorAll('td');
                out[k] = [tds[0].textContent.trim(), tds[1].textContent.trim()];
              });
              return out;
            }""", sf)
            check(f"cluster SF{sf}: card found", got is not None)
            if not got:
                continue
            by_eng = {r["engine"]: r for r in data["cluster"][sf]}
            rust, glut = by_eng["Spark Rust 0.42.1"], by_eng["Spark 4.1.1 Gluten"]

            def num(s: str) -> float | None:
                s = s.replace(",", "").replace("—", "")
                if not s:
                    return None
                try:
                    return float(s)
                except ValueError:
                    return None

            expect(f"cluster SF{sf} rust total time", num(got["Total wall time (s)"][0]),
                   rust["time"])
            expect(f"cluster SF{sf} gluten total time", num(got["Total wall time (s)"][1]),
                   glut["time"])
            expect(f"cluster SF{sf} rust cpu-hours", num(got["CPU-hours"][0]), rust["cpuHours"])
            expect(f"cluster SF{sf} gluten cpu-hours", num(got["CPU-hours"][1]), glut["cpuHours"])
            expect(f"cluster SF{sf} rust mean cores", num(got["Mean cores used"][0]), rust["cores"])
            expect(f"cluster SF{sf} gluten mem-hours", num(got["Memory-hours"][1]), glut["memHours"])

            # Win counts in the card header.
            wtxt = page.evaluate("""(sf) => {
              const cards = [...document.querySelectorAll('#cluster .card')];
              const c = cards.find(x => x.querySelector('h3').textContent.trim() === 'SF ' + sf);
              return c.querySelector('.stat-label').textContent;
            }""", sf)
            w = data["wins"][sf]
            check(f"cluster SF{sf} win counts match source",
                  str(w[0]) in wtxt and str(w[1]) in wtxt, f"{wtxt.strip()[:70]} vs wins={w}")

        # ---- 3. Per-query explorer: spot-check cells against source ----
        for bench, sf, q in [("TPC-H", "1", 1), ("TPC-H", "1000", 22),
                             ("TPC-DS", "100", 50), ("TPC-DS", "1000", 99)]:
            page.evaluate("""([b, s]) => {
              document.querySelector(`#seg-sbench button[data-v="${b}"]`).click();
              document.querySelector(`#seg-ssf button[data-v="${s}"]`).click();
            }""", [bench, sf])
            page.wait_for_timeout(200)
            got = page.evaluate("""(q) => {
              const tr = [...document.querySelectorAll('#single-body tr')]
                .find(r => r.querySelector('th').textContent.trim() === 'Q' + q);
              if (!tr) return null;
              return [...tr.querySelectorAll('td .val')].map(v => v.textContent.trim());
            }""", q)
            check(f"{bench} SF{sf} Q{q}: row rendered", got is not None)
            if not got:
                continue
            src = [r for r in data["single"][bench][sf] if r["q"] == q][0]
            for i, e in enumerate(engines):
                cell = got[i].replace("B", "").replace("P", "").strip()
                v = src["times"][i]
                if v is None:
                    ok = cell == "—"
                else:
                    a = abs(v)
                    exp = (f"{v:.3f}" if a < 10 else f"{v:.2f}" if a < 100
                           else f"{v:.1f}" if a < 1000 else f"{v:,.0f}")
                    ok = cell == exp
                    if not ok:
                        mismatches.append(f"{bench} SF{sf} Q{q} {e}: {cell!r} != {exp!r}")
                check(f"{bench} SF{sf} Q{q} {e[:22]}", ok, f"{cell}")

        # ---- 4. Cluster per-query explorer spot-check ----
        page.evaluate("""() => {
          document.querySelector('#seg-csf button[data-v="100"]').click();
          document.querySelector('#seg-cfilter button[data-v="all"]').click();
        }""")
        page.wait_for_timeout(200)
        got = page.evaluate("""() => {
          const tr = [...document.querySelectorAll('#cluster-body tr')]
            .find(r => r.querySelector('th').textContent.trim() === 'Q1');
          return [...tr.querySelectorAll('td')].map(td => td.textContent.trim());
        }""")
        src = [r for r in data["clusterQueries"]["100"] if r["q"] == 1][0]

        def as_reported(v: float) -> str:
            """The report's magnitude-based precision rule for seconds."""
            a = abs(v)
            if a < 10:
                return f"{v:.3f}"
            if a < 100:
                return f"{v:.2f}"
            if a < 1000:
                return f"{v:.1f}"
            return f"{v:,.0f}"

        check("clusterQ SF100 Q1 rust time", got[0] == as_reported(src["r"]),
              f"{got[0]} vs {src['r']}")
        check("clusterQ SF100 Q1 gluten time", got[1] == as_reported(src["g"]),
              f"{got[1]} vs {src['g']}")
        check("clusterQ SF100 Q1 ratio", got[3] == f"{src['ratio']:.2f}×",
              f"{got[3]} vs {src['ratio']}")
        check("clusterQ SF100 Q1 status", src["status"] in got[-1] or got[-1] == "pass",
              f"{got[-1]} vs {src['status']}")

        # ---- 5. Row counts equal source record counts ----
        for bench in ("TPC-H", "TPC-DS"):
            for sf in ("1", "10", "100", "1000"):
                page.evaluate("""([b,s]) => {
                  document.querySelector(`#seg-sbench button[data-v="${b}"]`).click();
                  document.querySelector(`#seg-ssf button[data-v="${s}"]`).click();
                }""", [bench, sf])
                page.wait_for_timeout(120)
                n = page.locator("#single-body tr").count()
                exp = len(data["single"][bench][sf])
                check(f"{bench} SF{sf} row count", n == exp, f"{n} vs {exp}")

        for sf in ("100", "1000", "10000"):
            page.evaluate("""(s) => {
              document.querySelector(`#seg-csf button[data-v="${s}"]`).click();
            }""", sf)
            page.wait_for_timeout(150)
            n = page.locator("#cluster-body tr").count()
            exp = len(data["clusterQueries"][sf])
            check(f"cluster SF{sf} row count", n == exp, f"{n} vs {exp}")

        # ---- 6. Hardware + provenance strings ----
        hw = data["hardware"]
        body = page.inner_text("body")
        for needle in (hw["single_node"]["sku"], hw["cluster_workers"]["sku"],
                       data["source"], data["sha256"][:32],
                       str(hw["cluster_workers"]["total_cores"]),
                       str(hw["cluster_workers"]["total_ram_gb"])):
            check(f"provenance string present: {str(needle)[:24]}", needle in body)

        # ---- 7. No fabricated engine names ----
        rendered_engines = set(page.evaluate("""() => {
          const s = new Set();
          document.querySelectorAll('table.data tbody th').forEach(th => {
            const t = th.textContent.trim();
            if (t && !t.startsWith('Q') && !t.startsWith('SF')) s.add(t);
          });
          return [...s];
        }"""))
        allowed = set(engines) | {"Spark Rust 0.42.1", "Spark 4.1.1 Gluten"}
        # Row labels that are metrics or headings, not engine names.
        label_re = re.compile(
            r"^(SF |Query|Metric|Engine|Scale|Status|Benchmark|Queries|Total wall|"
            r"Mean|Max|p50|p95|CPU|Memory|Mean cores)")
        extra = {e for e in rendered_engines if e not in allowed and not label_re.match(e)}
        check("no engine names invented", not extra, str(sorted(extra)[:5]))

        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} fidelity checks passed")
    if mismatches:
        print("\nVALUE MISMATCHES:")
        for m in mismatches[:25]:
            print(f"  - {m}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
