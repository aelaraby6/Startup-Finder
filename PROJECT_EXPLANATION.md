# Startup Finder: Codebase Architecture & File Walkthrough

This document provides a detailed, file-by-file, function-by-function walkthrough of the **Startup Finder** project. It explains how all components fit together, why specific code patterns were chosen, and how the data flows from web scrapers into the Streamlit UI and Excel sheets.

---

## 1. Architectural Overview: How Data Flows

When you select a Country/Category and click **Search Startups** in `app.py`, the following pipeline runs:

```
[app.py User Inputs] 
        │
        ▼ (Async Concurrency)
[fetchers/*.py] (YC, GitHub, Google, Crunchbase, Wellfound, Directory)
        │
        ▼ (Raw Company list)
[processors/normalize.py] (Cleans URLs, standardizes fields/formats)
        │
        ▼ (Normalized Company list)
[processors/deduplicate.py] (Fuzzy name & link matching + data merging)
        │
        ▼ (Deduplicated list)
[processors/validator.py] (Concurrently pings domains via HEAD/GET)
        │
        ▼ (Valid live companies)
[exporters/excel.py] (Writes styled Excel sheets and Summary dashboard)
        │
        ▼ (Streamlit UI)
[Interactive Table & Download Button]
```

---

## 2. Walkthrough of Individual Files

Let's examine every file in the codebase.

### 2.1 [models.py](file:///d:/Ai/Python/startup_finder/models.py)
Defines the structure of a single company record using a Python `dataclass`.

- **`Company` Dataclass**:
  Ensures every fetcher returns the exact same fields: `name`, `website`, `country`, `city`, `industry`, `category`, `description`, `founding_year`, `employee_count`, `funding_stage`, `total_funding`, `linkedin`, `email`, `technologies`, `source`, and `date_collected`.
- **`to_dict()`**:
  Translates the object properties into a flat Python dictionary. Specifically, it flattens the `technologies` list into a comma-separated string (e.g. `"Python, React"`) so it can be loaded directly into a Pandas DataFrame and formatted in Excel.
- **`from_dict()`**:
  Reconstructs a `Company` object from a dictionary. Handles reversing the comma-separated `technologies` string back into a Python list.

---

### 2.2 [config.py](file:///d:/Ai/Python/startup_finder/config.py)
Manages shared settings, supported items, and captures logs for the UI.

- **`CATEGORIES` & `COUNTRIES`**:
  Static lists containing the categories and countries presented in the selectboxes.
- **`StreamlitLogHandler` Class**:
  Inherits from Python's standard `logging.Handler`. Instead of printing logs to a file on disk, it appends formatted logs to a thread-safe list in memory (`self.logs`).
- **`logger` setup**:
  Attaches two handlers: `console_handler` (prints logs to the terminal) and `streamlit_handler` (captures logs in memory). The UI calls `get_streamlit_handler().get_new_logs()` to show active console outputs to the user.

---

### 2.3 [fetchers/base.py](file:///d:/Ai/Python/startup_finder/fetchers/base.py)
The template interface for scrapers.

- **`BaseFetcher` Abstract Class**:
  Declares the `fetch` abstract method. Any file added to `fetchers/` must copy this class and implement the `async def fetch(...)` method to retrieve data.
- **`name` Property**:
  Automatically extracts the source name from the class name (e.g. `YCFetcher` becomes `"YC"`).

---

### 2.4 [fetchers/__init__.py](file:///d:/Ai/Python/startup_finder/fetchers/__init__.py)
The plugin-discovery engine that makes the app easily extendable.

- **`get_all_fetchers()`**:
  1. Scans all files inside `fetchers/` using `os.listdir()`.
  2. Dynamically imports them using `importlib.import_module()`.
  3. Uses `inspect.getmembers()` to check if any class inside the imported file subclasses `BaseFetcher` (excluding the base class itself).
  4. Instantiates and returns them. This means **new fetchers are added automatically without editing code**.

---

### 2.5 [fetchers/yc.py](file:///d:/Ai/Python/startup_finder/fetchers/yc.py)
Queries Y Combinator startups.

- **`API_URL`**: Queries `yc-oss.github.io/api/companies/all.json` which aggregates 4000+ YC startups.
- **`_extract_year_from_batch()`**: Uses regular expressions to extract the founding year from strings like `Winter 2020` -> `2020`, `W18` -> `2018`.
- **`_matches_category()`**: Streamlit categories are mapped to YC tags and industry keywords (e.g. `FinTech` searches tags for `crypto`, `payments`, `finance`).
- **`fetch()`**: Fetches the JSON file asynchronously, runs location and category checks, and parses cities.

---

### 2.6 [fetchers/github.py](file:///d:/Ai/Python/startup_finder/fetchers/github.py)
Crawls GitHub organizations.

- **`fetch()`**: Queries `api.github.com/search/users?q=type:org+location:{country}+{category}` to find matching org logins.
- **`_fetch_org_details()`**: Runs concurrent HTTP requests for each organization's full profile to extract public emails, blog/website URLs, and creation dates (which serve as the `founding_year`). Guesses technologies by scanning the bio text. Handles GitHub's rate limits (HTTP 403) gracefully by skipping if blocked.

---

### 2.7 [fetchers/google.py](file:///d:/Ai/Python/startup_finder/fetchers/google.py)
Crawls standard search listings.

