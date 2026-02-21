# BookOutlet ISBN Checker

Reads a list of ISBNs from a Google Sheet, checks [bookoutlet.com](https://www.bookoutlet.com) for availability and price, and writes the results back to the sheet.

## How it works

For each ISBN the script hits `bookoutlet.com/products/{ISBN}B` directly:

- **404** → book is not listed on the site → writes "Not found"
- **200, inventory = 0** → listed but out of stock → writes "Not found"
- **200, inventory > 0** → in stock → writes the sale price and "Available"

Results are written to a configurable status column and price column. On subsequent runs, rows that already have a price are skipped unless `--force` is passed.

## Prerequisites

- Python 3.10+
- A Google Cloud **service account** with the Sheets and Drive APIs enabled
- The service account's JSON key saved as `credentials.json` in the project root
- Your Google Sheet shared with the service account's email address (Editor access)

## Setup

1. **Clone the repo and create a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Add your credentials**

   Place your service account JSON key at `credentials.json` in the project root.

4. **Configure `main.py`**

   Edit the `CONFIG` section near the top of `main.py`:

   ```python
   CREDENTIALS_FILE = "credentials.json"   # path to your service account key
   SPREADSHEET_ID   = "..."                # the long ID from your sheet's URL
   SHEET_NAME       = "Sheet1"             # exact name of the tab
   ISBN_COLUMN      = "F"                  # column containing ISBNs
   PRICE_COLUMN     = "H"                  # column to write prices into
   STATUS_COLUMN    = "G"                  # column to write "Available" / "Not found"
   START_ROW        = 2                    # first data row (row 1 is the header)
   ```

## Usage

```bash
# Skip rows that already have a price (default)
python main.py

# Re-check every row, overwriting existing values
python main.py --force
```

## Project structure

```
.
├── main.py          # Entry point and configuration
├── scraper.py       # BookOutlet HTTP scraping logic
├── sheets.py        # Google Sheets read/write helpers
├── credentials.json # Service account key (not committed)
└── requirements.txt # Python dependencies
```

## Dependencies

| Package | Purpose |
|---|---|
| `gspread` | Google Sheets API client |
| `google-auth` | Service account authentication |
| `cloudscraper` | Handles Cloudflare JS challenges |
| `beautifulsoup4` + `lxml` | HTML parsing |
