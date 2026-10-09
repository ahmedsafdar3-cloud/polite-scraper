import argparse
import json
import time
import requests

from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, HttpUrl, ValidationError


# --------------------------------------------------
# CONFIG
# --------------------------------------------------

START_URL = "https://books.toscrape.com/catalogue/page-1.html"

HEADERS = {
    "User-Agent": "PoliteScraper/1.0"
}

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

BOOKS_FILE = OUTPUT_DIR / "books.json"
ERRORS_FILE = OUTPUT_DIR / "errors.json"
REPORT_FILE = OUTPUT_DIR / "run-report.json"

parser = argparse.ArgumentParser(description="Collect and validate the first three Books to Scrape catalogue pages.")
parser.add_argument("--inject-failure", action="store_true", help="Include a deliberate missing URL to exercise error reporting")
args = parser.parse_args()
INJECT_BROKEN_URL = args.inject_failure


# --------------------------------------------------
# RUN STATISTICS
# --------------------------------------------------

run_started = datetime.now(timezone.utc)
run_start_timer = time.perf_counter()

stats = {
    "pages_fetched": 0,
    "cache_hits": 0,
    "failed_pages": 0,
}


# --------------------------------------------------
# PYDANTIC SCHEMA
# --------------------------------------------------

class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: Optional[str]
    source_page: HttpUrl
    fetched_at: str


# --------------------------------------------------
# FETCH + CACHE + RETRY
# --------------------------------------------------

def fetch_page(page_url, cache_path):
    cache_path = Path(cache_path)

    cache_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Use cached HTML if available
    if cache_path.exists():
        stats["cache_hits"] += 1

        print(
            f"CACHE HIT: {cache_path.name}"
        )

        return cache_path.read_text(
            encoding="utf-8"
        )

    max_attempts = 2

    for attempt in range(1, max_attempts + 1):

        try:
            print(
                f"FETCH attempt={attempt}: {page_url}"
            )

            response = requests.get(
                page_url,
                headers=HEADERS,
                timeout=5
            )

            stats["pages_fetched"] += 1


            # --------------------------------------
            # SUCCESS
            # --------------------------------------

            if response.status_code == 200:

                response.encoding = "utf-8"

                html = response.text

                cache_path.write_text(
                    html,
                    encoding="utf-8"
                )

                time.sleep(0.5)

                return html


            # --------------------------------------
            # DO NOT RETRY 403 OR 404
            # --------------------------------------

            if response.status_code in (
                403,
                404
            ):

                raise Exception(
                    f"HTTP {response.status_code}"
                )


            # --------------------------------------
            # RETRY 5xx ONCE
            # --------------------------------------

            if 500 <= response.status_code <= 599:

                if attempt < max_attempts:

                    print(
                        f"Server error "
                        f"{response.status_code}. "
                        f"Retrying once..."
                    )

                    time.sleep(1)

                    continue

                raise Exception(
                    f"HTTP {response.status_code}"
                )


            # --------------------------------------
            # OTHER HTTP ERRORS
            # --------------------------------------

            raise Exception(
                f"HTTP {response.status_code}"
            )


        # ------------------------------------------
        # RETRY TIMEOUT ONCE
        # ------------------------------------------

        except requests.Timeout:

            if attempt < max_attempts:

                print(
                    "Request timed out. "
                    "Retrying once..."
                )

                time.sleep(1)

                continue

            raise Exception(
                "Request timed out after retry"
            )


        # ------------------------------------------
        # OTHER NETWORK ERRORS
        # ------------------------------------------

        except requests.RequestException as error:

            raise Exception(
                f"Network error: {error}"
            )


# --------------------------------------------------
# DISCOVER FIRST 3 CATALOGUE PAGES
# --------------------------------------------------

catalogue_pages = 0
current_page_url = START_URL
discovered_books = []


