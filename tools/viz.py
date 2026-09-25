#!/usr/bin/env python3
"""viz.py — the maps, the infographics and the arithmetic.

Everything here is computed from the corpus at build time. Nothing is decorative: each
picture is the shortest way to say a thing the words would take a paragraph to say.

  distance_png     how near the nearest pit is, anywhere in the two states
  locator_svg      a place and its neighbours over a Natural Earth basemap, true scale
  where_svg        every place matching a style, a sauce, a person or a dish
  timeline_svg     when the pits that are still open opened
  ingredients_svg  what 142 Carolina recipes actually call for
  opendays_svg     which days a barbecue house is open
  kin_matrix_svg   which kinds of page point at which

Colour: one hue with position or lightness carrying the magnitude. The sequential ember
ramp below was checked with the dataviz skill's validator for monotone lightness and a
single hue (34 degrees); its light end recedes toward the surface, which is correct for a
continuous heatmap and is why every ramp here ships a numbered legend and a table twin.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import basemap
import roads

BOX = (-84.4, 31.9, -75.3, 36.7)
RAMP = ["#f3e2cf", "#e8bd93", "#dd9059", "#cf6a32", "#b5431f", "#8f3216", "#63200d"]
EMBER = "#b5431f"
E = __import__("html").escape


def hexrgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def project(lon, lat, w, h, box=BOX):
    return ((lon - box[0]) / (box[2] - box[0]) * w, (box[3] - lat) / (box[3] - box[1]) * h)


def frame(w=760, box=BOX):
    """Height that keeps the two states the right shape at this latitude."""
    k = math.cos(math.radians((box[1] + box[3]) / 2))
    return int(w * (box[3] - box[1]) / ((box[2] - box[0]) * k))


def _rings(geo, want_context=False):
    for st in geo["states"]:
        if st["context"] == want_context:
            for ring in st["rings"]:
                yield st, ring


def inside(rings, lon, lat) -> bool:
    for ring in rings:
        n, ins = len(ring), False
        for i in range(n):
            x1, y1 = ring[i]
            x2, y2 = ring[(i + 1) % n]
            if (y1 > lat) != (y2 > lat):
                if x1 + (lat - y1) * (x2 - x1) / (y2 - y1) > lon:
                    ins = not ins
        if ins:
            return True
    return False


# ------------------------------------------------------------------ the density map

def distance_png(geo: dict, places: list, out: Path, w=1100, step=0.035):
    """Every point in the two states, shaded by how far it is from the nearest pit.
    Drawn as pixels rather than 12,000 SVG rectangles, so the page stays light."""
    h = frame(w)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))   # transparent, so it sits on either theme
    d = ImageDraw.Draw(img)
    rings = [r for _, r in _rings(geo)]
    pts = [(p["lat"], p["lon"]) for p in places if p.get("lat") is not None]
    cell_w = w * step / (BOX[2] - BOX[0])
    cell_h = h * step / (BOX[3] - BOX[1])
    cuts = [3, 6, 10, 15, 22, 34]          # miles; the legend prints these
    colours = [hexrgb(c) for c in RAMP][::-1]   # near = dark
    far = []
    lat = BOX[1]
    while lat <= BOX[3]:
        lon = BOX[0]
        coslat = math.cos(math.radians(lat))
        while lon <= BOX[2]:
            if inside(rings, lon, lat):
                best = 1e9
                for plat, plon in pts:
                    dy = (plat - lat) * 69.0
                    dx = (plon - lon) * 69.0 * coslat
                    dd = dx * dx + dy * dy
                    if dd < best:
                        best = dd
                mi = math.sqrt(best)
                far.append((mi, lat, lon))
                band = next((i for i, c in enumerate(cuts) if mi <= c), len(cuts))
                x, y = project(lon, lat, w, h)
                d.rectangle([x, y - cell_h, x + cell_w, y], fill=colours[band])
            lon += step
        lat += step
    # state edges over the top, and the pits as small dark marks
    for st, ring in _rings(geo, want_context=True):
        d.line([project(x, y, w, h) for x, y in ring], fill=(160, 148, 130, 150), width=2)
    for st, ring in _rings(geo):
        pl = [project(x, y, w, h) for x, y in ring]
        d.line(pl + [pl[0]], fill=(150, 126, 96, 255), width=3)
    for plat, plon in pts:
        x, y = project(plon, plat, w, h)
        d.ellipse([x - 2.2, y - 2.2, x + 2.2, y + 2.2], fill=(24, 18, 14, 235))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    far.sort(reverse=True)
    return {"cuts": cuts, "ramp": RAMP[::-1], "worst": far[:6], "cells": len(far),
            "median": sorted(x[0] for x in far)[len(far) // 2] if far else 0}


# ------------------------------------------------------------------ small maps

LOC_KM = 250          # a locator's width, about 155 miles


def locator_frame(lat, lon, w=760):
    """The window a place page's map draws: the place at the centre, true scale."""
    return basemap.Frame(lat, lon, w, int(w * 0.62), LOC_KM)


