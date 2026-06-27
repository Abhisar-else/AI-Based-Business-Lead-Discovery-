"""
streamlit_app.py — AI Business Lead Discovery Dashboard

A premium Streamlit interface with:
  - Sidebar: search config, API status, Sheets toggle
  - Tab 1: 📊 Dashboard (KPI cards + interactive charts)
  - Tab 2: 📋 Leads Table (filterable, downloadable)
  - Tab 3: 🤖 AI Analysis (detail view per lead)
  - Tab 4: ⚙️ Settings (API keys, connection tests)
"""

import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH so `core.*` imports resolve
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from core import run_pipeline
from core.config import (
    TARGET_CATEGORIES,
    has_gemini_key,
    has_openai_key,
    has_serper_key,
    has_sheets_config,
    get_sheets_config_status,
    SHEET_COLUMNS,
)
from core.analyzer import get_analysis_mode
from core.data_pipeline import (
    get_summary_stats,
    filter_by_potential,
    filter_by_website_status,
    export_to_csv_bytes,
    load_from_csv,
    save_to_csv,
)
from core.sheets_client import (
    append_dataframe,
    overwrite_sheet,
    get_sheet_url,
    test_connection,
)


# ─── Page Configuration ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Lead Discovery — Business Intelligence",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─── Custom CSS — Premium Dark Theme ─────────────────────────────────────────

st.markdown("""
<style>
/* ─── Google Font ─── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ─── Root Variables ─── */
:root {
    --bg-primary: #0f1117;
    --bg-card: #1a1d29;
    --bg-card-hover: #222639;
    --accent-blue: #4f8cf7;
    --accent-purple: #a78bfa;
    --accent-green: #34d399;
    --accent-orange: #fb923c;
    --accent-red: #f87171;
    --text-primary: #e8eaed;
    --text-secondary: #9ca3af;
    --border: #2d3148;
    --glass-bg: rgba(26, 29, 41, 0.85);
    --glass-border: rgba(79, 140, 247, 0.15);
}

/* ─── Global Overrides ─── */
html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ─── Header Bar ─── */
.main-header {
    background: linear-gradient(135deg, #1e2745 0%, #0f1117 60%, #1a1038 100%);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.main-header::before {
    content: '';
    position: absolute;
    top: -40%;
    right: -10%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(79,140,247,0.12) 0%, transparent 70%);
    border-radius: 50%;
}
.main-header h1 {
    font-size: 1.75rem;
    font-weight: 800;
    background: linear-gradient(135deg, #4f8cf7, #a78bfa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
    letter-spacing: -0.02em;
}
.main-header p {
    color: var(--text-secondary);
    font-size: 0.95rem;
    margin-top: 0.4rem;
    font-weight: 400;
}

/* ─── KPI Cards ─── */
.kpi-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
}
.kpi-card {
    flex: 1;
    min-width: 140px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}
.kpi-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(79, 140, 247, 0.12);
    border-color: var(--glass-border);
}
.kpi-card .kpi-value {
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1.1;
}
.kpi-card .kpi-label {
    font-size: 0.78rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 0.4rem;
    font-weight: 600;
}
.kpi-blue .kpi-value { color: var(--accent-blue); }
.kpi-green .kpi-value { color: var(--accent-green); }
.kpi-orange .kpi-value { color: var(--accent-orange); }
.kpi-red .kpi-value { color: var(--accent-red); }
.kpi-purple .kpi-value { color: var(--accent-purple); }

/* ─── Status Badges ─── */
.badge {
    display: inline-block;
    padding: 0.22rem 0.7rem;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.badge-high   { background: rgba(52,211,153,0.15); color: #34d399; border: 1px solid rgba(52,211,153,0.3); }
.badge-medium { background: rgba(251,146,60,0.15); color: #fb923c; border: 1px solid rgba(251,146,60,0.3); }
.badge-low    { background: rgba(248,113,113,0.15); color: #f87171; border: 1px solid rgba(248,113,113,0.3); }

/* ─── API Status Pills ─── */
.api-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.8rem;
    border-radius: 10px;
    font-size: 0.8rem;
    margin-bottom: 0.4rem;
    font-weight: 500;
}
.api-ok   { background: rgba(52,211,153,0.1); color: #34d399; border: 1px solid rgba(52,211,153,0.25); }
.api-warn { background: rgba(251,146,60,0.1); color: #fb923c; border: 1px solid rgba(251,146,60,0.25); }

/* ─── Sidebar Polish ─── */
[data-testid="stSidebar"] {
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] h1 {
    font-size: 1.1rem !important;
    font-weight: 700;
}/* ─── Status Log Styling ─── */
[data-testid="stStatusWidget"] {
    font-size: 0.85rem;
}

 
/* ─── Smooth Transitions on interactive elements ─── */
button, .stButton>button {
    transition: all 0.2s ease !important;
}
button:hover, .stButton>button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(79,140,247,0.2) !important;
}
</style>
""", unsafe_allow_html=True)


