#!/usr/bin/env python3
"""pages.py — the pages that answer a question rather than describe a record.

  /near/    what is good near me, and what is worth the drive
  /sauce/   the sauce spectrum: how much tomato, sugar, vinegar and mustard, measured
  /quiz/    which side are you on
  /art/     handled by site.py's type index; this module supplies the gallery strip

Imported by site.py. Everything renders at build time; the only client-side work is
the reader's own geolocation (which never leaves the browser) and sorting.

Chart colours are validated with the dataviz skill's checker against this site's own
surfaces (light #fdfaf3, dark #1f1b18):

  four-class "first on the label" — vinegar #2a78d6, mustard #eda100, other #1baf7a,
  tomato #e34948 (light) / #3987e5 #c98500 #199e70 #e66767 (dark). Both modes pass;
  the CVD warn band obliges secondary encoding, which is here as direct labels, a
  legend, 2px gaps between segments and a table twin under every chart.

  Everything else is one hue (the site's ember) with position carrying the magnitude.
"""
from __future__ import annotations

import html
import json
import math
import re
import statistics

E = html.escape

# base key -> (label, one-line gloss). Order is east to west, the way the map reads.
BASES = [
    ("vinegar-pepper", "Vinegar and pepper", "vinegar, salt, black and red pepper. No tomato."),
    ("lexington-dip", "Lexington dip", "the same, with ketchup or tomato and a little sugar stirred in."),
    ("light-tomato", "Light tomato", "vinegar and pepper reddened with ketchup — thin, not sticky."),
    ("mustard", "Mustard", "prepared yellow mustard, vinegar, sugar, pepper."),
    ("heavy-tomato", "Heavy tomato", "tomato, brown sugar or molasses, vinegar, cooked down to cling."),
    ("hot-sauce", "Pepper sauce", "the bottle on the table beside the sauce, not instead of it."),
    ("other", "Other", "everything the four-sauce map does not cover."),
]
BASE_LABEL = {k: v for k, v, _ in BASES}

# first-ingredient classes, in stack order (validated adjacency)
FIRST_CLASSES = [
    ("vinegar", "Vinegar first", "#2a78d6", "#3987e5"),
    ("mustard", "Mustard first", "#eda100", "#c98500"),
    ("other", "Water, sugar or other first", "#1baf7a", "#199e70"),
    ("tomato", "Tomato or ketchup first", "#e34948", "#e66767"),
]

CHART_CSS = """
.viz{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:1rem 1.1rem;margin:1rem 0}
.viz h3{margin:.1rem 0 .2rem;font-size:1.06rem}.viz .note{font-size:.86rem;color:var(--mute);margin:.1rem 0 .7rem}
.viz svg{width:100%;height:auto;display:block;overflow:visible}
.viz .axis{font:500 11.5px -apple-system,"Segoe UI",Roboto,sans-serif;fill:var(--mute)}
.viz .rowlab{font:600 13px -apple-system,"Segoe UI",Roboto,sans-serif;fill:var(--ink)}
.viz .vallab{font:600 11.5px -apple-system,"Segoe UI",Roboto,sans-serif;fill:var(--mute)}
.viz .grid{stroke:var(--line);stroke-width:1}
.viz .dot{fill:var(--ember);stroke:var(--panel);stroke-width:2}
.viz .med{stroke:var(--ink);stroke-width:2;stroke-linecap:round}
.viz .seg{stroke:var(--panel);stroke-width:2}
.viz figcaption{font-size:.8rem;color:var(--mute);margin-top:.5rem}
.legend-row{display:flex;flex-wrap:wrap;gap:.45rem .9rem;margin:.5rem 0 .2rem;font-size:.84rem;font-family:-apple-system,"Segoe UI",Roboto,sans-serif}
.legend-row span{display:inline-flex;align-items:center;gap:.35rem;color:var(--ink)}
.legend-row i{width:.78rem;height:.78rem;border-radius:3px;display:inline-block}
details.tbl{margin:.6rem 0 0}details.tbl summary{cursor:pointer;font-size:.86rem;color:var(--mute);font-family:-apple-system,"Segoe UI",Roboto,sans-serif}
details.tbl table{font-size:.86rem;margin-top:.5rem}
.smallmult{display:grid;grid-template-columns:repeat(auto-fit,minmax(13rem,1fr));gap:.9rem;margin-top:.7rem}
.smallmult figure{margin:0;background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:.5rem .55rem}
.smallmult figcaption{font-size:.84rem;color:var(--ink);font-weight:600;margin:0 0 .25rem;font-family:-apple-system,"Segoe UI",Roboto,sans-serif}
.smallmult figcaption small{display:block;font-weight:400;color:var(--mute);font-size:.76rem}
"""

NEAR_CSS = """
.finder{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:1rem 1.1rem;margin:.8rem 0 1.2rem}
.finder .row{display:flex;gap:.6rem;flex-wrap:wrap;align-items:center}
.finder input[type=search]{flex:1;min-width:12rem;font:inherit;font-size:1.05rem;padding:.55rem .75rem;border:2px solid var(--line);border-radius:10px;background:var(--bg);color:var(--ink)}
.chips{display:flex;flex-wrap:wrap;gap:.4rem;margin:.7rem 0 0}
.chips button{font:inherit;font-size:.85rem;font-family:-apple-system,"Segoe UI",Roboto,sans-serif;padding:.3rem .7rem;border-radius:999px;border:1.5px solid var(--line);background:var(--bg);color:var(--ink);cursor:pointer}
.chips button[aria-pressed=true]{background:var(--ember);border-color:var(--ember);color:#fff}
.hit{display:grid;grid-template-columns:auto 1fr auto;gap:.2rem .8rem;align-items:baseline;padding:.55rem 0;border-bottom:1px solid var(--line)}
.hit .mi{font-variant-numeric:tabular-nums;font-weight:700;color:var(--ember);white-space:nowrap;font-family:-apple-system,"Segoe UI",Roboto,sans-serif}
.hit .nm{font-weight:600}.hit .wh{grid-column:2;font-size:.86rem;color:var(--mute)}
.hit .wk{grid-column:2;display:flex;align-items:center;gap:.55rem;margin-top:.3rem;font-size:.8rem;color:var(--mute)}
.hit .wk em{font-style:normal;color:var(--ember);font-weight:600}
.nohours{font-size:.8rem;color:var(--line)}
.daystrip{height:26px;width:176px;display:block;flex:0 0 auto}
.hit .tg{grid-column:2;font-size:.8rem;display:flex;flex-wrap:wrap;gap:.3rem;margin-top:.15rem}
.hit .go{font-size:.82rem;white-space:nowrap}
.drive{display:grid;grid-template-columns:repeat(auto-fill,minmax(16rem,1fr));gap:.9rem}
.drive .card b{display:block;font-size:1.05rem}
.drive .card .why{font-size:.84rem;color:var(--mute);margin-top:.25rem}
.stars{color:var(--gold);letter-spacing:.06em}
"""


