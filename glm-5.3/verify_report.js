/* DOM-level verification of the report: console errors, section content,
   layout overflow, and control interactions. Run: node verify_report.js */
const { chromium } = require("/home/support/.npm/_npx/e41f203b7505f1fb/node_modules/playwright-core");

(async () => {
  const browser = await chromium.launch();
  const results = [];
  const ok = (name, pass, detail = "") =>
    results.push(`${pass ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`);

  for (const vp of [{ w: 1280, h: 1000, tag: "desktop" }, { w: 390, h: 900, tag: "mobile" }]) {
    const page = await browser.newPage({ viewport: { width: vp.w, height: vp.h } });
    const errors = [];
    page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
    page.on("pageerror", e => errors.push(String(e)));
    await page.goto("http://127.0.0.1:8477/engine-comparison-report.html", { waitUntil: "networkidle" });

    if (vp.tag === "desktop") {
      ok("no console errors", errors.length === 0, errors.join(" | "));

      // sections rendered with content
      for (const id of ["kpiGrid", "setupBody", "totalsBody", "perqueryBody", "clusterBody", "methodBody"]) {
        const n = await page.locator("#" + id).evaluate(el => el.innerHTML.length);
        ok(`#${id} rendered`, n > 200, `${n} chars`);
      }
      // KPI cards
      const kpis = await page.locator("#kpiGrid .metric").count();
      ok("KPI cards present", kpis === 7, `${kpis} cards`);
      // totals tables: 2 benchmarks x (5 engines x 5 sf-groups) = 50 rows
      const tRows = await page.locator("#totalsBody tbody tr").count();
      ok("totals table rows", tRows === 50, `${tRows} rows`);
      // heatmap: TPC-H SF1 = 22 rows x 5 engines
      const heatCells = await page.locator("#perqueryBody table.heat td a").count();
      ok("heatmap cells", heatCells === 110, `${heatCells} cells`);
      // flagged markers visible in heatmap (TPC-H SF1000 has 3 B flags)
      await page.locator("#perqueryControls button[data-v='1000']").click();
      const flags = await page.locator("#perqueryBody td.flag").count();
      ok("flagged runs marked at SF1000", flags === 3, `${flags} flagged cells`);
      // switch benchmark to TPC-DS
      await page.locator("#perqueryControls button[data-v='TPC-DS']").click();
      const dsRows = await page.locator("#perqueryBody table.heat tbody tr").count();
      ok("TPC-DS heatmap rows", dsRows === 99, `${dsRows} rows`);
      // back to TPC-H SF1 for consistency
      await page.locator("#perqueryControls button[data-v='TPC-H']").click();
      await page.locator("#perqueryControls button[data-v='1']").click();

      // cluster: win bars + ratio charts + detail tables
      const winbars = await page.locator(".winbar").count();
      ok("cluster win bars", winbars === 3, `${winbars} bars`);
      const charts = await page.locator(".ratio-chart").count();
      ok("cluster ratio charts", charts === 3, `${charts} charts`);
      const chartCols = await page.locator(".ratio-chart .col").count();
      ok("ratio chart columns (99+99+94=292)", chartCols === 292, `${chartCols} cols`);
      const details = await page.locator("details.tbl").count();
      ok("collapsible detail tables", details === 4, `${details} details`);

      // theme toggle
      const before = await page.evaluate(() => getComputedStyle(document.body).color);
      await page.locator("#themeBtn").click();
      const after = await page.evaluate(() => getComputedStyle(document.body).color);
      ok("theme toggle changes colors", before !== after, `${before} -> ${after}`);

      // details expand
      await page.locator("details.tbl summary").first().click();
      const open = await page.locator("details.tbl[open]").count();
      ok("details expands", open === 1, `${open} open`);
    }

    // horizontal overflow check
    const overflow = await page.evaluate(() => ({
      doc: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      body: document.body.scrollWidth - document.body.clientWidth,
    }));
    ok(`${vp.tag}: no page-level horizontal overflow`, overflow.doc <= 0 && overflow.body <= 0,
      JSON.stringify(overflow));

    // focus visibility: tab to first nav link, check outline
    if (vp.tag === "desktop") {
      await page.keyboard.press("Tab");
      const outline = await page.evaluate(() => {
        const el = document.activeElement;
        const s = getComputedStyle(el);
        return s.outlineStyle !== "none" && s.outlineWidth !== "0px";
      });
      ok("focus-visible outline present", outline);
    }
    await page.close();
  }
  await browser.close();
  console.log(results.join("\n"));
  const fails = results.filter(r => r.startsWith("FAIL")).length;
  console.log(`\n${results.length - fails}/${results.length} checks passed`);
  process.exit(fails ? 1 : 0);
})().catch(e => { console.error("SCRIPT ERROR:", e); process.exit(2); });
