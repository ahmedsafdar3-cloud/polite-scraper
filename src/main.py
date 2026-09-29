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
    "User-Agent": "FlyRankInternship-A9/1.0"
}

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

BOOKS_FILE = OUTPUT_DIR / "books.json"
ERRORS_FILE = OUTPUT_DIR / "errors.json"


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
# FETCH + CACHE
# --------------------------------------------------

def fetch_page(page_url, cache_path):
    cache_path = Path(cache_path)

    cache_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if cache_path.exists():
        print(f"CACHE HIT: {cache_path.name}")

        return cache_path.read_text(
            encoding="utf-8"
        )

    print(f"FETCH: {page_url}")

    response = requests.get(
        page_url,
        headers=HEADERS,
        timeout=5
    )

    if response.status_code != 200:
        raise Exception(
            f"Request failed with status {response.status_code}"
        )

    response.encoding = "utf-8"

    html = response.text

    cache_path.write_text(
        html,
        encoding="utf-8"
    )

    time.sleep(0.5)

    return html


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
# REMOVE DUPLICATE BOOK URLS
# --------------------------------------------------

unique_books = {}

for book in discovered_books:

    product_url = book["product_url"]

    if product_url not in unique_books:
        unique_books[product_url] = book

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
# EXTRACT RAW RECORDS
# --------------------------------------------------

raw_records = []

for book in books_to_scrape:

    product_url = book["product_url"]
    source_page = book["source_page"]

    parsed_url = urlparse(product_url)

    product_slug = Path(
        parsed_url.path
    ).parent.name

    detail_cache = (
        f"cache/details/{product_slug}.html"
    )

    html = fetch_page(
        product_url,
        detail_cache
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )


    # TITLE

    title_element = soup.select_one(
        "div.product_main h1"
    )

    title = (
        title_element.get_text(strip=True)
        if title_element
        else None
    )


    # PRICE

    price_element = soup.select_one(
        "div.product_main p.price_color"
    )

    price_text = (
        price_element.get_text(strip=True)
        if price_element
        else None
    )


    # AVAILABILITY

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


    # RATING

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


    # DESCRIPTION

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


    # FETCH TIME

    fetched_at = datetime.now(
        timezone.utc
    ).isoformat()


    raw_record = {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at
    }

    raw_records.append(
        raw_record
    )


print(
    f"detail_pages={len(raw_records)}"
)


# --------------------------------------------------
# NORMALIZE + VALIDATE
# --------------------------------------------------

valid_records = []
errors = []

for raw_record in raw_records:

    try:
        # Convert "£51.77" -> 51.77
        price_text = raw_record["price_text"]

        price_gbp = float(
            price_text.replace("£", "").strip()
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

        errors.append({
            "record": raw_record,
            "reason": str(error)
        })


# --------------------------------------------------
# REMOVE DUPLICATES AGAIN BY CANONICAL PRODUCT URL
# --------------------------------------------------

deduplicated_records = {}

for record in valid_records:

    product_url = record["product_url"]

    deduplicated_records[
        product_url
    ] = record


final_records = list(
    deduplicated_records.values()
)


# --------------------------------------------------
# WRITE JSON OUTPUT
# --------------------------------------------------

BOOKS_FILE.write_text(
    json.dumps(
        final_records,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

ERRORS_FILE.write_text(
    json.dumps(
        errors,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# --------------------------------------------------
# STAGE 4 CHECKPOINT
# --------------------------------------------------

print(
    f"valid_records={len(final_records)}"
)

print(
    f"invalid_records={len(errors)}"
)

print(
    f"books_file={BOOKS_FILE}"
)

print(
    f"errors_file={ERRORS_FILE}"
)