def esc_js(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


# ---------------------------------------------------------------- near me

def near_page(page, places: dict, recs: list, tagvocab: dict, site_url: str) -> str:
    rows = []
    for p in places["places"]:
        if p.get("lat") is None:
            continue
        rows.append({
            "n": p["name"], "u": p.get("url"), "la": round(p["lat"], 4), "lo": round(p["lon"], 4),
            "c": p.get("city") or "", "co": p.get("county") or "", "s": p.get("state") or "",
            "t": p.get("tags") or [], "a": p.get("recognitions") or 0, "rb": p.get("recognized_by") or [],
            "d": "".join((p.get("days") or {}).get(k, "unknown")[0] for k in ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")),
            "so": bool(p.get("sold_out")), "ht": p.get("hours_text") or "",
            "b": (p.get("blurb") or "")[:150], "w": p.get("website") or "", "h": p.get("hours") or "",
            "st": p.get("styles") or [], "sc": p.get("status") or "",
        })
    towns: dict = {}
    for r in rows:
        if r["c"]:
            towns.setdefault(f"{r['c']}, {r['s']}", []).append((r["la"], r["lo"]))
    townpts = {k: [round(sum(x[0] for x in v) / len(v), 4), round(sum(x[1] for x in v) / len(v), 4)] for k, v in towns.items()}
    tags = [e for e in tagvocab.get("entries", []) if e["key"] in {t for r in rows for t in r["t"]}]
    drive = sorted([r for r in rows if r["a"] >= 1 and r["u"]], key=lambda r: (-r["a"], r["n"]))[:18]

    chips = ('<button type="button" data-tag="__sun" aria-pressed="false" title="A source says this one opens on Sunday">&#9788; Open Sunday</button>'
             '<button type="button" data-tag="__today" aria-pressed="false" title="Uses your own clock">&#128337; Open today</button>'
             + "".join(f'<button type="button" data-tag="{E(t["key"])}" aria-pressed="false">{E(t["icon"])} {E(t["label"])}</button>' for t in tags))
    drive_cards = "".join(
        f'<div class="card"><b><a href="../{E(r["u"])}index.html">{E(r["n"])}</a></b>'
        f'<span class="stars" aria-hidden="true">{"●" * min(r["a"], 5)}</span> '
        f'<span class="mute" style="font-size:.82rem">{r["a"]} {"recognition" if r["a"] == 1 else "recognitions"}</span>'
        f'<div class="why">{E(", ".join(r["rb"][:4]))}</div>'
        f'<div class="why">{E(r["c"])}{", " if r["c"] else ""}{E(r["s"])} — {E(r["b"][:110])}…</div></div>' for r in drive)

    counted = {e["key"]: sum(1 for r in rows if e["key"] in r["t"]) for e in tagvocab.get("entries", [])}
    empty = [e for e in tagvocab.get("entries", []) if counted.get(e["key"], 0) == 0]
    thin = [e for e in tagvocab.get("entries", []) if 0 < counted.get(e["key"], 0) <= 3]
    gaps = ""
    if empty:
        gaps += ("No place here carries " + ", ".join(f'<b>{E(e["label"].lower())}</b>' for e in empty)
                 + ". That is not a finding about the Carolinas — it is where our reading stopped. "
                 + "What would earn it: " + "; ".join(f'{E(e["label"].lower())} — {E(e["evidence"])}' for e in empty) + ". ")
    if thin:
        gaps += "Thin so far: " + ", ".join(f'{E(e["label"].lower())} ({counted[e["key"]]})' for e in thin) + ". "
    gaps += ('The directories we read are listed on <a href="../story/free-to-use/index.html">where all of this came from</a>. '
             'A business that wants a tag it has earned can say so on its own site or in any of those directories, and we will read it there.')
    body = f"""
<h1><span class="kind">Carolina Barbecue</span>Find the Q</h1>
<p class="lede">Two questions: what's good near me, and what's worth the gas.</p>

<div class="finder">
  <div class="row">
    <button class="btn" id="locate" type="button">📍 Use my location</button>
    <input id="town" type="search" list="towns" placeholder="or name a town — Ayden, Lexington, Hemingway…" aria-label="Town">
    <datalist id="towns">{"".join(f'<option value="{E(t)}">' for t in sorted(townpts))}</datalist>
    <button class="btn ghost" id="go" type="button">Search</button>
  </div>
  <div class="chips" id="chips" role="group" aria-label="Filters">{chips}
    <button type="button" data-tag="__page" aria-pressed="false">📄 Has a page here</button></div>
  <p class="mute" style="font-size:.84rem;margin:.6rem 0 0" id="status">Your browser reads your location and keeps it. Nothing leaves this page.</p>
</div>

<div id="out"></div>

<h2>Worth the drive</h2>
<p class="mute">Pits somebody already bragged on, in print: a Beard award, a spot on a trail, a wood-fire ticket, an oral history taken at the pit, a magazine list. The count is how many different folks said so — not how good we think it is. They're all named on the pit's own page.</p>
<div class="drive">{drive_cards}</div>

<h2 id="gaps">Still missing</h2>
<p class="mute">{gaps}</p>
<h2>Reading the tags</h2>
<table>{"".join(f'<tr><th>{E(t["icon"])} {E(t["label"])}</th><td>{E(t["evidence"])}</td></tr>' for t in tagvocab.get("entries", []))}</table>
<p class="mute">Every tag names its evidence on the pit's own page. No evidence, no tag. A missing tag says nothing about the pit, only about what we've read.</p>

<script>
(function(){{
var ROWS={esc_js(rows)}, TOWNS={esc_js(townpts)};
var TAGL={esc_js({e["key"]: (e["icon"] + " " + e["label"]) for e in tagvocab.get("entries", [])})};
var here=null, on={{}};
function esc(s){{return String(s==null?"":s).replace(/[&<>"]/g,function(c){{return {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]}})}}
function miles(a,b,c,d){{var R=3958.8,p=Math.PI/180,x=(c-a)*p,y=(d-b)*p,
  h=Math.sin(x/2)*Math.sin(x/2)+Math.cos(a*p)*Math.cos(c*p)*Math.sin(y/2)*Math.sin(y/2);
  return 2*R*Math.asin(Math.sqrt(h))}}
var TODAY=(new Date().getDay()+6)%7;   /* JS counts Sunday 0; this week starts Monday */
function keep(r){{
  for(var k in on){{ if(!on[k]) continue;
    if(k==="__page"){{ if(!r.u) return false; }}
    /* 'o' open, 'c' closed, 'u' nobody told us. A chip asks for OPEN, so 'u' is out —
       a pit we have not read is not evidence of anything either way. */
    else if(k==="__sun"){{ if(r.d.charAt(6)!=="o") return false; }}
    else if(k==="__today"){{ if(r.d.charAt(TODAY)!=="o") return false; }}
    else if(r.t.indexOf(k)<0) return false; }}
  return true}}
var DAYL=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],DAY1=["M","T","W","T","F","S","S"];
function strip(d){{
  if(!d||d==="uuuuuuu")return '<span class="nohours">hours not published</span>';
  var w=176,c=(w-10)/7,o='<svg class="daystrip" viewBox="0 0 '+w+' 26" role="img" aria-label="'+
    d.split("").map(function(x,i){{return DAYL[i]+" "+({{o:"open",c:"closed",u:"not published"}}[x])}}).join(", ")+'">';
  for(var i=0;i<7;i++){{var x=i*c+(i===6?10:0),st=d.charAt(i);
    var fill=st==="o"?"var(--ember)":"none",stroke=st==="o"?"var(--ember)":st==="c"?"var(--mute)":"var(--line)";
    var dash=st==="u"?' stroke-dasharray="2.5 2.5"':'',col=st==="o"?"#fff":st==="c"?"var(--mute)":"var(--line)";
    o+='<rect x="'+(x+1.5).toFixed(1)+'" y="3" width="'+(c-3).toFixed(1)+'" height="18" rx="4" fill="'+fill+'" stroke="'+stroke+'" stroke-width="1.6"'+dash+'/>'+
       '<text x="'+(x+c/2).toFixed(1)+'" y="17" text-anchor="middle" fill="'+col+'" style="font:700 11px -apple-system,sans-serif">'+DAY1[i]+'</text>';}}
  return o+'</svg>';
}}
function render(){{
  var out=document.getElementById("out");
  if(!here){{out.innerHTML="";return}}
  var hits=ROWS.filter(keep).map(function(r){{var d=miles(here[0],here[1],r.la,r.lo);return {{r:r,d:d}}}})
    .sort(function(a,b){{return a.d-b.d}}).slice(0,25);
  if(!hits.length){{out.innerHTML='<p class="mute">Nothing matches those filters yet. Fewer filters, or a different town.</p>';return}}
  out.innerHTML='<h2>Nearest first</h2>'+hits.map(function(h){{
    var r=h.r, tg=r.t.map(function(k){{return '<span class="chip">'+esc(TAGL[k]||k)+'</span>'}}).join("");
    var nm=r.u?('<a href="../'+esc(r.u)+'index.html">'+esc(r.n)+'</a>'):esc(r.n);
    var acc=r.a?(' <span class="stars" aria-hidden="true">'+"●".repeat(Math.min(r.a,5))+'</span>'):"";
    var where=[r.c,r.co?r.co+" County":"",r.s].filter(Boolean).join(" · ");
    var go=r.u?'<a class="go" href="../'+esc(r.u)+'index.html">page →</a>':(r.w?'<a class="go" href="'+esc(r.w)+'" rel="noopener">site →</a>':'<span class="go mute">no page yet</span>');
    return '<div class="hit"><span class="mi">'+h.d.toFixed(1)+' mi</span><span class="nm">'+nm+acc+'</span>'+go+
      '<span class="wh">'+esc(where)+(r.b?' — '+esc(r.b.slice(0,110))+'…':'')+'</span>'+
      '<span class="wk">'+strip(r.d)+(r.so?' <em>till it runs out</em>':'')+(r.ht?' <em>'+esc(r.ht)+'</em>':(r.h?' <span class="mute">'+esc(r.h)+'</span>':''))+'</span>'+
      (tg?'<span class="tg">'+tg+'</span>':'')+'</div>';
  }}).join("");
}}
document.getElementById("chips").addEventListener("click",function(e){{
  var b=e.target.closest("button[data-tag]"); if(!b)return;
  var k=b.getAttribute("data-tag"); on[k]=!on[k]; b.setAttribute("aria-pressed",on[k]?"true":"false"); render();
}});
document.getElementById("locate").addEventListener("click",function(){{
  var s=document.getElementById("status");
  if(!navigator.geolocation){{s.textContent="This browser will not share a location. Type a town instead.";return}}
  s.textContent="Asking your browser…";
  navigator.geolocation.getCurrentPosition(function(p){{
    here=[p.coords.latitude,p.coords.longitude];
    s.textContent="Sorted from where you are. Nothing left your browser.";render();
  }},function(){{s.textContent="Your browser said no. Type a town instead — it works the same, with no location at all.";}},{{timeout:10000}});
}});
function bytown(){{
  var v=document.getElementById("town").value.trim(), s=document.getElementById("status");
  if(!v)return; var hit=TOWNS[v];
  if(!hit){{ var k=Object.keys(TOWNS).filter(function(t){{return t.toLowerCase().indexOf(v.toLowerCase())===0}});
    if(k.length){{hit=TOWNS[k[0]];v=k[0]}} }}
  if(!hit){{s.textContent="No pit in this list is in a town by that name. Try the county seat next door.";return}}
  here=hit; s.textContent="Sorted from "+v+". No location was used."; render();
}}
document.getElementById("go").addEventListener("click",bytown);
document.getElementById("town").addEventListener("keydown",function(e){{if(e.key==="Enter"&&!e.isComposing){{e.preventDefault();bytown()}}}});
}})();
</script>
"""
    return page(f"Find the Q — Carolina Barbecue", body, 1,
                "Barbecue near you in North and South Carolina, and the pits worth a drive: wood-cooked, whole hog, Black-owned, woman-owned, LGBTQ+ welcoming — each tag with its evidence.",
                [{"@context": "https://schema.org", "@type": "WebPage", "name": "Find the Q", "url": f"{site_url}/near/"}],
                f"{site_url}/near/", extra_head=f"<style>{NEAR_CSS}</style>", card="near",
                og_alt="Find the Q: every barbecue pit in North and South Carolina, sorted from where you are")


# ---------------------------------------------------------------- sauce charts

def _first_class(ing: list) -> str:
    if not ing:
        return ""
    # A label prints an ingredient's own sub-ingredients in brackets after it —
    # YELLOW MUSTARD (DISTILLED VINEGAR, WATER, MUSTARD SEED, ...). Classify on the
    # ingredient's own name, so a mustard-first bottle is not read as vinegar-first.
    f = (ing[0] or "").lower().split("(")[0].split("[")[0]
    if "vinegar" in f:
        return "vinegar"
    if "mustard" in f:
        return "mustard"
    if "tomato" in f or "ketchup" in f or "catsup" in f:
        return "tomato"
    return "other"


def strip_plot(groups: list, unit: str, width=700, rowh=46) -> str:
    """One row per base, one dot per bottle, a median tick. Position carries the magnitude;
    one hue, because the rows are already labelled."""
    vals = [v for _, pts in groups for v, _ in pts]
    if not vals:
        return ""
    lo, hi = 0, max(vals) * 1.08
    left, right = 168, 24
    w = width
    h = len(groups) * rowh + 56
    px = lambda v: left + (v - lo) / (hi - lo) * (w - left - right)
    ticks = [t for t in (0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20) if t <= hi]
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Sugar per tablespoon, one dot per bottle, grouped by sauce base">']
    for t in ticks:
        out.append(f'<line class="grid" x1="{px(t):.1f}" y1="14" x2="{px(t):.1f}" y2="{h - 40}"/>'
                   f'<text class="axis" x="{px(t):.1f}" y="{h - 24}" text-anchor="middle">{t}</text>')
    out.append(f'<text class="axis" x="{left}" y="{h - 6}">{E(unit)}</text>')
    for i, (label, pts) in enumerate(groups):
        y = 32 + i * rowh
        out.append(f'<text class="rowlab" x="0" y="{y + 4}">{E(label)}</text>')
        if pts:
            med = statistics.median([v for v, _ in pts])
            out.append(f'<line class="med" x1="{px(med):.1f}" y1="{y - 13}" x2="{px(med):.1f}" y2="{y + 13}"><title>median {med:.1f}</title></line>')
            out.append(f'<text class="vallab" x="{px(med):.1f}" y="{y - 17}" text-anchor="middle">{med:.1f}</text>')
        seen: dict = {}
        for v, name in sorted(pts):
            k = round(px(v) / 7)
            off = seen.get(k, 0)
            seen[k] = off + 1
            dy = (off % 3 - 1) * 7
            out.append(f'<circle class="dot" cx="{px(v):.1f}" cy="{y + dy}" r="5"><title>{E(name)} — {v:g} {E(unit.split(",")[0])}</title></circle>')
    out.append("</svg>")
    return "".join(out)


def stacked_first(groups: list, dark=False, width=700) -> str:
    """Part-to-whole: what is the first ingredient on the label, by base. 2px surface gaps,
    direct labels on segments wide enough, a legend, and a table twin beside it."""
    left, right, barh, gap = 168, 30, 26, 16
    w = width
    h = len(groups) * (barh + gap) + 24
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="First ingredient on the label, share of bottles, by sauce base">']
    for i, (label, counts, total) in enumerate(groups):
        y = 8 + i * (barh + gap)
        out.append(f'<text class="rowlab" x="0" y="{y + barh - 8}">{E(label)}</text>')
        x = left
        span = w - left - right
        for key, lab, cl, cd in FIRST_CLASSES:
            n = counts.get(key, 0)
            if not n:
                continue
            bw = n / total * span
            col = cd if dark else cl
            out.append(f'<rect class="seg" x="{x:.1f}" y="{y}" width="{max(bw - 2, 1):.1f}" height="{barh}" rx="4" fill="{col}">'
                       f'<title>{E(label)}: {n} of {total} bottles, {lab.lower()}</title></rect>')
            if bw > 44:
                out.append(f'<text class="vallab" x="{x + bw / 2:.1f}" y="{y + barh / 2 + 4:.1f}" text-anchor="middle" style="fill:#fff">{n}</text>')
            x += bw
        out.append(f'<text class="vallab" x="{w - right + 6}" y="{y + barh / 2 + 4:.1f}">{total}</text>')
    out.append("</svg>")
    return "".join(out)


def sauce_map_multiples(states_geo: dict, by_base: dict, project, box, width=250) -> str:
    """Small multiples: one little two-state map per base, dots where the makers are.
    One series per panel, the panel title carries identity — no categorical palette needed."""
    h = int(width * (box[3] - box[1]) / ((box[2] - box[0]) * math.cos(math.radians(34.3))))
    shells = []
    for st in states_geo["states"]:
        d = []
        for ring in st["rings"]:
            pts = [project(x, y, box, width, h) for x, y in ring]
            d.append("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z")
        shells.append((("ctx" if st["context"] else "st"), " ".join(d)))
    out = ['<div class="smallmult">']
    for key, label, gloss in BASES:
        pts = by_base.get(key) or []
        if not pts:
            continue
        dots = []
        for s in pts:
            if s.get("lat") is None:
                continue
            x, y = project(s["lon"], s["lat"], box, width, h)
            if 0 <= x <= width and 0 <= y <= h:
                dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="var(--ember)" stroke="var(--bg)" stroke-width="1.5">'
                            f'<title>{E(s["name"])} — {E(s.get("maker", ""))}, {E(s.get("town", ""))}</title></circle>')
        paths = "".join(f'<path class="{c}" d="{d}"/>' for c, d in shells)
        out.append(f'<figure><figcaption>{E(label)} <small>{len(pts)} bottle{"s" if len(pts) != 1 else ""} · {E(gloss)}</small></figcaption>'
                   f'<svg viewBox="0 0 {width} {h}" role="img" aria-label="Makers of {E(label)} sauce in North and South Carolina">'
                   f'<style>.st{{fill:var(--chip);stroke:var(--mute);stroke-width:1}}.ctx{{fill:none;stroke:var(--line);stroke-width:.8}}</style>'
                   f'{paths}{"".join(dots)}</svg></figure>')
    out.append("</div>")
    return "".join(out)


def sauce_page(page, sauces: dict, recs: list, states_geo: dict, project, box, site_url: str) -> str:
    rows = [s for s in (sauces or {}).get("sauces", [])]
    sauce_recs = [r for r in recs if r["type"] == "sauce"]
    body = ['<h1><span class="kind">Carolina Barbecue</span>Inside the bottle</h1>',
            '<p class="lede">Read off the label, not the tongue: ingredients in order, sugar on the panel, the town it comes from. '
            'Nobody tasted a thing. Arguments over which one wins get settled elsewhere on this site, at length.</p>']
    if not rows:
        body.append('<p class="mute">The label survey has not been built yet — run the sauce harvest. The sauce pages themselves are up: '
                    + " · ".join(f'<a href="../sauce/{E(r["id"])}/index.html">{E(r["names"]["name"])}</a>' for r in sauce_recs) + "</p>")
        return page("What's in the sauce — Carolina Barbecue", "".join(body), 1, "The sauce spectrum.", None, f"{site_url}/sauce/",
                    extra_head=f"<style>{CHART_CSS}</style>", card="sauce")

    withsugar = [s for s in rows if s.get("sugar_g_per_tbsp") is not None]
    withing = [s for s in rows if s.get("ingredients")]
    nc = sum(1 for s in rows if s.get("state") == "NC")
    sc = sum(1 for s in rows if s.get("state") == "SC")
    body.append('<div class="facts">'
                + "".join(f'<div class="fact"><div class="n">{n}</div><div class="l">{E(l)}</div></div>' for n, l in
                          [(len(rows), "bottles read"), (nc, "North Carolina"), (sc, "South Carolina"), (len(withsugar), "with sugar on the label"), (len(withing), "with an ingredient list")])
                + "</div>")

    # chart 1 — sugar per tablespoon
    groups = []
    for key, label, _ in BASES:
        pts = [(s["sugar_g_per_tbsp"], f'{s["name"]} ({s.get("maker", "")})') for s in withsugar if s.get("base") == key]
        if pts:
            groups.append((label, pts))
    if groups:
        allv = [v for _, pts in groups for v, _ in pts]
        body.append('<div class="viz"><h3>Sugar, by the tablespoon</h3>'
                    f'<p class="note">One dot per bottle, {len(allv)} in all; the upright tick is the median of its row. '
                    f'A tablespoon of table sugar is about 12.6 g, so the right-hand end of this chart is nearly sugar. Hover a dot for the bottle.</p>'
                    + strip_plot(groups, "grams of sugar per tablespoon")
                    + '<details class="tbl"><summary>The same numbers as a table</summary><table><tr><th>Sauce</th><th>Maker</th><th>Base</th><th>Sugar g/tbsp</th></tr>'
                    + "".join(f'<tr><td>{E(s["name"])}</td><td>{E(s.get("maker", ""))}</td><td>{E(BASE_LABEL.get(s.get("base", ""), s.get("base", "")))}</td><td>{s["sugar_g_per_tbsp"]:g}</td></tr>'
                              for s in sorted(withsugar, key=lambda s: -s["sugar_g_per_tbsp"]))
                    + "</table></details></div>")

    # chart 2 — what is first on the label
    g2 = []
    for key, label, _ in BASES:
        counts: dict = {}
        for s in withing:
            if s.get("base") != key:
                continue
            c = _first_class(s["ingredients"])
            counts[c] = counts.get(c, 0) + 1
        tot = sum(counts.values())
        if tot:
            g2.append((label, counts, tot))
    if g2:
        leg = '<div class="legend-row">' + "".join(
            f'<span><i style="background:{cl}"></i>{E(lab)}</span>' for _, lab, cl, _ in FIRST_CLASSES) + "</div>"
        body.append('<div class="viz"><h3>What comes first on the label</h3>'
                    '<p class="note">Ingredients are printed in descending order by weight, so the first one is the sauce\'s argument in a single word. '
                    'Numbers on the segments are bottles; the number at the right is the row total.</p>'
                    + leg + stacked_first(g2)
                    + '<details class="tbl"><summary>The same counts as a table</summary><table><tr><th>Base</th>'
                    + "".join(f"<th>{E(lab)}</th>" for _, lab, _, _ in FIRST_CLASSES) + "<th>Bottles</th></tr>"
                    + "".join(f'<tr><td>{E(lab)}</td>' + "".join(f'<td>{c.get(k, 0)}</td>' for k, _, _, _ in FIRST_CLASSES) + f"<td>{t}</td></tr>" for lab, c, t in g2)
                    + "</table></details></div>")

    # chart 3 — where the makers are
    by_base: dict = {}
    for s in rows:
        if s.get("lat") is not None and s.get("state") in ("NC", "SC"):
            by_base.setdefault(s.get("base", "other"), []).append(s)
    if by_base:
        body.append('<div class="viz"><h3>Where the makers are</h3>'
                    '<p class="note">One little map per sauce. A dot is a bottler\'s town, not a restaurant; several bottles from one town sit on one dot. '
                    'The line across the middle is the state border.</p>'
                    + sauce_map_multiples(states_geo, by_base, project, box)
                    + '<figcaption>State outlines: Natural Earth, public domain. Towns geocoded from OpenStreetMap, ODbL.</figcaption></div>')

    # the ranks table — tomato/vinegar/mustard/sugar position
    body.append('<h2>Every bottle read</h2><p class="mute">Rank 1 means the first ingredient on the label. A dash means the label does not list it at all. '
                'Blank means we could not find a label to read, which is a fact about us, not about the sauce.</p>'
                '<div style="overflow-x:auto"><table><tr><th>Sauce</th><th>Maker</th><th>Town</th><th>Base</th><th>Vinegar</th><th>Tomato</th><th>Mustard</th><th>Sugar</th><th>Sugar g/tbsp</th><th>Label</th></tr>'
                + "".join(
                    "<tr><td>" + E(s["name"]) + "</td><td>" + E(s.get("maker", "")) + "</td><td>" + E((s.get("town") or "") + (", " + s["state"] if s.get("state") else "")) + "</td><td>"
                    + E(BASE_LABEL.get(s.get("base", ""), s.get("base", ""))) + "</td>"
                    + "".join("<td>" + ("—" if s.get(k) == 0 else ("" if s.get(k) is None else str(s[k]))) + "</td>" for k in ("vinegar_rank", "tomato_rank", "mustard_rank", "sugar_rank"))
                    + "<td>" + ("" if s.get("sugar_g_per_tbsp") is None else f'{s["sugar_g_per_tbsp"]:g}') + "</td>"
                    + "<td>" + (f'<a href="{E(s["source_url"])}" rel="noopener">seen here</a>' if s.get("source_url") else "") + "</td></tr>"
                    for s in sorted(rows, key=lambda s: (s.get("state") or "zz", s.get("base") or "", s["name"])))
                + "</table></div>")

    body.append("<h2>The sauces themselves</h2><div class=\"cards\">" + "".join(
        f'<div class="card"><a class="t" href="../sauce/{E(r["id"])}/index.html">{E(r["names"]["name"])}</a><p>{E(r["blurb"][:160])}</p></div>' for r in sauce_recs) + "</div>")
    body.append('<p class="legend">Labels were read on the makers\' own pages and on retailers\' product pages; each row links to the page it was read from, with the date on the sauce\'s own entry. '
                'Nutrition Facts round sugar to the gram, so a bottle showing 0 g may hold a little. The data is at <a href="../api/sauces.json">api/sauces.json</a>.</p>')
    return page("What is in the sauce — Carolina Barbecue", "".join(body), 1,
                "Carolina barbecue sauce measured from the label: sugar per tablespoon, what comes first on the ingredient list, and where the makers are.",
                [{"@context": "https://schema.org", "@type": "Dataset", "name": "Carolina barbecue sauce labels", "url": f"{site_url}/sauce/",
                  "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{site_url}/api/sauces.json"}]}],
                f"{site_url}/sauce/", extra_head=f"<style>{CHART_CSS}</style>", card="sauce",
                og_alt="Sugar, tomato, vinegar and mustard measured off 68 Carolina barbecue sauce labels")


