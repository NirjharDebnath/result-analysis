# pages/2_🏆_Rankings.py
import pandas as pd
import streamlit as st
from utils.constants import COLLEGE_NAME, SOFT_COLORS, UI_THEME
from utils.processor import require_data, apply_course_stream_filters, get_gpa_columns, parse_grade_value
from utils.visualizer import render_sidebar_branding, render_footer, download_table_button

st.set_page_config(page_title="Rankings", page_icon="🏆", layout="wide")

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