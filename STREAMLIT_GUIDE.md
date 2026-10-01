# Learning Streamlit: A Beginner's Guide to the Startup Finder Codebase

Welcome! This guide is designed to help you learn **Streamlit** and understand how this project's code is structured. We will break down the project module-by-module and go over the Streamlit elements used in `app.py`.

---

## 1. How Streamlit Works: The Core Concept

Before looking at the code, you need to understand Streamlit's execution model:
- **Top-Down Execution**: Every time a user interacts with a widget (clicks a button, moves a slider, selects a dropdown), **Streamlit reruns your entire script (`app.py`) from top to bottom**.
- **State Persistence**: Because the script reruns entirely, regular variables reset. We use `st.session_state` to store data (like search results) so it survives page reruns.
- **Python Only**: You write standard Python code. Streamlit automatically compiles it into a beautiful React-based frontend in the browser.

---

## 2. Walkthrough of `app.py` (The Frontend Layout)

Let's look at the specific Streamlit features used in [app.py](file:///d:/Ai/Python/startup_finder/app.py) to build our UI.

### 2.1 Page Setup
At the very top of your frontend script, you must configure the browser tab settings:
```python
st.set_page_config(
    page_title="Startup Finder Dashboard",
    page_icon="🚀",
    layout="wide",                  # Options: "centered" or "wide" (uses full screen width)
    initial_sidebar_state="expanded" # Keeps the sidebar open on load
)
```

### 2.2 Custom CSS Injection
Streamlit allows you to inject raw HTML and CSS using `st.markdown()` with `unsafe_allow_html=True`. We use this to apply Google Fonts and design custom metric cards:
```python
st.markdown("""
    <style>
    .main-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1F497D 0%, #3B82F6 50%, #10B981 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    </style>
""", unsafe_allow_html=True)
```

### 2.3 Interactive Sidebar Widgets
The sidebar is a dedicated left-hand panel. You prefix widgets with `st.sidebar.` to place them inside it:
- **Dropdowns (`st.sidebar.selectbox`)**: Searchable list select.
  ```python
  selected_country = st.sidebar.selectbox("Country", COUNTRIES, index=0)
  ```
- **Sliders (`st.sidebar.slider`)**: Numeric range controls.
  ```python
  max_results_input = st.sidebar.slider("Max Results", min_value=10, max_value=200, value=50)
  ```
- **Checkboxes (`st.sidebar.checkbox`)**: True/False toggles.
  ```python
  is_enabled = st.sidebar.checkbox("Validate Website Status", value=True)
  ```
- **Buttons (`st.sidebar.button`)**: Trigger events.
  ```python
  search_button = st.sidebar.button("🔍 Search Startups", type="primary")
  ```

### 2.4 Layout Placeholders (`st.empty`)
Because Streamlit runs top-down, elements are usually written in order. If you want to update a progress bar or status message in-place without adding new lines, you create an empty placeholder:
```python
status_box = st.empty()          # Creates an invisible box
progress_bar_box = st.empty()

# Later in the code, you can fill or overwrite the box:
status_box.info("Pipeline started...")
progress_bar_box.progress(50)    # Shows 50%
status_box.success("Finished!")  # Overwrites the .info message
```

### 2.5 Multi-Column Layouts (`st.columns`)
You can split the main panel horizontally using `st.columns()`. It returns containers you can write into:
```python
col1, col2, col3 = st.columns(3)
with col1:
    st.write("Column 1 content")
with col2:
    st.write("Column 2 content")
```

### 2.6 Data Tables (`st.dataframe`)
Streamlit has a native, high-performance table element that supports interactive sorting, filtering, and hyperlink rendering:
```python
st.dataframe(
    df_display,
    column_config={
        "Website": st.column_config.LinkColumn("Website"),
        "Linkedin": st.column_config.LinkColumn("LinkedIn"),
    },
    use_container_width=True,
    hide_index=True
)
```

### 2.7 Download Buttons (`st.download_button`)
Allows users to download in-memory byte streams or files directly from the browser:
```python
st.download_button(
    label="📥 Download Excel Report",
    data=excel_bytes,
    file_name="report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
```

---

## 3. Explaining the Processing Modules (Folder-by-Folder)

Our project splits logic into independent Python files. Here is what each folder does:

