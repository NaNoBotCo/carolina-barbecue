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
| pictures | 115, each with its licence and photographer, plus 190 share cards drawn from them |
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
- **[Make it](https://nanobotco.github.io/carolina-barbecue/make/)** — a sauce or a rub.
  Six sauce regions: two start from a published recipe (a Wikibooks Eastern North Carolina
  sauce, CC BY-SA; Mary Randolph's 1824 pepper vinegar), one descends from Mrs. Hill's 1867
  "Sauce for Barbecues", and three say plainly that the proportions are this project's own.
  Every result is drawn against the 68 measured bottles, which mostly out-sweeten anything
  you would make. Four rub levels climb from **salt and nothing else** — which is what most
  whole-hog pits do — through Ed Mitchell's four ingredients to a full modern rub, and the
  panel opens by saying that the seasoning deciding the flavour lands after the cook, at the
  chopping block. Four slaw dressings cover white, red, yellow and a boiled 1879 receipt
  that predates the mayonnaise jar; red slaw points you back to the dip you just built.
- **[Count it up](https://nanobotco.github.io/carolina-barbecue/numbers/)** — a map of
  the two states shaded by distance to the nearest pit (half of both is within 10.6
  miles of one), when the pits opened, what 142 recipes call for, which days they open,
  and a matrix of which kind of page points at which.
- **[The Great Divide](https://nanobotco.github.io/carolina-barbecue/story/the-great-divide/)**
  — the columnists' war, the 2006 bills, the 2007 compromise, and the part both camps skip.
- **[Pig art](https://nanobotco.github.io/carolina-barbecue/art/)** — the pig that
  serves itself, the mascots, the 1830s election prints.
- **[Which side are you on?](https://nanobotco.github.io/carolina-barbecue/quiz/)**

## Hours, and the Sunday question

Sunday is the day a Carolina barbecue house is most likely to be shut, and the day some
people will tell you not to order barbecue anyway. The finder has an **Open Sunday** chip
and an **Open today** chip, and every row carries a seven-box week: filled is open, hollow
is closed, and **dashed means nobody has published it** — a third state, drawn apart from
closed, because a reader will drive on this.

Of the 158 places whose days we could read, 91 open Sunday and 58 are shut; 224 more have
not published their days at all. [The Sunday question](https://nanobotco.github.io/carolina-barbecue/story/the-sunday-question/)
lays out the cooking-week reason, the church reason, and the belief that late-week
barbecue is not the same — recorded as a belief, which this directory does not test.

## The rule behind the tags

A place can be tagged Black-owned, woman-owned, LGBTQ+ welcoming, cooks over wood,
whole hog, family-run, cash only, closes when sold out, buffet, weekends only, serves
hash, closed. A tag names its evidence — the owner's own words, a press profile that
names the owner, a public directory, a certification list, or someone who stood there.
The validator currently rejects ownership and welcome tags at the tradition and
inference tiers.

A place with no tag has not been read yet. That is a fact about this project, not about
the place, and [the finder says so on its own page](https://nanobotco.github.io/carolina-barbecue/near/#gaps).

## Sharing

Pages carry their own 1200x630 card, drawn from the pictures in the corpus — the pit's
own photograph where there is one, a picture from a page it points at where there is not,
with its credit and licence. A place card shows the town, the tags it has earned and how
many people have written it down; a sauce card shows where its sugar sits against a spoonful
of sugar; a word card shows the root. `tools/cards.py` draws all 190 in about a minute.

Every page also has a Pass it on row: copy the link, or hand it to Bluesky, Mastodon, X,
Facebook, Reddit, WhatsApp, email, or the phone's own share sheet.

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
[LICENSE](LICENSE) and [NOTICE.txt](NOTICE.txt).

**Using it.** Attribution is the whole of the condition — copy it, adapt it,
sell it, index it, train on it, and say where it came from.
[Open an issue](https://github.com/NaNoBotCo/carolina-barbecue/issues) if something is missing.

---

Contact: Nan · nan@motdang.net · Sponsor: [Ko-fi](https://ko-fi.com/defiantchiangmai) · [Patreon](https://www.patreon.com/nanobotco)

<!-- fleet-roster -->

## Elsewhere from the same publisher

- [Mot Dang](https://motdang.net/) — city directory for Chiang Mai and Chiang Rai
- [wichaa](https://wichaa.net/) — Lanna manuscripts, the amulet market, and the traditions around them
- [Amulet Atlas](https://nanobotco.github.io/amulet-atlas/) — amulets, charms and talismans worldwide
- [Wing Country](https://nanobotco.github.io/buffalo-wings/) — the American chicken wing
- [Pink Box](https://nanobotco.github.io/pink-box/) — the American mom-and-pop donut shop
- [Basque Tables](https://nanobotco.github.io/basque-tables/) — Basque dining rooms of California, Nevada and Idaho
- [Pinot Country](https://nanobotco.github.io/pinot-noir/) — pinot noir: the vine, the regions, the cellars
- [Care Abroad](https://nanobotco.github.io/care-abroad/) — treatment across borders, with published prices and their dates
- [Thai Roots](https://nanobotco.github.io/thairoots/) — a root dictionary of Thai, with a word decomposer
- [The index](https://nanobotco.github.io/index/) — every corpus, site and repository, counted
- [Uptake](https://nanobotco.github.io/uptake/) — a field manual on publishing for machines that copy
- [NaNoBotCo](https://nanobotco.github.io/) — the portal
- [ฮักฝรั่ง](https://hakfarang.net/) — เรื่องเงิน วีซ่า และชีวิตกับแฟนฝรั่ง
- [Offrampt](https://offrampt.net/) — turning crypto into spendable local money, Thailand first

All of it, counted: https://nanobotco.github.io/index/ · roster as JSON: https://nanobotco.github.io/index/fleet.json