# ---------------------------------------------------------------- the quiz

def quiz_page(page, quiz: dict, by_id: dict, site_url: str) -> str:
    qs = quiz["questions"]
    res = quiz["results"]
    forms = []
    for i, q in enumerate(qs):
        opts = "".join(
            f'<label class="opt"><input type="radio" name="q{i}" value="{i}-{j}"> {E(a["t"])}</label>' for j, a in enumerate(q["a"]))
        forms.append(f'<fieldset class="qz"><legend>{i + 1}. {E(q["q"])}</legend>{opts}</fieldset>')
    scoring = [[a["s"] for a in q["a"]] for q in qs]
    results = {k: {"title": v["title"], "say": v["say"], "url": f"../style/{k}/index.html"} for k, v in res.items() if k in by_id}
    body = f"""
<h1><span class="kind">Carolina Barbecue</span>{E(quiz["title"])}</h1>
<p class="lede">{E(quiz["lede"])}</p>
<form id="qz">{"".join(forms)}
<div class="cta"><button class="btn" id="tally" type="button">Tally it up</button><button class="btn ghost" id="again" type="button">Start over</button></div></form>
<div id="verdict" aria-live="polite"></div>
<p class="legend">Nothing here is stored or sent anywhere; the scoring runs in your browser and forgets you when you close the tab.
Every result links to a style page, where the sources are.</p>
<style>
.qz{{border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:.8rem 1rem;margin:.9rem 0}}
.qz legend{{font-weight:600;padding:0 .4rem}}
.opt{{display:block;padding:.35rem .2rem;cursor:pointer}}
.opt input{{margin-right:.55rem}}
.verdict{{background:var(--panel);border:2px solid var(--ember);border-radius:14px;padding:1rem 1.2rem;margin:1rem 0}}
.verdict h2{{margin:.1rem 0 .3rem;border:0}}
.bars{{margin-top:.7rem}}
.bars div{{display:grid;grid-template-columns:11rem 1fr auto;gap:.6rem;align-items:center;margin:.25rem 0;font-size:.9rem}}
.bars i{{display:block;height:.7rem;border-radius:4px;background:var(--ember)}}
</style>
<script>
(function(){{
var S={esc_js(scoring)}, R={esc_js(results)};
function esc(s){{return String(s==null?"":s).replace(/[&<>"]/g,function(c){{return {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]}})}}
document.getElementById("tally").addEventListener("click",function(){{
  var sc={{}}, answered=0;
  S.forEach(function(q,i){{
    var el=document.querySelector('input[name="q'+i+'"]:checked'); if(!el)return; answered++;
    var j=parseInt(el.value.split("-")[1],10), s=q[j];
    for(var k in s) sc[k]=(sc[k]||0)+s[k];
  }});
  var v=document.getElementById("verdict");
  if(!answered){{v.innerHTML='<p class="mute">Answer at least one.</p>';return}}
  var rank=Object.keys(sc).sort(function(a,b){{return sc[b]-sc[a]}});
  var top=rank[0], max=sc[top], r=R[top]||{{title:top,say:"",url:"#"}};
  var bars=rank.map(function(k){{var w=Math.round(sc[k]/max*100);
    return '<div><span>'+esc((R[k]||{{}}).title||k)+'</span><i style="width:'+w+'%"></i><span>'+sc[k]+'</span></div>'}}).join("");
  v.innerHTML='<div class="verdict"><h2>'+esc(r.title)+'</h2><p>'+esc(r.say)+'</p>'+
    '<p><a class="btn" href="'+esc(r.url)+'">Read the style →</a></p><div class="bars">'+bars+'</div></div>';
  v.scrollIntoView({{behavior:"smooth",block:"nearest"}});
}});
document.getElementById("again").addEventListener("click",function(){{
  document.getElementById("qz").reset(); document.getElementById("verdict").innerHTML="";
}});
}})();
</script>
"""
    return page(f'{quiz["title"]} — Carolina Barbecue', body, 1, quiz["lede"], None, f"{site_url}/quiz/", card="quiz",
                og_alt="Which side are you on? A six-question Carolina barbecue quiz")


