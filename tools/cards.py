#!/usr/bin/env python3
"""cards.py — the picture that shows when a page is shared.

One 1200x630 card per record and per standing page, drawn with Pillow. Masters are
committed to `cards/` and copied into the site by site.py, which points og:image at a
card ONLY when its file exists — an og:image that 404s unfurls worse than none at all.

Each card says what kind of thing the page is, names it, and then shows the one fact
that makes it worth a click:

    place   the town, the tags it has earned, and a dot on a map of the two states
    style   the hog with this style's cuts lit
    sauce   where its sugar sits on the 0-13 g scale, against the other bases
    dish    the course, and the count of free recipes on the page
    person  the role and the place they are known for
    term    the root of the word
    art     the picture itself, bled to the edge
    story   the lede

A record with a photograph gets that photograph as a bleed on the right, which is the
strongest card this site can make, and the drawn panel otherwise.

    python3 tools/cards.py              # every card that is missing or out of date
    python3 tools/cards.py --all        # redraw everything
    python3 tools/cards.py place/skylight-inn index near
"""
from __future__ import annotations

import json
import math
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BUILD, DATA, GEO, IMAGES, ROOT, jload  # noqa: E402

CARDS = ROOT / "cards"
W, H = 1200, 630
PAD = 64

# The site's own ink-mode palette: a card is read at thumbnail size in a feed, so it is
# built on the dark ground where the ember reads hottest.
INK = (23, 20, 18)
INK_2 = (31, 27, 24)
CREAM = (241, 235, 224)
MUTE = (168, 158, 143)
EMBER = (200, 74, 35)
EMBER_HI = (232, 103, 60)
GOLD = (224, 182, 74)
LINE = (58, 50, 43)
CHIP_BG = (42, 36, 31)

SERIF = "/System/Library/Fonts/Supplemental/Iowan Old Style.ttc"
SERIF_FALLBACK = "/System/Library/Fonts/Supplemental/Georgia.ttf"
SANS = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
SANS_R = "/System/Library/Fonts/Supplemental/Arial.ttf"

TYPE_LABEL = {"style": "A STYLE", "sauce": "A SAUCE", "dish": "ON THE PLATE", "pit": "THE PIT", "place": "A PLACE",
              "person": "A PERSON", "org": "AN ORGANIZATION", "event": "AN EVENT", "term": "A WORD",
              "art": "PIG ART", "story": "A STORY"}
SITE_MARK = "CAROLINA BARBECUE"


def font(path: str, size: int, index: int = 0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except OSError:
        return ImageFont.truetype(SERIF_FALLBACK, size)


def F_TITLE(sz):
    return font(SERIF, sz, index=1)      # Iowan Old Style Bold


def F_BODY(sz):
    return font(SERIF, sz, index=0)


def F_SANS(sz):
    return font(SANS, sz)


def F_SANS_R(sz):
    return font(SANS_R, sz)


# ------------------------------------------------------------------ helpers

def fit_text(d: ImageDraw.ImageDraw, text: str, fnt_for, max_w: int, max_lines: int, start: int, floor: int):
    """Largest size at which `text` wraps into max_lines of max_w. Returns (font, lines)."""
    size = start
    while size >= floor:
        f = fnt_for(size)
        avg = d.textlength("n", font=f) or 1
        cols = max(8, int(max_w / avg * 1.05))
        lines = textwrap.wrap(text, width=cols) or [text]
        if len(lines) <= max_lines and all(d.textlength(l, font=f) <= max_w for l in lines):
            return f, lines
        size -= 3
    # nothing fits: take what does and end it honestly
    f = fnt_for(floor)
    avg = d.textlength("n", font=f) or 1
    cols = max(8, int(max_w / avg * 1.05))
    lines = textwrap.wrap(text, width=cols) or [text]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and d.textlength(last + "\u2026", font=f) > max_w:
            last = last[:-1]
        lines[-1] = last.rstrip(" ,;:\u2014-") + "\u2026"
    return f, lines


def draw_lines(d, x, y, lines, fnt, fill, leading=1.16):
    lh = int(fnt.size * leading)
    for i, line in enumerate(lines):
        d.text((x, y + i * lh), line, font=fnt, fill=fill)
    return y + len(lines) * lh


def chip(d, x, y, text, fnt, fg=CREAM, bg=CHIP_BG, border=LINE):
    tw = d.textlength(text, font=fnt)
    h = int(fnt.size * 1.95)
    d.rounded_rectangle([x, y, x + tw + 30, y + h], radius=h // 2, fill=bg, outline=border, width=2)
    d.text((x + 15, y + (h - fnt.size) / 2 - fnt.size * 0.08), text, font=fnt, fill=fg)
    return x + tw + 30 + 10


def base_card(photo: Image.Image | None = None):
    """The ground: ink, a warm glow behind the text column, an ember rule down the left,
    and the photograph bled into the right third under a gradient so type stays legible."""
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    glow = Image.new("RGB", (W, H), INK)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-260, 240, 520, 1040], fill=(46, 32, 25))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(120)), 0.9)
    d = ImageDraw.Draw(img)
    if photo is not None:
        pw = 520
        ph = photo.copy()
        ratio = max(pw / ph.width, H / ph.height)
        ph = ph.resize((max(1, int(ph.width * ratio)), max(1, int(ph.height * ratio))), Image.LANCZOS)
        left = max(0, (ph.width - pw) // 2)
        top = max(0, (ph.height - H) // 2)
        ph = ph.crop((left, top, left + pw, top + H))
        img.paste(ph, (W - pw, 0))
        # a horizontal fade so the photograph dissolves into the ground rather than butting it
        fade = Image.new("L", (240, 1), 0)
        for x in range(240):
            fade.putpixel((x, 0), int(255 * (1 - x / 240) ** 1.2))
        mask = fade.resize((240, H))
        img.paste(Image.new("RGB", (240, H), INK), (W - pw, 0), mask)
        d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 10, H], fill=EMBER)
    return img, d


