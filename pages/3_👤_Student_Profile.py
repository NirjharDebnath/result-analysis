# pages/3_👤_Student_Profile.py
import pandas as pd
import streamlit as st
from utils.constants import COLLEGE_NAME, PASSING_GRADES, SOFT_COLORS, UI_THEME
from utils.processor import require_data, apply_course_stream_filters, get_gpa_columns, parse_grade_value
from utils.subjects import format_subject_label, get_subject_mapping
from utils.visualizer import render_sidebar_branding, render_footer, download_table_button

st.set_page_config(page_title="Student Profile", page_icon="👤", layout="wide")

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
st.title("👤 Student Performance Dashboard")
st.caption("Look up any individual student's grades and GPA across all subjects. Use the course selector in the sidebar, then search for a student by roll number or name below.")

data = require_data()
if data:
    df, all_subject_cols = data
    subject_mapping = get_subject_mapping()
    course_df = apply_course_stream_filters(df, "Select Course", "student_course")

    student_options = (
        course_df[["ROLL NO", "NAME"]]
        .dropna().astype(str)
        .assign(DISPLAY=lambda d: d["ROLL NO"] + " - " + d["NAME"])
    )

    selected_display = st.selectbox("Select Student", sorted(student_options["DISPLAY"].unique().tolist()))
    selected_roll = selected_display.split(" - ", 1)[0]
    student_row = course_df[course_df["ROLL NO"].astype(str) == selected_roll].head(1)

    if not student_row.empty:
        sr = student_row.iloc[0]
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Student Details")
            st.write(f"**Name:** {sr.get('NAME')}")
            st.write(f"**Roll No:** {sr.get('ROLL NO')}")
            st.write(f"**Course:** {sr.get('COURSENAME')}")
        
        with col2:
            st.subheader("GPA Metrics")
            gpa_cols = get_gpa_columns(course_df)
            for gpa in gpa_cols:
                val = sr.get(gpa, "N/A")
                st.metric(label=gpa, value=val)

        valid_subjects = [c for c in all_subject_cols if c in course_df.columns and course_df[c].notna().any()]
        subject_rows = []
        backlog_count = 0
        
        # --- FIX: Prevent Metadata from entering the Subject Table ---
        skip_list = ["OVERALL RESULT", "SEMETER RESULT", "SEMESTER RESULT"]

        for subject in valid_subjects:
            if subject.upper() in skip_list:
                continue # Skip metadata columns explicitly
                
            val = sr.get(subject)
            if pd.isna(val) or str(val).strip() == "": continue

            grade, marks = parse_grade_value(val)
            status = "Pass"
            if grade == "F" or (marks is not None and marks == 0 and grade != "Q"):
                status = "Fail"
                backlog_count += 1
            elif grade not in PASSING_GRADES and marks is None:
                status = "Unknown"

            subject_rows.append({
                "SUBJECT": format_subject_label(subject, subject_mapping),
                "GRADE": grade if grade else "N/A",
                "STATUS": status
            })

        st.divider()
        st.subheader("Subject-wise Grades")
        subj_df = pd.DataFrame(subject_rows)
        st.table(subj_df) 
        
        # --- FIX: Render Overall Result below the table ---
        overall_result = sr.get("OVERALL RESULT", None)
        if overall_result and pd.notna(overall_result):
            # st.info(f"**Overall Degree/Year Status:** {overall_result}")
            
            st.info(f"**Overall Degree/Year Status:** {overall_result} | Summary: {len(subj_df)} Subjects Evaluated | {backlog_count} Current Backlogs Detected")

render_footer()
