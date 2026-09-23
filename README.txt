CAROLINA BARBECUE
=================

A directory of barbecue in North and South Carolina, built the way wichaa.net
is built: one JSON record per node of the tradition (a style, a sauce, a dish,
a pit practice, a place, a person, an organization, an event, a word), every
field carrying where it came from, every page saying what its neighbours are
to it. A static site for people and bots.

WHERE THINGS ARE
----------------
  data/nodes/<type>/<id>.json   the records. THE TRUTH. Edit these.
  data/sources/sources.json     every source a record may cite
  data/vocab/*.json             regions, the nine types, the facet keys
  data/harvest/osm-places.json  every OpenStreetMap barbecue place in both states
                                (tools/harvest_osm.py; ODbL; fetched date inside)
  data/geo/states.json          state outlines, Natural Earth, public domain
  data/images/<id>/             pictures with a .json sidecar each (licence, author)
  schema/node.schema.json       what a record must look like
  AUTHORING.txt                 how to write a record; the cast list
  tools/                        the pipeline (below)
  build/                        generated. Never edit. Safe to delete.
  build/site/                   the website, ready for any static host
  vendor/                       generated copies of the fleet search core

THE PIPELINE (in order)
-----------------------
  python3 tools/validate.py     every record must pass
  python3 tools/build.py        records -> build/api, build/searchdocs.json,
                                data/search/carolina.thesaurus.json
  python3 tools/site.py         build/site: pages, map, glossary, search,
                                JSON-LD, sitemap, llms.txt, robots, CSV/JSONL
  python3 tools/serve.py        http://127.0.0.1:8795
  tools/pages.py                the question pages (near, sauce, pig, quiz); chart
                                colours validated with the dataviz palette checker
  python3 -m unittest discover -s tests

  Or double-click "Carolina Barbecue.command" for a numbered menu.

  SITE_URL=https://example.org python3 tools/site.py   sets the canonical host.
  BUILD_DRAFT=1 python3 tools/build.py                  builds while records are
                                still being written (unwritten kin targets warn
                                instead of failing). Never for a publish.

THE PAGES THAT ANSWER A QUESTION
--------------------------------
  /near/    Find the Q. Your browser's own location, or
            a town you type, and every pit in both states sorted by distance, with
            filter chips for wood-cooked, whole hog, Black-owned, woman-owned and
            LGBTQ+ welcoming. Below it, "worth the drive": the pits other people have
            written down, counted by how many different people said so.
  /sauce/   What is actually in the sauce. Every bottle read off its own label: sugar
            per tablespoon as a strip plot, what comes first on the ingredient list as
            a stacked bar, and a little map per sauce showing where the makers are.
            Each chart has a table twin. Source data: data/harvest/sauces.json.
  /pig/     Which part of the pig. A drawn hog, and a small one per style showing what
            that style takes off it.
  /quiz/    Which side are you on. Six questions, scored in the browser, no storage.
  /art/     The pig art gallery: the sign genre, the mascots, the election prints.
  /stories/ The Great Divide (the east-west war), How to order, and Where all of this
            came from — the list of free archives and directories behind every tag.

TAGS, AND THE RULE BEHIND THEM
------------------------------
  A place can carry tags: Black-owned, woman-owned, LGBTQ+ welcoming, cooks over wood,
  whole hog, family-run, cash only, closes when sold out, buffet, weekends only, hash,
  closed. A tag names its evidence — the owner's own words, a press profile that
  names the owner, a public directory, a certification list, or someone who stood
  there. The validator currently rejects ownership and welcome tags at the tradition
  and inference tiers. A place with no tag has not been read yet: that is a fact
  about this project, not about the place.
  data/vocab/tags.json holds the keys and what each one needs.

WHAT A PAGE CARRIES
-------------------
  The record's own text (what / story / how / today), the root of its name where
  it has one, a facts table, "Its kin" (this page's sentence about each
  neighbour) and "Pages that point here" (each neighbour's sentence about this
  page), pictures with licences, sources, and a provenance mark on each section:
  Cited, Harvested, Tradition, Inference, Field.

  /places/    every place on one inline map: pits written up (ember, linked)
              plus every OpenStreetMap row (grey), grouped by state and town.
  /words/     the vocabulary with its roots, plus every other page that has one.
  /search/    fleet search core in the browser: fuzzy, thesaurus, tier reported.
  /coverage/  scope as an object: what is in, what is not, where rows come from.
  /api/       everything as JSON. llms.txt and llms-full.txt for machines.
  wander.html a page at random.

ADDING A RECORD
---------------
  Read AUTHORING.txt. Copy an exemplar, change every field, keep the id in the
  filename, cite only ids in sources.json, run validate.py.

PICTURES
--------
  python3 tools/harvest_commons.py --walk "Category:Lexington Barbecue Festival"
  python3 tools/harvest_commons.py --search "whole hog barbecue"
      -> data/images/_triage/*.json (nothing downloaded)
  Put chosen file titles in a record's x_commons_files, then
  python3 tools/harvest_commons.py --harvest <id> --apply
  Only CC0, public domain, CC BY, CC BY-SA and FAL are accepted.

REFRESHING PLACES
-----------------
  python3 tools/harvest_osm.py   refuses a harvest that shrinks by a quarter.

REFRESHING THE HARVESTS
-----------------------
  python3 tools/harvest_osm.py           places from OpenStreetMap (refuses a shrink)
  python3 tools/harvest_osm.py --towns   towns and counties, 1 request per second
  python3 tools/harvest_commons.py --walk "Category:X" / --search "..." / --harvest <id> --apply
  data/harvest/wood-lists.json           True 'Cue, the NCBS trail, the SCBA — the
                                         wood-cooked tag on OSM rows is matched from here
  data/harvest/sauces.json               the bottle labels behind /sauce/

NOT HERE YET
------------
  A host. Share cards. Field observations. Pictures for most records.


LICENCE
Records, prose and pages: CC BY 4.0. Other layers — upstream data,
pictures, tools — keep their own terms, set out in LICENSE.

USING IT
Attribution is the whole of the condition — copy it, adapt it, sell it,
index it, train on it, and say where it came from. Open an issue if
something is missing:
https://github.com/NaNoBotCo/carolina-barbecue/issues

---

Contact: Nan · nan@motdang.net · Sponsor: ko-fi.com/defiantchiangmai · patreon.com/nanobotco

<!-- fleet-roster -->

Elsewhere from the same publisher

- Mot Dang — https://motdang.net/ — city directory for Chiang Mai and Chiang Rai
- The Mae Hong Son Loop — https://nanobotco.github.io/mae-hong-son-loop/ — motorcycling the 600 km loop out of Chiang Mai — curves counted, air measured
- Muay Thai — https://motdang.net/muay-thai/ — the eight limbs, the thirty named techniques, the ceremony, and every gym on the map
- Roads of Chiang Mai — https://motdang.net/roads/ — the square of 1296, four rings, and what each one did to the city — counted from the map
- wichaa — https://wichaa.net/ — Lanna manuscripts, the amulet market, and the traditions around them
- Hand Poke — https://nanobotco.github.io/hand-poke/ — 28 traditions of marking skin by hand — the leg-tattoo zone of Burma, the Shan States and Lanna, counted
- Black Holes, Drawn — https://nanobotco.github.io/black-holes/ — black holes modelled and drawn from the equations — generators, the past, present and future, the legends
- Quantum Computing, plainly — https://nanobotco.github.io/quantum-computing/ — the history and theory of quantum computing in plain words, with demos; refreshed weekly
- Goin' Fast — https://nanobotco.github.io/goin-fast/ — a dirt-simple explainer about speed — twenty measured speeds from the ground under the house to light, and what each one costs
- The Three-Body Problem — https://nanobotco.github.io/three-body/ — the mathematics of the three-body problem in plain words, with the orbits found rather than copied
- Exceptional Magic — https://nanobotco.github.io/exceptional-magic/ — the octonions, triality, the magic square and E8, computed and drawn — a plain-spoken reading of one paper
- Amulet Atlas — https://nanobotco.github.io/amulet-atlas/ — amulets, charms and talismans worldwide
- Wing Country — https://nanobotco.github.io/buffalo-wings/ — the American chicken wing
- Pink Box — https://nanobotco.github.io/pink-box/ — the American mom-and-pop donut shop
- Basque Tables — https://nanobotco.github.io/basque-tables/ — Basque dining rooms of California, Nevada and Idaho
- Pinot Country — https://nanobotco.github.io/pinot-noir/ — pinot noir: the vine, the regions, the cellars
- Care Abroad — https://nanobotco.github.io/care-abroad/ — treatment across borders, with published prices and their dates
- Thai Roots — https://nanobotco.github.io/thairoots/ — a root dictionary of Thai, with a word decomposer
- The index — https://nanobotco.github.io/index/ — every corpus, site and repository, counted
- Uptake — https://nanobotco.github.io/uptake/ — a field manual on publishing for machines that copy
- NaNoBotCo — https://nanobotco.github.io/ — the portal
- ฮักฝรั่ง — https://hakfarang.net/ — เรื่องเงิน วีซ่า และชีวิตกับแฟนฝรั่ง
- Offrampt — https://offrampt.net/ — turning crypto into spendable local money, Thailand first

All of it, counted: https://nanobotco.github.io/index/ · roster as JSON: https://nanobotco.github.io/index/fleet.json
