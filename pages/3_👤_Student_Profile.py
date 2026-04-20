# pages/3_👤_Student_Profile.py
import pandas as pd
import streamlit as st
from utils.constants import COLLEGE_NAME, PASSING_GRADES
from utils.processor import require_data, apply_course_stream_filters, get_gpa_columns, parse_grade_value
from utils.visualizer import render_sidebar_branding, render_footer, download_table_button

st.set_page_config(page_title="Student Profile", page_icon="👤", layout="wide")
render_sidebar_branding()

st.header(COLLEGE_NAME)
st.title("👤 Student Performance Dashboard")

data = require_data()
if data:
    df, all_subject_cols = data
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
                "SUBJECT": subject,
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

