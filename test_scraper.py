"""
Tests for scraper.py. No network access: a fake session serves trimmed copies of
real bookoutlet.com responses. Run with: python -m unittest
"""

import unittest

from scraper import normalize_isbn, search_isbn

HANDLE = "hamilton-the-revolution-9781455539741b"

# /search/suggest.json?q=9781455539741&resources[options][fields]=variants.barcode,variants.sku
SEARCH_HIT = {"resources": {"results": {"products": [
    {"available": True, "handle": HANDLE, "price": "20.49", "title": "Hamilton: The Revolution", "variants": []},
]}}}
SEARCH_MISS = {"resources": {"results": {"products": []}}}

# /products/hamilton-the-revolution-9781455539741b.js
PRODUCT = {
    "title": "Hamilton: The Revolution",
    "handle": HANDLE,
    "available": True,
    "price": 2049,
    "variants": [{
        "title": "Bargain",
        "sku": "9781455539741B",
        "barcode": "9781455539741",
        "available": True,
        "price": 2049,
    }],
}


class FakeResponse:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self.ok = status_code < 400
        self._body = body
        self.text = text

    def json(self):
        if self._body is None:
            raise ValueError("not JSON")
        return self._body


class FakeSession:
    """Serves responses keyed by URL path; unknown paths return 404."""

    def __init__(self, routes):
        self.routes = routes
        self.requested = []

    def get(self, url, params=None, timeout=None):
        path = url.removeprefix("https://www.bookoutlet.com")
        self.requested.append(path)
        return self.routes.get(path, FakeResponse(404))


def session_for(search, product=None):
    routes = {"/search/suggest.json": search}
    if product is not None:
        routes[f"/products/{HANDLE}.js"] = product
    return FakeSession(routes)


class NormalizeIsbnTest(unittest.TestCase):
    def test_isbn13_passes_through(self):
        self.assertEqual(normalize_isbn("978-1-4555-3974-1"), "9781455539741")

    def test_isbn10_is_converted(self):
        self.assertEqual(normalize_isbn("1455539740"), "9781455539741")
        self.assertEqual(normalize_isbn("0-8044-2957-x"), "9780804429573")

    def test_goodreads_wrapper_and_lost_leading_zero(self):
        self.assertEqual(normalize_isbn('="9780439023481"'), "9780439023481")
        self.assertEqual(normalize_isbn("439023483"), "9780439023481")

    def test_invalid_values(self):
        for raw in ["9780439023482", "0439023484", "N/A", "", "12345"]:
            with self.subTest(raw=raw):
                self.assertIsNone(normalize_isbn(raw))


class SearchIsbnTest(unittest.TestCase):
    def test_available(self):
        session = session_for(FakeResponse(body=SEARCH_HIT), FakeResponse(body=PRODUCT))
        result = search_isbn("978-1-4555-3974-1", session)
        self.assertEqual(result, {"available": True, "price": "$20.49",
                                  "title": "Hamilton: The Revolution", "error": None})
        self.assertEqual(session.requested, ["/search/suggest.json", f"/products/{HANDLE}.js"])

    def test_not_listed_makes_one_request(self):
        session = session_for(FakeResponse(body=SEARCH_MISS))
        result = search_isbn("9781455539741", session)
        self.assertEqual(result, {"available": False, "price": None, "title": None, "error": None})
        self.assertEqual(len(session.requested), 1)

    def test_sold_out(self):
        sold_out = {**PRODUCT, "variants": [{**PRODUCT["variants"][0], "available": False}]}
        result = search_isbn("9781455539741", session_for(FakeResponse(body=SEARCH_HIT), FakeResponse(body=sold_out)))
        self.assertFalse(result["available"])
        self.assertEqual(result["title"], "Hamilton: The Revolution")
        self.assertIsNone(result["error"])

    def test_lowest_available_price_wins(self):
        used = {**PRODUCT["variants"][0], "title": "Used - Good", "sku": "9781455539741U", "price": 1599}
        sold_out_bargain = {**PRODUCT["variants"][0], "available": False, "price": 999}
        product = {**PRODUCT, "variants": [sold_out_bargain, used]}
        result = search_isbn("9781455539741", session_for(FakeResponse(body=SEARCH_HIT), FakeResponse(body=product)))
        self.assertEqual(result["price"], "$15.99")

    def test_search_hit_for_other_isbn_is_not_found(self):
        other = {**PRODUCT, "variants": [{**PRODUCT["variants"][0], "barcode": "9780000000002", "sku": "9780000000002B"}]}
        result = search_isbn("9781455539741", session_for(FakeResponse(body=SEARCH_HIT), FakeResponse(body=other)))
        self.assertEqual(result, {"available": False, "price": None, "title": None, "error": None})

    def test_http_error_is_reported(self):
        result = search_isbn("9781455539741", session_for(FakeResponse(429)))
        self.assertEqual(result["error"], "HTTP 429")

    def test_non_json_response_is_reported(self):
        result = search_isbn("9781455539741", session_for(FakeResponse(200, text="<html>Just a moment...</html>")))
        self.assertIn("not JSON", result["error"])

    def test_unexpected_json_shape_is_reported_not_raised(self):
        result = search_isbn("9781455539741", session_for(FakeResponse(body={"unexpected": True})))
        self.assertTrue(result["error"])

    def test_invalid_isbn_makes_no_request(self):
        session = session_for(FakeResponse(body=SEARCH_HIT))
        result = search_isbn("not-an-isbn", session)
        self.assertEqual(result["error"], "Invalid ISBN: not-an-isbn")
        self.assertEqual(session.requested, [])


if __name__ == "__main__":
    unittest.main()
