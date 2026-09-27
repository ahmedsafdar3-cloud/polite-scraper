import time
import requests

from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin


url = "https://books.toscrape.com/catalogue/page-1.html"

headers = {
    "User-Agent": "FlyRankInternship-A9/1.0"
}


def fetch_page(page_url, cache_path):
    cache_path = Path(cache_path)

    if cache_path.exists():
        print(f"CACHE HIT: {cache_path.name}")
        return cache_path.read_text(encoding="utf-8")

    print(f"FETCH: {page_url}")

    response = requests.get(
        page_url,
        headers=headers,
        timeout=5
    )

    if response.status_code != 200:
        raise Exception(
            f"Request failed with status {response.status_code}"
        )

    html = response.text

    cache_path.write_text(
        html,
        encoding="utf-8"
    )

    time.sleep(0.5)

    return html


# -------------------------
# PAGE 1
# -------------------------

html = fetch_page(
    url,
    "cache/catalogue-page-1.html"
)

print(f"Response size: {len(html)} bytes")

soup = BeautifulSoup(
    html,
    "html.parser"
)

book_links = []

for book in soup.select("article.product_pod h3 a"):
    href = book.get("href")

    absolute_url = urljoin(
        url,
        href
    )

    book_links.append(
        absolute_url
    )

print(
    f"discovered_on_page_1={len(book_links)}"
)


# -------------------------
# PAGE 2 AND PAGE 3
# -------------------------

catalogue_pages = 1

all_book_links = book_links.copy()

next_link = soup.select_one(
    "li.next a"
)

while next_link and catalogue_pages < 3:

    next_href = next_link.get("href")

    next_page_url = urljoin(
        url,
        next_href
    )

    next_page_number = catalogue_pages + 1

    cache_path = (
        f"cache/catalogue-page-{next_page_number}.html"
    )

    html = fetch_page(
        next_page_url,
        cache_path
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    for book in soup.select(
        "article.product_pod h3 a"
    ):

        href = book.get("href")

        absolute_url = urljoin(
            next_page_url,
            href
        )

        all_book_links.append(
            absolute_url
        )

    catalogue_pages += 1

    next_link = soup.select_one(
        "li.next a"
    )


# -------------------------
# REMOVE DUPLICATES
# -------------------------

unique_book_links = list(
    set(all_book_links)
)


# -------------------------
# FINAL SUMMARY
# -------------------------

print(
    f"catalogue_pages={catalogue_pages}"
)

print(
    f"discovered={len(all_book_links)}"
)

print(
    f"unique_urls={len(unique_book_links)}"
)