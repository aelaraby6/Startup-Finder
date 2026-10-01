# Startup Finder

A production-quality Python web application built using **Streamlit** that allows users to search, aggregate, normalize, deduplicate, validate, and export software startup profiles from multiple sources concurrently.

## Technology Stack

- **Python 3.12+**
- **Streamlit** (interactive dashboard UI)
- **Pandas** (data structures and manipulation)
- **AioHTTP & Asyncio** (concurrent fetching and active website checks)
- **BeautifulSoup4** (HTML parsing and snippet extraction)
- **OpenPyXL** (premium styled Excel spreadsheets)
- **Logging** (thread-safe, memory-captured logs shown live in the UI)

---

## Project Structure

```
startup_finder/
├── app.py                      # Main Streamlit web application & UI layout
├── config.py                   # Central settings, categories, countries, and logging handler
├── models.py                   # Company schema definition (Python dataclass)
├── requirements.txt            # Python library dependencies
├── README.md                   # System documentation
├── test_pipeline.py            # Unit test suite verifying all pipeline components
├── fetchers/
│   ├── __init__.py             # Dynamic fetcher discovery and instantiation
│   ├── base.py                 # Abstract BaseFetcher interface
│   ├── crunchbase.py           # Crunchbase profile finder (via search engine indexing)
│   ├── github.py               # GitHub Organization Search API crawler
│   ├── google.py               # Search engine crawler to discover direct startup domains
│   ├── startup_directory.py    # Hybrid directory fetcher with curated fallback data
│   ├── wellfound.py            # Wellfound profile finder (via search engine indexing)
│   └── yc.py                   # Y Combinator companies JSON database query client
├── processors/
│   ├── __init__.py             # Processors module exporter
│   ├── deduplicate.py          # Fuzzy company matching and data merging logic
│   ├── normalize.py            # String, URL, and funding value standardizer
│   └── validator.py            # Concurrent async HEAD/GET website link verifier
└── exporters/
    ├── __init__.py             # Exporters module exporter
    └── excel.py                # Premium openpyxl styling and Excel summary report writer
```

---

## Architectural Decisions & Key Features

### 1. Future-Ready Fetchers (Plugins)
The application automatically discovers search fetchers. All scrapers inherit from `BaseFetcher` (in `fetchers/base.py`). In `fetchers/__init__.py`, a dynamic module loader automatically scans the folder, imports modules, and instantiates any subclasses of `BaseFetcher`. Adding a new fetcher is as simple as dropping a new `.py` file into the `fetchers/` directory.

### 2. Bypass Scrape Blocks (Anti-Bot Resilience)
To avoid anti-scraping systems on platforms like Crunchbase and Wellfound, the application performs targeted searches on search engines (using DuckDuckGo HTML) and parses details out of search snippets. This guarantees stability and bypasses Cloudflare/CAPTCHA challenges.

### 3. Smart Deduplication and Merging
Fuzzy deduplication checks match companies by:
1. Normalized website domain.
2. LinkedIn company profile.
3. Simplified name comparison (stripping common suffixes like `LLC`, `Ltd`, `Inc`, `Co`).
When duplicates are found, they are merged by picking the best available records (longest descriptions, non-empty emails, highest employee counts, most specific funding stage, and aggregated technologies and sources).

### 4. Styled Excel Summary Sheet
The Excel exporter does not just dump a CSV. It uses `openpyxl` to:
- Stylize header rows with a modern navy color scheme.
- Enable autofilters.
- Freeze the top row.
- Auto-fit all column widths.
- Build a dedicated **Summary Dashboard** sheet showing total counts, and individual tabular breakdowns by Source, Category, and Country.

### 5. Live Scrolling Logs
A custom thread-safe `StreamlitLogHandler` is attached to the central logger. This captures all system logs in memory. The Streamlit UI queries this log handler during the search lifecycle, rendering a live, scrolling code block showing exactly what each worker thread is doing in real-time.

---

## Installation & Setup

1. **Clone/Navigate** to the project directory:
   ```bash
   cd d:/Ai/Python/startup_finder
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Unit Tests**:
   ```bash
   python -m unittest test_pipeline.py
   ```

4. **Launch the Streamlit App**:
   ```bash
   streamlit run app.py
   ```

---

## User Interface Guidelines

- **Search panel**: Adjust the country, category, search sources, maximum results, and website validation toggle on the left sidebar.
- **Console Output**: Watch live logs scroll in real-time as fetchers run concurrently.
- **KPI Metrics**: Inspect summary statistics for your results once finished.
- **Interactive Table**: Explore the clean aggregated dataset with live hyperlinks to websites and LinkedIn.
- **Excel Export**: Click **Download Excel Report** to download the professional styled spreadsheet.