- **`fetch()`**: Queries DuckDuckGo HTML for `<country> <category> startups list`.
- **`_clean_ddg_url()`**: Extracts final target URLs from DuckDuckGo redirect wrappers (e.g. strips out `https://duckduckgo.com/l/?uddg=...`).
- **`EXCLUDED_DOMAINS`**: Filters out sites like LinkedIn, Medium, TechCrunch, and Reddit to find direct startup websites.

---

### 2.8 [fetchers/crunchbase.py](file:///d:/Ai/Python/startup_finder/fetchers/crunchbase.py) & [wellfound.py](file:///d:/Ai/Python/startup_finder/fetchers/wellfound.py)
Bypasses Cloudflare firewalls.

- Instead of scraping Crunchbase or Wellfound directly (which triggers bot blocks), they query DuckDuckGo for `site:crunchbase.com/organization <country> <category>` or `site:wellfound.com/company`.
- They parse the search snippets using BeautifulSoup to extract:
  - Company name (parsed from the URL slug, e.g. `/organization/lendo` -> `Lendo`).
  - Company descriptions (from the DDG search snippet text).
  - Employee counts and funding stages (by scanning description text using regex matchers like `(\d+)-(\d+)\s+employees`).

---

### 2.9 [fetchers/startup_directory.py](file:///d:/Ai/Python/startup_finder/fetchers/startup_directory.py)
Curated high-fidelity registry.

- Contains a hardcoded dictionary (`CURATED_DATABASE`) of major, real startups globally (e.g. Tamara, Tabby, Moyasar, Foodics in Saudi Arabia; OpenAI, Notion, Stripe in the US; Revolut in the UK).
- If the target country and category match, it returns these pre-compiled records. This guarantees that you always get detailed, realistic results (such as exact funding stages and email addresses) to view and test, even if external internet scrapers get throttled.

---

### 2.10 [processors/normalize.py](file:///d:/Ai/Python/startup_finder/processors/normalize.py)
Standardizes and cleans fields.

- **`clean_url()`**: Strips `http://`, `https://`, `www.`, and trailing slashes so URL domains are uniform (used for duplicate matching).
- **`format_website()`**: Upgrades `http://` websites to secure `https://` protocols.
- **`normalize_funding()`**: Parses numeric strings (e.g. `$1,500,000` or `8.5M` or `120000`) and standardizes them into shortened formats like `$1.5M`, `$8.5M`, and `$120K`.
- **`normalize_company()`**: Fixes name casings (keeps acronyms like `AI` or `SaaS` capitalized, title-cases others, and handles hyphens like `My-Startup`), cleans locations, and dedupes/standardizes technology names.

---

### 2.11 [processors/deduplicate.py](file:///d:/Ai/Python/startup_finder/processors/deduplicate.py)
Deduplication and data mergers.

- **`simplify_name()`**: Strips punctuation and corporate suffixes like `LLC`, `LTD`, `Inc`, and `Co` from company names (e.g. `"Tamara Co"` -> `"tamara"`).
- **`deduplicate_companies()`**: Matches duplicates by comparing normalized websites, LinkedIn links, and simplified names.
- **`_get_stage_specificity()`**: Ranks funding stages: `Unknown` is ranked 1, `Growth` or `Early` (generic) is ranked 2, and specific rounds (e.g., `Series C`, `Seed`) are ranked 3.
- **`merge_companies()`**: Combines duplicate records, selecting the highest specificity stage/funding, merging technology sets, combining source origins (e.g. `"YC, GitHub"`), and choosing the longest description.

---

### 2.12 [processors/validator.py](file:///d:/Ai/Python/startup_finder/processors/validator.py)
Validates website status.

- **`validate_companies_websites()`**: Runs an asynchronous HTTP request connector.
- **`validate_single_website()`**: Checks domains concurrently. It attempts a fast `HEAD` check first. If the domain blocks it, it falls back to a standard `GET` request. If the site fails to resolve or returns a 4xx/5xx error, it is marked dead and filtered out.

---

### 2.13 [exporters/excel.py](file:///d:/Ai/Python/startup_finder/exporters/excel.py)
Writes styled Excel workbooks.

- **`export_to_excel()`**:
  Converts our company list into a Pandas DataFrame and writes it to two sheets:
  - **`Companies` (Raw data)**: Headers are styled with a corporate dark navy background (`#1F497D`) and bold white text. Column widths are automatically adjusted. Hyperlinks are highlighted, filters are enabled, and the header row is frozen (`freeze_panes = "A2"`).
  - **`Summary` (Dashboard)**: Uses `openpyxl` grid positioning to draw key metric cards and stacked tables showing company breakdowns by Source, Category, and Country.

---

### 2.14 [app.py](file:///d:/Ai/Python/startup_finder/app.py)
The central Streamlit UI orchestrator.

- **Page Styling**: Injects CSS to enforce layout fonts, metric boxes, and header colors.
- **Sidebar Checkboxes**: Instantiates `get_all_fetchers()` and loops over them to draw checkboxes. If a new fetcher is added to the folder, a checkbox for it appears here automatically.
- **Search Execution**:
  Since Streamlit runs synchronously, clicking the search button runs an asynchronous executor loop:
  ```python
  loop = asyncio.new_event_loop()
  final_list = loop.run_until_complete(execute_search(...))
  ```
- **Live Status Feed**:
  During search runs, the app loops over active fetcher tasks and prints Captured Log entries from `config.get_streamlit_handler()` in real-time inside a scrollable `st.empty` block.
- **KPI Metrics**: Displays summary statistics and binds the Excel file bytes to `st.download_button` so users can download reports instantly.