# ---------------------------------------------------------------- the pig

# A side-view hog, facing left, in a 420×230 frame. The body is composed of simple shapes
# so that each region can be painted separately: the regions are rectangles clipped to the
# animal's own silhouette, which keeps the outline honest however the fills change.
# A side-view hog, facing left, in a 420x250 frame. The body is composed of simple shapes
# so each region can be painted separately: the regions are rectangles clipped to the
# animal's own silhouette, so the outline stays honest however the fills change.
HOG_SHAPES = (
    '<ellipse cx="228" cy="122" rx="112" ry="56"/>'
    '<ellipse cx="118" cy="128" rx="52" ry="42"/>'
    '<path d="M96 114 C72 110 52 114 40 122 C30 129 32 140 44 144 C58 149 78 148 92 142 Z"/>'
    '<path d="M104 94 L96 66 L132 84 Z"/>'
    '<rect x="132" y="160" width="20" height="56" rx="7"/>'
    '<rect x="160" y="162" width="19" height="52" rx="7"/>'
    '<rect x="276" y="160" width="21" height="56" rx="7"/>'
    '<rect x="304" y="162" width="19" height="52" rx="7"/>'
)
HOG_TAIL = ('<path d="M338 102 c16 -6 24 6 16 16 c-6 8 -18 6 -20 -2" fill="none" '
            'stroke="var(--ink)" stroke-width="5" stroke-linecap="round"/>')
HOG_EYE = '<circle cx="104" cy="114" r="5" fill="var(--ink)"/>'
# key, x, width, y, height, short label, gloss, label x, label y
HOG_REGIONS = [
    ("jowl", 36, 84, 66, 120, "jowl", "the head, the cheeks and the snout — whole-hog country only", 70, 232),
    ("shoulder", 120, 62, 66, 128, "shoulder", "the Boston butt on top and the picnic below: the Lexington cut", 150, 40),
    ("loin", 182, 78, 66, 44, "loin and ribs", "the long muscle along the back, and the ribs under it", 250, 22),
    ("belly", 182, 78, 110, 84, "belly", "the side, which is bacon anywhere else", 214, 244),
    ("ham", 260, 82, 66, 128, "ham", "the back leg, which Midlands pits cook by itself", 322, 40),
]


def hog_svg(lit: set, width=420, label=True, ident="") -> str:
    """One hog. Regions in `lit` are painted ember, the rest recede. Emphasis, not categories."""
    cid = f"hogclip{ident}"
    # The rim is drawn first as a fat stroke on every shape; the clipped fill then covers the
    # inner half of it, so the animal keeps one clean outer edge and no construction seams.
    out = [f'<svg viewBox="0 0 420 250" role="img" aria-label="A hog in side view; {", ".join(sorted(lit)) if lit else "no part"} marked">',
           f'<defs><clipPath id="{cid}">{HOG_SHAPES}</clipPath></defs>',
           f'<g fill="var(--ink)" stroke="var(--ink)" stroke-width="7" stroke-linejoin="round">{HOG_SHAPES}</g>',
           f'<g clip-path="url(#{cid})"><rect x="0" y="0" width="420" height="250" fill="var(--chip)"/>']
    for key, x, w, y, h, _, _, _, _ in HOG_REGIONS:
        if key in lit:
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="var(--ember)"/>')
    out.append("</g>")
    out.append(HOG_TAIL + HOG_EYE)
    if label:
        for key, x, w, y, h, lab, _, lx, ly in HOG_REGIONS:
            above = ly < 120
            y1 = ly + (6 if above else -12)
            y2 = y if above else y + h
            out.append(f'<line x1="{lx}" y1="{y1}" x2="{lx}" y2="{y2}" stroke="var(--mute)" stroke-width="1.5" stroke-dasharray="4 3"/>')
            out.append(f'<circle cx="{lx}" cy="{y2}" r="3" fill="var(--mute)"/>')
            out.append(f'<text x="{lx}" y="{ly}" text-anchor="middle" fill="var(--ink)" '
                       f'style="font:600 15px -apple-system,\'Segoe UI\',Roboto,sans-serif">{E(lab)}</text>')
    out.append("</svg>")
    return "".join(out)