def footer(d, right_note: str = ""):
    f = F_SANS(21)
    d.text((PAD, H - 62), SITE_MARK, font=f, fill=GOLD)
    if right_note:
        fr = F_SANS_R(21)
        tw = d.textlength(right_note, font=fr)
        d.text((W - PAD - tw, H - 62), right_note, font=fr, fill=MUTE)


def eyebrow(d, text: str, y=PAD):
    f = F_SANS(23)
    t = " ".join(text.upper())
    d.text((PAD, y), t, font=f, fill=EMBER_HI)
    return y + 44


def _open(im: dict):
    p = IMAGES / im["file"]
    if not p.exists():
        return None
    try:
        return Image.open(p).convert("RGB")
    except Exception:  # noqa: BLE001
        return None


def vivid(ph: Image.Image) -> Image.Image:
    """Warm the picture toward the site's ember and lift it, so a card glows in a feed
    instead of sitting grey next to it. Never so far that a red sauce reads orange."""
    from PIL import ImageEnhance
    ph = ImageEnhance.Color(ph).enhance(1.22)
    ph = ImageEnhance.Contrast(ph).enhance(1.10)
    ph = ImageEnhance.Brightness(ph).enhance(1.04)
    warm = Image.new("RGB", ph.size, (214, 92, 40))
    return Image.blend(ph, warm, 0.06)


def load_photo(rec: dict, ctx: dict | None = None):
    """The record's own picture if it has one; otherwise the best picture among the pages
    it points at, then its style's, then its type's. Returns (image, credit, borrowed_from)."""
    own = rec.get("primary_image") or (rec.get("images") or [None])[0]
    if own:
        ph = _open(own)
        if ph:
            return ph, f'{own.get("author", "")} · {own.get("license", "")}'.strip(" ·"), None
    if not ctx:
        return None, "", None
    by_id = ctx.get("by_id") or {}
    order = [k["to"] for k in (rec.get("kin_out") or [])] + [k["from"] for k in (rec.get("kin_in") or [])]
    # a style or a place makes a better stand-in than a word does
    rank = {"art": 0, "place": 1, "style": 2, "pit": 3, "dish": 4, "event": 5, "sauce": 6, "person": 7}
    cands = [by_id[i] for i in order if i in by_id and by_id[i].get("images")]
    cands.sort(key=lambda r: rank.get(r["type"], 9))
    seed = sum(ord(ch) for ch in rec["id"])
    for c in cands:
        imgs = c.get("images") or []
        if not imgs:
            continue
        im = imgs[seed % len(imgs)]
        ph = _open(im)
        if ph:
            return ph, f'{im.get("author", "")} · {im.get("license", "")}'.strip(" ·"), c["names"]["name"]
    for sid in ((rec.get("facets") or {}).get("styles") or []):
        st = by_id.get(sid)
        if st and st.get("images"):
            im = st["images"][seed % len(st["images"])]
            ph = _open(im)
            if ph:
                return ph, f'{im.get("author", "")} · {im.get("license", "")}'.strip(" ·"), st["names"]["name"]
    fb = ctx.get("fallback_by_type", {}).get(rec["type"]) or ctx.get("fallback")
    if fb:
        ph = _open(fb[0])
        if ph:
            return ph, f'{fb[0].get("author", "")} · {fb[0].get("license", "")}'.strip(" ·"), fb[1]
    return None, "", None