def basemap_boxes() -> list:
    """Every box a map on this site draws, for tools/basemap.py to clip to."""
    from common import load_nodes
    return [locator_frame(r["geo"]["lat"], r["geo"]["lon"]).box
            for r in load_nodes() if r.get("type") == "place" and r.get("geo")]


def road_points() -> list:
    """Every point tools/roads.py measures between: the places with a page."""
    from common import load_nodes
    return [(r["geo"]["lat"], r["geo"]["lon"]) for r in load_nodes() if r.get("type") == "place" and r.get("geo")]


def nearest(here: tuple, others: list, n=5, look=10) -> list:
    """(miles, by_road, item) for the n nearest of others=[((lat, lon), item)], by road
    where roads.py has a usable route, else straight-line and marked so."""
    crow = sorted(((roads.crow_mi(here, ll), ll, it) for ll, it in others), key=lambda x: x[0])[:look]
    out = []
    for c, ll, it in crow:
        r = roads.road_mi(here, ll)
        out.append((round(c if r is None else r, 1), r is not None, it))
    out.sort(key=lambda x: x[0])
    return out[:n]


def locator_layout(lat, lon, others: list, w=760):
    """The frame and the pins it draws: (x, y, name, lat, lon), the place itself first."""
    fr = locator_frame(lat, lon, w)
    pins = [(*fr.xy(lon, lat), "", lat, lon)]
    for o in others:
        if o.get("lat") is not None and fr.inside(o["lon"], o["lat"], 4):
            pins.append((*fr.xy(o["lon"], o["lat"]), o["name"], o["lat"], o["lon"]))
    return fr, pins


def locator_svg(lat, lon, others: list, w=760, label=""):
    """One place at the centre and its neighbours, over Natural Earth land, water, state
    lines, highways and towns."""
    fr, pins = locator_layout(lat, lon, others, w)
    (cx, cy, *_), rest = pins[0], pins[1:]
    avoid = [(cx, cy, 20)] + [(x, y, 6) for x, y, *_ in rest]
    return "".join([
        f'<svg class="bm" viewBox="0 0 {fr.w} {fr.h}" style="border-radius:10px;overflow:hidden" role="img" '
        f'aria-label="Map of the country around {E(label or "this place")}, {LOC_KM / 1.609344:.0f} miles across">',
        basemap.draw(fr, basemap.load(), avoid),
        *(basemap.pin_svg(x, y, "", name) for x, y, name, *_ in rest),
        basemap.pin_svg(cx, cy, "var(--ember)", big=True), basemap.scale_bar(fr), "</svg>"])


def where_svg(geo: dict, pts: list, w=430, title=""):
    """The two states with a set of places lit — the answer to 'where is this style'."""
    h = frame(w)
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Where {E(title)} is found">']
    for st, ring in _rings(geo, want_context=True):
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in (project(a, b, w, h) for a, b in ring))
        out.append(f'<polyline points="{p}" fill="none" stroke="var(--line)" stroke-width="1"/>')
    for st, ring in _rings(geo):
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in (project(a, b, w, h) for a, b in ring))
        out.append(f'<polygon points="{p}" fill="var(--chip)" stroke="var(--mute)" stroke-width="1.4"/>')
    for p in pts:
        if p.get("lat") is None:
            continue
        x, y = project(p["lon"], p["lat"], w, h)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="var(--ember)" stroke="var(--panel)" stroke-width="1.5">'
                   f'<title>{E(p.get("name", ""))}</title></circle>')
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------ charts