# ─── Session State Defaults ───────────────────────────────────────────────────

if "leads_df" not in st.session_state:
    st.session_state.leads_df = pd.DataFrame(columns=SHEET_COLUMNS)
if "pipeline_running" not in st.session_state:
    st.session_state.pipeline_running = False
if "pipeline_logs" not in st.session_state:
    st.session_state.pipeline_logs = []


# ─── Header ──────────────────────────────────────────────────────────────────

st.markdown("""
<div class="main-header">
    <h1>🔍 AI Business Lead Discovery</h1>
    <p>Discover, audit & classify businesses with digital presence gaps — powered by AI intelligence</p>
</div>
""", unsafe_allow_html=True)


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🎯 Search Configuration")

    selected_category = st.selectbox(
        "Industry Category",
        options=TARGET_CATEGORIES,
        index=0,
        help="Select the business sector to search for.",
    )

    location = st.text_input(
        "Location",
        value="Indore",
        placeholder="e.g. Mumbai, Delhi, Bangalore...",
        help="City or area to search.",
    )

    max_results = st.slider(
        "Maximum Leads",
        min_value=5,
        max_value=50,
        value=15,
        step=5,
        help="Number of businesses to discover per search.",
    )

    st.markdown("---")

    # API Status section
    st.markdown("### 🔌 API Status")

    serper_ok   = has_serper_key()
    gemini_ok   = has_gemini_key()
    openai_ok   = has_openai_key()
    sheets_ok   = has_sheets_config()

    st.markdown(
        f'<div class="api-status {"api-ok" if serper_ok else "api-warn"}">'
        f'{"✅" if serper_ok else "⚠️"} Serper.dev (Google Maps)</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="api-status {"api-ok" if gemini_ok else "api-warn"}">'
        f'{"✅" if gemini_ok else "⚠️"} Gemini AI</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="api-status {"api-ok" if sheets_ok else "api-warn"}">'
        f'{"✅" if sheets_ok else "⚠️"} Google Sheets</div>',
        unsafe_allow_html=True,
    )

    st.caption(f"Analysis Mode: {get_analysis_mode()}")

    st.markdown("---")

    # Run button
    run_btn = st.button(
        "🚀  Run Discovery",
        use_container_width=True,
        type="primary",
        disabled=st.session_state.pipeline_running,
    )

    # Load cached data
    st.markdown("---")
    if st.button("📂  Load Cached Data", use_container_width=True):
        cached = load_from_csv()
        if not cached.empty:
            st.session_state.leads_df = cached
            st.success(f"Loaded {len(cached)} cached leads")
            st.rerun()
        else:
            st.info("No cached data found. Run a discovery first!")


# ─── Pipeline Execution ──────────────────────────────────────────────────────

