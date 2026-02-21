"""
Google Sheets helpers using gspread + a service account credential file.
"""

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_client(credentials_path: str) -> gspread.Client:
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return gspread.authorize(creds)


def read_isbns(sheet: gspread.Worksheet, isbn_col: str, start_row: int) -> list[tuple[int, str]]:
    """
    Read all non-empty values from `isbn_col` starting at `start_row`.

    Returns a list of (row_number, isbn_string) tuples.
    """
    col_idx = col_letter_to_index(isbn_col)
    all_values = sheet.col_values(col_idx)  # 1-indexed column, 0-indexed list

    results = []
    for i, val in enumerate(all_values[start_row - 1:], start=start_row):
        val = str(val).strip()
        if val:
            results.append((i, val))
    return results


def read_existing_prices(sheet: gspread.Worksheet, price_col: str, start_row: int) -> set[int]:
    """
    Return the set of row numbers that already have a non-empty price value.
    Used to skip rows on subsequent runs (unless --force is passed).
    """
    col_idx = col_letter_to_index(price_col)
    all_values = sheet.col_values(col_idx)

    filled_rows = set()
    for i, val in enumerate(all_values[start_row - 1:], start=start_row):
        if str(val).strip():
            filled_rows.add(i)
    return filled_rows


def write_cell(sheet: gspread.Worksheet, row: int, col: str, value: str) -> None:
    sheet.update_acell(f"{col}{row}", value)


def col_letter_to_index(letter: str) -> int:
    """Convert a column letter (A, B, … Z, AA, AB …) to a 1-based column index."""
    letter = letter.upper().strip()
    result = 0
    for ch in letter:
        result = result * 26 + (ord(ch) - ord("A") + 1)
    return result