PIG_STYLES = [
    ("eastern-nc", "Eastern North Carolina", {"jowl", "shoulder", "loin", "belly", "ham"}, "The whole animal goes on the pit and comes off the block in one chop — ham, shoulder, loin, belly and crisp skin together."),
    ("sc-pee-dee", "The Pee Dee", {"jowl", "shoulder", "loin", "belly", "ham"}, "The same whole hog across the state line, cooked the same way over hardwood coals."),
    ("lexington", "Lexington", {"shoulder"}, "The shoulder, and only the shoulder: fattier, darker, ten hours over hickory, and the outside brown is the part regulars ask for by name."),
    ("sc-mustard", "The Midlands", {"shoulder", "ham"}, "Hams and shoulders at most pits, whole hogs at some — and whatever is left over goes into the hash pot."),
    ("sc-heavy-tomato", "The Upstate", {"shoulder", "loin"}, "Shoulders and butts, plus ribs and chicken, which the rest of the Carolinas regards as a separate meal."),
]


def pig_page(page, by_id: dict, site_url: str) -> str:
    cuts = [i for i in ("whole-hog", "pork-shoulder", "outside-brown", "pork-skins", "hash-and-rice", "boston-butt") if i in by_id]
    body = ['<h1><span class="kind">Carolina Barbecue</span>Which part of the pig</h1>',
            '<p class="lede">Every argument here comes down to how much of the hog goes on the fire. '
            'Here\'s the hog, and here\'s what each style takes off it.</p>',
            '<div class="viz"><h3>How a pit crew divides a hog</h3>'
            '<p class="note">Side view, facing left. A pit that cooks the whole hog uses all of this at once; a pit that cooks shoulders uses one block of it.</p>'
            + '<div style="max-width:620px;margin:0 auto">' + hog_svg(set(), ident="all") + "</div>"
            + '<table style="margin-top:.8rem">'
            + "".join(f"<tr><th>{E(lab)}</th><td>{E(gloss)}</td></tr>" for _, _, _, _, _, lab, gloss, _, _ in HOG_REGIONS)
            + "</table></div>"]
    body.append('<div class="smallmult" style="grid-template-columns:repeat(auto-fit,minmax(17rem,1fr))">')
    for sid, label, lit, gloss in PIG_STYLES:
        rec = by_id.get(sid)
        link = f'<a href="../style/{E(sid)}/index.html">{E(label)}</a>' if rec else E(label)
        body.append(f'<figure><figcaption>{link} <small>{E(", ".join(sorted(lit)) if len(lit) < 5 else "the whole animal")}</small></figcaption>'
                    + hog_svg(lit, width=420, label=False, ident=sid)
                    + f'<figcaption style="font-weight:400;margin-top:.4rem">{E(gloss)}</figcaption></figure>')
    body.append("</div>")
    body.append('<h2>The cuts, in their own words</h2><div class="cards">' + "".join(
        f'<div class="card"><a class="t" href="../{"pit" if by_id[c]["type"] == "pit" else "dish"}/{E(c)}/index.html">{E(by_id[c]["names"]["name"])}</a>'
        f'<p>{E(by_id[c]["blurb"][:170])}</p></div>' for c in cuts) + "</div>")
    body.append('<p class="legend">The drawing is this project\'s own, and it is a diagram rather than a butcher\'s chart: '
                'the lines are where the styles differ, not where a knife goes. For the actual seams, a pork cutting chart from a state extension service is the thing to read.</p>')
    return page("Which part of the pig — Carolina Barbecue", "".join(body), 1,
                "A diagram of the hog with what each Carolina barbecue style cooks: whole hog in the east and the Pee Dee, the shoulder in Lexington, hams and shoulders in the Midlands.",
                None, f"{site_url}/pig/", extra_head=f"<style>{CHART_CSS}</style>", card="pig",
                og_alt="A hog in side view with the cuts each Carolina barbecue style cooks")


# ---------------------------------------------------------------- the numbers

import viz  # noqa: E402


