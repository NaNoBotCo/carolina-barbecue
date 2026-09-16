# Carolina Barbecue

A directory of barbecue in North and South Carolina: the styles, the sauces, the
plates, the pit, the places, the people, the words — and what each one is to the
others.

**Live:** https://nanobotco.github.io/carolina-barbecue/

One JSON record per node of the tradition. Every field says where it came from.
Every page says what its neighbours are to it, in both directions.

| | |
|---|---|
| records | 178 — 6 styles, 15 sauces, 27 dishes, 11 pit practices, 58 places, 25 people, 4 organizations, 7 events, 15 words, 7 art genres, 3 stories |
| places on the map | 373 — the written-up pits plus every OpenStreetMap barbecue row in both states |
| recipes | 142, free to use: 79 public-domain cookbook texts in full, 58 from Wikibooks under CC BY-SA, 5 ingredients-only |
| sauce labels read | 68 bottles: sugar per tablespoon, what comes first on the list, the maker's town |
| pictures | 115, each with its licence and photographer |
| sources | 590 |

## The pages that answer a question

- **[Find the Q](https://nanobotco.github.io/carolina-barbecue/near/)** — your own
  browser's location, or a town you type, and every pit sorted by distance. Filter by
  cooks over wood, whole hog, Black-owned, woman-owned, LGBTQ+ welcoming, cash only,
  closes when sold out, buffet, weekends only, serves hash. Below it, the pits other
  people have written down, counted by how many different people said so.
- **[What is actually in the sauce](https://nanobotco.github.io/carolina-barbecue/sauce/)**
  — 68 labels, read not tasted. Median sugar per tablespoon: mustard 5.3 g, heavy
  tomato 5.0, Lexington dip 3.5, light tomato 2.0, vinegar and pepper 0.5. A
  tablespoon of table sugar is 12.6 g.
- **[Which part of the pig](https://nanobotco.github.io/carolina-barbecue/pig/)** — a
  drawn hog, and a small one per style showing what that style takes off it.
- **[The Great Divide](https://nanobotco.github.io/carolina-barbecue/story/the-great-divide/)**
  — the columnists' war, the 2006 bills, the 2007 compromise, and the part both camps skip.
- **[Pig art](https://nanobotco.github.io/carolina-barbecue/art/)** — the pig that
  serves itself, the mascots, the 1830s election prints.
- **[Which side are you on?](https://nanobotco.github.io/carolina-barbecue/quiz/)**

## The rule behind the tags

A place can be tagged Black-owned, woman-owned, LGBTQ+ welcoming, cooks over wood,
whole hog, family-run, cash only, closes when sold out, buffet, weekends only, serves
hash, closed. **Every tag names its evidence** — the owner's own words, a press profile
that names the owner, a public directory, a certification list, or someone who stood
there. Ownership and welcome tags are never inferred from a name or a photograph; the
validator refuses them at the tradition and inference tiers.

A place with no tag has not been read yet. That is a fact about this project, not about
the place, and [the finder says so on its own page](https://nanobotco.github.io/carolina-barbecue/near/#gaps).

## Sharing

Every page carries its own 1200x630 card, drawn from the pictures in the corpus — the pit's
own photograph where there is one, a picture from a page it points at where there is not,
always credited and licensed. A place card shows the town, the tags it has earned and how
many people have written it down; a sauce card shows where its sugar sits against a spoonful
of sugar; a word card shows the root. `tools/cards.py` draws all 190 in about a minute.

Every page also has a Pass it on row: copy the link, or hand it to Bluesky, Mastodon, X,
Facebook, Reddit, WhatsApp, email, or the phone's own share sheet. No third-party script,
no tracking pixel, nothing loaded from anywhere else.

## For machines

`llms.txt`, `llms-full.txt`, `ai.txt`, `humans.txt`, a sitemap with the image extension, an
Atom feed, OpenSearch, CSV and JSONL dumps, and JSON-LD on every page — `Restaurant` with
coordinates for a pit, `Recipe` with its ingredients and its licence for all 142 recipes,
`DefinedTerm` for the vocabulary, `ImageObject` with the licence for every picture, and a
`BreadcrumbList` throughout. The whole corpus as JSON under `/api/`:
[`nodes.json`](https://nanobotco.github.io/carolina-barbecue/api/nodes.json) ·
[`places.json`](https://nanobotco.github.io/carolina-barbecue/api/places.json) ·
[`kin.json`](https://nanobotco.github.io/carolina-barbecue/api/kin.json) ·
[`sauces.json`](https://nanobotco.github.io/carolina-barbecue/api/sauces.json) ·
[`coverage.json`](https://nanobotco.github.io/carolina-barbecue/api/coverage.json), which
states the scope, where each kind of row comes from, and what is missing.

`robots.txt` allows everything and says so with a Content-Signal header: search yes,
AI input yes, AI training yes.

## Running it

Stdlib Python 3.9+, no dependencies, no build step.

```
python3 tools/validate.py     # every record must pass
python3 tools/build.py        # records -> build/api, search tables
python3 tools/site.py         # build/site
python3 tools/serve.py        # http://127.0.0.1:8795
python3 -m unittest discover -s tests
./publish.sh                  # build into docs/, which is what Pages serves
```

`README.txt` is the fuller guide; `AUTHORING.txt` is how to write a record.

## Licence

Records CC BY 4.0. Place points © OpenStreetMap contributors under ODbL 1.0
(share-alike). Pictures carry their own licences, stated per file. Code MIT. See
[LICENSE](LICENSE).
