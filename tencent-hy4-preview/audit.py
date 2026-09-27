"""Programmatic audit of the generated report: structure, contrast, a11y, isolation."""
import json
import re
from playwright.sync_api import sync_playwright

URL = "file:///home/support/Documents/model-comparison/somemodel/engine-comparison-report.html"

CONTRAST_JS = """
() => {
  function lum(c){
    const [r,g,b]=c.map(v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);});
    return 0.2126*r+0.7152*g+0.0722*b;
  }
  function parse(s){const m=s.match(/[\\d.]+/g);return m?m.slice(0,3).map(Number):null;}
  function bgOf(el){
    let e=el;
    while(e){const c=getComputedStyle(e).backgroundColor;
      if(c && c!=='rgba(0, 0, 0, 0)' && c!=='transparent'){const p=parse(c);if(p)return p;}
      e=e.parentElement;}
    return [255,255,255];
  }
  const out=[];
  const sel='p,li,td,th,span.pill,.kpi .n,.kpi .l,.kpi .sub,.bl,.bv,.tbl-note,summary,h1,h2,h3,h4,caption,dt,dd,.muted,.small,footer,.factlist .k,.factlist .v,a';
  document.querySelectorAll(sel).forEach(el=>{
    const txt=(el.textContent||'').trim();
    if(!txt) return;
    const cs=getComputedStyle(el);
    if(cs.display==='none'||cs.visibility==='hidden') return;
    const fg=parse(cs.color); if(!fg) return;
    const bg=bgOf(el);
    const L1=lum(fg),L2=lum(bg);
    const ratio=(Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);
    const size=parseFloat(cs.fontSize), bold=parseInt(cs.fontWeight)>=700;
    const large = size>=24 || (size>=18.66 && bold);
    const need = large?3.0:4.5;
    if(ratio < need){
      out.push({tag:el.tagName, cls:(el.className||'').toString().slice(0,28),
        txt:txt.slice(0,42), ratio:+ratio.toFixed(2), need, size:+size.toFixed(1)});
    }
  });
  // dedupe by class+txt
  const seen=new Set();
  return out.filter(o=>{const k=o.cls+o.txt;if(seen.has(k))return false;seen.add(k);return true;});
}
"""

