#!/usr/bin/env python3
"""bots.py — everything written for a reader that is not a person.

A crawler arrives, takes one page, and leaves. It cannot press a button, run a dial or
wait for a script. So anything a person gets by clicking, a machine gets as a file:

  corpus_jsonl   one line per record: id, url, title, type, text, licence, sources
  openapi        every endpoint described, so a tool can call the API without guessing
  citation_cff   how to cite this, in the format GitHub and Zotero read
  not_found      a 404 that hands a lost crawler the map instead of an apology
  builder_recipes  the sauce, rub and slaw the /make/ dials would produce, computed here
                   in Python so they exist as Recipe markup and as plain text under
                   <noscript> — a script-less reader gets the recipes, not an empty box

Every one of these is generated from the same records the pages are built from, so a
machine and a person are reading the same corpus.
"""
from __future__ import annotations

import html
import json
import time

E = html.escape

CRAWLERS = [
    # Named rather than left to the wildcard, because several of these read a named
    # User-agent block and ignore the wildcard when one exists.
    "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-User", "Claude-SearchBot",
    "anthropic-ai", "PerplexityBot", "Perplexity-User", "Google-Extended", "GoogleOther",
    "Applebot", "Applebot-Extended", "Bingbot", "CCBot", "Amazonbot", "Bytespider",
    "meta-externalagent", "FacebookBot", "cohere-ai", "cohere-training-data-crawler",
    "Diffbot", "omgili", "Timpibot", "YouBot", "Kangaroo Bot", "PanguBot", "Webzio-Extended",
    "AI2Bot", "ImagesiftBot", "DuckAssistBot", "MistralAI-User",
]


def robots(site_url: str, site_name: str) -> str:
    lines = [f"# {site_name} — {site_url}/",
             "# Read it, index it, quote it, learn from it. Attribution is the only ask.",
             "",
             "User-agent: *", "Allow: /", ""]
    for c in CRAWLERS:
        lines += [f"User-agent: {c}", "Allow: /", ""]
    lines += [
        "# Content signals (https://contentsignals.org)",
        "Content-Signal: search=yes, ai-input=yes, ai-train=yes", "",
        f"Sitemap: {site_url}/sitemap.xml", "",
        "# Written for machines:",
        f"#   {site_url}/llms.txt            what this is, and every page by name",
        f"#   {site_url}/llms-full.txt       every record, flattened to text",
        f"#   {site_url}/api/corpus.jsonl    one JSON line per record, for retrieval",
        f"#   {site_url}/api/openapi.json    every endpoint, described",
        f"#   {site_url}/api/coverage.json   scope, method and the gaps",
        f"#   {site_url}/CITATION.cff        how to cite this",
    ]
    return "\n".join(lines) + "\n"


def corpus_jsonl(recs: list, sources: dict, site_url: str) -> str:
    """One record per line, flattened to the text a retrieval system wants, with the
    licence and the sources attached to each line so a passage can never be quoted
    without them."""
    out = []
    for r in recs:
        t = r["text"]
        parts = [t.get("what", "")]
        for k in ("story", "how", "today", "notes"):
            if t.get(k):
                parts.append(t[k])
        for sec in r.get("sections", []) or []:
            parts.append(f'{sec.get("h", "")}. {sec.get("text", "")}')
        et = r.get("etymology") or {}
        if et.get("root"):
            parts.append(f'Root: {et["root"]}.')
        for k in r.get("kin_out", []):
            parts.append(f'{r["names"]["name"]} to {k["name"]}: {k["as"]}')
        for c in r.get("confusable_with", []):
            parts.append(f'Not to be confused with {c["id"]}: {c["tell"]}')
        for rc in r.get("recipes", []) or []:
            bits = [rc.get("title", "")]
            if rc.get("ingredients"):
                bits.append("Ingredients: " + "; ".join(rc["ingredients"]))
            if rc.get("text"):
                bits.append(rc["text"])
            parts.append(" ".join(bits))
        out.append(json.dumps({
            "id": r["id"], "type": r["type"], "title": r["names"]["name"],
            "url": f'{site_url}/{("word" if r["type"] == "term" else r["type"])}/{r["id"]}/',
            "json": f'{site_url}/api/{r["type"]}/{r["id"]}.json',
            "aliases": r["names"].get("aliases", []),
            "region": [x.get("name", x["key"]) for x in r.get("region_terms", [])],
            "text": "\n\n".join(p.strip() for p in parts if p and p.strip()),
            "tier": (r.get("provenance", {}).get("default") or {}).get("tier"),
            "sources": [{"id": s, "title": sources.get(s, {}).get("title", ""),
                         "url": sources.get(s, {}).get("url", "")} for s in r.get("sources", [])],
            "images": [{"url": f'{site_url}/images/{im["file"]}', "license": im.get("license", ""),
                        "author": im.get("author", "")} for im in r.get("images", [])],
            "license": "CC BY 4.0",
            "attribution": f"{r['names']['name']} — Carolina Barbecue, {site_url}/",
            "updated": r["updated"],
        }, ensure_ascii=False))
    return "\n".join(out) + "\n"


