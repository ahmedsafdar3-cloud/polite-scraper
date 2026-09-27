import requests
from pathlib import Path

url = "https://books.toscrape.com/catalogue/page-1.html"

cache_file = Path("cache/catalogue-page-1.html")

headers = {
    "User-Agent": "FlyRankInternship-A9/1.0"
}

if cache_file.exists():
    html = cache_file.read_text(encoding="utf-8")
    print("CACHE HIT")

else:
    print("FETCH")

    response = requests.get(
        url,
        headers=headers,
        timeout=5
    )

    if response.status_code != 200:
        raise Exception(
            f"Request failed with status {response.status_code}"
        )

    html = response.text
    cache_file.write_text(html, encoding="utf-8")

print(f"Response size: {len(html)} bytes")