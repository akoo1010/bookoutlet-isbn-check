"""
BookOutlet scraper.

Uses a direct product URL lookup instead of search:
  https://www.bookoutlet.com/products/{ISBN}B

  - 404  → book not listed on the site
  - 200, inventory == 0 → listed but out of stock
  - 200, inventory  > 0 → available, returns sale price

Uses cloudscraper to handle Cloudflare's JS challenge automatically.
"""

import json
import random
import time

import cloudscraper
from bs4 import BeautifulSoup

PRODUCT_URL = "https://www.bookoutlet.com/products/{}B"


def make_session() -> cloudscraper.CloudScraper:
    return cloudscraper.create_scraper()


def search_isbn(isbn: str, session: cloudscraper.CloudScraper) -> dict:
    """
    Look up a book by ISBN on bookoutlet.com.

    Returns a dict:
        available (bool)  – True if in stock
        price     (str)   – e.g. "$9.99", or None
        title     (str)   – book title, or None
        error     (str)   – error message, or None on success
    """
    isbn = str(isbn).strip().replace("-", "").replace(" ", "")
    url = PRODUCT_URL.format(isbn)

    try:
        resp = session.get(url, timeout=15)
    except Exception as e:
        return _err(str(e))

    if resp.status_code == 404:
        return {"available": False, "price": None, "title": None, "error": None}

    if not resp.ok:
        return _err(f"HTTP {resp.status_code}")

    return _parse_product_page(resp.text)


def _parse_product_page(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return _err("Could not find product data on page")

    try:
        data = json.loads(tag.string)
        details = data["props"]["pageProps"]["details"]
    except (json.JSONDecodeError, KeyError):
        return _err("Unexpected page data structure")

    inventory = details.get("inventory", 0) or 0
    title = details.get("title")
    sale_price = details.get("actual_price_usd") or details.get("sale_price_usd")

    if inventory == 0:
        return {"available": False, "price": None, "title": title, "error": None}

    price_str = f"${sale_price:.2f}" if sale_price is not None else "N/A"
    return {"available": True, "price": price_str, "title": title, "error": None}


def sleep_between_requests(min_s: float = 1.0, max_s: float = 2.5) -> None:
    time.sleep(random.uniform(min_s, max_s))


def _err(message: str) -> dict:
    return {"available": False, "price": None, "title": None, "error": message}
