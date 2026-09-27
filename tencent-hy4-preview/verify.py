"""Verify rendered HTML numbers against the source JSON."""
import json
import re
from playwright.sync_api import sync_playwright

URL = "file:///home/support/Documents/model-comparison/somemodel/engine-comparison-report.html"
D = json.load(open("engine-comparison-summary-data.json"))
E = D["engines"]

fails, checks = [], 0


def chk(name, cond, detail=""):
    global checks
    checks += 1
    if not cond:
        fails.append(f"{name}: {detail}")


with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1440, "height": 1000})
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(400)

    # 1. Single-node totals table: TPC-H then TPC-DS, rows in engine order.
    rows = pg.evaluate("""() => {
      const t=[...document.querySelectorAll('#single table')].filter(x=>x.querySelector('caption').textContent.includes('Total wall-clock'));
      return t.map(tb=>[...tb.querySelectorAll('tbody tr')].map(tr=>[...tr.children].map(td=>td.textContent.trim())));
    }""")
    chk("two totals tables", len(rows) == 2, f"got {len(rows)}")
    for bi, bench in enumerate(("TPC-H", "TPC-DS")):
        for ri, eng in enumerate(E):
            cells = rows[bi][ri]
            chk(f"{bench} row label", cells[0] in eng, f"{cells[0]} vs {eng}")
            for si, sf in enumerate(["1", "10", "100", "1000"]):
                want = D["totals"][bench][bi * 5 + ri] if False else None
            # compare all-SF time (second-to-last numeric pair)
            allr = [r for r in D["totals"][bench] if r["sf"] == "all" and r["engine"] == eng][0]
            want_time = f"{allr['time']:,.2f}"
            got_time = cells[-2]
            chk(f"{bench} {eng} all-SF time", got_time == want_time, f"{got_time} != {want_time}")
            want_ratio = f"{allr['ratio']:,.3f}"
            chk(f"{bench} {eng} all-SF ratio", want_ratio in cells[-1], f"{cells[-1]} !~ {want_ratio}")

    # 2. Per-query tables: verify every cell against JSON.
    for bench in ("TPC-H", "TPC-DS"):
        for sf in ["1", "10", "100", "1000"]:
            got = pg.evaluate(
                """(id) => {
                  const tb=document.getElementById(id).querySelector('table');
                  return [...tb.querySelectorAll('tbody tr')].map(tr=>[...tr.children].map(td=>td.textContent.trim()));
                }""",
                f"panel-{bench}-{sf}",
            )
            src = D["single"][bench][sf]
            chk(f"{bench} SF{sf} row count", len(got) == len(src), f"{len(got)} vs {len(src)}")
            for i, row in enumerate(src):
                chk(f"{bench} SF{sf} Q{row['q']} label", got[i][0] == f"Q{row['q']}", got[i][0])
                for j in range(5):
                    want = f"{row['times'][j]:,.3f}"
                    cell = got[i][1 + j]
                    chk(f"{bench} SF{sf} Q{row['q']} {E[j]}", cell.startswith(want), f"{cell} !~ {want}")

    # 3. Cluster per-query tables.
    for sf in ["100", "1000", "10000"]:
        pg.evaluate("() => document.querySelectorAll('details').forEach(d=>d.open=true)")
        got = pg.evaluate(
            """(sf) => {
              const cap=[...document.querySelectorAll('caption')].find(c=>c.textContent.startsWith('SF '+sf+':'));
              const tb=cap.closest('table');
              return [...tb.querySelectorAll('tbody tr')].map(tr=>[...tr.children].map(td=>td.textContent.trim()));
            }""",
            sf,
        )
        src = D["clusterQueries"][sf]
        chk(f"cluster SF{sf} row count", len(got) == len(src), f"{len(got)} vs {len(src)}")
        for i, row in enumerate(src):
            chk(f"cluster SF{sf} Q{row['q']} label", got[i][0] == f"Q{row['q']}", got[i][0])
            for j, key in enumerate(["r", "g"]):
                v = row[key]
                want = "—" if v is None else f"{v:,.2f}"
                chk(f"cluster SF{sf} Q{row['q']} {key}", got[i][1 + j] == want, f"{got[i][1+j]} != {want}")

    # 4. Appendix A matched values verbatim.
    for bench in ("TPC-H", "TPC-DS"):
        got = pg.evaluate(
            """(bench) => {
              const h=[...document.querySelectorAll('#matched h3')].find(x=>x.textContent.trim()===bench);
              const tb=h.nextElementSibling.querySelector('table');
              return [...tb.querySelectorAll('tbody tr')].map(tr=>[...tr.children].map(td=>td.textContent.trim()));
            }""",
            bench,
        )
        for ri, eng in enumerate(E):
            r = [x for x in D["totals"][bench] if x["sf"] == "all" and x["engine"] == eng][0]
            chk(f"appendix {bench} {eng} matched", got[ri][4] == f"{r['matched']:,.6f}", f"{got[ri][4]} != {r['matched']}")
            chk(f"appendix {bench} {eng} ratio", got[ri][3] == f"{r['ratio']:,.6f}", got[ri][3])

    # 5. Hardware facts present.
    body = pg.evaluate("() => document.body.innerText")
    for token in [D["hardware"]["single_node"]["sku"], str(D["hardware"]["single_node"]["cores"]),
                  str(D["hardware"]["single_node"]["ram_gb"]), D["hardware"]["cluster_workers"]["sku"],
                  str(D["hardware"]["cluster_workers"]["total_cores"]), D["sha256"][:16], D["source"]]:
        chk(f"token {token}", token in body, "missing")

    # 6. Cluster KPI cards: win counts.
    for sf in ["100", "1000", "10000"]:
        chk(f"wins {sf} in text", f"{D['wins'][sf][0]} – {D['wins'][sf][1]}" in body or
            f"{D['wins'][sf][0]}–{D['wins'][sf][1]}" in body, "missing")

    b.close()

print(f"checks run: {checks}")
print(f"failures: {len(fails)}")
for f in fails[:40]:
    print("  FAIL", f)
