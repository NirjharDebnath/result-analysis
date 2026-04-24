# pages/1_📊_Course_Insights.py
import pandas as pd
import streamlit as st
from utils.constants import COLLEGE_NAME
from utils.processor import require_data, apply_course_stream_filters, get_gpa_columns, parse_grade_value
from utils.visualizer import render_sidebar_branding, render_footer
from utils.analytics import get_class_masks, determine_student_status, calculate_subject_stats, calculate_z_scores
from utils.charts import plot_status_bars, plot_normal_curve, plot_z_score_distribution
from utils.pdf_generator import create_master_report_pdf

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
    div[data-baseweb="select"] > div {
        white-space: normal !important;
        word-wrap: break-word !important;
    }
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

    # --- SUBJECT FILTER ---
    skip_list = ["OVERALL RESULT", "SEMETER RESULT", "SEMESTER RESULT", "TOTAL MAR POINTS", "TOTAL MARK POINTS", "TOTAL MAR \nPOINTS"]
    valid_subjects = []
    
    for c in all_subject_cols:
        if c in filtered_df.columns and str(c).upper().strip() not in skip_list:
            has_real_data = False
            for val in filtered_df[c].dropna():
                grade, marks = parse_grade_value(val)
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

    # --- CALCULATE PASS PERCENTAGES & CORE METRICS ---
    total_students = len(filtered_df)
    current_pass = len(filtered_df[filtered_df["STATUS"] == "Current Batch"])
    current_backlog = len(filtered_df[filtered_df["STATUS"] == "Backlog (Current Batch)"])
    total_current = current_pass + current_backlog
    
    current_pass_pct = (current_pass / total_current * 100) if total_current > 0 else 0
    old_batch_count = len(filtered_df[filtered_df["STATUS"] == "Old Batch (Re-appearing)"])

    # --- PRE-GENERATE FIGURES FOR UI & PDF ---
    status_fig = plot_status_bars(filtered_df["STATUS"].value_counts(), total_students)
    stats_df = calculate_subject_stats(filtered_df, valid_subjects)

    # 🧮 DYNAMICALLY INJECT PASS PERCENTAGE INTO THE TABLE
    if not stats_df.empty and all(g in stats_df.columns for g in ['O', 'E', 'A', 'B', 'C', 'D', 'F']):
        total_graded = stats_df[['O', 'E', 'A', 'B', 'C', 'D', 'F']].sum(axis=1)
        passed = total_graded - stats_df['F']
        pass_pct = (passed / total_graded * 100).fillna(0).map(lambda x: f"{x:.1f}%")
        
        if "Skewness" in stats_df.columns:
            loc = stats_df.columns.get_loc("Skewness") + 1
            stats_df.insert(loc, "Pass %", pass_pct)
        else:
            stats_df["Pass %"] = pass_pct

    gpa_curve_fig = None
    subject_curve_fig = None
    z_summary_df = pd.DataFrame()

    tab1, tab2, tab3, tab4 = st.tabs(["📑 Executive Summary", "🧮 Statistical Matrix", "📈 Distribution Curves", "📥 Export PDF"])

    with tab1:
        st.subheader("Batch Overview & Pass Rates")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Evaluated", total_students)
        m2.metric("Current Batch Size", total_current)
        m3.metric("Current Batch Pass %", f"{current_pass_pct:.1f}%")
        m4.metric("Old Batch (Re-appearing)", old_batch_count)
        
        st.divider()

        col1, col2 = st.columns([1.5, 1])
        with col1:
            st.pyplot(status_fig, use_container_width=True)

        with col2:
            st.write("**Detailed Status Breakdown**")
            summary_data = []
            for s, c in filtered_df["STATUS"].value_counts().items():
                display_name = s
                if s == "Current Batch": display_name = "Current Batch (All Clear)"
                if s == "Backlog (Current Batch)": display_name = "Current Batch (Backlogs)"
                
                summary_data.append({
                    "Status Category": display_name, 
                    "Count": c, 
                    "% of Class": f"{(c/total_students*100):.1f}%"
                })
            st.dataframe(pd.DataFrame(summary_data), hide_index=True, use_container_width=True)
            
            st.write("") 
            if current_pass_pct >= 90:
                st.success(f"🌟 **Excellent Performance:** The current batch has a highly successful pass rate of {current_pass_pct:.1f}%.")
            elif current_pass_pct < 60:
                st.error(f"⚠️ **Attention Needed:** The current batch pass rate is only {current_pass_pct:.1f}%. Many students have backlogs.")
            else:
                st.warning(f"📊 **Average Performance:** The current batch pass rate is {current_pass_pct:.1f}%.")

    with tab2:
        st.subheader("Consolidated Result Matrix")
        if not stats_df.empty:
            st.dataframe(stats_df, width='stretch', hide_index=True)
            if "Skewness" in stats_df.columns:
                hardest_subject = stats_df.loc[stats_df["Skewness"].idxmax()]["Subject"]
                highest_skew = stats_df["Skewness"].max()
                if highest_skew > 0.5: 
                    st.warning(f"⚠️ **Anomaly Detected:** The subject **{hardest_subject}** has the highest positive skewness ({highest_skew}). This indicates a difficult paper where the majority scored below average.")

    with tab3:
        st.subheader("Statistical Bell Curves")
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
                gpa_curve_fig = plot_normal_curve(full_gpa, reg_gpa, title=f"{selected_gpa} Curve", is_grade_scale=False)
                st.pyplot(gpa_curve_fig, width='stretch')

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

                subject_curve_fig = plot_normal_curve(full_subj, reg_subj, title=f"{selected_subj} Distribution", is_grade_scale=True)
                st.pyplot(subject_curve_fig, width='stretch')

        st.divider()
        z_metric_choice = st.radio("Analyze Z-Scores for:", ["Selected Subject", "Selected GPA Metric"], horizontal=True)

        target_col = None
        if z_metric_choice == "Selected Subject" and selected_subj:
            target_col = selected_subj
        elif z_metric_choice == "Selected GPA Metric" and selected_gpa:
            target_col = selected_gpa

        if target_col:
            st.markdown(f"#### 🔍 Z-Score Analysis for: **{target_col}**")
            try:
                z_df = calculate_z_scores(display_df, target_col)
                if not z_df.empty:
                    z_summary_df = z_df[["ROLL NO", "NAME", "NUMERIC_VAL", "Z-Score", "Performance"]].copy()
                    z_summary_df.columns = ["ROLL NO", "NAME", "VALUE", "Z-SCORE", "CATEGORY"]
                    st.dataframe(z_summary_df, width='stretch', hide_index=True)

                    st.write("") 
                    c_top, c_worst = st.columns(2)
                    if len(z_df) > 0:
                        c_top.success(f"🏆 **Top Performer:** {z_df.iloc[0]['NAME']}  \n*(Z-Score: +{z_df.iloc[0]['Z-Score']:.2f}, Value: {z_df.iloc[0]['NUMERIC_VAL']})*")
                        c_worst.error(f"⚠️ **Needs Attention:** {z_df.iloc[-1]['NAME']}  \n*(Z-Score: {z_df.iloc[-1]['Z-Score']:.2f}, Value: {z_df.iloc[-1]['NUMERIC_VAL']})*")
                else:
                    st.warning(f"Not enough valid numerical data to calculate Z-Scores for {target_col}.")
            except Exception as e:
                st.error(f"Could not calculate Z-scores for {target_col}. Error: {e}")

    with tab4:
        st.subheader("📥 Export Master PDF Report")
        st.info("💡 **What this does:** Compiles the Executive Summary, the FULL Statistical Matrix, background-generates distribution curves for **every valid subject**, includes the Z-Score Table, and optionally attaches the Semester Comparison graph.")
        
        course_name_string = str(course_df["COURSENAME"].iloc[0]) if not course_df.empty else "Unknown Course"
        
        saved_comp_fig = st.session_state.get("comparison_fig")
        include_comp = False
        
        if saved_comp_fig:
            include_comp = st.checkbox("Include Semester Comparison Graph in PDF", value=True)
        else:
            st.info("💡 To include a comparison graph, visit the 'Semester Comparison' page and generate one first.")

        if st.button("Generate Master Report PDF"):
            if gpa_curve_fig is None:
                st.warning("⚠️ Please open Tab 3 at least once to select a GPA metric and Z-Score target before downloading.")
            else:
                with st.spinner("Generating graphs for all subjects and building PDF (this might take a few seconds)..."):
                    import matplotlib.pyplot as plt 
                    
                    try:
                        all_subject_figs = []
                        grade_to_point = {'O':10,'E':9,'A':8,'B':7,'C':6,'D':5,'F':0}
                        exclude_old_batch_state = exclude_old_batch 
                        
                        for subj in valid_subjects:
                            full_grades = filtered_df[subj].apply(lambda x: parse_grade_value(x)[0])
                            full_subj_num = pd.to_numeric(full_grades.map(grade_to_point), errors='coerce')

                            if not exclude_old_batch_state:
                                reg_grades = filtered_df[current_class_mask][subj].apply(lambda x: parse_grade_value(x)[0])
                                reg_subj_num = pd.to_numeric(reg_grades.map(grade_to_point), errors='coerce')
                            else:
                                reg_subj_num = None

                            fig = plot_normal_curve(full_subj_num, reg_subj_num, title=f"{subj} Distribution", is_grade_scale=True)
                            if fig is not None:
                                all_subject_figs.append(fig)

                        summary = {
                            "Total Evaluated": len(filtered_df),
                            "Course": course_name_string,
                            "Semester": selected_semester,
                            "Current Batch (Total)": int(total_current),
                            "Current Batch Pass %": f"{current_pass_pct:.1f}%",
                            "Old Batch Students": int(old_batch_count)
                        }
                        
                        pdf_bytes = create_master_report_pdf(
                            college_name=COLLEGE_NAME,
                            course_name=course_name_string,
                            semester=selected_semester,
                            summary_table=summary,
                            status_fig=status_fig, 
                            subject_stats_df=stats_df, 
                            gpa_curve_fig=gpa_curve_fig, 
                            subject_curve_figs=all_subject_figs, 
                            z_score_df=z_summary_df, 
                            comparison_fig=saved_comp_fig if include_comp else None
                        )
                        
                        for fig in all_subject_figs:
                            plt.close(fig)
                        
                        st.download_button(
                            label="Download Full Report",
                            data=pdf_bytes,
                            file_name=f"Result_Analysis_{selected_semester}.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"Error generating PDF. Details: {e}")

render_footer()