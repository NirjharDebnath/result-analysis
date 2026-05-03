# pages/2_🏆_Rankings.py
import pandas as pd
import streamlit as st
from utils.constants import COLLEGE_NAME
from utils.processor import require_data, apply_course_stream_filters, get_gpa_columns, parse_grade_value
from utils.visualizer import render_sidebar_branding, render_footer, download_table_button

st.set_page_config(page_title="Rankings", page_icon="🏆", layout="wide")

st.markdown("""
    <style>
    .stButton>button, .stDownloadButton>button {
        background-color: #1565C0 !important; color: white !important;
        border-radius: 8px !important; border: none !important;
        padding: 10px 24px !important; font-weight: 600 !important; transition: 0.3s ease-in-out !important;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background-color: #1976D2 !important; transform: translateY(-2px) !important;
        box-shadow: 0 4px 10px rgba(21, 101, 192, 0.3) !important;
    }
    </style>
""", unsafe_allow_html=True)

render_sidebar_branding()

st.header(COLLEGE_NAME)
st.title("🏆 Student Rankings")
st.caption("Rank students by GPA, individual subject marks, or total marks. Use the sidebar to choose a course, then pick your ranking method below.")

data = require_data()
if data:
    df, subject_cols = data
    course_df = apply_course_stream_filters(df, "Select Course", "rank_course")
    semesters = sorted(course_df["SEMESTER"].dropna().astype(str).unique().tolist())
    selected_semester = st.selectbox("Select Semester", semesters, key="rank_sem")
    
    # Filter down to the specific course and semester
    filtered_df = course_df[course_df["SEMESTER"].astype(str).str.strip() == str(selected_semester).strip()].copy()

    st.info("📌 **How to rank:** Choose a ranking basis (GPA / Subject / Total Marks), pick a ranking type, then select the specific column to rank by. The table will appear below with rank positions.")

    ranking_mode = st.radio("Ranking Basis", ["GPA Metrics", "By Subject", "Total Marks"], horizontal=True)
    rank_type = st.selectbox("Ranking Type", ["Standard", "Dense"])
    rank_method = "min" if rank_type == "Standard" else "dense"

    rank_df = filtered_df[["ROLL NO", "NAME", "COURSENAME", "SEMESTER"]].copy()
    metric_col = None

    if ranking_mode == "GPA Metrics":
        gpa_cols = get_gpa_columns(filtered_df)
        if gpa_cols:
            metric_col = st.selectbox("Select GPA Column to Rank By", gpa_cols)
            rank_df[metric_col] = pd.to_numeric(filtered_df[metric_col], errors="coerce")
        else:
            st.error("No GPA columns detected in this file.")

    elif ranking_mode == "By Subject":
        # --- THE FIX IS HERE ---
        # Only keep subjects that actually have data (not completely empty or NaN) in this filtered view
        valid_subject_choices = []
        for c in subject_cols:
            if c in filtered_df.columns:
                # Check if there is at least one row with actual text/numbers in this column
                has_data = filtered_df[c].astype(str).str.strip().replace(r'^(nan|None|)$', pd.NA, regex=True).notna().any()
                if has_data:
                    valid_subject_choices.append(c)

        if not valid_subject_choices:
            st.warning("No subjects found with data for this specific course and semester.")
        else:
            metric_col = st.selectbox("Select Subject", valid_subject_choices)
            # Extract numeric value from Grade(Points) format
            rank_df[metric_col] = filtered_df[metric_col].apply(lambda x: parse_grade_value(x)[1])

    else: # Total Marks
        # Also apply the valid subjects filter here so we don't loop through empty columns
        valid_subject_choices = [c for c in subject_cols if c in filtered_df.columns and filtered_df[c].astype(str).str.strip().replace(r'^(nan|None|)$', pd.NA, regex=True).notna().any()]
        
        overall_marks = []
        for _, row in filtered_df.iterrows():
            total = 0
            for col in valid_subject_choices:
                _, marks = parse_grade_value(row.get(col))
                if marks: total += marks
            overall_marks.append(total)
        metric_col = "TOTAL_MARKS"
        rank_df[metric_col] = overall_marks

    # Render the table if a valid metric was selected
    if metric_col:
        rank_df = rank_df.dropna(subset=[metric_col]).copy()
        rank_df["RANK"] = rank_df[metric_col].rank(method=rank_method, ascending=False).astype(int)
        rank_df = rank_df.sort_values(["RANK", metric_col, "NAME"], ascending=[True, False, True])

        st.dataframe(rank_df, width='stretch')
        download_table_button(rank_df, "Download rank list", "rank_list.csv")

render_footer()