# ------------------------------------------------------------------ the little map

_GEO = None


def states():
    global _GEO
    if _GEO is None:
        _GEO = jload(GEO / "states.json")
    return _GEO


def mini_map(size=(430, 300), dot=None, dots=None, dot_r=9):
    """The two states, with one pit lit or many. Drawn at 3x and downsampled, because a
    1px state border at card size looks like a scan artefact otherwise."""
    S = 3
    w, h = size[0] * S, size[1] * S
    box = (-84.4, 31.9, -75.3, 36.7)
    img = Image.new("RGB", (w, h), INK)
    d = ImageDraw.Draw(img)
    k = math.cos(math.radians(34.3))

    def proj(lon, lat):
        x = (lon - box[0]) / (box[2] - box[0]) * w
        y = (box[3] - lat) / (box[3] - box[1]) * h * ((box[2] - box[0]) * k / (box[3] - box[1])) / (w / h) * (w / h)
        y = (box[3] - lat) / (box[3] - box[1]) * h
        return x, y

    for st in states()["states"]:
        for ring in st["rings"]:
            pts = [proj(x, y) for x, y in ring]
            if st["context"]:
                d.line(pts + [pts[0]], fill=(46, 40, 34), width=2 * S)
            else:
                d.polygon(pts, fill=(44, 38, 32), outline=(120, 104, 84))
                d.line(pts + [pts[0]], fill=(150, 130, 104), width=2 * S)
    for p in (dots or []):
        x, y = proj(p[1], p[0])
        d.ellipse([x - 3 * S, y - 3 * S, x + 3 * S, y + 3 * S], fill=(176, 84, 48))
    if dot:
        x, y = proj(dot[1], dot[0])
        r = dot_r * S
        d.ellipse([x - r * 2.4, y - r * 2.4, x + r * 2.4, y + r * 2.4], fill=(70, 38, 26))
        d.ellipse([x - r, y - r, x + r, y + r], fill=EMBER_HI, outline=CREAM, width=2 * S)
    return img.resize(size, Image.LANCZOS)


# ------------------------------------------------------------------ the hog

def mini_hog(lit: set, size=(430, 250)):
    """The same animal the /pig/ page draws, at card scale, with this style's cuts lit."""
    S = 3
    w, h = size[0] * S, size[1] * S
    img = Image.new("RGB", (w, h), INK)
    d = ImageDraw.Draw(img)
    sx, sy = w / 420, h / 250

    def R(x, y, x2, y2):
        return [x * sx, y * sy, x2 * sx, y2 * sy]

    body = Image.new("L", (w, h), 0)
    bd = ImageDraw.Draw(body)
    bd.ellipse(R(116, 66, 340, 178), fill=255)
    bd.ellipse(R(66, 86, 170, 170), fill=255)
    bd.polygon([(40 * sx, 122 * sy), (96 * sx, 104 * sy), (96 * sx, 142 * sy)], fill=255)
    bd.polygon([(104 * sx, 94 * sy), (96 * sx, 66 * sy), (132 * sx, 84 * sy)], fill=255)
    for lx in (132, 160, 276, 304):
        bd.rounded_rectangle(R(lx, 150, lx + 19, 214), radius=7 * S, fill=255)

    fill = Image.new("RGB", (w, h), (52, 45, 38))
    fd = ImageDraw.Draw(fill)
    regions = {"jowl": (36, 66, 120, 186), "shoulder": (120, 66, 182, 194),
               "loin": (182, 66, 260, 110), "belly": (182, 110, 260, 194), "ham": (260, 66, 342, 194)}
    for key, (x, y, x2, y2) in regions.items():
        if key in lit:
            fd.rectangle(R(x, y, x2, y2), fill=EMBER)
    img.paste(fill, (0, 0), body)
    edge = body.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(5))
    img.paste(Image.new("RGB", (w, h), CREAM), (0, 0), edge)
    d.ellipse(R(100, 110, 110, 120), fill=CREAM)
    return img.resize(size, Image.LANCZOS)