def timeline_svg(rows: list, w=760):
    """One stem per pit, by the year it opened. Rows stack where years collide."""
    if not rows:
        return ""
    years = [y for y, _ in rows]
    lo, hi = min(years) // 10 * 10, (max(years) // 10 + 1) * 10
    h, base = 300, 232
    px = lambda y: 52 + (y - lo) / (hi - lo) * (w - 96)
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="When the pits opened, {lo} to {hi}">']
    for t in range(lo, hi + 1, 10):
        out.append(f'<line x1="{px(t):.1f}" y1="34" x2="{px(t):.1f}" y2="{base}" stroke="var(--line)" stroke-width="1"/>'
                   f'<text x="{px(t):.1f}" y="{base + 22}" text-anchor="middle" fill="var(--mute)" '
                   f'style="font:600 12px -apple-system,sans-serif">{t}</text>')
    seen: dict = {}
    for y, name in sorted(rows):
        k = round(px(y) / 9)
        lvl = seen.get(k, 0)
        seen[k] = lvl + 1
        yy = base - 14 - lvl * 15
        out.append(f'<line x1="{px(y):.1f}" y1="{base}" x2="{px(y):.1f}" y2="{yy:.1f}" stroke="var(--ember)" stroke-width="2" opacity=".55"/>'
                   f'<circle cx="{px(y):.1f}" cy="{yy:.1f}" r="5" fill="var(--ember)"><title>{E(name)} — {y}</title></circle>')
    out.append(f'<line x1="40" y1="{base}" x2="{w - 30}" y2="{base}" stroke="var(--ink)" stroke-width="2"/>')
    out.append("</svg>")
    return "".join(out)


def bars_svg(rows: list, w=760, unit="", rowh=30, left=190):
    """Horizontal bars, one hue, value at the end of each. The plainest honest form."""
    if not rows:
        return ""
    top = max(v for _, v in rows)
    h = len(rows) * rowh + 16
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{E(unit or "counts")}">']
    for i, (label, v) in enumerate(rows):
        y = 8 + i * rowh
        bw = (w - left - 74) * v / top
        out.append(f'<text x="{left - 12}" y="{y + rowh * 0.62:.0f}" text-anchor="end" fill="var(--ink)" '
                   f'style="font:600 14px -apple-system,sans-serif">{E(label)}</text>'
                   f'<rect x="{left}" y="{y + 4}" width="{max(bw, 2):.1f}" height="{rowh - 12}" rx="4" fill="var(--ember)"/>'
                   f'<text x="{left + bw + 10:.1f}" y="{y + rowh * 0.62:.0f}" fill="var(--mute)" '
                   f'style="font:600 13px -apple-system,sans-serif">{v}</text>')
    out.append("</svg>")
    return "".join(out)


DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
DAY_NAME = {"Mo": "Monday", "Tu": "Tuesday", "We": "Wednesday", "Th": "Thursday", "Fr": "Friday", "Sa": "Saturday", "Su": "Sunday"}


def open_days(hours_strings: list) -> dict:
    """Expand OpenStreetMap opening_hours into a count per weekday. Ranges like Mo-Sa are
    expanded; a day named with 'off' is removed again."""
    count = {d: 0 for d in DAYS}
    for s in hours_strings:
        days = set()
        for part in s.split(";"):
            part = part.strip()
            spec = re.findall(r"\b(Mo|Tu|We|Th|Fr|Sa|Su)\b(?:\s*-\s*(Mo|Tu|We|Th|Fr|Sa|Su))?", part)
            got = set()
            for a, b in spec:
                if b:
                    i, j = DAYS.index(a), DAYS.index(b)
                    got |= set(DAYS[i:j + 1] if i <= j else DAYS[i:] + DAYS[:j + 1])
                else:
                    got.add(a)
            if "off" in part.lower() or "closed" in part.lower():
                days -= got
            elif got:
                days |= got
            elif re.search(r"24/7", part):
                days |= set(DAYS)
        for d in days:
            count[d] += 1
    return count


def kin_matrix_svg(edges: list, types: list, labels: dict, w=700):
    """Which kind of page points at which. A square of cells, one hue, darker where more
    links run — the shape of the site's own argument."""
    n = len(types)
    cell = (w - 150) / n
    h = int(cell * n + 150)
    m: dict = {}
    for e in edges:
        m[(e["from_type"], e["to_type"])] = m.get((e["from_type"], e["to_type"]), 0) + 1
    top = max(m.values()) if m else 1
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="A matrix of which kinds of page link to which">']
    for i, a in enumerate(types):
        y = 96 + i * cell
        out.append(f'<text x="{140 - 10}" y="{y + cell * 0.62:.0f}" text-anchor="end" fill="var(--ink)" '
                   f'style="font:600 13px -apple-system,sans-serif">{E(labels.get(a, a))}</text>')
        for j, b in enumerate(types):
            x = 140 + j * cell
            v = m.get((a, b), 0)
            t = (v / top) ** 0.55
            col = RAMP[min(len(RAMP) - 1, int(t * (len(RAMP) - 1) + 0.0001))] if v else "var(--chip)"
            out.append(f'<rect x="{x + 1.5:.1f}" y="{y + 1.5:.1f}" width="{cell - 3:.1f}" height="{cell - 3:.1f}" rx="3" '
                       f'fill="{col}"><title>{E(labels.get(a, a))} → {E(labels.get(b, b))}: {v}</title></rect>')
            if v and t > 0.45:
                out.append(f'<text x="{x + cell / 2:.1f}" y="{y + cell * 0.62:.0f}" text-anchor="middle" fill="#fff" '
                           f'style="font:600 12px -apple-system,sans-serif">{v}</text>')
    for j, b in enumerate(types):
        x = 140 + j * cell + cell / 2
        out.append(f'<text transform="translate({x:.1f},88) rotate(-52)" fill="var(--ink)" '
                   f'style="font:600 13px -apple-system,sans-serif">{E(labels.get(b, b))}</text>')
    out.append(f'<text x="140" y="{h - 16}" fill="var(--mute)" style="font:400 12.5px -apple-system,sans-serif">'
               f'row points at column · darkest cell = {top} links</text>')
    out.append("</svg>")
    return "".join(out)