def openapi(site_url: str, site_name: str, types: list, counts: dict) -> str:
    def path(summary, desc, example=None):
        return {"get": {"summary": summary, "description": desc,
                        "responses": {"200": {"description": "OK", "content": {"application/json": {}}}},
                        **({"externalDocs": {"url": site_url + example}} if example else {})}}
    paths = {
        "/api/index.json": path("Every record, in brief", "id, type, name, aliases, region, facets, blurb, image and url for all records."),
        "/api/nodes.json": path("Every record, in full", "The complete corpus, each record enriched with its kin, sources, tier labels and market or profile data."),
        "/api/places.json": path("Every place on the map", "Curated pits plus every OpenStreetMap barbecue row in both states, with per-day open state. OpenStreetMap rows carry ODbL."),
        "/api/kin.json": path("Every link between pages", "Directed edges: from, to, the relation, and the sentence the source page says about the target."),
        "/api/coverage.json": path("Scope, method and gaps", "What this covers, where each kind of row comes from, how many places carry each tag, and what has not been read."),
        "/api/sources.json": path("The source registry", "Every source a record may cite, by id. Records cite only these."),
        "/api/sauces.json": path("Bottled sauces, measured", "Sixty-eight labels: ingredient order, sugar per tablespoon, sodium, the maker's town and coordinates."),
        "/api/corpus.jsonl": path("The whole corpus as JSON Lines", "One record per line, flattened to text with its licence, sources and images. Written for retrieval."),
        "/llms.txt": path("Orientation for language models", "Names this corpus and every page in it."),
        "/llms-full.txt": path("Every record as plain text", "The whole corpus, flattened."),
        "/nodes.csv": path("Every record as CSV", "One row per record."),
        "/nodes.jsonl": path("Every record as JSON Lines", "One record per line, unflattened."),
        "/sitemap.xml": path("Sitemap", "Every page, with lastmod and image extensions."),
        "/feed.xml": path("Atom feed", "The most recently updated records."),
    }
    for t in types:
        paths[f"/api/{t}/{{id}}.json"] = {"get": {
            "summary": f"One {t} record",
            "description": f"The full record. {counts.get(t, 0)} exist; ids are listed in /api/index.json.",
            "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"},
                            "description": "kebab-case record id"}],
            "responses": {"200": {"description": "OK", "content": {"application/json": {}}},
                          "404": {"description": "No record with that id"}}}}
    return json.dumps({
        "openapi": "3.1.0",
        "info": {
            "title": site_name,
            "version": time.strftime("%Y.%m.%d"),
            "summary": "Barbecue in North and South Carolina: styles, sauces, dishes, pit practice, places, people, organizations, events, vocabulary, art and long reads.",
            "description": ("One JSON record per node of the tradition. Every field carries a provenance tier — cited, "
                            "harvested, tradition, inference or field — and cites a source in /api/sources.json. "
                            "Records are CC BY 4.0. Place points come from OpenStreetMap under ODbL 1.0 and stay under it. "
                            "Pictures carry their own licences, stated per file. No key, no rate limit, no account: these "
                            "are static files on a static host."),
            "license": {"name": "CC BY 4.0", "url": "https://creativecommons.org/licenses/by/4.0/"},
            "contact": {"url": site_url + "/"},
        },
        "servers": [{"url": site_url}],
        "externalDocs": {"description": "Scope, method and gaps", "url": site_url + "/api/coverage.json"},
        "paths": dict(sorted(paths.items())),
    }, ensure_ascii=False, indent=1) + "\n"


