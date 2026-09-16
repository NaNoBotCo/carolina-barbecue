"""tests — run with:  python3 -m unittest discover -s tests -v

Covers: every record validates · build produces the API and the kin edges resolve ·
search answers golden queries within the top 3 (Python core, same tables the page
uses) · the site carries its bot-legibility files and no host paths.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

# (query, expected id in top 3) — plainly spelled and misspelled.
GOLDEN = [
    ("skylight inn", "skylight-inn"),
    ("ayden", "skylight-inn"),
    ("whole hog vinegar", "eastern-nc"),
    ("mustard sauce", "mustard-sauce"),
    ("piggie park", "maurices-piggie-park"),
    ("lexington dip", "lexington-dip"),
    ("hush puppies", "hushpuppies"),
    ("brownies", "outside-brown"),
    ("cracklins", "pork-skins"),
    ("lexingtion", "lexington"),
    ("wilburs", "wilbers-barbecue"),
    ("bessingers", "bessingers-bar-b-q"),
    ("rodney scott", "rodney-scott"),
]


class Records(unittest.TestCase):
    def test_validate(self):
        r = subprocess.run([sys.executable, str(TOOLS / "validate.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_every_record_has_what_and_provenance(self):
        for p in (ROOT / "data" / "nodes").rglob("*.json"):
            d = json.loads(p.read_text(encoding="utf-8"))
            self.assertTrue(d["text"].get("what"), f"{p.name}: no what")
            self.assertTrue(d["provenance"]["default"]["tier"], p.name)


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r = subprocess.run([sys.executable, str(TOOLS / "build.py")], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr

    def test_api_files(self):
        api = ROOT / "build" / "api"
        for f in ("nodes.json", "index.json", "places.json", "kin.json", "coverage.json", "sources.json"):
            self.assertTrue((api / f).exists(), f)

    def test_kin_edges_resolve(self):
        api = ROOT / "build" / "api"
        ids = {n["id"] for n in json.loads((api / "index.json").read_text())["nodes"]}
        for e in json.loads((api / "kin.json").read_text())["edges"]:
            self.assertIn(e["to"], ids)
            self.assertIn(e["from"], ids)

    def test_places_table_has_osm_rows(self):
        t = json.loads((ROOT / "build" / "api" / "places.json").read_text())
        self.assertGreater(t["harvested"], 100)
        self.assertEqual(t["count"], len(t["places"]))


class Search(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common import search_core
        cls.sc, _ = search_core()
        docs = json.loads((ROOT / "build" / "searchdocs.json").read_text())["docs"]
        groups = json.loads((ROOT / "data" / "search" / "carolina.thesaurus.json").read_text())["groups"]
        cls.core = cls.sc.SearchCore(groups, [])
        cls.index = cls.sc.Index(cls.core)
        cls.prep = {}
        for d in docs:
            f = {"name": (d["names"], 3), "terms": (d["terms"], 2), "text": (d["text"], 1)}
            cls.index.add(d, f)
            cls.prep[d["id"]] = cls.core.prepare_doc(f)
        cls.index.finalize()

    def top(self, q, n=3):
        an = self.core.analyze(q, self.index)
        rows = []
        for i, p in self.prep.items():
            r = self.core.score_doc(an, p)
            if r:
                rows.append((i, r))
        whole = [x for x in rows if x[1]["coverage"] >= 1]
        rows = whole or rows
        rows.sort(key=lambda x: -x[1]["score"])
        return [i for i, _ in rows[:n]]

    def test_golden(self):
        for q, want in GOLDEN:
            self.assertIn(want, self.top(q), f"{q!r} → {self.top(q)}")


class Site(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r = subprocess.run([sys.executable, str(TOOLS / "site.py")], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr

    def test_bot_files(self):
        site = ROOT / "build" / "site"
        for f in ("index.html", "llms.txt", "llms-full.txt", "sitemap.xml", "robots.txt", "feed.xml", "opensearch.xml", "nodes.csv", "nodes.jsonl", "search/index.html", "search/tables.json", "places/index.html", "coverage/index.html"):
            self.assertTrue((site / f).exists(), f)
        self.assertIn("Content-Signal", (site / "robots.txt").read_text())

    def test_structured_data_parses_everywhere(self):
        """Every JSON-LD block parses and names a type; every index page carries one."""
        import re
        site = ROOT / "build" / "site"
        bare = []
        for f in site.rglob("*.html"):
            h = f.read_text(encoding="utf-8")
            blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)
            if not blocks and f.name == "index.html":
                bare.append(str(f.relative_to(site)))
            for b in blocks:
                d = json.loads(b)            # raises on malformed
                self.assertTrue(d.get("@type"), f"{f}: block with no @type")
                self.assertTrue(d.get("@context"), f"{f}: block with no @context")
        self.assertEqual(bare, [], "pages carrying no structured data")

    def test_machine_files(self):
        site = ROOT / "build" / "site"
        for f in ("api/corpus.jsonl", "api/openapi.json", "CITATION.cff", "404.html"):
            self.assertTrue((site / f).exists(), f)
        lines = (site / "api" / "corpus.jsonl").read_text().strip().split("\n")
        idx = json.loads((site / "api" / "index.json").read_text())
        self.assertEqual(len(lines), idx["count"], "one corpus line per record")
        for ln in lines[:5]:
            d = json.loads(ln)
            for k in ("id", "url", "text", "license", "sources"):
                self.assertIn(k, d)
        api = json.loads((site / "api" / "openapi.json").read_text())
        self.assertEqual(api["openapi"], "3.1.0")
        self.assertGreater(len(api["paths"]), 15)
        robots = (site / "robots.txt").read_text()
        for bot in ("GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended"):
            self.assertIn(bot, robots)

    def test_builder_recipes_are_readable_without_scripts(self):
        h = (ROOT / "build" / "site" / "make" / "index.html").read_text()
        self.assertIn("<noscript>", h)
        import re
        recipes = [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)]
        kinds = [d for d in recipes if d.get("@type") == "Recipe"]
        self.assertGreaterEqual(len(kinds), 14, "every dial preset should exist as a Recipe")
        for r in kinds:
            self.assertTrue(r.get("recipeIngredient"), r.get("name"))

    def test_no_host_paths(self):
        site = ROOT / "build" / "site"
        for p in site.rglob("*"):
            if p.is_file() and p.suffix in (".html", ".json", ".txt", ".xml", ".csv", ".jsonl"):
                self.assertNotIn("/Users/", p.read_text(encoding="utf-8", errors="ignore"), str(p))

    def test_every_record_has_a_page(self):
        site = ROOT / "build" / "site"
        idx = json.loads((site / "api" / "index.json").read_text())
        for n in idx["nodes"]:
            self.assertTrue((site / n["url"] / "index.html").exists(), n["url"])


if __name__ == "__main__":
    unittest.main()
