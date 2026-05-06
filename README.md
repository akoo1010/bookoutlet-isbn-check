# BookOutlet ISBN Checker

Reads a list of ISBNs from a Google Sheet, checks [bookoutlet.com](https://www.bookoutlet.com) for availability and price, and writes the results back to the sheet. And where's a great source for ISBNs? [Goodreads export](https://help.goodreads.com/s/article/How-do-I-import-or-export-my-books-1553870934590) 

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
- A Google Sheet to store the data, shared with the service account's email address (Editor access)

## Setup

### 1. Google Cloud Setup (Credentials)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new Project (or select an existing one).
3. Navigate to **APIs & Services > Library** and enable both the **Google Sheets API** and **Google Drive API**.
4. Go to **APIs & Services > Credentials**.
5. Click **Create Credentials > Service Account**. Fill in the details and create the account.
6. Once created, click on the new service account in the list, go to the **Keys** tab, and click **Add Key > Create new key**.
7. Choose **JSON** and download the file. 
8. Rename the downloaded file to `credentials.json` and place it in the root folder of this project.

### 2. Google Sheet Setup

1. Create a new [Google Sheet](https://sheets.google.com) (or use an existing one, like an exported Goodreads library).
2. Open your `credentials.json` file and find the `client_email` address.
3. Click the **Share** button in the top right corner of your Google Sheet.
4. Paste the `client_email` address and give it **Editor** access. This allows the script to read and write to your sheet.
5. Get your `SPREADSHEET_ID`. Look at your Google Sheet's URL:
   `https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID_IS_HERE/edit`
   Copy the long string of letters and numbers (the part between `/d/` and `/edit`).

### 3. Local Project Setup

1. **Clone the repo and create a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure `main.py`**

   Edit the `CONFIG` section near the top of `main.py`:

   ```python
   CREDENTIALS_FILE = "credentials.json"   # path to your service account key
   SPREADSHEET_ID   = "YOUR_SPREADSHEET_ID_IS_HERE" # the long ID from your sheet's URL
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

## Important Notes

*   **Header Rows:** The script is configured to start reading data at row 2 (`START_ROW = 2`), assuming row 1 contains column headers. If your sheet doesn't have headers, change `START_ROW` to `1` in `main.py`.
*   **Sheet Tab Name:** The script looks for a tab named exactly `"Sheet1"` by default. If you import a CSV (like a Goodreads export), Google Sheets often names the tab after the file. Ensure `SHEET_NAME` in `main.py` exactly matches the name of the tab at the bottom of your screen.
*   **ISBN Formatting:** You don't need to clean your ISBNs beforehand. The script automatically strips dashes and spaces (e.g., `978-3-16-148410-0` becomes `9783161484100`) before searching.
*   **Execution Speed:** To avoid triggering Cloudflare's bot protection on BookOutlet, the script includes a randomized 1 to 2.5-second delay between requests. Consequently, checking a list of 1,000 books will take roughly 30-40 minutes.
*   **Security:** Be careful not to accidentally commit your modified `main.py` file to a public repository, as it contains your private `SPREADSHEET_ID`. The `credentials.json` file is already ignored by default via `.gitignore`.

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
