# Polite Scraper

A Python scraper for [Books to Scrape](https://books.toscrape.com/), a site designed for scraping practice. It collects the first three catalogue pages, visits book detail pages, normalizes prices, validates records with Pydantic, and writes structured JSON.

## Setup and usage

Python 3.11 is recommended. Run from the repository root:

```powershell
git clone https://github.com/ahmedsafdar3-cloud/polite-scraper.git
cd polite-scraper
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src/main.py
```

## Outputs

| File | Contents |
| --- | --- |
| `output/books.json` | Deduplicated, validated book records |
| `output/errors.json` | Fetch failures and validation errors |
| `output/run-report.json` | Counts, timestamps, cache hits, and duration |

Each book includes title, product URL, raw price, numeric GBP price, availability, rating, description, source page, and fetch timestamp. The checked-in output is an example run; rerunning overwrites it.

## Request behavior

The scraper uses a descriptive user agent, a five-second request timeout, at most two attempts, and a half-second delay after successful network fetches. Cached HTML is reused from `cache/`. HTTP 403/404 responses are reported without retry; timeouts and server errors can be retried once. Cache entries have no expiry; remove `cache/` to fetch fresh content.

To exercise failure reporting deliberately:

```powershell
python src/main.py --inject-failure
```

This adds a known missing book URL. Normal runs do not inject errors. The scraper targets only the configured practice site; it does not implement automatic robots.txt enforcement, login, JavaScript rendering, or distributed crawling.

## Verification

A normal cached run produced 60 valid records, zero validation errors, zero failed pages, and 63 cache hits. `run-report.json` records the actual counts for each execution. This is a bounded demonstration rather than a general-purpose crawler.

## Files

- `src/main.py`: catalogue discovery, detail parsing, validation, and reporting.
- `requirements.txt`: Requests, Beautiful Soup, and Pydantic dependencies.
- `output/`: example records and reports.

The repository currently has no open-source license.
