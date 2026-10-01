import streamlit as st
import pandas as pd
import asyncio
import os
from typing import List
from datetime import datetime

# Import project modules
from config import CATEGORIES, COUNTRIES, get_streamlit_handler, logger
from models import Company
from fetchers import get_all_fetchers
from processors import deduplicate_companies, validate_companies_websites
from exporters import export_to_excel

# Set page configuration
st.set_page_config(
    page_title="Startup Finder Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Custom CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Grotesk:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .main-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1F497D 0%, #3B82F6 50%, #10B981 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        font-size: 1.2rem;
        color: #4B5563;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    .console-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.1rem;
        font-weight: 600;
        color: #1F497D;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }
    
    .metric-card {
        background-color: #F3F4F6;
        border-radius: 10px;
        padding: 1.2rem;
        border-left: 5px solid #1F497D;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    .metric-val {
        font-size: 2rem;
        font-weight: 700;
        color: #1F497D;
    }
    
    .metric-lbl {
        font-size: 0.85rem;
        color: #6B7280;
        text-transform: uppercase;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize Session States
if "companies" not in st.session_state:
    st.session_state.companies = []
if "search_completed" not in st.session_state:
    st.session_state.search_completed = False
if "excel_filename" not in st.session_state:
    st.session_state.excel_filename = ""
if "excel_filepath" not in st.session_state:
    st.session_state.excel_filepath = ""

async def execute_search(
    country: str,
    category: str,
    max_results: int,
    enabled_sources: List[str],
    validate_web: bool,
    status_placeholder,
    progress_bar,
    log_area
):
    """Runs the asynchronous fetch, merge, deduplication and validation pipeline."""
    handler = get_streamlit_handler()
    handler.clear()
    
    logger.info("Initializing search pipeline...")
    status_placeholder.info("Discovering fetchers...")
    progress_bar.progress(10)
    
    # 1. Discover all fetchers
    all_fetchers = get_all_fetchers()
    active_fetchers = [f for f in all_fetchers if f.name in enabled_sources]
    
    if not active_fetchers:
        logger.error("No search sources enabled!")
        status_placeholder.error("Please enable at least one search source in the sidebar.")
        progress_bar.progress(0)
        return []
        
    # Update status
    status_placeholder.info("Running search sources concurrently...")
    progress_bar.progress(35)
    
    # 2. Run enabled fetchers concurrently
    tasks = [f.fetch(country, category, max_results) for f in active_fetchers]
    
    # Simple log updater task to refresh log console during fetch
    async def fetch_with_log_refresh():
        # Schedule the fetch tasks
        gather_task = asyncio.gather(*tasks, return_exceptions=True)
        
        while not gather_task.done():
            # Refresh logs in UI
            logs = handler.get_new_logs()
            log_area.code("\n".join(logs), language="text")
            await asyncio.sleep(0.5)
            
        return await gather_task

    results = await fetch_with_log_refresh()
    
    # Consolidate results
    raw_companies = []
    for f, res in zip(active_fetchers, results):
        if isinstance(res, Exception):
            logger.error(f"Fetcher '{f.name}' failed with exception: {res}")
        elif res:
            raw_companies.extend(res)
            
    # Update status
    status_placeholder.info(f"Deduplicating and merging {len(raw_companies)} raw records...")
    progress_bar.progress(70)
    
    # Refresh logs
    log_area.code("\n".join(handler.get_new_logs()), language="text")
    
    # 3. Deduplicate
    deduplicated = deduplicate_companies(raw_companies)
    
    # Refresh logs
    log_area.code("\n".join(handler.get_new_logs()), language="text")
    
    # 4. Validate websites
    status_placeholder.info("Validating company websites (active link checks)...")
    progress_bar.progress(85)
    
    # Create web validation task while updating logs
    validate_task = asyncio.create_task(validate_companies_websites(deduplicated, enabled=validate_web))
    while not validate_task.done():
        log_area.code("\n".join(handler.get_new_logs()), language="text")
        await asyncio.sleep(0.5)
        
    final_companies = await validate_task
    
    # 5. Sort by company name
    final_companies.sort(key=lambda c: c.name.lower())
    
    status_placeholder.success(f"Search complete! Found {len(final_companies)} companies.")
    progress_bar.progress(100)
    
    # Final log refresh
    log_area.code("\n".join(handler.get_new_logs()), language="text")
    
    return final_companies


# Main Page Header
st.markdown('<div class="main-title">🚀 Startup Finder Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Aggregate, clean, and export software startup profiles from YC, GitHub, Crunchbase, and more.</div>', unsafe_allow_html=True)

# ----------------- SIDEBAR -----------------
st.sidebar.image("https://img.icons8.com/clouds/200/rocket-take-off.png", width=120)
st.sidebar.markdown("### Search Configurations")

# Country & Category Controls
selected_country = st.sidebar.selectbox("Country", COUNTRIES, index=0)
selected_category = st.sidebar.selectbox("Startup Category", CATEGORIES, index=1) # Default to AI

# Dynamic Fetcher Registration Checkboxes
st.sidebar.markdown("---")
st.sidebar.markdown("#### Search Sources")
discover_fetchers = get_all_fetchers()
enabled_fetcher_names = []

for f in discover_fetchers:
    is_enabled = st.sidebar.checkbox(f.name, value=True, help=f"Enable searching via {f.name}")
    if is_enabled:
        enabled_fetcher_names.append(f.name)

# Advanced Controls
st.sidebar.markdown("---")
st.sidebar.markdown("#### Advanced Options")
max_results_input = st.sidebar.slider("Max Results Per Source", min_value=10, max_value=200, value=50, step=10)
enable_validation = st.sidebar.checkbox("Validate Website Status", value=True, help="Perform active HTTP checks to remove dead domains")

# Search Trigger
st.sidebar.markdown("---")
search_button = st.sidebar.button("🔍 Search Startups", use_container_width=True, type="primary")

# ----------------- MAIN PANEL -----------------
# Log Console Container (Shown only when searching or finished)
status_box = st.empty()
progress_bar_box = st.empty()

# Create a columns-based layout for search logs and results
if search_button:
    # Set progress UI placeholders
    prog_bar = progress_bar_box.progress(0)
    status_msg = status_box.info("Search pipeline started...")
    
    st.markdown('<div class="console-header">💻 Console Output Logs</div>', unsafe_allow_html=True)
    log_box = st.empty()
    
    # Run pipeline
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        final_list = loop.run_until_complete(
            execute_search(
                country=selected_country,
                category=selected_category,
                max_results=max_results_input,
                enabled_sources=enabled_fetcher_names,
                validate_web=enable_validation,
                status_placeholder=status_msg,
                progress_bar=prog_bar,
                log_area=log_box
            )
        )
        st.session_state.companies = final_list
        st.session_state.search_completed = True
        
        # Save Excel File
        if final_list:
            safe_country = selected_country.replace(" ", "_")
            safe_cat = selected_category.replace(" ", "_")
            filename = f"{safe_country}_{safe_cat}_Startups.xlsx"
            filepath = os.path.join(os.getcwd(), filename)
            
            export_to_excel(final_list, filepath)
            st.session_state.excel_filename = filename
            st.session_state.excel_filepath = filepath
        else:
            st.session_state.excel_filename = ""
            st.session_state.excel_filepath = ""
            
    except Exception as e:
        status_box.error(f"Search pipeline failed: {e}")
        logger.error(f"Pipeline error: {e}", exc_info=True)
    finally:
        loop.close()

# ----------------- DISPLAY RESULTS -----------------
if st.session_state.search_completed:
    companies = st.session_state.companies
    
    if not companies:
        st.warning("No startups found matching the search criteria. Try enabling more sources or broadening the category.")
    else:
        st.markdown("---")
        st.markdown("### 📊 Search Summary")
        
        # Calculate dashboard metrics
        source_set = set()
        tech_set = set()
        for c in companies:
            for s in c.source.split(","):
                if s.strip():
                    source_set.add(s.strip())
            for t in c.technologies:
                tech_set.add(t)

        # Render KPI metrics in custom stylized cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-lbl">Total Companies</div>
                    <div class="metric-val">{len(companies)}</div>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div class="metric-card" style="border-left-color: #10B981;">
                    <div class="metric-lbl">Unique Sources</div>
                    <div class="metric-val">{len(source_set)}</div>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
                <div class="metric-card" style="border-left-color: #3B82F6;">
                    <div class="metric-lbl">Technologies Found</div>
                    <div class="metric-val">{len(tech_set)}</div>
                </div>
            """, unsafe_allow_html=True)
        with col4:
            # Download Button
            st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
            if st.session_state.excel_filepath and os.path.exists(st.session_state.excel_filepath):
                with open(st.session_state.excel_filepath, "rb") as f:
                    excel_bytes = f.read()
                st.download_button(
                    label="📥 Download Excel Report",
                    data=excel_bytes,
                    file_name=st.session_state.excel_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

        st.markdown("### 🔍 Aggregated Startup Database")
        
        # Convert to Pandas for display
        df_display = pd.DataFrame([c.to_dict() for c in companies])
        
        # Capitalize and pretty-print columns
        df_display.columns = [c.replace("_", " ").title() for c in df_display.columns]
        
        # Display DataFrame
        st.dataframe(
            df_display,
            column_config={
                "Website": st.column_config.LinkColumn("Website"),
                "Linkedin": st.column_config.LinkColumn("LinkedIn"),
                "Email": st.column_config.TextColumn("Email"),
            },
            use_container_width=True,
            hide_index=True
        )
