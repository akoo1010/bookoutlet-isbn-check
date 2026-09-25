"""
BookOutlet scraper.

bookoutlet.com is a Shopify store. Product URLs include a title slug
(/products/hamilton-the-revolution-9781455539741b), so they can't be built from
an ISBN. Instead each lookup:

  1. Searches the store's predictive search (/search/suggest.json) on the
     variant barcode and SKU fields, which hold the ISBN-13
     (barcode "9781455539741", SKU "9781455539741B").
  2. Fetches /products/{handle}.js for the matching product and reads the
     variants whose barcode or SKU is that ISBN.

  - no matching product              → not listed
  - matching variants, none available → listed but out of stock
  - any matching variant available    → available, returns the lowest price

Uses cloudscraper to handle Cloudflare's JS challenge automatically.
"""

import random
import re
import time

import cloudscraper

BASE_URL = "https://www.bookoutlet.com"
SEARCH_URL = BASE_URL + "/search/suggest.json"
PRODUCT_URL = BASE_URL + "/products/{}.js"

MAX_CANDIDATES = 3  # product pages fetched per ISBN when search returns several


class LookupFailed(Exception):
    pass


def make_session() -> cloudscraper.CloudScraper:
    return cloudscraper.create_scraper()


def search_isbn(isbn: str, session: cloudscraper.CloudScraper) -> dict:
    """
    Look up a book by ISBN on bookoutlet.com. Never raises.

    Returns a dict:
        available (bool)  – True if in stock
        price     (str)   – e.g. "$9.99", or None
        title     (str)   – book title, or None
        error     (str)   – error message, or None on success
    """
    isbn13 = normalize_isbn(isbn)
    if isbn13 is None:
        return _err(f"Invalid ISBN: {isbn}")

    try:
        return _lookup(isbn13, session)
    except LookupFailed as e:
        return _err(str(e))
    except Exception as e:  # network errors, unexpected JSON: report the row, don't stop the run
        return _err(f"{type(e).__name__}: {e}")


def _lookup(isbn13: str, session: cloudscraper.CloudScraper) -> dict:
    results = _get_json(session, SEARCH_URL, params={
        "q": isbn13,
        "resources[type]": "product",
        "resources[limit]": 10,
        "resources[options][unavailable_products]": "show",
        "resources[options][fields]": "variants.barcode,variants.sku",
    })
    if results is None:
        raise LookupFailed("Search returned HTTP 404")

    handles = [p["handle"] for p in results["resources"]["results"]["products"]]
    handles.sort(key=lambda h: isbn13 not in h)  # handles usually end in "-{isbn}b"

    for handle in handles[:MAX_CANDIDATES]:
        product = _get_json(session, PRODUCT_URL.format(handle))
        if product is None:
            continue
        variants = [v for v in product["variants"] if _variant_matches(v, isbn13)]
        if variants:
            return _summarize(product, variants)

    return {"available": False, "price": None, "title": None, "error": None}


def _summarize(product: dict, variants: list[dict]) -> dict:
    title = str(product["title"]) if product.get("title") else None
    in_stock = [v for v in variants if v.get("available") is True]
    if not in_stock:
        return {"available": False, "price": None, "title": title, "error": None}

    cents = [v["price"] for v in in_stock if isinstance(v.get("price"), int)]
    price_str = f"${min(cents) / 100:.2f}" if cents else None
    return {"available": True, "price": price_str, "title": title, "error": None}


def _variant_matches(variant: dict, isbn13: str) -> bool:
    barcode = str(variant.get("barcode") or "").strip()
    sku = str(variant.get("sku") or "").strip().upper()
    return barcode == isbn13 or sku.startswith(isbn13)


def _get_json(session: cloudscraper.CloudScraper, url: str, params: dict | None = None):
    """GET a JSON endpoint. Returns None on 404; raises LookupFailed on other failures."""
    resp = session.get(url, params=params, timeout=15)
    if resp.status_code == 404:
        return None
    if not resp.ok:
        raise LookupFailed(f"HTTP {resp.status_code}")
    try:
        return resp.json()
    except ValueError:
        raise LookupFailed("Response was not JSON (blocked by a bot check?)")


def normalize_isbn(raw: str) -> str | None:
    """
    Return the ISBN-13 for an ISBN-10 or ISBN-13, or None if `raw` isn't a valid ISBN.

    Ignores dashes, spaces and Goodreads' ="..." wrapper, and restores leading
    zeros lost when an ISBN-10 was stored as a number.
    """
    s = re.sub(r"[^0-9X]", "", str(raw).upper())
    if s.isdigit() and 7 <= len(s) <= 9:
        s = s.zfill(10)

    if re.fullmatch(r"\d{9}[\dX]", s):
        total = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(s))
        if total % 11:
            return None
        s = "978" + s[:9]
        return s + _isbn13_check_digit(s)

    if re.fullmatch(r"97[89]\d{10}", s) and _isbn13_check_digit(s[:12]) == s[12]:
        return s
    return None


def _isbn13_check_digit(first12: str) -> str:
    total = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(first12))
    return str(-total % 10)


def sleep_between_requests(min_s: float = 1.0, max_s: float = 2.5) -> None:
    time.sleep(random.uniform(min_s, max_s))


def _err(message: str) -> dict:
    return {"available": False, "price": None, "title": None, "error": message}


if __name__ == "__main__":
    # Quick check without touching the sheet: python scraper.py 9781455539741 0446676217
    import sys

    session = make_session()
    for arg in sys.argv[1:]:
        print(arg, search_isbn(arg, session))
