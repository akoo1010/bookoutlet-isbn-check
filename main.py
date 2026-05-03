#!/usr/bin/env python3
"""
BookOutlet ISBN Checker
=======================
Reads a list of ISBNs from a Google Sheet, checks bookoutlet.com for each one,
and writes the price (and availability status) back to the sheet.

Usage
-----
    python main.py              # skip rows that already have a price
    python main.py --force      # re-check every row, overwriting existing values

Setup
-----
1. Create a Google Cloud service account and download the JSON key as credentials.json
2. Share your Google Sheet with the service account's email address (Editor access)
3. Fill in the CONFIG section below
4. pip install -r requirements.txt
5. python main.py
"""

import argparse
import sys

from scraper import make_session, search_isbn, sleep_between_requests
from sheets import (
    col_letter_to_index,
    get_client,
    read_existing_prices,
    read_isbns,
    write_cell,
)

# ── CONFIG ────────────────────────────────────────────────────────────────────

CREDENTIALS_FILE = "credentials.json"   # path to your service account key file

SPREADSHEET_ID   = "YOUR_SPREADSHEET_ID_HERE"  # the long ID from your sheet's URL
SHEET_NAME       = "Sheet1"             # exact name of the tab

ISBN_COLUMN      = "F"                  # column that holds the ISBNs
PRICE_COLUMN     = "H"                  # column to write the price into
STATUS_COLUMN    = "G"                  # column to write "Available" / "Not found"

START_ROW        = 2                    # first data row (row 1 is assumed to be a header)

# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check BookOutlet availability for ISBNs stored in a Google Sheet."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-check all rows, overwriting any prices already in the sheet.",
    )
    args = parser.parse_args()

    if SPREADSHEET_ID == "YOUR_SPREADSHEET_ID_HERE":
        print("ERROR: Set SPREADSHEET_ID in the CONFIG section of main.py first.")
        sys.exit(1)

    # ── connect to Google Sheets ──────────────────────────────────────────────
    print("Connecting to Google Sheets…")
    client = get_client(CREDENTIALS_FILE)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

    # ── read ISBNs ────────────────────────────────────────────────────────────
    print("Reading ISBNs from sheet…")
    isbns = read_isbns(sheet, ISBN_COLUMN, START_ROW)

    if not isbns:
        print(f"No ISBNs found in column {ISBN_COLUMN} starting at row {START_ROW}.")
        sys.exit(0)

    # ── filter already-filled rows (unless --force) ───────────────────────────
    filled_rows = set() if args.force else read_existing_prices(sheet, PRICE_COLUMN, START_ROW)
    to_check = [(row, isbn) for row, isbn in isbns if row not in filled_rows]
    skipped = len(isbns) - len(to_check)

    if skipped:
        print(f"Skipping {skipped} row(s) that already have a price (use --force to override).")

    if not to_check:
        print("Nothing new to check.")
        sys.exit(0)

    print(f"Checking {len(to_check)} ISBN(s) on bookoutlet.com…\n")

    # ── pre-compute column indices ────────────────────────────────────────────
    price_col_idx  = col_letter_to_index(PRICE_COLUMN)
    status_col_idx = col_letter_to_index(STATUS_COLUMN) if STATUS_COLUMN else None

    # ── main loop ─────────────────────────────────────────────────────────────
    session = make_session()
    errors = []

    for i, (row, isbn) in enumerate(to_check, 1):
        print(f"[{i}/{len(to_check)}] ISBN {isbn} … ", end="", flush=True)

        result = search_isbn(isbn, session)

        error   = result.get("error")
        is_real_error = error and not error.startswith("_")  # internal codes start with _

        if is_real_error:
            price_val  = f"Error: {error}"
            status_val = "Error"
            print(f"ERROR — {error}")
            errors.append((isbn, error))

        elif result["available"]:
            price_val  = result["price"] or "N/A"
            status_val = "Available"
            title_hint = f" ({result['title'][:50]})" if result.get("title") else ""
            print(f"Available — {price_val}{title_hint}")

        else:
            price_val  = ""
            status_val = "Not found"
            print("Not found")

        # Write back to the sheet
        sheet.update_cell(row, price_col_idx, price_val)
        if status_col_idx:
            sheet.update_cell(row, status_col_idx, status_val)

        # Polite delay between requests (skip after the last one)
        if i < len(to_check):
            sleep_between_requests()

    # ── summary ───────────────────────────────────────────────────────────────
    print(f"\nDone. Checked {len(to_check)} ISBN(s).", end="")
    if errors:
        print(f" {len(errors)} error(s):")
        for isbn, msg in errors:
            print(f"  • {isbn}: {msg}")
    else:
        print()


if __name__ == "__main__":
    main()
