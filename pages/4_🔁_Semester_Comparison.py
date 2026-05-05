# pages/4_📈_Semester_Comparison.py
import pandas as pd
import streamlit as st
from utils.constants import COLLEGE_NAME, SOFT_COLORS, UI_THEME
from utils.processor import require_data, apply_course_stream_filters, get_gpa_columns
from utils.visualizer import render_sidebar_branding, render_footer, download_table_button
from utils.analytics import build_file_comparison_data
from utils.charts import plot_grouped_multi_metric_bars

st.set_page_config(page_title="Semester Comparison", page_icon="📈", layout="wide")

THEME = SOFT_COLORS

st.markdown(f"""
    <style>

        /* Main buttons */
        .stButton>button, .stDownloadButton>button {{
            background-color: {THEME["primary"]} !important;
            color: white !important;
            border-radius: 8px !important;
            border: none !important;
            padding: 10px 24px !important;
            font-weight: 600 !important;
            transition: 0.3s ease-in-out !important;
        }}

        .stButton>button:hover, .stDownloadButton>button:hover {{
            background-color: {THEME["button_hover"]} !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 10px {THEME["grid"]} !important;
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 10px;
        }}

        .stTabs [data-baseweb="tab"] {{
            background-color: {THEME["bg"]};
            border-radius: 6px 6px 0 0;
            padding: 10px 20px;
            border: 1px solid {THEME["grid"]};
            border-bottom: none;
            color: #2F3A45;
        }}

        .stTabs [aria-selected="true"] {{
            background-color: {THEME["primary"]} !important;
            color: white !important;
            font-weight: bold;
        }}

        /* Selectbox text wrapping */
        div[data-baseweb="select"] > div {{
            white-space: normal !important;
            word-wrap: break-word !important;
        }}

        /* Main app background */
        .stApp {{
            background-color: {THEME["bg"]};
        }}

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background-color: {THEME["sidebar"]} !important;
        }}

        /* Caption */
        div[data-testid="stCaptionContainer"] {{
            color: {UI_THEME["text"]} !important;
            opacity: 0.85;
        }}

        /* Success box */
        div[data-testid="stAlert"][kind="success"] {{
            background-color: {THEME["success_bg"]} !important;
            border-left: 5px solid {THEME["pass"]} !important;
            color: #2F3A45 !important;
        }}

        /* Info box */
        div[data-testid="stAlert"][kind="info"] {{
            background-color: {THEME["info_bg"]} !important;
            border-left: 5px solid {THEME["primary"]} !important;
            color: #2F3A45 !important;
        }}

        /* Warning box */
        div[data-testid="stAlert"][kind="warning"] {{
            background-color: {THEME["warning_bg"]} !important;
            border-left: 5px solid {THEME["lag"]} !important;
            color: #2F3A45 !important;
        }}

        /* Error box */
        div[data-testid="stAlert"][kind="error"] {{
            background-color: {THEME["error_bg"]} !important;
            border-left: 5px solid {THEME["fail"]} !important;
            color: #2F3A45 !important;
        }}
        
        /* Selectbox selected item */
        div[data-baseweb="select"] > div {{
            # background-color: {THEME["bg"]} !important;
            border: 1px solid {THEME["grid"]} !important;
            color: #2F3A45 !important;
        }}

        /* Dropdown hover */
        div[data-baseweb="option"]:hover {{
            background-color: {THEME["accent"]} !important;
            color: #2F3A45 !important;
        }}

        /* Selected dropdown option */
        div[aria-selected="true"][role="option"] {{
            background-color: {THEME["primary"]} !important;
            color: white !important;
        }}
    </style>
""", unsafe_allow_html=True)

render_sidebar_branding()
st.header(COLLEGE_NAME)
st.title("📈 Inter-Semester & Session Comparison")
st.caption("Compare GPA metrics across multiple semesters or exam sessions for the same course. Upload result files from different semesters first, then use this page to visualise trends over time.")