def numbers_page(page, recs: list, places: dict, geo: dict, site_url: str, site_dir) -> str:
    import collections
    import re as _re

    pl = places["places"]
    by_id = {r["id"]: r for r in recs}

    # 1 — how near the nearest pit is, anywhere in the two states
    out_png = site_dir / "viz" / "near-the-nearest-pit.png"
    stats = viz.distance_png(geo, pl, out_png)

    # 2 — when the pits opened
    years = []
    for r in recs:
        y = (r.get("facets") or {}).get("founded")
        if r["type"] == "place" and y and _re.fullmatch(r"\d{4}", str(y)):
            years.append((int(y), r["names"]["name"]))

    # 3 — what the recipes call for
    stop = {"teaspoon", "teaspoons", "tablespoon", "tablespoons", "tbsp", "tsp", "cups", "cup", "quart", "pound",
            "pounds", "ounce", "ounces", "optional", "ground", "minced", "chopped", "finely", "taste", "large",
            "small", "fresh", "about", "into", "with", "plus", "each", "more", "than", "very", "well", "your",
            "prepared", "granulated", "packed", "pieces", "piece", "inch", "size", "good", "half", "them", "from"}
    words = collections.Counter()
    nrec = 0
    for r in recs:
        for rc in r.get("recipes", []):
            nrec += 1
            seen = set()
            for i in rc.get("ingredients", []):
                for wd in _re.findall(r"[a-z]{4,}", i.lower()):
                    if wd not in stop:
                        seen.add(wd)
            words.update(seen)
    ing_rows = [(w, c) for w, c in words.most_common(16)]

    # 4 — which days a barbecue house is open
    known = [p for p in pl if any(v != "unknown" for v in (p.get("days") or {}).values())]
    nh = len(known)
    days = {d: sum(1 for p in known if (p.get("days") or {}).get(d) == "open") for d in viz.DAYS}
    closed_su = sum(1 for p in known if (p.get("days") or {}).get("Su") == "closed")
    unk_su = len(pl) - nh
    day_rows = [(viz.DAY_NAME[d], days[d]) for d in viz.DAYS]

    # 5 — which kinds of page point at which
    edges = []
    for r in recs:
        for k in r.get("kin_out", []):
            t = by_id.get(k["to"])
            if t:
                edges.append({"from_type": r["type"], "to_type": t["type"]})
    order = ["style", "sauce", "dish", "pit", "place", "person", "org", "event", "term", "art", "story"]
    present = [t for t in order if any(e["from_type"] == t or e["to_type"] == t for e in edges)]
    labels = {"style": "styles", "sauce": "sauces", "dish": "dishes", "pit": "the pit", "place": "places",
              "person": "people", "org": "orgs", "event": "events", "term": "words", "art": "art", "story": "stories"}

    # a few numbers worth stating plainly
    lat_lon = [(p["lat"], p["lon"]) for p in pl if p.get("lat") is not None]
    import math as _m
    nearest = []
    for i, (a, b) in enumerate(lat_lon):
        best = min(((a - c) * 69) ** 2 + ((b - d) * 69 * _m.cos(_m.radians(a))) ** 2
                   for j, (c, d) in enumerate(lat_lon) if i != j)
        nearest.append(_m.sqrt(best))
    nearest.sort()
    med_gap = nearest[len(nearest) // 2] if nearest else 0

    body = ['<h1><span class="kind">Carolina Barbecue</span>Count it up</h1>',
            '<p class="lede">Adding it up.</p>',
            '<div class="facts">'
            + "".join(f'<div class="fact"><div class="n">{n}</div><div class="l">{E(l)}</div></div>' for n, l in [
                (f"{stats['median']:.1f} mi", "median distance to a pit, anywhere in the two states"),
                (f"{med_gap:.1f} mi", "median distance from one pit to the next"),
                (len(pl), "places"), (nrec, "recipes"), (len(edges), "links between pages")])
            + "</div>"]

    body.append('<div class="viz"><h3>Nowhere sits far from a pit</h3>'
                f'<p class="note">Every point in North and South Carolina, shaded by the distance to the closest of the {len(lat_lon)} places on the map. '
                f'Black dots are the places themselves. Half of both states is within {stats["median"]:.1f} miles of one.</p>'
                f'<img src="../viz/near-the-nearest-pit.png" alt="A map of North and South Carolina shaded by distance to the nearest barbecue place; the coastal plain and the piedmont are dark, the mountains and the southern swamps pale." style="width:100%;border-radius:10px;display:block">'
                + viz.ramp_legend(stats["cuts"], stats["ramp"], "miles to the nearest pit")
                + '<details class="tbl"><summary>The far corners</summary><table><tr><th>Miles to a pit</th><th>Where</th></tr>'
                + "".join(f'<tr><td>{mi:.0f}</td><td>{lat:.2f}, {lon:.2f}</td></tr>' for mi, lat, lon in stats["worst"])
                + '</table></details></div>')

    if years:
        body.append('<div class="viz"><h3>Who opened when</h3>'
                    f'<p class="note">The {len(years)} places here whose founding year is on a page. Stems stack where a year is crowded. '
                    'Hover one for the name.</p>' + viz.timeline_svg(years)
                    + '<details class="tbl"><summary>By decade</summary><table><tr><th>Decade</th><th>Pits</th></tr>'
                    + "".join(f"<tr><td>{d}s</td><td>{c}</td></tr>" for d, c in sorted(collections.Counter((y // 10) * 10 for y, _ in years).items()))
                    + "</table></details></div>")

    body.append('<div class="viz"><h3>Every recipe reaches for pepper</h3>'
                f'<p class="note">Across {nrec} recipes, counting each ingredient once per recipe. Measures and cutting words are dropped.</p>'
                + viz.bars_svg(ing_rows, unit="recipes calling for it")
                + '<details class="tbl"><summary>As a table</summary><table><tr><th>Ingredient word</th><th>Recipes</th></tr>'
                + "".join(f"<tr><td>{E(w)}</td><td>{c}</td></tr>" for w, c in ing_rows) + "</table></details></div>")

    body.append('<div class="viz"><h3>Which days they open</h3>'
                f'<p class="note">From the {nh} places whose days we could read. Saturday is the day nearly all of them keep. '
                f'Sunday is the one they drop: {closed_su} of the {nh} are shut, and another {unk_su} have not published their days at all. '
                'Monday is the next thinnest, which is the pit crew catching up. '
                '<a href="../story/the-sunday-question/index.html">Why Sunday →</a></p>'
                + viz.bars_svg(day_rows, unit="places open", left=140)
                + '<details class="tbl"><summary>As a table</summary><table><tr><th>Day</th><th>Open</th></tr>'
                + "".join(f"<tr><td>{E(d)}</td><td>{c}</td></tr>" for d, c in day_rows) + "</table></details></div>")

    body.append('<div class="viz"><h3>Who is kin to who</h3>'
                f'<p class="note">Every one of the {len(edges)} links between pages, by the kind of page at each end. '
                'The row points at the column.</p>'
                + viz.kin_matrix_svg(edges, present, labels) + "</div>")

    body.append('<p class="legend">The distance map is computed on a grid of about two miles, clipped to the states\' own outlines '
                '(Natural Earth, public domain) and measured against every place on the map, most of which come from OpenStreetMap under the ODbL. '
                'Everything else is counted straight out of <a href="../api/nodes.json">the records</a>.</p>')
    return page("Count it up — Carolina Barbecue", "".join(body), 1,
                "Carolina barbecue counted: how near the nearest pit is anywhere in the two states, when the pits opened, what the recipes call for, which days they open.",
                None, f"{site_url}/numbers/", extra_head=f"<style>{CHART_CSS}</style>", card="numbers",
                og_alt="A map of North and South Carolina shaded by distance to the nearest barbecue place")


# ---------------------------------------------------------------- make a sauce

MAKE_CSS = """
.dials{display:grid;grid-template-columns:repeat(auto-fit,minmax(13rem,1fr));gap:1rem;background:var(--panel);
  border:1px solid var(--line);border-radius:14px;padding:1rem 1.1rem;margin:.6rem 0 1.2rem}
.dial b{display:block;font-size:.78rem;text-transform:uppercase;letter-spacing:.14em;color:var(--gold);
  font-family:var(--sign,sans-serif);margin-bottom:.4rem}
.dial .opts{display:flex;flex-wrap:wrap;gap:.35rem}
.dial button{font:inherit;font-size:.86rem;font-family:var(--ui,sans-serif);padding:.32rem .72rem;border-radius:999px;
  border:1.5px solid var(--line);background:var(--bg);color:var(--ink);cursor:pointer}
.dial button[aria-pressed=true]{background:var(--ember);border-color:var(--ember);color:#fff}
.recipe{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:1.2rem 1.3rem}
.recipe h3{margin:.1rem 0 .1rem;font-size:1.3rem}
.recipe .says{color:var(--mute);font-style:italic;margin:0 0 .9rem}
.recipe ul{list-style:none;margin:.2rem 0 1rem;padding:0}
.recipe li{display:flex;gap:.7rem;padding:.3rem 0;border-bottom:1px dotted var(--line);font-size:1rem}
.recipe li .q{flex:0 0 9.5rem;text-align:right;font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}
@media(max-width:520px){.recipe li{flex-direction:column;gap:0}.recipe li .q{text-align:left;flex:none}}
.recipe li.zero{display:none}
.recipe ol{margin:.2rem 0 1rem;padding-left:1.2rem}.recipe ol li{display:list-item;border:0;padding:.15rem 0}
.recipe .prov{font-size:.85rem;color:var(--mute);border-top:1px solid var(--line);padding-top:.7rem;margin-top:.4rem}
.sugarline{display:flex;align-items:baseline;gap:.6rem;flex-wrap:wrap;margin:.2rem 0 .3rem}
.sugarline b{font-size:1.5rem;font-family:var(--display,serif)}
.nearby{font-size:.88rem;color:var(--mute);margin:.5rem 0 0}
.mk-actions{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:1rem}
"""


MAKE_TABS_CSS = """
.tabs{display:flex;gap:.4rem;margin:.2rem 0 1rem}
.tabs button{font:inherit;font-family:var(--sign,sans-serif);font-size:.95rem;letter-spacing:.04em;padding:.5rem 1.1rem;
  border-radius:999px;border:2px solid var(--line);background:var(--bg);color:var(--ink);cursor:pointer}
.tabs button[aria-selected=true]{background:var(--ember);border-color:var(--ember);color:#fff}
.panel[hidden]{display:none}
.carolina-note{background:var(--panel);border-left:5px solid var(--gold);border-radius:0 12px 12px 0;padding:.8rem 1rem;margin:.2rem 0 1rem;font-size:.95rem}
.per{font-size:.86rem;color:var(--mute);margin:.1rem 0 .8rem}
"""


def make_page(page, builder: dict, sauces: dict, recs: list, site_url: str, rub: dict | None = None, slaw: dict | None = None) -> str:
    by_id = {r["id"]: r for r in recs}
    # every bottle we measured, so the result can be put beside them
    bottles = [{"n": s["name"], "b": s.get("base"), "g": s.get("sugar_g_per_tbsp")}
               for s in sauces.get("sauces", []) if s.get("sugar_g_per_tbsp") is not None]
    for b in builder["bases"]:
        rec = by_id.get(b["sauce"])
        b["href"] = f"../sauce/{b['sauce']}/index.html" if rec else ""
        st = by_id.get(b["style"])
        b["style_href"] = f"../style/{b['style']}/index.html" if st else ""
        b["style_name"] = st["names"]["name"] if st else ""

    # The page opens on the recipe as its source has it — heat and sweetness at 1.0 — so the
    # first thing a reader sees is the cited proportions, and the dials move away from them.
    DEFAULTS = {"base": builder["bases"][0]["key"], "heat": "medium", "sweet": "sweet", "batch": "quart"}

    def dial(name, key, opts):
        return (f'<div class="dial"><b>{E(name)}</b><div class="opts" data-dial="{key}">'
                + "".join(f'<button type="button" data-v="{E(o["key"])}" '
                          f'aria-pressed="{"true" if o["key"] == DEFAULTS[key] else "false"}">{E(o["label"])}</button>'
                          for o in opts) + "</div></div>")

    RDEF = {"level": rub["levels"][0]["key"], "meat": "shoulder", "heat": "medium"}
    SDEF = {"kind": slaw["kinds"][0]["key"], "size": "head", "sweet": "some", "heat": "some"}

    def sdial(name, key, opts):
        return (f'<div class="dial"><b>{E(name)}</b><div class="opts" data-dial="{key}">'
                + "".join(f'<button type="button" data-v="{E(o["key"])}" '
                          f'aria-pressed="{"true" if o["key"] == SDEF[key] else "false"}">{E(o["label"])}</button>'
                          for o in opts) + "</div></div>")

    def rdial(name, key, opts):
        return (f'<div class="dial"><b>{E(name)}</b><div class="opts" data-dial="{key}">'
                + "".join(f'<button type="button" data-v="{E(o["key"])}" '
                          f'aria-pressed="{"true" if o["key"] == RDEF[key] else "false"}">{E(o["label"])}</button>'
                          for o in opts) + "</div></div>")

    body = f"""
<h1><span class="kind">Carolina Barbecue</span>Make it</h1>
<p class="lede">Build a sauce, a rub or a slaw from sources this site can cite. Published recipes get named where they
exist. Everything else says plainly that the proportions are ours.</p>

<div class="tabs" role="tablist">
  <button type="button" role="tab" data-panel="sauce" aria-selected="true">A sauce</button>
  <button type="button" role="tab" data-panel="rub" aria-selected="false">A rub</button>
  <button type="button" role="tab" data-panel="slaw" aria-selected="false">Slaw</button>
</div>

<section class="panel" id="panel-sauce">
<div class="dials">
  {dial("Region", "base", [{"key": b["key"], "label": b["name"]} for b in builder["bases"]])}
  {dial("Heat", "heat", builder["heats"])}
  {dial("Sweetness", "sweet", builder["sweets"])}
  {dial("How much", "batch", builder["batches"])}
</div>

<div class="recipe" id="out"></div>

</section>

<section class="panel" id="panel-rub" hidden>
<p class="carolina-note">{E(rub["carolina_note"])}</p>
<div class="dials">
  {rdial("How far out", "level", [{"key": l["key"], "label": l["name"]} for l in rub["levels"]])}
  {rdial("What you are cooking", "meat", [{"key": m["key"], "label": m["label"]} for m in rub["meats"]])}
  {rdial("Heat", "heat", rub["heats"])}
</div>
<div class="recipe" id="rubout"></div>
<p class="legend">Amounts per pound are this project's rule of thumb, not a pit's measurement — the proportions inside
each level are the cited thing. A rub is easy to overdo and hard to undo; the block will take care of the rest.</p>
</section>

<section class="panel" id="panel-slaw" hidden>
<p class="carolina-note">{E(slaw["carolina_note"])}</p>
<div class="dials">
  {sdial("Which slaw", "kind", [{"key": k["key"], "label": k["name"]} for k in slaw["kinds"]])}
  {sdial("How much cabbage", "size", [{"key": z["key"], "label": z["label"]} for z in slaw["sizes"]])}
  {sdial("Sweetness", "sweet", slaw["sweets"])}
  {sdial("Heat", "heat", slaw["heats"])}
</div>
<div class="recipe" id="slawout"></div>
<p class="legend">A medium head runs 2 lb and shreds to 8 cups; quantities scale off that. Three dressings follow
the records' cited descriptions and say so. The 1879 one keeps its author's quantities.</p>
</section>

<p class="legend">Sugar is worked out from the quantities on screen: {builder["sugar_g_per_tbsp"]["sugar"]} g of sugar in a
tablespoon of sugar, {builder["sugar_g_per_tbsp"]["molasses"]} g in molasses, {builder["sugar_g_per_tbsp"]["ketchup"]} g in
ketchup. The bottles it is drawn against were read off their own labels for
<a href="../sauce/index.html">the sauce page</a>.</p>

<script>
(function(){{
var B={esc_js(builder)}, BOTTLES={esc_js(bottles)};
var pick={{base:B.bases[0].key, heat:"medium", sweet:"sweet", batch:"quart"}};
function esc(s){{return String(s==null?"":s).replace(/[&<>"]/g,function(c){{return {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]}})}}
var FRAC=[[1,"1"],[0.75,"¾"],[0.6667,"⅔"],[0.5,"½"],[0.3333,"⅓"],[0.25,"¼"],[0.125,"⅛"]];
function nice(tbsp){{
  /* the kitchen unit a cook would actually reach for */
  if(tbsp<=0) return null;
  var p=function(v,w){{return frac(v)+" "+w+(v>1.02?"s":"")}};
  if(tbsp>=16) return p(tbsp/16,"cup");
  if(tbsp>=1) return p(tbsp,"tablespoon");
  return p(tbsp*3,"teaspoon");
}}
function frac(v){{
  var whole=Math.floor(v+1e-9), rem=v-whole, best="", bd=9;
  for(var i=0;i<FRAC.length;i++){{var d=Math.abs(rem-FRAC[i][0]); if(d<bd){{bd=d;best=FRAC[i][1];}}}}
  if(rem<0.06) return String(whole||"0");
  if(bd>0.06&&whole===0) return (Math.round(v*100)/100).toString();
  if(best==="1"){{whole+=1;best="";}}
  return (whole?whole+(best?" ":""):"")+best;
}}
function base(){{return B.bases.filter(function(b){{return b.key===pick.base}})[0]}}
function mult(list,key){{var m=list.filter(function(x){{return x.key===key}})[0]; return m?m.mult:1}}
function compute(){{
  var b=base(), tbsp=B.batches.filter(function(x){{return x.key===pick.batch}})[0].tbsp;
  var hm=mult(B.heats,pick.heat), sm=mult(B.sweets,pick.sweet);
  var rows=[], vol=0, sugar=0;
  b.ingredients.forEach(function(ing){{
    var f=ing.per_tbsp;
    if(ing.dial==="heat") f*=hm;
    if(ing.dial==="sweet") f*=sm;
    var q=f*tbsp;
    vol+=q;
    if(ing.sugar) sugar+=q*B.sugar_g_per_tbsp[ing.sugar];
    rows.push({{name:ing.name, q:q, hint:ing.unit_hint||""}});
  }});
  return {{b:b, rows:rows, vol:vol, sugar:vol>0?sugar/vol:0, tbsp:tbsp}};
}}
function scale(g){{
  /* the same 0 to 12.6 scale the sauce page uses */
  var w=420, x0=10, x1=w-10, pos=function(v){{return x0+(x1-x0)*Math.min(v/12.6,1)}};
  var o='<svg viewBox="0 0 '+w+' 64" role="img" aria-label="Where this sauce sits for sugar against the bottles measured for this site">';
  o+='<rect x="'+x0+'" y="26" width="'+(x1-x0)+'" height="8" rx="4" fill="var(--chip)"/>';
  BOTTLES.forEach(function(bt){{ o+='<circle cx="'+pos(bt.g).toFixed(1)+'" cy="30" r="3.4" fill="var(--mute)" opacity=".65"><title>'+esc(bt.n)+' — '+bt.g+' g</title></circle>'; }});
  o+='<circle cx="'+pos(g).toFixed(1)+'" cy="30" r="11" fill="var(--ember)" opacity=".25"/>';
  o+='<circle cx="'+pos(g).toFixed(1)+'" cy="30" r="7" fill="var(--ember)" stroke="var(--panel)" stroke-width="2"/>';
  o+='<text x="'+x0+'" y="56" fill="var(--mute)" style="font:600 11px var(--ui,sans-serif)">0 g</text>';
  o+='<text x="'+x1+'" y="56" text-anchor="end" fill="var(--mute)" style="font:600 11px var(--ui,sans-serif)">12.6 g — a spoonful of sugar</text>';
  return o+'</svg>';
}}
function gap(g,key){{
  /* the distance between what you just built and what the shelf sells, which is nearly
     all sugar — the site's own measurement, not an opinion about either one */
  var mine=BOTTLES.filter(function(b){{return b.b===key}}).map(function(b){{return b.g}}).sort(function(a,c){{return a-c}});
  if(mine.length<2) return "";
  var med=mine[Math.floor(mine.length/2)];
  var d=med-g;
  if(Math.abs(d)<0.6) return '<p class="nearby">That is about where the bottles of this kind sit — a median of '+med+' g.</p>';
  if(d>0) return '<p class="nearby">A bottle of this kind carries about <b>'+med+' g</b>, so the shelf is '+
    (d/Math.max(g,0.1)>=2?'several times':'a good deal')+' sweeter than this. Closing that gap means adding sugar until it is '+
    'roughly a quarter of the jar by weight, which is what those labels describe.</p>';
  return '<p class="nearby">That is sweeter than the bottles of this kind, which sit around '+med+' g.</p>';
}}function render(){{
  var r=compute(), b=r.b, a=b.anchor;
  var heat=B.heats.filter(function(x){{return x.key===pick.heat}})[0].label.toLowerCase();
  var sweet=B.sweets.filter(function(x){{return x.key===pick.sweet}})[0].label.toLowerCase();
  var batch=B.batches.filter(function(x){{return x.key===pick.batch}})[0].label;
  var ing=r.rows.map(function(x){{
    var q=nice(x.q);
    return '<li class="'+(q?'':'zero')+'"><span class="q">'+esc(q||'')+'</span><span>'+esc(x.name)+
      (x.hint?' <span class="mute">('+esc(x.hint)+')</span>':'')+'</span></li>';
  }}).join("");
  var near=BOTTLES.filter(function(bt){{return bt.b===b.key}})
      .sort(function(p,q){{return Math.abs(p.g-r.sugar)-Math.abs(q.g-r.sugar)}}).slice(0,3);
  var prov;
  if(a.kind==="recipe") prov='Built on <b>'+esc(a.title)+'</b>'+(a.year?', '+a.year:'')+', '+esc(a.publisher)+
      ' — '+esc(a.license)+(a.url?' · <a href="'+esc(a.url)+'" rel="noopener">the recipe</a>':'')+'. '+esc(a.note||'');
  else if(a.kind==="ancestor") prov='Descends from <b>'+esc(a.title)+'</b>, '+esc(a.publisher)+' '+(a.year||'')+
      ' ('+esc(a.license)+'). '+esc(a.note||'');
  else prov='<b>These proportions are this project\\'s own.</b> '+esc(a.note||'');
  document.getElementById("out").innerHTML=
    '<h3>'+esc(b.name)+', '+esc(heat)+', '+esc(sweet)+' — '+esc(batch)+'</h3>'+
    '<p class="says">'+esc(b.says)+' · '+esc(b.region)+'</p>'+
    '<ul>'+ing+'</ul>'+
    '<h4>How</h4><ol>'+b.method.map(function(m){{return '<li>'+esc(m)+'</li>'}}).join("")+'</ol>'+
    '<div class="sugarline"><b>'+r.sugar.toFixed(1)+' g</b><span class="mute">of sugar in a tablespoon of it</span></div>'+
    scale(r.sugar)+
    gap(r.sugar,b.key)+
    (near.length?'<p class="nearby">Nearest bottles on the shelf: '+near.map(function(x){{return esc(x.n)+' ('+x.g+' g)'}}).join(' · ')+'</p>':'')+
    '<div class="mk-actions"><button type="button" class="btn" id="copy">Copy the recipe</button>'+
    (b.href?'<a class="btn ghost" href="'+b.href+'">About this sauce</a>':'')+
    (b.style_href?'<a class="btn ghost" href="'+b.style_href+'">'+esc(b.style_name)+'</a>':'')+'</div>'+
    '<p class="prov">'+prov+' Method '+(b.method_tier==="cited"?'as published':b.method_tier==="tradition"?'as the tradition has it':'is ours')+'.</p>';
  document.getElementById("copy").addEventListener("click",function(){{
    var txt=b.name+' sauce — '+heat+', '+sweet+', '+batch+'\\n\\n'+
      r.rows.filter(function(x){{return nice(x.q)}}).map(function(x){{return nice(x.q)+'  '+x.name}}).join('\\n')+
      '\\n\\n'+b.method.join('\\n')+'\\n\\n'+r.sugar.toFixed(1)+' g sugar per tablespoon.\\n'+
      'From Carolina Barbecue — {site_url}/make/';
    (navigator.clipboard?navigator.clipboard.writeText(txt):Promise.reject()).then(function(){{
      document.getElementById("copy").textContent="Copied";
      setTimeout(function(){{document.getElementById("copy").textContent="Copy the recipe"}},1600);}},function(){{}});
  }});
}}
document.querySelector("#panel-sauce .dials").addEventListener("click",function(e){{
  var btn=e.target.closest("button[data-v]"); if(!btn)return;
  var group=btn.closest("[data-dial]"), k=group.dataset.dial;
  pick[k]=btn.dataset.v;
  [].forEach.call(group.querySelectorAll("button"),function(x){{x.setAttribute("aria-pressed",x===btn?"true":"false")}});
  render();
}});
render();
}})();

/* ------------------------------------------------------------------ the rub */
(function(){{
var R={esc_js(rub)}, pick={{level:R.levels[0].key, meat:"shoulder", heat:"medium"}};
function esc(s){{return String(s==null?"":s).replace(/[&<>"]/g,function(c){{return {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]}})}}
var FR=[[1,"1"],[0.75,"¾"],[0.6667,"⅔"],[0.5,"½"],[0.3333,"⅓"],[0.25,"¼"],[0.125,"⅛"]];
function frac(v){{var w=Math.floor(v+1e-9),r=v-w,b="",bd=9;
  for(var i=0;i<FR.length;i++){{var d=Math.abs(r-FR[i][0]); if(d<bd){{bd=d;b=FR[i][1];}}}}
  if(r<0.06)return String(w||"0");
  if(bd>0.08&&w===0)return (Math.round(v*100)/100).toString();
  if(b==="1"){{w+=1;b="";}}
  return (w?w+(b?" ":""):"")+b;}}
function nice(tbsp){{if(tbsp<=0)return null;
  var p=function(v,wd){{return frac(v)+" "+wd+(v>1.02?"s":"")}};
  if(tbsp>=16)return p(tbsp/16,"cup");
  if(tbsp>=1)return p(tbsp,"tablespoon");
  return p(tbsp*3,"teaspoon");}}
function rate(tbspPerLb){{
  /* under a tablespoon reads better as teaspoons, which is where every level but the last sits */
  if(tbspPerLb>=1) return frac(tbspPerLb)+' tablespoon'+(tbspPerLb>1.02?'s':'');
  var t=tbspPerLb*3; return frac(t)+' teaspoon'+(t>1.02?'s':'');
}}
function lvl(){{return R.levels.filter(function(x){{return x.key===pick.level}})[0]}}
function render(){{
  var L=lvl(), M=R.meats.filter(function(x){{return x.key===pick.meat}})[0];
  var hm=R.heats.filter(function(x){{return x.key===pick.heat}})[0];
  var total=L.tbsp_per_lb*M.lb, rows=[], sum=0;
  for(var k in L.parts){{
    var f=L.parts[k];
    if(R.heat_ingredients.indexOf(k)>=0) f*=hm.mult;
    rows.push({{name:k, q:f*total}}); sum+=f*total;
  }}
  var a=L.anchor, prov;
  if(a.kind==="recipe") prov='<b>'+esc(a.title)+'</b>, '+esc(a.publisher)+' — '+esc(a.license)+
     (a.url?' · <a href="'+esc(a.url)+'" rel="noopener">the recipe</a>':'')+'. '+esc(a.note);
  else if(a.kind==="named") prov='<b>'+esc(a.title)+'</b>, from '+esc(a.publisher)+
     (a.url?' · <a href="'+esc(a.url)+'" rel="noopener">the article</a>':'')+'. '+esc(a.note);
  else prov=esc(a.note);
  document.getElementById("rubout").innerHTML=
    '<h3>'+esc(L.name)+' — for '+esc(M.label.toLowerCase())+'</h3>'+
    '<p class="says">'+esc(L.says)+'</p>'+
    '<p class="per">'+esc(M.label)+' is taken as <b>'+M.lb+' lb</b> ('+esc(M.note)+'), at '+
      rate(L.tbsp_per_lb)+' of rub to the pound.</p>'+
    '<ul>'+rows.map(function(x){{var q=nice(x.q);
      return '<li class="'+(q?'':'zero')+'"><span class="q">'+esc(q||'')+'</span><span>'+esc(x.name)+'</span></li>';}}).join("")+'</ul>'+
    '<p class="per">About '+esc(nice(sum)||"nothing")+' of rub in all.</p>'+
    (L.when?'<h4>When</h4><ol>'+L.when.map(function(m){{return '<li>'+esc(m)+'</li>'}}).join("")+'</ol>':'')+
    '<div class="mk-actions"><button type="button" class="btn" id="rubcopy">Copy the rub</button>'+
    '<a class="btn ghost" href="../pit/whole-hog/index.html">Whole hog</a>'+
    '<a class="btn ghost" href="../pit/chopping-block/index.html">The block</a></div>'+
    '<p class="prov">'+prov+'</p>';
  document.getElementById("rubcopy").addEventListener("click",function(){{
    var txt=L.name+' — for '+M.label.toLowerCase()+' ('+M.lb+' lb)\\n\\n'+
      rows.filter(function(x){{return nice(x.q)}}).map(function(x){{return nice(x.q)+'  '+x.name}}).join('\\n')+
      '\\n\\nFrom Carolina Barbecue — {site_url}/make/';
    (navigator.clipboard?navigator.clipboard.writeText(txt):Promise.reject()).then(function(){{
      var b=document.getElementById("rubcopy"); b.textContent="Copied";
      setTimeout(function(){{b.textContent="Copy the rub"}},1600);}},function(){{}});
  }});
}}
document.querySelector("#panel-rub .dials").addEventListener("click",function(e){{
  var btn=e.target.closest("button[data-v]"); if(!btn)return;
  var g=btn.closest("[data-dial]"); pick[g.dataset.dial]=btn.dataset.v;
  [].forEach.call(g.querySelectorAll("button"),function(x){{x.setAttribute("aria-pressed",x===btn?"true":"false")}});
  render();
}});
render();
}})();

/* ------------------------------------------------------------------ the slaw */
(function(){{
var S={esc_js(slaw)}, pick={{kind:S.kinds[0].key, size:"head", sweet:"some", heat:"some"}};
function esc(s){{return String(s==null?"":s).replace(/[&<>"]/g,function(c){{return {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]}})}}
var FS=[[1,"1"],[0.75,"¾"],[0.6667,"⅔"],[0.5,"½"],[0.3333,"⅓"],[0.25,"¼"],[0.125,"⅛"]];
function frac(v){{var w=Math.floor(v+1e-9),r=v-w,b="",bd=9;
  for(var i=0;i<FS.length;i++){{var d=Math.abs(r-FS[i][0]); if(d<bd){{bd=d;b=FS[i][1];}}}}
  if(r<0.06)return String(w||"0");
  if(bd>0.08&&w===0)return (Math.round(v*100)/100).toString();
  if(b==="1"){{w+=1;b="";}}
  return (w?w+(b?" ":""):"")+b;}}
function amount(q,unit){{
  /* cups fall back to tablespoons and spoons to each other, so nothing reads as 0.06 cup */
  if(q<=0)return null;
  var plural=function(v,w){{return frac(v)+" "+w+(v>1.02?"s":"")}};
  if(unit==="cup"){{ if(q<0.25) return plural(q*16,"tablespoon"); return plural(q,"cup"); }}
  if(unit==="tbsp"){{ if(q<1) return plural(q*3,"teaspoon"); return plural(q,"tablespoon"); }}
  if(unit==="tsp"){{ if(q>=3) return plural(q/3,"tablespoon"); return plural(q,"teaspoon"); }}
  if(unit==="egg"){{ return frac(q); }}
  return plural(q,unit);
}}
function kind(){{return S.kinds.filter(function(x){{return x.key===pick.kind}})[0]}}
function render(){{
  var K=kind(), Z=S.sizes.filter(function(x){{return x.key===pick.size}})[0];
  var sw=S.sweets.filter(function(x){{return x.key===pick.sweet}})[0].mult;
  var ht=S.heats.filter(function(x){{return x.key===pick.heat}})[0].mult;
  var rows=K.per_cup.map(function(ing){{
    var q=ing.q*Z.cups;
    if(ing.dial==="sweet") q*=sw;
    if(ing.dial==="heat") q*=ht;
    return {{name:ing.name, txt:amount(q,ing.unit), opt:!!ing.optional}};
  }});
  var a=K.anchor, prov;
  if(a.kind==="recipe") prov='<b>'+esc(a.title)+'</b>, '+esc(a.publisher)+' '+(a.year||'')+' ('+esc(a.license)+'). '+esc(a.note);
  else prov='<b>These proportions are ours.</b> '+esc(a.note);
  document.getElementById("slawout").innerHTML=
    '<h3>'+esc(K.name)+' — '+esc(Z.label.toLowerCase())+'</h3>'+
    '<p class="says">'+esc(K.says)+' · '+esc(K.region)+'</p>'+
    '<p class="per">Shreds to about <b>'+Z.cups+' cups</b> ('+Z.lb+' lb).</p>'+
    '<ul><li><span class="q">'+Z.cups+' cups</span><span>cabbage, chopped fine</span></li>'+
    rows.map(function(x){{
      return '<li class="'+(x.txt?'':'zero')+'"><span class="q">'+esc(x.txt||'')+'</span><span>'+esc(x.name)+
        (x.opt?' <span class="mute">(optional)</span>':'')+'</span></li>';}}).join("")+'</ul>'+
    '<h4>How</h4><ol>'+K.steps.map(function(m){{return '<li>'+esc(m)+'</li>'}}).join("")+'</ol>'+
    (K.swap?'<p class="per"><b>Or:</b> '+esc(K.swap)+'</p>':'')+
    '<div class="mk-actions"><button type="button" class="btn" id="slawcopy">Copy the slaw</button>'+
    '<a class="btn ghost" href="../dish/'+esc(K.dish)+'/index.html">About this slaw</a></div>'+
    '<p class="prov">'+prov+(K.verbatim?' Steps quoted from the receipt.':' Steps are ours.')+'</p>';
  document.getElementById("slawcopy").addEventListener("click",function(){{
    var txt=K.name+' — '+Z.label.toLowerCase()+'\\n\\n'+Z.cups+' cups  cabbage, chopped fine\\n'+
      rows.filter(function(x){{return x.txt}}).map(function(x){{return x.txt+'  '+x.name}}).join('\\n')+
      '\\n\\n'+K.steps.join('\\n')+'\\n\\nFrom Carolina Barbecue — {site_url}/make/';
    (navigator.clipboard?navigator.clipboard.writeText(txt):Promise.reject()).then(function(){{
      var b=document.getElementById("slawcopy"); b.textContent="Copied";
      setTimeout(function(){{b.textContent="Copy the slaw"}},1600);}},function(){{}});
  }});
}}
document.querySelector("#panel-slaw .dials").addEventListener("click",function(e){{
  var btn=e.target.closest("button[data-v]"); if(!btn)return;
  var g=btn.closest("[data-dial]"); pick[g.dataset.dial]=btn.dataset.v;
  [].forEach.call(g.querySelectorAll("button"),function(x){{x.setAttribute("aria-pressed",x===btn?"true":"false")}});
  render();
}});
render();
}})();

/* ------------------------------------------------------------------ the tabs */
(function(){{
var tabs=document.querySelector(".tabs");
tabs.addEventListener("click",function(e){{
  var b=e.target.closest("button[data-panel]"); if(!b)return;
  [].forEach.call(tabs.querySelectorAll("button"),function(x){{
    var on=x===b; x.setAttribute("aria-selected",on?"true":"false");
    document.getElementById("panel-"+x.dataset.panel).hidden=!on;
  }});
}});
}})();
</script>
"""
    return page("Make it — Carolina Barbecue", body, 1,
                "Build a Carolina barbecue sauce by region and taste, or a rub from salt alone out to a full modern one. Every proportion says whether it came from a published recipe, a named pitmaster, or this project.",
                None, f"{site_url}/make/", extra_head=f"<style>{MAKE_CSS}{MAKE_TABS_CSS}{CHART_CSS}</style>", card="make",
                og_alt="Make a Carolina barbecue sauce or rub")