if run_btn:
    st.session_state.pipeline_running = True
    st.session_state.pipeline_logs = []

    # Create a clean container for status
    progress_bar = st.progress(0, text="Initializing...")
    status_container = st.container()
    
    with status_container:
        status_header = st.status(
            f"🔍 Discovering **{selected_category}** in **{location}**...",
            expanded=True,
        )
        log_placeholder = st.empty()  # Shows last 5 lines only

    def _progress_handler(*args, **kwargs):
        """
        Callback from pipeline → UI updates.
        Handles: callback(str), callback(str, float), callback(dict)
        """
        # Extract message and percentage from various call signatures
        if len(args) == 1 and isinstance(args[0], dict):
            msg_dict = args[0]
            text = msg_dict.get("message") or msg_dict.get("msg") or msg_dict.get("status") or str(msg_dict)
            pct = msg_dict.get("progress", 0.5)
        elif len(args) >= 1:
            text = str(args[0])
            pct = args[1] if len(args) > 1 else kwargs.get("pct", 0.5)
        else:
            return

        # Skip empty or useless messages
        if not text or text.strip() in ("{}", "[]"):
            return

        # Truncate very long messages
        if len(text) > 150:
            text = text[:147] + "..."

        # Update progress bar
        progress_bar.progress(min(pct, 1.0), text=text)
        
        # Update log (keep only last 8 lines visible)
        st.session_state.pipeline_logs.append(text)
        recent_logs = st.session_state.pipeline_logs[-8:]
        log_html = "<br>".join(f"• {log}" for log in recent_logs)
        log_placeholder.markdown(
            f'<div style="background: #1a1d29; padding: 0.8rem; border-radius: 8px; '
            f'font-family: monospace; font-size: 0.8rem; color: #9ca3af; '
            f'max-height: 200px; overflow-y: auto;">{log_html}</div>',
            unsafe_allow_html=True
        )

    try:
        df = run_pipeline(
            query=selected_category,
            location=location,
            max_results=max_results,
            progress_callback=_progress_handler,
        )

        if not df.empty:
            st.session_state.leads_df = df
            progress_bar.progress(1.0, text="✅ Discovery complete!")
            status_header.update(
                label=f"✅ Found {len(df)} business leads!",
                state="complete",
                expanded=False,
            )
        else:
            progress_bar.progress(1.0, text="⚠️ No results found")
            status_header.update(
                label="⚠️ No businesses found for this search.",
                state="error",
                expanded=False,
            )

    except Exception as exc:
        progress_bar.progress(1.0, text="❌ Pipeline error")
        status_header.update(label=f"❌ Error: {exc}", state="error")
        st.error(f"Pipeline encountered an error: {exc}")

    finally:
        st.session_state.pipeline_running = False


# ─── Main Content Tabs ───────────────────────────────────────────────────────

df = st.session_state.leads_df

tab_dashboard, tab_table, tab_analysis, tab_settings = st.tabs([
    "📊 Dashboard",
    "📋 Leads Table",
    "🤖 AI Analysis",
    "⚙️ Settings",
])


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 1: Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