data = require_data()
if data:
    df, _ = data
    
    course_df = apply_course_stream_filters(df, "Select Course to Analyze", "comp_course")
    
    if course_df.empty:
        st.warning("No data found for the selected course.")
        st.stop()

    st.info("""
        💡 **How to use this page:**
        1. Select **one or more GPA Metrics** to compare (e.g., SGPA from Semester 3, 4, 8).
        2. Choose how failing grades ('F') are counted — strict average includes zeros, pass average ignores failed students.
        3. Pick the **Groups** (semester / exam sessions) you want to visualise side-by-side.
        4. The bar chart groups your selected metrics for direct comparison across sessions.
        5. After generating, the chart is also saved and can be included in the PDF report from the Course Insights page.
    """)

    gpa_options = get_gpa_columns(course_df)
    if not gpa_options:
        st.error("No GPA columns detected in the uploaded data.")
        st.stop()

    selected_metrics = st.multiselect(
        "Select GPA Metrics to Compare", 
        options=gpa_options, 
        default=[gpa_options[0]] if gpa_options else []
    )

    if not selected_metrics:
        st.warning("Please select at least one metric to visualize.")
        st.stop()

    st.divider()
    st.subheader("⚙️ Calculation Settings")
    f_handling = st.radio(
        "How should Failing grades ('F') be handled in the average?",
        [
            "Count 'F' as 0.0 (Strict Average: Lowers class average, includes failed students in headcount)", 
            "Ignore 'F' (Pass Average: Excludes failed students, calculates average only for valid numeric scores)"
        ],
        horizontal=False
    )

    # --- HANDLE 'F' LOGIC BASED ON USER CHOICE ---
    working_df = course_df.copy()
    
    if "Count 'F' as 0.0" in f_handling:
        for col in selected_metrics:
            # 1. Safely convert to numeric first (turns blanks and text into NaN)
            temp_numeric = pd.to_numeric(working_df[col], errors='coerce')
            
            # 2. Check for literal 'F' in the column itself
            is_literal_f = working_df[col].astype(str).str.strip().str.upper() == 'F'
            temp_numeric = temp_numeric.mask(is_literal_f, 0.0)
            
            # 3. Check the Result column for fails/backlogs (where SGPA is left blank by the college)
            if "SEMESTER RESULT" in working_df.columns:
                is_fail = ~working_df["SEMESTER RESULT"].astype(str).str.upper().str.contains("PASS", na=False)
                # If they failed and have no GPA recorded, force it to 0.0 so they are counted
                temp_numeric = temp_numeric.mask(is_fail & temp_numeric.isna(), 0.0)
            
            # Put the cleaned data back into the dataframe
            working_df[col] = temp_numeric.astype(str)
    
    comparison_results = build_file_comparison_data(working_df, selected_metrics)
    comparison_results = comparison_results[comparison_results["AVG_VALUE"] > 1]
    
    if comparison_results.empty:
        st.error("Could not process comparison data. Ensure your files have numeric GPA values.")
        st.stop()

    all_groups = comparison_results["GROUP_LABEL"].unique().tolist()
    selected_groups = st.multiselect(
        "Select Semester/Exam Sessions to Include",
        options=all_groups,
        default=all_groups
    )

    if not selected_groups:
        st.warning("Select at least one group to display the chart.")
        st.stop()

    st.divider()
    
    # --- RENDER SINGLE COMBINED GRAPH ---
    fig = plot_grouped_multi_metric_bars(
        comparison_results, 
        selected_metrics=selected_metrics,
        selected_groups=selected_groups,
        title="Combined GPA Comparison"
    )
    st.pyplot(fig, width='stretch')
    st.session_state["comparison_fig"] = fig

    with st.expander("📝 View Comparison Data Table"):
        display_table = comparison_results[
            (comparison_results["GROUP_LABEL"].isin(selected_groups)) & 
            (comparison_results["METRIC"].isin(selected_metrics))
        ].sort_values(["GROUP_LABEL", "METRIC"])
        st.dataframe(display_table, hide_index=True, width='stretch')
        download_table_button(display_table, "Download Comparison CSV", "semester_comparison.csv")

render_footer()