### 📁 Models & Configurations
- **[models.py](file:///d:/Ai/Python/startup_finder/models.py)**: Defines the data model (`Company` dataclass). It enforces that every startup has the exact same fields (Name, Website, Country, email, etc.).
- **[config.py](file:///d:/Ai/Python/startup_finder/config.py)**: Holds standard datasets (supported startup categories and countries). It also defines a custom logger that stores console logs in memory so our Streamlit app can read and print them live.

### 📁 Fetchers (Scrapers)
These query different internet sources concurrently to find startups matching your country and category:
- **[fetchers/base.py](file:///d:/Ai/Python/startup_finder/fetchers/base.py)**: The template class (`BaseFetcher`). Every fetcher must copy this template and implement a `.fetch()` method.
- **[fetchers/yc.py](file:///d:/Ai/Python/startup_finder/fetchers/yc.py)**: Downloads Y Combinator's daily public JSON directory and filters results.
- **[fetchers/github.py](file:///d:/Ai/Python/startup_finder/fetchers/github.py)**: Crawls the public GitHub search API to find software organizations in the specified location.
- **[fetchers/google.py](file:///d:/Ai/Python/startup_finder/fetchers/google.py)**: Queries DuckDuckGo HTML and extracts company names and domains from search results.
- **[fetchers/crunchbase.py](file:///d:/Ai/Python/startup_finder/fetchers/crunchbase.py)** & **[fetchers/wellfound.py](file:///d:/Ai/Python/startup_finder/fetchers/wellfound.py)**: Perform search engine checks targeting these sites and extract details from snippets, bypassing Cloudflare anti-bot firewalls.
- **[fetchers/startup_directory.py](file:///d:/Ai/Python/startup_finder/fetchers/startup_directory.py)**: A local dictionary registry of real, validated startups. Acts as a high-quality demo resource if internet connections are slow or blocked.

### 📁 Processors (Cleaning Pipeline)
Once we collect raw data from fetchers, it goes through a three-stage clean-up:
1. **[processors/normalize.py](file:///d:/Ai/Python/startup_finder/processors/normalize.py)**: Cleans text strings. Capitalizes names, formats funding values (e.g. `$1,500,000` to `$1.5M`), converts `http://` to `https://`, and removes invalid emails.
2. **[processors/deduplicate.py](file:///d:/Ai/Python/startup_finder/processors/deduplicate.py)**: Scans for duplicate companies using website domains, LinkedIn profiles, and fuzzy name comparisons (strips endings like `LLC` or `Inc`). When duplicates are found, it merges them, keeping the most complete information.
3. **[processors/validator.py](file:///d:/Ai/Python/startup_finder/processors/validator.py)**: Runs concurrent HTTP requests to all company websites. If a website fails to respond or has broken DNS, it is removed from the dataset.

### 📁 Exporters (Excel Writer)
- **[exporters/excel.py](file:///d:/Ai/Python/startup_finder/exporters/excel.py)**: Takes our Pandas DataFrame and styles it using `openpyxl`. It adds filter buttons, locks the first row, and creates a **Summary Dashboard** sheet with custom key metrics (Total Startups, counts by Country, counts by Category, and counts by Source).

---

## 4. How Async / Concurrency Works in this App

Scraping websites one-by-one is slow. To speed things up, we use Python's **`asyncio`** library:
- **`async def`**: Declares a function that can pause and run in the background.
- **`await asyncio.gather(*tasks)`**: Triggers all tasks (like querying 6 different websites) at the exact same time. The program pauses until all of them complete, saving significant wait time.
- **Integrating with Streamlit**: Streamlit runs synchronously. To bridge them, when the search button is clicked, we launch the async loop inside Streamlit:
  ```python
  loop = asyncio.new_event_loop()
  final_list = loop.run_until_complete(execute_search(...))
  ```

---

## 5. Next Steps for Learning
1. Open [app.py](file:///d:/Ai/Python/startup_finder/app.py) and change a title style or CSS theme color.
2. Look at [fetchers/yc.py](file:///d:/Ai/Python/startup_finder/fetchers/yc.py) and add a new tag check inside the `CATEGORY_MAPPING` dictionary.
3. Run the Streamlit server: `streamlit run app.py` and interact with the UI sliders to observe the reactive behavior.
