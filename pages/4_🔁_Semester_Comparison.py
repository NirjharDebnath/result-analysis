# pages/4_📈_Semester_Comparison.py
import pandas as pd
import streamlit as st
from utils.constants import COLLEGE_NAME
from utils.processor import require_data, apply_course_stream_filters, get_gpa_columns
from utils.visualizer import render_sidebar_branding, render_footer, download_table_button
from utils.analytics import build_file_comparison_data
from utils.charts import plot_grouped_multi_metric_bars

st.set_page_config(page_title="Semester Comparison", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .stButton>button, .stDownloadButton>button {
        background-color: #D35400 !important; color: white !important; 
        border-radius: 8px !important; border: none !important; 
        padding: 10px 24px !important; font-weight: 600 !important; transition: 0.3s ease-in-out !important;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background-color: #E67E22 !important; transform: translateY(-2px) !important;
        box-shadow: 0 4px 10px rgba(211, 84, 0, 0.3) !important;
    }
    </style>
    """, unsafe_allow_html=True)

render_sidebar_branding()
st.header(COLLEGE_NAME)
st.title("📈 Inter-Semester & Session Comparison")

data = require_data()
if data:
    df, _ = data
    
    course_df = apply_course_stream_filters(df, "Select Course to Analyze", "comp_course")
    
    if course_df.empty:
        st.warning("No data found for the selected course.")
        st.stop()

    st.info("""
        💡 **How to use this page:** 1. Select **multiple GPA Metrics** (e.g., SGPA3, SGPA4, SGPA8).
        2. Select the **Groups** (Semesters/Exam Sessions) to view.
        3. The graph will group your selected metrics side-by-side for direct comparison.
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
    st.pyplot(fig, use_container_width=True)
    st.session_state["comparison_fig"] = fig

    with st.expander("📝 View Comparison Data Table"):
        display_table = comparison_results[
            (comparison_results["GROUP_LABEL"].isin(selected_groups)) & 
            (comparison_results["METRIC"].isin(selected_metrics))
        ].sort_values(["GROUP_LABEL", "METRIC"])
        st.dataframe(display_table, hide_index=True, use_container_width=True)
        download_table_button(display_table, "Download Comparison CSV", "semester_comparison.csv")

render_footer()