# ------------------------------------------------------------------ the sugar scale

def sugar_scale(img: Image.Image, x: int, y: int, value, others: list, w=470):
    """Where this bottle sits between nothing and a spoonful of sugar. Drawn straight onto
    the card through an alpha layer, so the photograph stays visible behind it."""
    S = 3
    h = 92
    layer = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, x1, cy = 8 * S, (w - 8) * S, 34 * S
    d.rounded_rectangle([x0, cy - 5 * S, x1, cy + 5 * S], radius=5 * S, fill=(255, 255, 255, 46))
    for o in others:
        ox = x0 + (x1 - x0) * min(o / 12.6, 1)
        d.ellipse([ox - 4 * S, cy - 4 * S, ox + 4 * S, cy + 4 * S], fill=(255, 255, 255, 120))
    if value is not None:
        vx = x0 + (x1 - x0) * min(value / 12.6, 1)
        d.ellipse([vx - 14 * S, cy - 14 * S, vx + 14 * S, cy + 14 * S], fill=EMBER + (110,))
        d.ellipse([vx - 9 * S, cy - 9 * S, vx + 9 * S, cy + 9 * S], fill=EMBER_HI + (255,), outline=CREAM + (255,), width=2 * S)
    f = font(SANS, 17 * S)
    d.text((x0, cy + 18 * S), "0 g", font=f, fill=MUTE + (255,))
    t = "12.6 g \u2014 a spoonful of sugar"
    d.text((x1 - d.textlength(t, font=f), cy + 18 * S), t, font=f, fill=MUTE + (255,))
    img.paste(layer.resize((w, h), Image.LANCZOS), (x, y), layer.resize((w, h), Image.LANCZOS))


# ------------------------------------------------------------------ record cards

def photo_ground(ph: Image.Image, strength=1.0):
    """The picture, warmed and bled edge to edge, with a scrim that is opaque under the
    text column and clear on the right. This is the card; the type sits on top of it."""
    img = Image.new("RGB", (W, H), INK)
    ph = vivid(ph)
    ratio = max(W / ph.width, H / ph.height)
    ph = ph.resize((max(1, int(ph.width * ratio)), max(1, int(ph.height * ratio))), Image.LANCZOS)
    img.paste(ph, ((W - ph.width) // 2, (H - ph.height) // 2))
    # horizontal scrim: solid ink at the left edge, gone by 70% across
    grad = Image.new("L", (W, 1), 0)
    for x in range(W):
        t = x / W
        v = 252 if t < 0.26 else int(252 * max(0.0, (0.76 - t) / 0.5) ** 0.85)
        grad.putpixel((x, 0), int(v * strength))
    img.paste(Image.new("RGB", (W, H), INK), (0, 0), grad.resize((W, H)))
    # a bottom band so the footer line always has ground under it
    bot = Image.new("L", (1, H), 0)
    for y in range(H):
        bot.putpixel((0, y), int(210 * max(0.0, (y - H * 0.80) / (H * 0.20)) ** 1.1))
    img.paste(Image.new("RGB", (W, H), INK), (0, 0), bot.resize((W, H)))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 10, H], fill=EMBER)
    return img, d


FOOT_Y = H - 62          # the footer baseline
FACT_Y = H - 168         # chips, dots and panels hang from here, never from the flow