while current_page_url and catalogue_pages < 3:

    catalogue_pages += 1

    catalogue_cache = (
        f"cache/catalogue-page-{catalogue_pages}.html"
    )

    html = fetch_page(
        current_page_url,
        catalogue_cache
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    for book in soup.select(
        "article.product_pod h3 a"
    ):

        href = book.get("href")

        product_url = urljoin(
            current_page_url,
            href
        )

        discovered_books.append({
            "product_url": product_url,
            "source_page": current_page_url
        })

    next_link = soup.select_one(
        "li.next a"
    )

    if next_link and catalogue_pages < 3:

        current_page_url = urljoin(
            current_page_url,
            next_link.get("href")
        )

    else:
        current_page_url = None


# --------------------------------------------------
# REMOVE DUPLICATES
# --------------------------------------------------

unique_books = {}

for book in discovered_books:

    product_url = book["product_url"]

    if product_url not in unique_books:

        unique_books[
            product_url
        ] = book


books_to_scrape = list(
    unique_books.values()
)


print(
    f"catalogue_pages={catalogue_pages}"
)

print(
    f"discovered={len(discovered_books)}"
)

print(
    f"unique_urls={len(books_to_scrape)}"
)


# --------------------------------------------------
# OPTIONAL FAILURE INJECTION
# --------------------------------------------------

if INJECT_BROKEN_URL:

    books_to_scrape.append({
        "product_url":
            "https://books.toscrape.com/catalogue/"
            "this-book-does-not-exist-999999/"
            "index.html",

        "source_page":
            START_URL
    })


# --------------------------------------------------
# EXTRACT DETAIL PAGES
# --------------------------------------------------

raw_records = []
failed_pages = []


for book in books_to_scrape:

    product_url = book["product_url"]
    source_page = book["source_page"]

    try:

        parsed_url = urlparse(
            product_url
        )

        product_slug = Path(
            parsed_url.path
        ).parent.name

        detail_cache = (
            f"cache/details/"
            f"{product_slug}.html"
        )

        html = fetch_page(
            product_url,
            detail_cache
        )

        soup = BeautifulSoup(
            html,
            "html.parser"
        )


        # ------------------------------------------
        # TITLE
        # ------------------------------------------

        title_element = soup.select_one(
            "div.product_main h1"
        )

        title = (
            title_element.get_text(
                strip=True
            )
            if title_element
            else None
        )


        # ------------------------------------------
        # PRICE
        # ------------------------------------------

        price_element = soup.select_one(
            "div.product_main p.price_color"
        )

        price_text = (
            price_element.get_text(
                strip=True
            )
            if price_element
            else None
        )


        # ------------------------------------------
        # AVAILABILITY
        # ------------------------------------------

        availability_element = soup.select_one(
            "div.product_main p.availability"
        )

        availability_text = (
            availability_element.get_text(
                " ",
                strip=True
            )
            if availability_element
            else None
        )


        # ------------------------------------------
        # RATING
        # ------------------------------------------

        rating_element = soup.select_one(
            "div.product_main p.star-rating"
        )

        rating_text = None

        if rating_element:

            rating_classes = rating_element.get(
                "class",
                []
            )

            for rating_class in rating_classes:

                if rating_class != "star-rating":

                    rating_text = rating_class

                    break


        # ------------------------------------------
        # DESCRIPTION
        # ------------------------------------------

        description_element = soup.select_one(
            "#product_description + p"
        )

        description = (
            description_element.get_text(
                " ",
                strip=True
            )
            if description_element
            else None
        )


        # ------------------------------------------
        # FETCH TIME
        # ------------------------------------------

        fetched_at = datetime.now(
            timezone.utc
        ).isoformat()


        # ------------------------------------------
        # RAW RECORD
        # ------------------------------------------

        raw_record = {
            "title": title,
            "product_url": product_url,
            "price_text": price_text,
            "availability_text":
                availability_text,
            "rating_text": rating_text,
            "description": description,
            "source_page": source_page,
            "fetched_at": fetched_at
        }

        raw_records.append(
            raw_record
        )


    # ----------------------------------------------
    # ONE BAD PAGE DOES NOT KILL THE RUN
    # ----------------------------------------------

    except Exception as error:

        stats["failed_pages"] += 1

        failed_page = {
            "url": product_url,
            "reason": str(error)
        }

        failed_pages.append(
            failed_page
        )

        print(
            f"FAILED: {product_url}"
        )

        print(
            f"Reason: {error}"
        )

        continue


print(
    f"detail_pages={len(raw_records)}"
)


# --------------------------------------------------
# NORMALIZE + VALIDATE
# --------------------------------------------------

valid_records = []
validation_errors = []


for raw_record in raw_records:

    try:

        price_text = raw_record[
            "price_text"
        ]

        price_gbp = float(
            price_text
            .replace("£", "")
            .strip()
        )


        normalized_record = {
            **raw_record,
            "price_gbp": price_gbp
        }


        validated = BookRecord(
            **normalized_record
        )


        valid_records.append(
            validated.model_dump(
                mode="json"
            )
        )


    except (
        ValidationError,
        ValueError,
        TypeError,
        AttributeError
    ) as error:

        validation_errors.append({
            "record": raw_record,
            "reason": str(error)
        })


# --------------------------------------------------
# DEDUPLICATE BY CANONICAL PRODUCT URL
# --------------------------------------------------

deduplicated_records = {}


for record in valid_records:

    product_url = record[
        "product_url"
    ]

    deduplicated_records[
        product_url
    ] = record


final_records = list(
    deduplicated_records.values()
)


# --------------------------------------------------
# BUILD ERRORS.JSON
# --------------------------------------------------

all_errors = []


for error in validation_errors:

    all_errors.append({
        "type": "validation_error",
        **error
    })


for failed_page in failed_pages:

    all_errors.append({
        "type": "failed_page",
        **failed_page
    })


# --------------------------------------------------
# WRITE BOOKS.JSON
# --------------------------------------------------

BOOKS_FILE.write_text(
    json.dumps(
        final_records,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# --------------------------------------------------
# WRITE ERRORS.JSON
# --------------------------------------------------

ERRORS_FILE.write_text(
    json.dumps(
        all_errors,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# --------------------------------------------------
# RUN REPORT
# --------------------------------------------------

run_finished = datetime.now(
    timezone.utc
)

duration_seconds = (
    time.perf_counter()
    - run_start_timer
)


run_report = {
    "started_at":
        run_started.isoformat(),

    "finished_at":
        run_finished.isoformat(),

    "duration_seconds":
        round(
            duration_seconds,
            2
        ),

    "catalogue_pages":
        catalogue_pages,

    "discovered":
        len(discovered_books),

    "unique_urls":
        len(unique_books),

    "pages_fetched":
        stats["pages_fetched"],

    "cache_hits":
        stats["cache_hits"],

    "valid_records":
        len(final_records),

    "invalid_records":
        len(validation_errors),

    "failed_pages":
        stats["failed_pages"]
}


REPORT_FILE.write_text(
    json.dumps(
        run_report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# --------------------------------------------------
# RUN SUMMARY
# --------------------------------------------------

print("\nRUN COMPLETE")

print(
    f"valid_records="
    f"{len(final_records)}"
)

print(
    f"invalid_records="
    f"{len(validation_errors)}"
)

print(
    f"failed_pages="
    f"{stats['failed_pages']}"
)

print(
    f"cache_hits="
    f"{stats['cache_hits']}"
)

print(
    f"pages_fetched="
    f"{stats['pages_fetched']}"
)

print(
    f"duration_seconds="
    f"{round(duration_seconds, 2)}"
)

print(
    f"books_file={BOOKS_FILE}"
)

print(
    f"errors_file={ERRORS_FILE}"
)

print(
    f"report_file={REPORT_FILE}"
)