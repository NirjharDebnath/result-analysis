# pages/1_📊_Course_Insights.py
import pandas as pd
import streamlit as st
from utils.constants import COLLEGE_NAME
from utils.processor import require_data, apply_course_stream_filters, get_gpa_columns, parse_grade_value
from utils.visualizer import render_sidebar_branding, render_footer
from utils.analytics import get_class_masks, determine_student_status, calculate_subject_stats, calculate_z_scores
from utils.charts import plot_status_bars, plot_normal_curve

st.set_page_config(page_title="Course Insights", page_icon="📊", layout="wide")

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
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #FDF5E6; border-radius: 6px 6px 0 0; padding: 10px 20px;
        border: 1px solid #EAECEE; border-bottom: none;
    }
    .stTabs [aria-selected="true"] { background-color: #D35400 !important; color: white !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

render_sidebar_branding()
st.header(COLLEGE_NAME)
st.title("📊 Course & Subject Insights")

data = require_data()
if data:
    df, all_subject_cols = data
    st.sidebar.header("Data Filters")
    course_df = apply_course_stream_filters(df, "Select Course", "insight_course")

    semesters = sorted(course_df["SEMESTER"].dropna().astype(str).unique().tolist())
    selected_semester = st.sidebar.selectbox("Select Semester", semesters)
    filtered_df = course_df[course_df["SEMESTER"].astype(str).str.strip() == str(selected_semester).strip()].copy()

    # --- THE FIX: BULLETPROOF SUBJECT FILTER ---
    skip_list = ["OVERALL RESULT", "SEMETER RESULT", "SEMESTER RESULT", "TOTAL MAR POINTS", "TOTAL MARK POINTS", "TOTAL MAR \nPOINTS"]
    valid_subjects = []
    
    for c in all_subject_cols:
        if c in filtered_df.columns and str(c).upper().strip() not in skip_list:
            # We use our own parser to check if there's any actual grade data in this column
            has_real_data = False
            for val in filtered_df[c].dropna():
                grade, marks = parse_grade_value(val)
                # If parse_grade_value successfully extracts a grade or a mark, it's a real subject!
                if grade is not None or marks is not None:
                    has_real_data = True
                    break
            
            if has_real_data:
                valid_subjects.append(c)

    if filtered_df.empty:
        st.warning("No data found for this selection.")
        st.stop()

    filtered_df = determine_student_status(filtered_df, selected_semester)
    current_class_mask, old_batch_mask = get_class_masks(filtered_df)

    tab1, tab2, tab3 = st.tabs(["📑 Executive Summary", "🧮 Statistical Matrix", "📈 Distribution Curves"])

    with tab1:
        st.subheader("Batch Overview")
        st.info("💡 **What this shows:** A high-level view separating the current batch (Regular + Laterals) from older batch students reappearing for exams.")
        col1, col2 = st.columns([1.5, 1])
        with col1:
            st.pyplot(plot_status_bars(filtered_df["STATUS"].value_counts()), use_container_width=True)

        with col2:
            st.write("**Tabular Result Summary**")
            total_students = len(filtered_df)
            summary_data = [{"Status": status, "Count": count, "Percentage": f"{(count / total_students * 100):.1f}%"} for status, count in filtered_df["STATUS"].value_counts().items()]
            st.dataframe(pd.DataFrame(summary_data), hide_index=True, use_container_width=True)
            st.divider()
            st.write(f"🎓 **Total Evaluated:** {total_students}")
            st.write(f"🍁 **Current Batch (Regular + Lateral):** {current_class_mask.sum()}")
            st.write(f"🍂 **Old Batch (Re-appearing):** {old_batch_mask.sum()}")

    with tab2:
        st.subheader("Consolidated Result Matrix")
        stats_df = calculate_subject_stats(filtered_df, valid_subjects)
        if not stats_df.empty:
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
            if "Skewness" in stats_df.columns:
                hardest_subject = stats_df.loc[stats_df["Skewness"].idxmax()]["Subject"]
                highest_skew = stats_df["Skewness"].max()
                if highest_skew > 0.5: 
                    st.warning(f"⚠️ **Anomaly Detected:** The subject **{hardest_subject}** has the highest positive skewness ({highest_skew}). This indicates a difficult paper where the majority scored below average.")

    with tab3:
        st.subheader("Statistical Bell Curves")
        st.info("💡 **What this shows:** The Normal Distribution of marks/GPAs. The orange line isolates your Current Batch, while the shaded area shows the whole class.")

        exclude_old_batch = st.toggle("🔍 Exclude Old Batch Students (Show Current Batch Only)", value=False)
        display_df = filtered_df[current_class_mask] if exclude_old_batch else filtered_df

        col_gpa, col_subj = st.columns(2)
        selected_gpa = None
        selected_subj = None

        grade_to_point = {'O': 10, 'E': 9, 'A': 8, 'B': 7, 'C': 6, 'D': 5, 'F': 0}

        with col_gpa:
            gpa_cols = get_gpa_columns(filtered_df)
            if gpa_cols:
                selected_gpa = st.selectbox("Select GPA Metric", gpa_cols)
                full_gpa = pd.to_numeric(filtered_df[selected_gpa], errors='coerce')
                reg_gpa = pd.to_numeric(filtered_df[current_class_mask][selected_gpa], errors='coerce') if not exclude_old_batch else None
                st.pyplot(plot_normal_curve(full_gpa, reg_gpa, title=f"{selected_gpa} Curve", is_grade_scale=False), use_container_width=True)

        with col_subj:
            if valid_subjects:
                selected_subj = st.selectbox("Select Subject", valid_subjects)

                full_grades = filtered_df[selected_subj].apply(lambda x: parse_grade_value(x)[0])
                full_subj = pd.to_numeric(full_grades.map(grade_to_point), errors='coerce')

                if not exclude_old_batch:
                    reg_grades = filtered_df[current_class_mask][selected_subj].apply(lambda x: parse_grade_value(x)[0])
                    reg_subj = pd.to_numeric(reg_grades.map(grade_to_point), errors='coerce')
                else:
                    reg_subj = None

                st.pyplot(plot_normal_curve(full_subj, reg_subj, title=f"{selected_subj} Distribution", is_grade_scale=True), use_container_width=True)

        st.divider()
        z_metric_choice = st.radio("Analyze Z-Scores for:", ["Selected Subject", "Selected GPA Metric"], horizontal=True)

        target_col = None
        if z_metric_choice == "Selected Subject" and selected_subj:
            target_col = selected_subj
        elif z_metric_choice == "Selected GPA Metric" and selected_gpa:
            target_col = selected_gpa

        if target_col:
            st.markdown(f"#### 🔍 Z-Score Analysis for: **{target_col}**")
            st.caption("Identifies students significantly above or below the class average based on Standard Deviations (\u03c3). Z-Score > 1 means excellent performance; Z-Score < -1 means struggling performance.")
            try:
                z_df = calculate_z_scores(display_df, target_col)
                
                if not z_df.empty:
                    # Make a copy for display so we don't overwrite the original columns we need
                    z_summary = z_df[["ROLL NO", "NAME", "NUMERIC_VAL", "Z-Score", "Performance"]].copy()
                    z_summary.columns = ["ROLL NO", "NAME", "VALUE", "Z-SCORE", "CATEGORY"]
                    st.dataframe(z_summary.head(20), use_container_width=True, hide_index=True)

                    st.write("") 
                    c_top, c_worst = st.columns(2)
                    if len(z_df) > 0:
                        # --- THE FIX: We use the original z_df column names here, which prevents the KeyError crash! ---
                        c_top.success(f"🏆 **Top Performer:** {z_df.iloc[0]['NAME']}  \n*(Z-Score: +{z_df.iloc[0]['Z-Score']:.2f}, Value: {z_df.iloc[0]['NUMERIC_VAL']})*")
                        c_worst.error(f"⚠️ **Needs Attention:** {z_df.iloc[-1]['NAME']}  \n*(Z-Score: {z_df.iloc[-1]['Z-Score']:.2f}, Value: {z_df.iloc[-1]['NUMERIC_VAL']})*")
                else:
                    st.warning(f"Not enough valid numerical data to calculate Z-Scores for {target_col}.")
                    
            except Exception as e:
                st.error(f"Could not calculate Z-scores for {target_col}. Error: {e}")

render_footer()