def record_card(rec: dict, ctx: dict) -> Image.Image:
    t = rec["type"]
    photo, credit, borrowed = load_photo(rec, ctx)
    art = t == "art" and photo is not None and not borrowed

    if art:
        img = Image.new("RGB", (W, H), INK)
        ph = vivid(photo)
        ratio = max(W / ph.width, H / ph.height)
        ph = ph.resize((int(ph.width * ratio), int(ph.height * ratio)), Image.LANCZOS)
        img.paste(ph, ((W - ph.width) // 2, (H - ph.height) // 2))
        scrim = Image.new("L", (1, H), 0)
        for yy in range(H):
            scrim.putpixel((0, yy), int(248 * max(0.0, (yy - H * 0.32) / (H * 0.68)) ** 1.05))
        img.paste(Image.new("RGB", (W, H), INK), (0, 0), scrim.resize((W, H)))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 10, H], fill=EMBER)
        col_w, y, title_lines = W - PAD * 2, eyebrow(d, TYPE_LABEL.get(t, t), y=int(H * 0.50)), 2
    elif photo is not None:
        img, d = photo_ground(photo)
        col_w, y, title_lines = int(W * 0.55), eyebrow(d, TYPE_LABEL.get(t, t)), 2
    else:
        img, d = base_card(None)
        col_w, y, title_lines = W - PAD * 2 - 470, eyebrow(d, TYPE_LABEL.get(t, t)), 3

    f, lines = fit_text(d, rec["names"]["name"], F_TITLE, col_w, title_lines, 78, 32)
    y = draw_lines(d, PAD, y + 4, lines, f, CREAM, 1.07) + 10

    a = rec.get("address") or {}
    fc = rec.get("facets") or {}
    sub = ""
    if t == "place":
        sub = ", ".join(x for x in (a.get("city"), a.get("state")) if x)
    elif t == "person":
        sub = ", ".join((fc.get("role") or [])[:2]).replace("-", " ")
    elif t in ("style", "sauce"):
        sub = (rec.get("region_terms") or [{}])[0].get("name", "")
    elif t == "term":
        sub = "a word, with its root"
    elif t == "dish":
        sub = {"main": "on the plate", "side": "a side", "bread": "bread", "sweet": "a sweet",
               "drink": "a drink", "condiment": "a condiment"}.get(fc.get("course", ""), "")
    elif t == "event":
        sub = str(fc.get("when", "") or "")
    if sub:
        d.text((PAD, y), sub[:60], font=F_SANS(25), fill=GOLD)
        y += 44

    # the blurb takes whatever room is left above the fact line, and no more
    room = FACT_Y - 16 - y
    if room > 40:
        maxl = max(1, min(3, room // 39))
        fb, bl = fit_text(d, rec.get("blurb") or rec["text"]["what"], F_BODY, col_w, maxl, 29, 20)
        draw_lines(d, PAD, y, bl, fb, (208, 199, 185), 1.3)

    # the one fact, anchored
    fy = FACT_Y
    if t == "place":
        x = PAD
        fchip = F_SANS(20)
        for tg in (rec.get("tag_facts") or [])[:4]:
            lab = tg.get("label", "")
            if x + d.textlength(lab, font=fchip) + 42 > PAD + col_w:
                break
            x = chip(d, x, fy, lab, fchip, fg=CREAM, border=GOLD if tg.get("group") == "ownership" else LINE)
        n = rec.get("acclaim") or 0
        if n:
            d.text((PAD, fy + 54), "\u25cf" * min(n, 5) + f"  written down by {n} others", font=F_SANS(20), fill=GOLD)
        if rec.get("geo") and photo is None:
            img.paste(mini_map(dot=(rec["geo"]["lat"], rec["geo"]["lon"]), dots=ctx.get("dots")), (W - PAD - 430, 210))
    elif t == "style":
        cuts = ctx.get("style_cuts", {}).get(rec["id"], set())
        if photo is None:
            img.paste(mini_hog(cuts), (W - PAD - 430, 290))
        elif cuts:
            chip(d, PAD, fy + 18, {5: "the whole hog", 1: "the shoulder only"}.get(len(cuts), ", ".join(sorted(cuts))), F_SANS(21), fg=CREAM, border=GOLD)
    elif t == "sauce":
        pf = rec.get("profile") or {}
        v = pf.get("sugar_g_per_tbsp")
        if v is not None:
            d.text((PAD, fy - 6), f"{v:g} g of sugar in a tablespoon", font=F_SANS(23), fill=CREAM)
            sugar_scale(img, PAD, fy + 26, v, ctx.get("sugars", []), min(470, col_w))
        elif pf.get("ingredients"):
            chip(d, PAD, fy + 18, "first on the label: " + pf["ingredients"][0][:32], F_SANS(21), fg=CREAM, border=GOLD)
    elif t == "dish" and rec.get("recipes"):
        n = len(rec["recipes"])
        free = sum(1 for r in rec["recipes"] if "ingredients-only" not in (r.get("license") or "").lower())
        chip(d, PAD, fy + 18, f"{n} recipe{'s' if n != 1 else ''}, {free} you may copy in full", F_SANS(21), fg=CREAM, border=GOLD)
    elif t == "term":
        root = (rec.get("etymology") or {}).get("root", "")
        if root:
            fr, rl = fit_text(d, root, F_BODY, col_w, 2, 25, 18)
            draw_lines(d, PAD, fy, rl, fr, CREAM, 1.24)
    elif t == "person":
        pl = [k["name"] for k in (rec.get("kin_out") or []) if k.get("type") == "place"][:2]
        if pl:
            chip(d, PAD, fy + 18, " \u00b7 ".join(pl)[:46], F_SANS(21), fg=CREAM, border=LINE)

    note = credit if (photo is not None and not borrowed) else (f"picture: {borrowed}" if borrowed else ctx.get("host", ""))
    footer(d, note[:74])
    return img


# ------------------------------------------------------------------ page cards

def page_card(title: str, lede: str, eyebrow_text: str, ctx: dict, panel=None, stats=None, photo_id=None) -> Image.Image:
    ph = None
    if photo_id:
        rec = (ctx.get("by_id") or {}).get(photo_id)
        if rec and rec.get("images"):
            ph = _open(rec["images"][0])
    if ph is not None:
        img, d = photo_ground(ph)
        panel = None
    else:
        img, d = base_card()
    y = eyebrow(d, eyebrow_text)
    f, lines = fit_text(d, title, F_TITLE, W - PAD * 2 - (470 if panel is not None else 0), 2, 86, 40)
    y = draw_lines(d, PAD, y + 4, lines, f, CREAM, 1.06) + 16
    fb, bl = fit_text(d, lede, F_BODY, W - PAD * 2 - (470 if panel is not None else 0), 3, 31, 22)
    y = draw_lines(d, PAD, y, bl, fb, MUTE, 1.3) + 18
    if stats:
        x, y = PAD, max(y, FACT_Y - 30)
        for n, lab in stats:
            fn, fl = F_TITLE(44), F_SANS(19)
            d.text((x, y), str(n), font=fn, fill=EMBER_HI)
            d.text((x, y + 52), lab.upper(), font=fl, fill=MUTE)
            x += max(d.textlength(str(n), font=fn), d.textlength(lab.upper(), font=fl)) + 52
    if panel is not None:
        img.paste(panel, (W - PAD - panel.width, (H - panel.height) // 2))
    footer(d, ctx.get("host", ""))
    return img


# ------------------------------------------------------------------ main

def main(argv: list[str]) -> int:
    api = BUILD / "api"
    if not (api / "nodes.json").exists():
        print("run tools/build.py first")
        return 1
    recs = jload(api / "nodes.json")["nodes"]
    places = jload(api / "places.json")
    cov = jload(api / "coverage.json")
    sauces = jload(DATA / "harvest" / "sauces.json") if (DATA / "harvest" / "sauces.json").exists() else {"sauces": []}
    CARDS.mkdir(exist_ok=True)

    style_cuts = {"eastern-nc": {"jowl", "shoulder", "loin", "belly", "ham"}, "sc-pee-dee": {"jowl", "shoulder", "loin", "belly", "ham"},
                  "lexington": {"shoulder"}, "sc-mustard": {"shoulder", "ham"}, "sc-heavy-tomato": {"shoulder", "loin"},
                  "sc-light-tomato": {"shoulder", "ham", "loin"}}
    ctx = {"by_id": {r["id"]: r for r in recs},
           "dots": [(p["lat"], p["lon"]) for p in places["places"] if p.get("lat") is not None],
           "style_cuts": style_cuts,
           "sugars": [s["sugar_g_per_tbsp"] for s in sauces.get("sauces", []) if s.get("sugar_g_per_tbsp") is not None],
           "host": "nanobotco.github.io/carolina-barbecue"}

    want = set(argv)
    redraw_all = "--all" in want
    want.discard("--all")
    made = 0

    def save(img: Image.Image, name: str):
        """JPEG, because these are photographs: the same cards as PNG came to 164 MB.
        Every unfurler takes JPEG, and 1200x630 at q86 is about 120 KB."""
        nonlocal made
        p = CARDS / (name + ".jpg")
        p.parent.mkdir(parents=True, exist_ok=True)
        img.save(p, "JPEG", quality=86, optimize=True, progressive=True, subsampling=1)
        made += 1

    # standing pages
    allmap = mini_map(size=(470, 330), dots=ctx["dots"])
    pages = {
        "index": ("Carolina Barbecue", "The pits, the plates and the words of North and South Carolina — whole hog in the east, shoulders and a red dip in the Piedmont, mustard in the Midlands.", "a directory of a living tradition", allmap,
                  [(cov["records"]["place"] + places["harvested"], "places"), (sum(cov["records"].values()), "records"), (cov["recipes"], "recipes"), (cov["images"]["count"], "pictures")], "whole-hog"),
        "near": ("Find the Q", "Every pit in both states sorted from where you are, and the ones worth a tank of gas. Filter by cooks over wood, whole hog, Black-owned, woman-owned, LGBTQ+ welcoming.", "find the q", allmap, None, None),
        "sauce": ("What is actually in the sauce", "Sixty-eight bottles read off their own labels: sugar by the tablespoon, what comes first on the list, and where the makers are.", "measured, not tasted", None,
                  [(len(sauces.get("sauces", [])), "bottles read"), ("5.3 g", "mustard, sugar per tbsp"), ("0.5 g", "vinegar and pepper")], "vinegar-pepper-sauce"),
        "pig": ("Which part of the pig", "Every argument here is, underneath, an argument about how much of the animal goes on the fire.", "the animal", mini_hog({"jowl", "shoulder", "loin", "belly", "ham"}, (470, 280)), None, None),
        "make": ("Make a sauce", "Pick a region and how you like it. Vinegar and pepper, Lexington dip, light tomato, mustard, heavy tomato or pepper vinegar — with the sugar worked out and every proportion's source named.", "build one", None,
                 [("6", "regions"), ("2", "period recipes"), ("68", "bottles to measure against")], "vinegar-pepper-sauce"),
        "quiz": ("Which side are you on?", "Six questions about sauce, slaw and how you order. At the end, a style claims you.", "a quiz", None, None, "lexington"),
        "art": ("Pigs that serve themselves", "The sign genre, the mascots, the 1830s election prints — every picture free to use, its licence beside it.", "pig art", None, None, "cannibal-pig-sign"),
        "places": ("Pits and places", "Every barbecue place in North and South Carolina we know of, on one map, with what each one has earned.", "the map", allmap, None, None),
        "words": ("The words, with their roots", "Barbecue from the Taíno barbacoa. Dip, slaw, hash, light bread, outside brown, Down East.", "vocabulary", None, None, "barbecue"),
        "coverage": ("What this covers, and what it does not", "The scope as an object: where every row comes from, how many places carry each tag, and what has not been read yet.", "coverage", None, None, None),
        "search": ("Search the directory", "Spelled however you spell it: barbeque, bar-b-q, 'cue. Near spellings are found and said to be near.", "search", None, None, None),
        "sources": ("Five hundred and ninety sources", "Every book, article, oral history, dataset and page the records cite, by id.", "sources", None, None, None),
        "stories": ("The stories", "The east-west war, how to order, and where all of this came from.", "long reads", None, None, "political-barbecue"),
    }
    for name, (title, lede, eb, panel, stats, photo_id) in pages.items():
        if want and name not in want:
            continue
        p = CARDS / (name + ".jpg")
        if not redraw_all and not want and p.exists():
            continue
        save(page_card(title, lede, eb, ctx, panel, stats, photo_id), name)

    # records
    for r in recs:
        key = f'{r["type"]}__{r["id"]}'
        sel = f'{r["type"]}/{r["id"]}'
        if want and sel not in want and key not in want:
            continue
        p = CARDS / (key + ".jpg")
        if not redraw_all and not want and p.exists():
            continue
        try:
            save(record_card(r, ctx), key)
        except Exception as e:  # noqa: BLE001
            print(f"  {key}: {e}")
    total = len(list(CARDS.glob("*.jpg")))
    size = sum(f.stat().st_size for f in CARDS.glob("*.jpg"))
    print(f"cards: {made} drawn, {total} on file, {size/1e6:.1f} MB in {CARDS}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