def ramp_legend(cuts: list, ramp: list, unit: str) -> str:
    """A numbered key. The ramp's pale end recedes into the page, so the numbers do the work."""
    n = len(ramp)
    cells = []
    for i, c in enumerate(ramp):
        lab = ("under " + str(cuts[0])) if i == 0 else (f"{cuts[i-1]}–{cuts[i]}" if i < len(cuts) else f"over {cuts[-1]}")
        cells.append(f'<span style="display:inline-flex;flex-direction:column;align-items:center;gap:.2rem">'
                     f'<i style="width:3.1rem;height:.85rem;background:{c};border-radius:2px;display:block"></i>'
                     f'<small style="font-size:.72rem;color:var(--mute)">{E(lab)}</small></span>')
    return (f'<div style="display:flex;gap:.35rem;flex-wrap:wrap;align-items:flex-end;margin:.6rem 0 .2rem">'
            + "".join(cells) + f'<span style="font-size:.8rem;color:var(--mute);margin-left:.5rem">{E(unit)}</span></div>')


# ------------------------------------------------------------------ the week

DAY_ORDER = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
DAY_ONE = {"Mo": "M", "Tu": "T", "We": "W", "Th": "T", "Fr": "F", "Sa": "S", "Su": "S"}


def day_strip(days: dict, w=176, h=26, title=True) -> str:
    """Seven boxes, Monday to Sunday. Filled means open, hollow means closed, dashed means
    nobody has told us. Sunday is drawn apart because Sunday is the question people ask."""
    if not days:
        return ""
    cell = (w - 10) / 7
    out = [f'<svg class="daystrip" viewBox="0 0 {w} {h}" role="img" aria-label="'
           + E(", ".join(f"{DAY_NAME[d]} {days.get(d, 'unknown')}" for d in DAY_ORDER)) + '">']
    for i, d in enumerate(DAY_ORDER):
        st = days.get(d, "unknown")
        x = i * cell + (10 if d == "Su" else 0)
        fill = {"open": "var(--ember)", "closed": "none", "unknown": "none"}[st]
        stroke = {"open": "var(--ember)", "closed": "var(--mute)", "unknown": "var(--line)"}[st]
        dash = ' stroke-dasharray="2.5 2.5"' if st == "unknown" else ""
        col = {"open": "#fff", "closed": "var(--mute)", "unknown": "var(--line)"}[st]
        out.append(f'<rect x="{x + 1.5:.1f}" y="3" width="{cell - 3:.1f}" height="{h - 8}" rx="4" fill="{fill}" '
                   f'stroke="{stroke}" stroke-width="1.6"{dash}/>'
                   f'<text x="{x + cell / 2:.1f}" y="{h / 2 + 4.5:.0f}" text-anchor="middle" fill="{col}" '
                   f'style="font:700 11px -apple-system,sans-serif">{DAY_ONE[d]}</text>')
        if title:
            out.append(f'<title>{E(DAY_NAME[d])}: {E(st)}</title>')
    out.append("</svg>")
    return "".join(out)


def day_key() -> str:
    return ('<span class="daykey"><i class="on"></i> open <i class="off"></i> closed '
            '<i class="unk"></i> not published</span>')


DAY_CSS = """
.daystrip{height:26px;width:176px;display:block}
.daykey{font-size:.76rem;color:var(--mute);display:inline-flex;align-items:center;gap:.3rem;font-family:var(--ui,sans-serif)}
.daykey i{width:.7rem;height:.9rem;border-radius:3px;display:inline-block;margin-left:.5rem}
.daykey i.on{background:var(--ember);border:1.6px solid var(--ember)}
.daykey i.off{border:1.6px solid var(--mute)}
.daykey i.unk{border:1.6px dashed var(--line)}
.sunday-yes{color:var(--ember);font-weight:700}
.sunday-no{color:var(--mute)}
"""
