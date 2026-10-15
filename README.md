*English · [Leia em português](README.pt-BR.md)* · **Vai à Festa do Livro?** Abra o guia: **https://jvlcapi.github.io/guia-nao-oficial-festa-do-livro/**

# Unofficial Guide to the USP Book Fair

**Live site: https://jvlcapi.github.io/guia-nao-oficial-festa-do-livro/** (in Portuguese)

A searchable price catalog and shopping-list planner for the [Festa do Livro da USP](https://festadolivro.edusp.com.br), the yearly book fair at the University of São Paulo where around 190 publishers sell their catalogs at half the cover price or less.

| | |
|---|---|
| Books in the catalog | **34,780** |
| Publisher price lists parsed | **191** (PDFs in dozens of different layouts) |
| Prices checked against the source PDF | every book with an ISBN; 158 flagged for review |
| Backend, accounts, API keys | **none** |
| Hosting cost | **zero** (GitHub Pages + GitHub Actions) |
| Unique visitors, one per browser | [![Unique visitors](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fabacus.jasoncameron.dev%2Fget%2Fguia-nao-oficial-festa-do-livro%2Fvisitantes&query=%24.value&label=unique%20visitors&color=2a4fd1&cacheSeconds=3600)](https://jvlcapi.github.io/guia-nao-oficial-festa-do-livro/) |

Community project, not affiliated with Edusp or the University of São Paulo. Prices come from the lists publishers post on the official site and may change before the fair.

## The problem

Every year each publisher uploads its own price list to the fair's website, as a PDF. There is no single place to search across publishers, compare editions, or add up what a shopping list will cost. The PDFs follow no common format: some are real tables, some are text laid out to look like tables, columns are cut off, numbers spill into neighbouring cells, and a few lists only give the cover price plus a discount percentage.

## What it does

- **One catalog for the whole fair.** Search every publisher at once by title, author, publisher or subject; filter by stall and price range; sort by price or discount.
- **A shopping list with the math done.** Total at the fair, savings over cover price, spending by publisher and by genre, and an optional budget meter.
- **Share by link.** A list becomes a URL that anyone can open, see with current prices, and copy into their own list. The same link moves a list from phone to laptop. Imported books carry a colored tag with the name of the list they came from, one stable color per source, and the list can be filtered by source.
- **Works offline.** After the first visit the site and the catalog stay on the device, because the signal inside the fair tent is unreliable.
- **Ready for next year with no code changes.** The pipeline detects the current edition on its own and rebuilds the catalog and the site on a schedule.

## Architecture

```
official fair website (public JSON API + one PDF price list per publisher)
        │
        │  GitHub Actions, daily from September to December, or on demand
        ▼
┌───────────────────────────────────────────────────────────────┐
│ Python pipeline                                               │
│  1. detect the current edition from the homepage              │
│  2. list publishers through the API, download PDFs (cached)   │
│  3. parse each PDF two ways, keep the more complete result    │
│  4. verify every price against the PDF line of its ISBN       │
│  5. write catalog + edition info + verification report        │
└───────────────────────────────────────────────────────────────┘
        │  commit only when data changed, then deploy
        ▼
GitHub Pages: static HTML/CSS/JS + catalogo.json + edicao.json
        │
        ▼
visitor's browser: search, totals and the list (stored on the device)
```

## Engineering decisions

**Edition-agnostic by design.** Nothing about a specific year lives in the code. The homepage declares the current edition, the pipeline reads it, and the site reads the edition name and dates from a small `edicao.json` published next to the catalog. A fixed edition can still be pinned in `settings.json` or through an environment variable.

**Two parsers instead of one clever one.** Each PDF goes through a table-cell reader (PyMuPDF table detection) and a positional reader that clusters text spans by their x-coordinates. The pipeline keeps whichever finds more complete books. Price columns are decided per table shape, so row numbers, stall numbers and internal codes are never mistaken for prices. Author and imprint names cut off by narrow cells are completed from the PDF's raw text.

**Every price is verified against its source.** After parsing, each book's cover and fair prices must appear on the PDF line of the same ISBN; anything else lands in a per-publisher report shown in the CI run summary. This check is what surfaced the real bugs: a "Mesa" (stall number) column read as the price of 277 books, a letter spilling from the neighbouring cell ("S 44,90") that hid 764 cover prices, and numeric titles such as *1984* and *2666* being taken for internal codes. Each one became a regression test built on the publisher's real PDF.

**No backend on purpose.** The list is the only personal data, and a shopping list fits on the visitor's own device. It lives in `localStorage`, keyed by edition. Sharing encodes the book IDs and an optional name in the URL fragment (`#lista=...`), which browsers never send to the server. The result: no accounts, no database, no personal data collected, no running costs, and nothing for the maintainer to operate.

**Reach without analytics.** To get a sense of how many people use the guide, the published page adds one to a public counter (abacus.jasoncameron.dev) the first time each browser opens it, and remembers in `localStorage` that it already counted. No cookies, no identifiers, nothing from the list; local copies and forks never count. The README badge reads the total without adding to it, and a weekly workflow writes it to `data/visitantes.csv`, so the history survives even if the counter service goes away (it also deletes counters untouched for six months).

**Offline-first for the venue.** A small service worker uses a network-first strategy with the cache as fallback: visitors online always get the latest catalog, and the site keeps working without signal. The 6.5 MB catalog travels as about 1.5 MB gzipped, and revisits only revalidate it.

**A public repository with nothing to leak.** The pipeline needs no keys: the source API is public, CI commits with the ephemeral `GITHUB_TOKEN`, and Pages deploys through OIDC. Some publisher PDFs embed links with third-party access tokens, so the catalog builder strips credential query parameters and drops cover-image URLs. A test fails the build if any tracked file matches a credential pattern, and GitHub secret scanning with push protection is enabled.

**Reproducible output.** PDF library versions are pinned after finding that a newer `pypdf` splits lines differently and truncates author names. The catalog generated on the macOS development machine and on the Linux CI runner is identical.

## Tech stack

- **Pipeline:** Python 3.12, PyMuPDF, pypdf, pytest
- **Site:** plain HTML, CSS and JavaScript with no framework and no build step; Service Worker, Web Share API, Clipboard API
- **Automation and hosting:** GitHub Actions (scheduled data refresh, weekly visitor-count snapshot, tests, deploy) and GitHub Pages

## Tests and quality

- 46 automated tests, run on every push.
- Regression tests run on real price-list PDFs from six publishers, including the layouts that broke earlier versions of the parser.
- Unit tests cover edition detection, API pagination, download caching, table parsing edge cases, URL sanitizing, site assembly and repository hygiene.
- The CI run publishes a verification report: total books, lists that could not be read, and price mismatches by publisher.
- Work is planned in milestones and issues: [project milestones](https://github.com/jvlcapi/guia-nao-oficial-festa-do-livro/milestones?state=all).

## Run it locally

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest -q
.venv/bin/python -m festa_do_livro detect-edition   # which edition would be used
.venv/bin/python -m festa_do_livro build            # download, parse, verify, write data/
.venv/bin/python -m festa_do_livro assemble-site    # build _site/ for GitHub Pages
python3 -m http.server 8765 --bind 127.0.0.1 --directory _site
```

The site is then at http://127.0.0.1:8765. To build another edition: `--edition 28-festa-do-livro-da-usp`.

## Repository layout

```
settings.json                 edition ("auto" or a fixed id) and source site address
src/festa_do_livro/
  fair_site.py                homepage edition detection, event and publisher API client
  price_list_download.py      cached PDF downloads
  pdf_reading.py              tables, raw text and text positions from PDFs
  table_parser.py             table-cell parser
  position_parser.py          positional parser
  catalog_builder.py          cleanup, name repair, URL sanitizing, catalogo.json
  price_verification.py       price checks and the report
  site_assembly.py            folder published to GitHub Pages
site/                         the public site (page, offline worker, icon, manifest)
data/                         generated catalogs, one folder per edition; visitantes.csv with the weekly visitor count
tests/                        unit and regression tests, with real PDF fixtures
.github/workflows/            catalog refresh, site deploy, tests
```

The maintenance runbook for launch day (when the new edition's lists come out) is in the [Portuguese README](README.pt-BR.md#roteiro-do-dia-em-que-a-lista-sair).

## License

Code, site and documentation: [PolyForm Noncommercial 1.0.0](LICENSE.md). You may use, study, modify and share it for noncommercial purposes, as long as every copy keeps the license terms and the credit line:

```
Required Notice: Copyright 2026 João Vitor Lopes Capi (https://github.com/jvlcapi)
```

Commercial use requires written permission from the author.

The book data (titles, authors and prices) comes from the price lists publishers post on the official fair website and is not covered by this license. The PDFs in `tests/fixtures/price_lists/` are those public price lists, kept only to test the parser.