def citation_cff(site_url: str, site_name: str, cov: dict) -> str:
    return (
        "cff-version: 1.2.0\n"
        f"title: \"{site_name}\"\n"
        "message: \"If you use this data, please cite it.\"\n"
        "type: dataset\n"
        "authors:\n"
        "  - name: \"NaN\"\n"
        f"    website: \"{site_url}/\"\n"
        f"url: \"{site_url}/\"\n"
        f"repository-code: \"https://github.com/NaNoBotCo/carolina-barbecue\"\n"
        "license: CC-BY-4.0\n"
        f"date-released: \"{cov.get('built', time.strftime('%Y-%m-%d'))}\"\n"
        "abstract: >-\n"
        "  A directory of barbecue in North and South Carolina: styles, sauces, dishes, pit\n"
        "  practice, places, people, organizations, events, vocabulary and art. One JSON\n"
        "  record per node, every field carrying a provenance tier and citing a named source.\n"
        "  Place points derive from OpenStreetMap under ODbL 1.0.\n"
        "keywords:\n"
        "  - barbecue\n  - North Carolina\n  - South Carolina\n  - foodways\n  - open data\n"
    )


def not_found(site_url: str, site_name: str, css: str, counts: dict) -> str:
    """A 404 that hands a lost crawler the map."""
    rows = "".join(f'<li><a href="{site_url}/{p}/">{E(label)}</a></li>' for p, label in [
        ("", "Directory"), ("near", "Near me"), ("places", "Map"), ("sauce", "Sauce"), ("make", "Make"),
        ("pig", "Pig"), ("art", "Art"), ("stories", "Stories"), ("numbers", "Numbers"), ("words", "Words"),
        ("sources", "Sources"), ("coverage", "Coverage"), ("search", "Search")])
    api = "".join(f'<li><a href="{site_url}/{p}">{E(p)}</a> — {E(d)}</li>' for p, d in [
        ("llms.txt", "orientation for language models"),
        ("llms-full.txt", "every record as text"),
        ("api/index.json", "every record in brief"),
        ("api/corpus.jsonl", "one JSON line per record, for retrieval"),
        ("api/openapi.json", "every endpoint described"),
        ("api/coverage.json", "scope, method and gaps"),
        ("sitemap.xml", "every page")])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Not here — {E(site_name)}</title>
<meta name="robots" content="noindex,follow">
<meta name="color-scheme" content="light dark">
<style>{css}</style>
</head>
<body>
<header class="top"><a class="brand" href="{site_url}/">Carolina <b>Barbecue</b></a></header>
<main>
<h1><span class="kind">404</span>Nothing at that address</h1>
<p class="lede">The page moved or never existed. Everything here is one of these:</p>
<h2>Pages</h2><ul>{rows}</ul>
<h2>For machines</h2><ul>{api}</ul>
<p class="legend">{counts.get('total', 0)} records. Records CC BY 4.0; place points OpenStreetMap under ODbL;
pictures carry their own licences.</p>
</main>
</body>
</html>
"""


# ---------------------------------------------------------------- the builders, computed

TBSP = {"tsp": 1 / 3, "tbsp": 1, "cup": 16, "egg": 1}


def _amount(q: float, unit: str) -> str:
    """Kitchen units, in words, matching what the page's own script prints."""
    fr = [(1, "1"), (0.75, "¾"), (0.6667, "⅔"), (0.5, "½"), (0.3333, "⅓"), (0.25, "¼"), (0.125, "⅛")]

    def frac(v):
        w = int(v + 1e-9)
        rem = v - w
        best, bd = "", 9
        for val, sym in fr:
            if abs(rem - val) < bd:
                bd, best = abs(rem - val), sym
        if rem < 0.06:
            return str(w or 0)
        if bd > 0.08 and w == 0:
            return str(round(v, 2))
        if best == "1":
            w, best = w + 1, ""
        return (f"{w} " if w else "") + best

    def plural(v, word):
        return f"{frac(v)} {word}" + ("s" if v > 1.02 else "")

    if q <= 0:
        return ""
    if unit == "cup":
        return plural(q * 16, "tablespoon") if q < 0.25 else plural(q, "cup")
    if unit == "tbsp":
        return plural(q * 3, "teaspoon") if q < 1 else plural(q, "tablespoon")
    if unit == "tsp":
        return plural(q / 3, "tablespoon") if q >= 3 else plural(q, "teaspoon")
    if unit == "egg":
        return frac(q)
    return plural(q, unit)