with tab_dashboard:
    if df.empty:
        st.info(
            "👈 Configure your search in the sidebar and click **Run Discovery** "
            "to populate the dashboard.",
            icon="🔍",
        )
    else:
        stats = get_summary_stats(df)

        # KPI Cards
        st.markdown(f"""
        <div class="kpi-row">
            <div class="kpi-card kpi-blue">
                <div class="kpi-value">{stats['total']}</div>
                <div class="kpi-label">Total Leads</div>
            </div>
            <div class="kpi-card kpi-green">
                <div class="kpi-value">{stats['high']}</div>
                <div class="kpi-label">High Potential</div>
            </div>
            <div class="kpi-card kpi-orange">
                <div class="kpi-value">{stats['medium']}</div>
                <div class="kpi-label">Medium Potential</div>
            </div>
            <div class="kpi-card kpi-red">
                <div class="kpi-value">{stats['low']}</div>
                <div class="kpi-label">Low Potential</div>
            </div>
            <div class="kpi-card kpi-purple">
                <div class="kpi-value">{stats['no_website']}</div>
                <div class="kpi-label">No Website</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Charts Row
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("##### Lead Potential Distribution")
            potential_data = df["Potential Category"].value_counts().reset_index()
            potential_data.columns = ["Category", "Count"]
            color_map = {"High": "#34d399", "Medium": "#fb923c", "Low": "#f87171"}
            fig_bar = px.bar(
                potential_data,
                x="Category",
                y="Count",
                color="Category",
                color_discrete_map=color_map,
                template="plotly_dark",
            )
            fig_bar.update_layout(
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=10, b=40),
                height=300,
                font=dict(family="Inter"),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
            )
            fig_bar.update_traces(
                marker_line_width=0,
                marker_cornerradius=8,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_chart2:
            st.markdown("##### Website Status Breakdown")
            web_data = df["Website Status"].value_counts().reset_index()
            web_data.columns = ["Status", "Count"]
            web_colors = {
                "No Website": "#f87171",
                "Poor Website": "#fb923c",
                "Good Website": "#34d399",
            }
            fig_pie = px.pie(
                web_data,
                values="Count",
                names="Status",
                color="Status",
                color_discrete_map=web_colors,
                template="plotly_dark",
                hole=0.45,
            )
            fig_pie.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=10, b=20),
                height=300,
                font=dict(family="Inter"),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.15,
                    xanchor="center",
                    x=0.5,
                ),
            )
            fig_pie.update_traces(
                textposition="inside",
                textinfo="percent+value",
                marker=dict(line=dict(width=0)),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # Contact info row
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("📧 With Email", stats["with_email"])
        col_s2.metric("📞 With Phone", stats["with_phone"])
        col_s3.metric("🌐 Good Websites", stats["good_website"])


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 2: Leads Table
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 2: Leads Table
# ═══════════════════════════════════════════════════════════════════════════════

with tab_table:
    if df.empty:
        st.info("No leads yet. Run a discovery to populate this table.")
    else:
        # ─── Filter Row ───────────────────────────────────────────────────
        st.markdown("#### 🔍 Filters")

        col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 1])

        with col_f1:
            potential_filter = st.multiselect(
                "Potential",
                options=["High", "Medium", "Low"],
                default=["High", "Medium", "Low"],
                key="potential_filter",
            )
        with col_f2:
            web_filter = st.multiselect(
                "Website Status",
                options=["No Website", "Poor Website", "Good Website"],
                default=["No Website", "Poor Website", "Good Website"],
                key="web_filter",
            )
        with col_f3:
            search_term = st.text_input(
                "Search",
                placeholder="Name, location, category...",
                key="search_leads",
            )
        with col_f4:
            st.markdown("<div style='margin-top: 1.65rem;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Reset", use_container_width=True, key="reset_filters"):
                for key in ["potential_filter", "web_filter", "search_leads",
                            "sort_column", "sort_order", "visible_columns"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

        # ─── Sort & Customize Row ───────────────────────────────────────
        col_s1, col_s2, col_s3 = st.columns([2, 1, 1])

        default_display_cols = [
            "Business Name", "Industry Category", "Location",
            "Website Status", "Phone Number", "Email Address",
            "Potential Category", "Reasoning",
        ]
        available_default = [c for c in default_display_cols if c in df.columns]
        all_columns       = df.columns.tolist()

        with col_s1:
            sort_column = st.selectbox(
                "Sort by",
                options=available_default or all_columns,
                index=0,
                key="sort_column",
            )
        with col_s2:
            sort_order = st.radio(
                "Order",
                options=["↓ Desc", "↑ Asc"],
                horizontal=True,
                key="sort_order",
                label_visibility="collapsed",
            )
        with col_s3:
            with st.popover("⚙️ Columns", use_container_width=True):
                visible_cols = st.multiselect(
                    "Visible columns",
                    options=all_columns,
                    default=available_default,
                    key="visible_columns",
                )
                if not visible_cols:
                    visible_cols = available_default
                    st.caption("⚠️ Showing default columns (none selected)")

        # ─── Apply Filters ──────────────────────────────────────────────
        filtered = df.copy()

        # Potential filter
        if potential_filter and "Potential Category" in filtered.columns:
            filtered = filtered[filtered["Potential Category"].isin(potential_filter)]

        # Website filter
        if web_filter and "Website Status" in filtered.columns:
            filtered = filtered[filtered["Website Status"].isin(web_filter)]

        # Search filter (multi-column, case-insensitive)
        if search_term:
            mask = filtered.apply(
                lambda r: search_term.lower() in str(r).lower(),
                axis=1
            )
            filtered = filtered[mask]

        # Sort
        if sort_column in filtered.columns:
            ascending = sort_order == "↑ Asc"
            filtered = filtered.sort_values(
                by=sort_column,
                ascending=ascending,
                na_position="last",
            )

        # ─── Result Badges ──────────────────────────────────────────────
        if not filtered.empty and "Potential Category" in filtered.columns:
            high_count   = (filtered["Potential Category"] == "High").sum()
            medium_count = (filtered["Potential Category"] == "Medium").sum()
            low_count    = (filtered["Potential Category"] == "Low").sum()
        else:
            high_count = medium_count = low_count = 0

        st.markdown(f"""
        <div style="
            display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;
            padding: 0.7rem 1rem; margin: 0.8rem 0 1rem 0;
            background: var(--bg-card, #1a1d29);
            border: 1px solid var(--border, #2d3148);
            border-radius: 10px; font-size: 0.85rem;
        ">
            <span style="font-weight: 600;">📊 Showing
                <b style="color: var(--accent-blue, #4f8cf7);">{len(filtered)}</b>
                of <b>{len(df)}</b> leads
            </span>
            <span style="margin-left: auto; display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <span class="badge badge-high">🟢 {high_count} High</span>
                <span class="badge badge-medium">🟡 {medium_count} Medium</span>
                <span class="badge badge-low">🔴 {low_count} Low</span>
            </span>
        </div>
        """, unsafe_allow_html=True)

        # ─── Empty State ────────────────────────────────────────────────
        if filtered.empty:
            st.warning("⚠️ No leads match your current filters.")
            st.markdown("**Try:**")
            st.markdown("- Removing the search term")
            st.markdown("- Selecting more potential categories")
            st.markdown("- Including all website statuses")
            st.stop()

        # ─── Data Table ─────────────────────────────────────────────────
        display_data = filtered[visible_cols] if visible_cols else filtered

        # Build dynamic column config
        column_config = {}
        col_widths = {
            "Business Name":      "medium",
            "Industry Category":  "small",
            "Location":           "medium",
            "Website Status":     "small",
            "Phone Number":       "small",
            "Email Address":      "medium",
            "Potential Category": "small",
            "Reasoning":          "large",
            "Website URL":        "medium",
            "Google Maps Link":   "medium",
            "Owner / Founder":    "medium",
            "LinkedIn Profile":   "medium",
            "Business Description": "large",
        }
        col_labels = {
            "Business Name":        "Business",
            "Industry Category":    "Category",
            "Location":             "Location",
            "Website Status":       "Web Status",
            "Phone Number":         "Phone",
            "Email Address":        "Email",
            "Potential Category":   "Potential",
            "Reasoning":            "AI Reasoning",
            "Website URL":          "URL",
            "Google Maps Link":     "Maps",
            "Owner / Founder":      "Owner",
            "LinkedIn Profile":     "LinkedIn",
            "Business Description": "Description",
        }
        for col in display_data.columns:
            label = col_labels.get(col, col)
            width = col_widths.get(col, "small")
            column_config[col] = st.column_config.TextColumn(label, width=width)

        st.dataframe(
            display_data,
            use_container_width=True,
            height=500,
            hide_index=True,
            column_config=column_config,
        )

        # ─── Quick Copy (collapsible) ──────────────────────────────────
        with st.expander("📋 Quick Copy Lead", expanded=False):
            col_qc1, col_qc2 = st.columns([1, 2])
            with col_qc1:
                copy_target = st.selectbox(
                    "Lead",
                    options=filtered["Business Name"].tolist(),
                    key="copy_lead",
                    index=None,
                    placeholder="Choose a lead...",
                )
            with col_qc2:
                if copy_target:
                    row = filtered[filtered["Business Name"] == copy_target].iloc[0]
                    copy_text = (
                        f"🏢 {row.get('Business Name', 'N/A')}\n"
                        f"📂 {row.get('Industry Category', 'N/A')}\n"
                        f"📍 {row.get('Location', 'N/A')}\n"
                        f"📞 {row.get('Phone Number', 'N/A')}\n"
                        f"📧 {row.get('Email Address', 'N/A')}\n"
                        f"🌐 {row.get('Website URL', 'N/A')}\n"
                        f"👤 {row.get('Owner / Founder', 'N/A')}\n"
                        f"⭐ {row.get('Potential Category', 'N/A')}\n"
                        f"\n💡 {row.get('Reasoning', 'N/A')}"
                    )
                    st.code(copy_text, language="text")
                else:
                    st.info("Select a lead above to generate a copyable text block.")

        # ─── Export Row ─────────────────────────────────────────────────
        st.markdown("#### 📤 Export")

        col_e1, col_e2, col_e3, col_e4 = st.columns(4)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        safe_cat  = selected_category.lower().replace(" ", "_")
        safe_loc  = location.lower().replace(" ", "_")

        with col_e1:
            st.download_button(
                label="⬇️  Filtered CSV",
                data=export_to_csv_bytes(filtered),
                file_name=f"leads_{safe_cat}_{safe_loc}_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True,
                help=f"Download the {len(filtered)} filtered leads",
            )

        with col_e2:
            if st.button("📤  Append to Sheets", use_container_width=True, key="append_btn"):
                with st.spinner("Appending to Google Sheets..."):
                    success, msg = append_dataframe(filtered)
                    if success:
                        st.success(msg)
                        url = get_sheet_url()
                        if url:
                            st.markdown(f"[📊 Open Google Sheet]({url})")
                    else:
                        st.error(msg)

        with col_e3:
            if st.button("🔄  Overwrite Sheet", use_container_width=True, key="overwrite_btn"):
                with st.spinner("Refreshing Google Sheet..."):
                    success, msg = overwrite_sheet(filtered)
                    if success:
                        st.success(msg)
                        url = get_sheet_url()
                        if url:
                            st.markdown(f"[📊 Open Google Sheet]({url})")
                    else:
                        st.error(msg)

        with col_e4:
            st.download_button(
                label="📋  Full Data CSV",
                data=export_to_csv_bytes(df),
                file_name=f"all_leads_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True,
                help=f"Download all {len(df)} leads (ignores filters)",
            )

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 3: AI Analysis (Detail View)
# ═══════════════════════════════════════════════════════════════════════════════

with tab_analysis:
    if df.empty:
        st.info("No leads to analyze. Run a discovery first.")
    else:
        st.markdown("### 🤖 Individual Lead Analysis")
        st.caption(f"Analysis powered by: {get_analysis_mode()}")

        # Lead selector
        lead_names = df["Business Name"].tolist()
        selected_lead = st.selectbox(
            "Select a business to inspect",
            options=lead_names,
            index=0,
        )

        if selected_lead:
            row = df[df["Business Name"] == selected_lead].iloc[0]

            # Detail card
            col_d1, col_d2 = st.columns([2, 1])

            with col_d1:
                st.markdown(f"## {row.get('Business Name', 'N/A')}")
                st.markdown(f"**Category:** {row.get('Industry Category', 'N/A')}")
                st.markdown(f"**Location:** {row.get('Location', 'N/A')}")

                desc = row.get('Business Description', '')
                if desc:
                    st.markdown(f"**Description:** {desc}")

                st.markdown("---")

                st.markdown("#### 🌐 Digital Presence")
                web_status = row.get('Website Status', 'Unknown')
                url = row.get('Website URL', '')

                badge_class = {
                    "No Website": "badge-high",
                    "Poor Website": "badge-medium",
                    "Good Website": "badge-low",
                }.get(web_status, "badge-medium")

                st.markdown(
                    f'Website: <span class="badge {badge_class}">{web_status}</span>',
                    unsafe_allow_html=True,
                )
                if url:
                    st.markdown(f"🔗 [{url}]({url})")

                st.markdown("---")

                st.markdown("#### 📬 Contact Information")
                phone   = row.get("Phone Number", "")
                email   = row.get("Email Address", "")
                owner   = row.get("Owner / Founder", "")
                linkedin = row.get("LinkedIn Profile", "")

                contact_items = [
                    ("📞 Phone", phone),
                    ("📧 Email", email),
                    ("👤 Owner", owner),
                    ("🔗 LinkedIn", linkedin),
                ]
                for label, val in contact_items:
                    if val:
                        st.markdown(f"**{label}:** {val}")
                    else:
                        st.markdown(f"**{label}:** *Not available*")

            with col_d2:
                # Potential Score Card
                potential = row.get("Potential Category", "Medium")
                color = {"High": "#34d399", "Medium": "#fb923c", "Low": "#f87171"}.get(
                    potential, "#9ca3af"
                )
                emoji = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}.get(potential, "⚪")

                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, {color}15, {color}08);
                    border: 1px solid {color}40;
                    border-radius: 16px;
                    padding: 1.5rem;
                    text-align: center;
                    margin-bottom: 1rem;
                ">
                    <div style="font-size: 2.5rem; margin-bottom: 0.3rem;">{emoji}</div>
                    <div style="font-size: 1.8rem; font-weight: 800; color: {color};">
                        {potential}
                    </div>
                    <div style="font-size: 0.75rem; color: #9ca3af; text-transform: uppercase;
                                letter-spacing: 0.08em; font-weight: 600;">
                        Lead Potential
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # AI Reasoning
                reasoning = row.get("Reasoning", "No reasoning available.")
                st.markdown(f"""
                <div style="
                    background: var(--bg-card, #1a1d29);
                    border: 1px solid var(--border, #2d3148);
                    border-radius: 12px;
                    padding: 1.2rem;
                ">
                    <div style="font-size: 0.72rem; color: #9ca3af; text-transform: uppercase;
                                letter-spacing: 0.06em; font-weight: 700; margin-bottom: 0.5rem;">
                        🧠 AI Reasoning
                    </div>
                    <div style="color: #e8eaed; font-size: 0.9rem; line-height: 1.5;">
                        {reasoning}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Maps link
                maps_link = row.get("Google Maps Link", "")
                if maps_link:
                    st.markdown(f"[📍 View on Google Maps]({maps_link})")


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 4: Settings
# ═══════════════════════════════════════════════════════════════════════════════

with tab_settings:
    st.markdown("### ⚙️ System Configuration")

    col_set1, col_set2 = st.columns(2)

    with col_set1:
        st.markdown("#### 🔑 API Keys Status")
        st.markdown(
            f"{'✅' if serper_ok else '❌'} **Serper.dev** — "
            f"{'Configured' if serper_ok else 'Not set in `.env`'}"
        )
        st.markdown(
            f"{'✅' if gemini_ok else '❌'} **Gemini AI** — "
            f"{'Configured' if gemini_ok else 'Not set in `.env`'}"
        )
        st.markdown(
            f"{'✅' if openai_ok else '⚪'} **OpenAI** — "
            f"{'Configured' if openai_ok else 'Optional, not set'}"
        )

        st.markdown("---")
        st.markdown("#### 🤖 Analysis Mode")
        st.info(get_analysis_mode())

    with col_set2:
        st.markdown("#### 📊 Google Sheets Connection")
        sheets_status = get_sheets_config_status()

        if sheets_ok:
            if st.button("🔄  Test Connection", use_container_width=True):
                with st.spinner("Testing connection..."):
                    ok, msg = test_connection()
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

            url = get_sheet_url()
            if url:
                st.markdown(f"[📊 Open Google Sheet]({url})")
            st.caption(f"Worksheet: `{sheets_status['sheet_name']}`")
        else:
            missing_items = []
            if not sheets_status["has_spreadsheet_id"]:
                missing_items.append("Add `SPREADSHEET_ID` to `.env`.")
            if not sheets_status["has_credentials"]:
                missing_items.append(
                    "Save the service-account JSON at "
                    f"`{sheets_status['credentials_path']}` or set "
                    "`GOOGLE_SERVICE_ACCOUNT_JSON`."
                )

            st.warning(
                "Google Sheets not configured.\n\n"
                + "\n".join(f"- {item}" for item in missing_items)
            )
            st.markdown(
                """
                Setup checklist:

                1. Enable the Google Sheets API in Google Cloud.
                2. Create a Service Account and download its JSON key.
                3. Share the spreadsheet with the service account email.
                4. Restart Streamlit after editing `.env`.
                """
            )

    st.markdown("---")
    st.markdown("#### 📁 Setup Instructions")
    st.markdown("""
    1. **Copy** `.env.example` → `.env` and fill in your API keys
    2. **Serper.dev** — API key from [serper.dev](https://serper.dev)
    3. **Gemini** — Free at [aistudio.google.com](https://aistudio.google.com)
    4. **Google Sheets** — [Create Service Account](https://console.cloud.google.com/iam-admin/serviceaccounts)
    5. Run: `pip install -r requirements.txt`
    6. Run: `streamlit run app/streamlit_app.py`
    """)


# ─── Footer ──────────────────────────────────────────────────────────────────

st.markdown("---")
st.caption(
    "AI Business Lead Discovery System — "
    f"Built with Streamlit • {datetime.now():%Y-%m-%d %H:%M} • "
    f"{len(df)} leads loaded"
)
