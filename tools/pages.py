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

    chips = "".join(f'<button type="button" data-tag="{E(t["key"])}" aria-pressed="false">{E(t["icon"])} {E(t["label"])}</button>' for t in tags)
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
<p class="lede">Two questions, one page. What is good near me, and what is worth a tank of gas.</p>

<div class="finder">
  <div class="row">
    <button class="btn" id="locate" type="button">📍 Use my location</button>
    <input id="town" type="search" list="towns" placeholder="or type a town — Ayden, Lexington, Hemingway…" aria-label="Town">
    <datalist id="towns">{"".join(f'<option value="{E(t)}">' for t in sorted(townpts))}</datalist>
    <button class="btn ghost" id="go" type="button">Search</button>
  </div>
  <div class="chips" id="chips" role="group" aria-label="Filters">{chips}
    <button type="button" data-tag="__page" aria-pressed="false">📄 Has a page here</button></div>
  <p class="mute" style="font-size:.84rem;margin:.6rem 0 0" id="status">Your location is read by your own browser and stays there. Nothing is sent anywhere, nothing is stored.</p>
</div>

<div id="out"></div>

<h2>Worth the drive</h2>
<p class="mute">Places others have written down: a James Beard award, a spot on a trail, a wood-fire certification, an oral history recorded at the pit, a magazine's list. The count is how many different people said so, not how good we think it is. Every one is named on the place's own page.</p>
<div class="drive">{drive_cards}</div>

<h2 id="gaps">What we have not found</h2>
<p class="mute">{gaps}</p>
<h2>How to read the tags</h2>
<table>{"".join(f'<tr><th>{E(t["icon"])} {E(t["label"])}</th><td>{E(t["evidence"])}</td></tr>' for t in tagvocab.get("entries", []))}</table>
<p class="mute">A tag names its evidence on the place's page. No evidence, no tag — and a missing tag says nothing about a place, only about what we have read.</p>

<script>
(function(){{
var ROWS={esc_js(rows)}, TOWNS={esc_js(townpts)};
var TAGL={esc_js({e["key"]: (e["icon"] + " " + e["label"]) for e in tagvocab.get("entries", [])})};
var here=null, on={{}};
function esc(s){{return String(s==null?"":s).replace(/[&<>"]/g,function(c){{return {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]}})}}
function miles(a,b,c,d){{var R=3958.8,p=Math.PI/180,x=(c-a)*p,y=(d-b)*p,
  h=Math.sin(x/2)*Math.sin(x/2)+Math.cos(a*p)*Math.cos(c*p)*Math.sin(y/2)*Math.sin(y/2);
  return 2*R*Math.asin(Math.sqrt(h))}}
function keep(r){{
  for(var k in on){{ if(!on[k]) continue;
    if(k==="__page"){{ if(!r.u) return false; }}
    else if(r.t.indexOf(k)<0) return false; }}
  return true}}
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
      '<span class="wh">'+esc(where)+(r.h?' · '+esc(r.h):'')+(r.b?' — '+esc(r.b.slice(0,110))+'…':'')+'</span>'+
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
                f"{site_url}/near/", extra_head=f"<style>{NEAR_CSS}</style>")


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
    body = [f'<h1><span class="kind">Carolina Barbecue</span>What is actually in the sauce</h1>',
            '<p class="lede">Every bottle on this page was read off its own label: the ingredient list in order, the sugar on the Nutrition Facts panel, the town the maker works in. '
            'Nobody tasted anything. The argument about which sauce is correct is conducted elsewhere on this site, at length.</p>']
    if not rows:
        body.append('<p class="mute">The label survey has not been built yet — run the sauce harvest. The sauce pages themselves are up: '
                    + " · ".join(f'<a href="../sauce/{E(r["id"])}/index.html">{E(r["names"]["name"])}</a>' for r in sauce_recs) + "</p>")
        return page("What is in the sauce — Carolina Barbecue", "".join(body), 1, "The sauce spectrum.", None, f"{site_url}/sauce/",
                    extra_head=f"<style>{CHART_CSS}</style>")

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
                f"{site_url}/sauce/", extra_head=f"<style>{CHART_CSS}</style>")


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
    return page(f'{quiz["title"]} — Carolina Barbecue', body, 1, quiz["lede"], None, f"{site_url}/quiz/")


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
            '<p class="lede">Every argument on this site is, underneath, an argument about how much of the animal goes on the fire. '
            'Here is the animal, and here is what each style takes off it.</p>',
            '<div class="viz"><h3>The hog, as a pit crew divides it</h3>'
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
                None, f"{site_url}/pig/", extra_head=f"<style>{CHART_CSS}</style>")