def builder_recipes(sauce: dict, rub: dict, slaw: dict, site_url: str) -> list:
    """Every default the /make/ dials open on, computed here so a crawler and a reader
    without scripts get the recipes rather than an empty box."""
    out = []
    quart = 64  # tablespoons
    for b in sauce["bases"]:
        ings = []
        for ing in b["ingredients"]:
            q = ing["per_tbsp"] * quart          # heat and sweetness open at 1.0
            a = _amount(q, "tbsp")
            if a:
                ings.append(f'{a} {ing["name"]}')
        out.append({"id": "sauce-" + b["key"], "name": f'{b["name"]} sauce', "kind": "sauce",
                    "yield": "about a quart", "ingredients": ings, "steps": b["method"],
                    "about": b["says"], "region": b["region"], "anchor": b["anchor"]})
    for lv in rub["levels"]:
        meat = next(m for m in rub["meats"] if m["key"] == "shoulder")
        total = lv["tbsp_per_lb"] * meat["lb"]
        ings = []
        for name, frac_ in lv["parts"].items():
            a = _amount(frac_ * total, "tbsp")
            if a:
                ings.append(f"{a} {name}")
        out.append({"id": "rub-" + lv["key"], "name": lv["name"], "kind": "rub",
                    "yield": f'enough for {meat["label"].lower()}, about {meat["lb"]} lb',
                    "ingredients": ings, "steps": lv.get("when", []), "about": lv["says"],
                    "region": "", "anchor": lv["anchor"]})
    for k in slaw["kinds"]:
        size = next(z for z in slaw["sizes"] if z["key"] == "head")
        ings = [f'{size["cups"]} cups cabbage, chopped fine']
        for ing in k["per_cup"]:
            a = _amount(ing["q"] * size["cups"], ing["unit"])
            if a:
                ings.append(f'{a} {ing["name"]}' + (" (optional)" if ing.get("optional") else ""))
        out.append({"id": "slaw-" + k["key"], "name": k["name"], "kind": "slaw",
                    "yield": f'{size["label"].lower()} of cabbage, about {size["lb"]} lb',
                    "ingredients": ings, "steps": k["steps"], "about": k["says"],
                    "region": k["region"], "anchor": k["anchor"]})
    return out


def recipe_jsonld(r: dict, site_url: str) -> dict:
    a = r.get("anchor") or {}
    d = {"@context": "https://schema.org", "@type": "Recipe",
         "@id": f'{site_url}/make/#{r["id"]}',
         "name": r["name"], "description": r["about"],
         "url": f'{site_url}/make/#{r["id"]}',
         "recipeCategory": {"sauce": "Sauce", "rub": "Seasoning", "slaw": "Side dish"}[r["kind"]],
         "recipeCuisine": "Barbecue, Southern United States",
         "recipeYield": r["yield"],
         "recipeIngredient": r["ingredients"],
         "inLanguage": "en",
         "isPartOf": {"@id": f"{site_url}/make/"},
         "license": "https://creativecommons.org/licenses/by/4.0/"}
    if r["steps"]:
        d["recipeInstructions"] = [{"@type": "HowToStep", "text": s} for s in r["steps"]]
    if a.get("title"):
        d["isBasedOn"] = {"@type": "CreativeWork", "name": a["title"],
                          **({"url": a["url"]} if a.get("url") else {}),
                          **({"datePublished": str(a["year"])} if a.get("year") else {}),
                          **({"publisher": {"@type": "Organization", "name": a["publisher"]}} if a.get("publisher") else {})}
    if a.get("note"):
        d["disambiguatingDescription"] = a["note"]
    return d


def builders_noscript(recipes: list) -> str:
    """The same recipes as plain HTML, for a reader whose scripts never run."""
    out = ['<noscript><div class="recipe"><h3>Every recipe these dials make</h3>',
           '<p class="says">Scripts are off, so here they all are at their opening settings.</p>']
    for r in recipes:
        out.append(f'<h4 id="{E(r["id"])}">{E(r["name"])}</h4><p>{E(r["about"])}</p><ul>'
                   + "".join(f"<li>{E(i)}</li>" for i in r["ingredients"]) + "</ul>"
                   + (("<ol>" + "".join(f"<li>{E(s)}</li>" for s in r["steps"]) + "</ol>") if r["steps"] else "")
                   + f'<p class="prov">{E((r.get("anchor") or {}).get("note", ""))}</p>')
    out.append("</div></noscript>")
    return "".join(out)