STRUCT_JS = """
() => {
  const heads=[...document.querySelectorAll('h1,h2,h3,h4')].map(h=>({t:h.tagName,x:h.textContent.trim().slice(0,52)}));
  // heading order violations
  const bad=[]; let prev=0;
  heads.forEach(h=>{const lvl=+h.t[1]; if(prev && lvl>prev+1) bad.push(h); prev=lvl;});
  const noAlt=[...document.querySelectorAll('img')].filter(i=>!i.alt).length;
  const btns=[...document.querySelectorAll('button')].map(b=>({t:b.textContent.trim().slice(0,20), lbl:b.getAttribute('aria-label')||b.textContent.trim().slice(0,20)}));
  const tables=[...document.querySelectorAll('table')].map(t=>({
    cap: t.querySelector('caption')? t.querySelector('caption').textContent.trim().slice(0,40):null,
    th: t.querySelectorAll('th').length, rows: t.querySelectorAll('tbody tr').length,
    scrollable: (()=>{let e=t.parentElement;while(e){const cs=getComputedStyle(e);if(cs.overflowX==='auto'||cs.overflowX==='scroll')return true;e=e.parentElement;}return false;})()
  }));
  const tabs=[...document.querySelectorAll('[role=tab]')].map(t=>({id:t.id,sel:t.getAttribute('aria-selected'),ctrl:t.getAttribute('aria-controls')}));
  const dupIds=(()=>{const s=new Set(),d=[];document.querySelectorAll('[id]').forEach(e=>{if(s.has(e.id))d.push(e.id);s.add(e.id);});return d;})();
  return {heads, bad, noAlt, btns, tables, tabs, dupIds,
    lang: document.documentElement.lang,
    title: document.title,
    viewport: document.querySelector('meta[name=viewport]')?.content,
    desc: document.querySelector('meta[name=description]')?.content?.slice(0,60)};
}
"""

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1440, "height": 1000})
    reqs = []
    pg.on("request", lambda r: reqs.append(r.url))
    errs = []
    pg.on("pageerror", lambda ex: errs.append(str(ex)))
    pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(500)

    print("=== NETWORK ===")
    ext = [u for u in reqs if not u.startswith("file://")]
    print("total requests:", len(reqs), "| non-file:", ext)

    print("\n=== STRUCTURE ===")
    s = pg.evaluate(STRUCT_JS)
    print("lang:", s["lang"], "| viewport:", s["viewport"])
    print("title:", s["title"])
    print("headings:", len(s["heads"]), "| order violations:", s["bad"])
    print("imgs missing alt:", s["noAlt"], "| duplicate ids:", s["dupIds"])
    print("buttons:", s["btns"])
    print("tables:", len(s["tables"]))
    nocap = [t for t in s["tables"] if not t["cap"]]
    noscroll = [t for t in s["tables"] if not t["scrollable"]]
    noth = [t for t in s["tables"] if t["th"] == 0]
    print("  missing caption:", len(nocap), "| not in scroll wrapper:", len(noscroll), "| no th:", len(noth))
    print("tabs:", len(s["tabs"]), "| selected:", [t["id"] for t in s["tabs"] if t["sel"] == "true"])

    print("\n=== CONTRAST (light) ===")
    cl = pg.evaluate(CONTRAST_JS)
    print("failures:", len(cl))
    for o in cl[:25]:
        print("  ", o)

    # dark theme
    pg.click("#themeBtn")
    pg.wait_for_timeout(300)
    print("\n=== CONTRAST (dark) ===")
    cd = pg.evaluate(CONTRAST_JS)
    print("failures:", len(cd))
    for o in cd[:25]:
        print("  ", o)
    pg.click("#themeBtn")
    pg.wait_for_timeout(200)

    print("\n=== KEYBOARD / TABS ===")
    # tab through first 12 focusables
    order = []
    for _ in range(12):
        pg.keyboard.press("Tab")
        order.append(pg.evaluate("() => {const a=document.activeElement; return a.tagName+':'+(a.textContent||a.getAttribute('aria-label')||'').trim().slice(0,26);}"))
    print("focus order:", order)

    # exercise a tab control
    pg.click("#tab-TPC-H-100")
    pg.wait_for_timeout(200)
    vis = pg.evaluate("""() => {
      const ids=['panel-TPC-H-1','panel-TPC-H-10','panel-TPC-H-100','panel-TPC-H-1000'];
      return ids.map(i=>({i, hidden: document.getElementById(i).hidden}));
    }""")
    print("after clicking SF 100:", vis)
    sel = pg.evaluate("() => [...document.querySelectorAll('#tab-TPC-H-1,#tab-TPC-H-10,#tab-TPC-H-100,#tab-TPC-H-1000')].map(t=>t.id+'='+t.getAttribute('aria-selected'))")
    print("aria-selected:", sel)

    # arrow key nav
    pg.focus("#tab-TPC-H-100")
    pg.keyboard.press("ArrowRight")
    pg.wait_for_timeout(150)
    print("after ArrowRight, active:", pg.evaluate("() => document.activeElement.id"))

    print("\n=== DETAILS / PRINT ===")
    pg.evaluate("() => document.querySelectorAll('details').forEach(d=>d.open=true)")
    pg.wait_for_timeout(300)
    print("details count:", pg.evaluate("() => document.querySelectorAll('details').length"))
    print("open panels rows:", pg.evaluate("() => document.querySelectorAll('details table tbody tr').length"))

    print("\n=== JS ERRORS ===")
    print(errs)

    # narrow viewport re-check
    pg.set_viewport_size({"width": 360, "height": 800})
    pg.wait_for_timeout(300)
    ov = pg.evaluate("() => ({sw:document.documentElement.scrollWidth, cw:document.documentElement.clientWidth})")
    print("\n=== NARROW 360 ===", ov)
    b.close()
