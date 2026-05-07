# pages/1_📊_Course_Insights.py
import os
import pandas as pd
import streamlit as st
from utils.constants import COLLEGE_NAME, LOGO_CANDIDATE_PATHS, SOFT_COLORS, UI_THEME
from utils.processor import require_data, apply_course_stream_filters, get_gpa_columns, parse_grade_value
from utils.subjects import get_subject_mapping, subject_label_formatter
from utils.visualizer import render_sidebar_branding, render_footer
from utils.analytics import get_class_masks, determine_student_status, calculate_subject_stats, calculate_z_scores, get_lateral_mask, get_semester_order
from utils.charts import (
    plot_status_bars,
    plot_normal_curve,
    plot_gpa_bucket_distribution,
    plot_normal_distribution_stats,
    plot_z_score_distribution,
    plot_executive_overview,
    plot_subject_grade_distribution_bars,
    plot_subject_metric_comparison_bars,
)
from utils.pdf_generator import create_master_report_pdf

st.set_page_config(page_title="Course Insights", page_icon="📊", layout="wide")

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
st.title("📊 Course & Subject Insights")
st.caption("Use the sidebar to select a course and semester. This page analyses the full batch — pass rates, subject performance, grade distributions, and statistical outliers.")

data = require_data()
if data:
    
    df, all_subject_cols = data
    subject_mapping = get_subject_mapping()
    format_subject = subject_label_formatter(subject_mapping)
    st.sidebar.header("Data Filters")
    course_df = apply_course_stream_filters(df, "Select Course", "insight_course")

    semesters = sorted(course_df["SEMESTER"].dropna().astype(str).unique().tolist())
    selected_semester = st.sidebar.selectbox("Select Semester", semesters)
    filtered_df = course_df[course_df["SEMESTER"].astype(str).str.strip() == str(selected_semester).strip()].copy()
    
    current_class_mask, old_batch_mask = get_class_masks(filtered_df)

    # --- CALCULATE ACADEMIC YEAR & EXAM SESSION ---
    sem_order = get_semester_order(selected_semester)
    if sem_order != 999:
        year_num = (sem_order + 1) // 2
        ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])
        academic_year_str = f"{ordinal(year_num)} Year"
    else:
        academic_year_str = "Unknown Year"

    exam_session_str = ""
    if "EXAM SESSION" in filtered_df.columns:
        mode_session = filtered_df["EXAM SESSION"].mode()
        if not mode_session.empty:
            exam_session_str = str(mode_session.iloc[0])

    # --- PROMINENT UI DISPLAY ---
    st.markdown(f"### 🎓 **{academic_year_str}** | {selected_semester}")
    if exam_session_str:
        st.caption(f"🗓️ **Exam Conducted:** {exam_session_str}")

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
    lateral_mask = get_lateral_mask(filtered_df)
    overview_fig = plot_executive_overview(filtered_df, current_class_mask, lateral_mask)
    stats_df = calculate_subject_stats(filtered_df, valid_subjects)

    # 🧮 DYNAMICALLY INJECT PASS PERCENTAGE INTO THE TABLE
    if not stats_df.empty and all(g in stats_df.columns for g in ['O', 'E', 'A', 'B', 'C', 'D', 'F']):
        total_graded = stats_df[['O', 'E', 'A', 'B', 'C', 'D', 'F']].sum(axis=1)
        passed = total_graded - stats_df['F']
        pass_pct = (passed / total_graded * 100).fillna(0).map(lambda x: f"{x:.1f}%")
        stats_df["Pass %"] = pass_pct

    if not stats_df.empty and "Subject" in stats_df.columns:
        stats_df["Subject"] = stats_df["Subject"].apply(format_subject)

    gpa_curve_fig = None
    subject_curve_fig = None
    z_summary_df = pd.DataFrame()
    subject_grade_bars_fig = None
    subject_metric_comp_fig = None

    # Pre-compute valid GPA columns: only those with actual numeric data for the selected course/semester
    _all_gpa_cols = get_gpa_columns(filtered_df)
    valid_gpa_cols = [
        col for col in _all_gpa_cols
        if pd.to_numeric(filtered_df[col], errors='coerce').dropna().shape[0] > 0
    ]

    tab1, tab2, tab3, tab4 = st.tabs(["📑 Executive Summary", "🧮 Statistical Matrix", "📈 Distribution Curves", "📥 Export PDF"])

    with tab1:
        st.subheader("Batch Overview & Pass Rates")
        st.caption("A high-level snapshot of the selected batch — how many students were evaluated, how many belong to the current year, and the overall pass/fail breakdown.")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Evaluated", total_students)
        m2.metric("Current Batch Size", total_current)
        m3.metric("Current Batch Pass %", f"{current_pass_pct:.1f}%")
        m4.metric("Old Batch (Re-appearing)", old_batch_count)
        
        st.divider()

        st.pyplot(overview_fig, width="content")

        st.divider()

        col1, col2 = st.columns([1.5, 1])
        with col1:
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
            st.dataframe(pd.DataFrame(summary_data), hide_index=True, width="stretch")
            
        with col2:
            st.write("") 
            if current_pass_pct >= 90:
                st.success(f"🌟 **Excellent Performance:** The current batch has a highly successful pass rate of {current_pass_pct:.1f}%.")
            elif current_pass_pct < 60:
                st.error(f"⚠️ **Attention Needed:** The current batch pass rate is only {current_pass_pct:.1f}%. Many students have backlogs.")
            else:
                st.warning(f"📊 **Average Performance:** The current batch pass rate is {current_pass_pct:.1f}%.")

    with tab2:
        st.subheader("Consolidated Result Matrix")
        st.caption("Subject-wise statistics table includes mean, median, standard deviation, skewness, pass percentage, and full grade distribution (O → F). Visual comparison charts use mean, median, standard deviation, and pass percentage.")
        if not stats_df.empty:
            st.divider()
            st.dataframe(stats_df, width='stretch', hide_index=True)
            if "Skewness" in stats_df.columns:
                hardest_subject = stats_df.loc[stats_df["Skewness"].idxmax()]["Subject"]
                highest_skew = stats_df["Skewness"].max()
                if highest_skew > 0.5: 
                    st.warning(f"⚠️ **Anomaly Detected:** The subject **{hardest_subject}** has the highest positive skewness ({highest_skew}). This indicates a difficult paper where the majority scored below average.")
            st.divider()
            stat_left, stat_right = st.columns(2)
            with stat_left:
                st.markdown("#### 📊 Per-Subject Grade Distribution")
                grade_subject_options = stats_df["Subject"].astype(str).tolist()
                selected_grade_subject = st.selectbox(
                    "Select Subject for Grade Distribution",
                    grade_subject_options,
                    key="stat_grade_subject_select",
                )
                subject_grade_bars_fig = plot_subject_grade_distribution_bars(stats_df, selected_subject=selected_grade_subject)
                st.pyplot(subject_grade_bars_fig, width="stretch")
            with stat_right:
                st.markdown("#### 📈 Comparative Metrics by Subject Code")
                metric_options = [m for m in ["Mean", "Median", "Std Dev (σ)", "Pass %"] if m in stats_df.columns]
                selected_metric = st.selectbox(
                    "Select Metric",
                    metric_options,
                    key="stat_metric_select",
                )
                subject_metric_comp_fig = plot_subject_metric_comparison_bars(
                    stats_df,
                    selected_metric=selected_metric,
                    use_subject_codes=True,
                )
                st.pyplot(subject_metric_comp_fig, width="stretch")

    with tab3:
        st.subheader("Statistical Bell Curves")
        with st.expander("💡 What is a Normal Distribution (Bell Curve) & What does it tell us?"):
            st.markdown("""
            A **Normal Distribution** is a visual representation of how grades are spread across the entire batch. In a perfectly balanced exam, the data naturally forms a symmetrical "Bell Curve", where the majority of students score near the class average (the peak), and fewer students score exceptionally high or low (the tails).

            **The Golden Rule (68-95-99.7 Rule):**
            In a standard normal distribution:
            * ~**68%** of students fall within 1 Standard Deviation ($\pm 1\sigma$) of the Mean ($\mu$). This is your "average" majority.
            * ~**95%** of students fall within 2 Standard Deviations ($\pm 2\sigma$).

            **How it helps us analyze results:**
            * **Detect Paper Difficulty (Skewness):** If the curve's peak is shifted heavily to the left, it means most students scored poorly, indicating a **tough paper** or strict grading. If shifted to the right, it was an **easy paper**.
            * **Measure Batch Disparity (Width):** A **wide and flat** curve (high standard deviation) means there is a massive gap between the top students and the bottom students. A **tall and narrow** curve means the batch is highly consistent and learned at the same pace.
            * **Identify True Outliers:** The shaded regions visually isolate the exceptional performers (the far right tail) and those who might need immediate academic intervention (the far left tail).
            """)
        st.caption("GPA metrics show bucket-wise student counts first, followed by a separate normal-distribution analysis with mean, standard deviation, and σ-region coverage. Subject distributions keep the histogram+curve view with the grade split pie chart shown below.")
        exclude_old_batch = st.toggle("🔍 Exclude Old Batch Students (Show Current Batch Only)", value=False)
        display_df = filtered_df[current_class_mask] if exclude_old_batch else filtered_df

        col_gpa, col_subj = st.columns(2)
        selected_gpa = None
        selected_subj = None

        grade_to_point = {'O': 10, 'E': 9, 'A': 8, 'B': 7, 'C': 6, 'D': 5, 'F': 0}

        with col_gpa:
            if valid_gpa_cols:
                selected_gpa = st.selectbox("Select GPA Metric", valid_gpa_cols)
                full_gpa = pd.to_numeric(filtered_df[selected_gpa], errors='coerce')
                reg_gpa = pd.to_numeric(filtered_df[current_class_mask][selected_gpa], errors='coerce') if not exclude_old_batch else None
                gpa_bucket_fig = plot_gpa_bucket_distribution(full_gpa, title=f"{selected_gpa} Distribution")
                gpa_curve_fig = plot_normal_distribution_stats(
                    reg_gpa if reg_gpa is not None else full_gpa,
                    title=f"{selected_gpa} Normal Distribution",
                    is_grade_scale=False,
                )
                st.pyplot(gpa_bucket_fig, width='stretch')
                st.pyplot(gpa_curve_fig, width='stretch')

        with col_subj:
            if valid_subjects:
                selected_subj = st.selectbox(
                    "Select Subject",
                    valid_subjects,
                    format_func=format_subject,
                )

                full_grades = display_df[selected_subj].apply(lambda x: parse_grade_value(x)[0])
                full_subj = pd.to_numeric(full_grades.map(grade_to_point), errors='coerce')
                # print(full_subj)
                if not exclude_old_batch:
                    reg_grades = filtered_df[current_class_mask][selected_subj].apply(lambda x: parse_grade_value(x)[0])
                    reg_subj = pd.to_numeric(reg_grades.map(grade_to_point), errors='coerce')
                else:
                    reg_subj = None

                subject_curve_fig, subject_pie_fig = plot_normal_curve(
                    full_subj,
                    reg_subj,
                    title=f"{format_subject(selected_subj)} Distribution",
                    is_grade_scale=True,
                )
                st.pyplot(subject_curve_fig, width='stretch')
                if subject_pie_fig is not None:
                    st.pyplot(subject_pie_fig, width='stretch')

        st.divider()
        z_metric_choice = st.radio("Analyze Z-Scores for:", ["Selected Subject", "Selected GPA Metric"], horizontal=True)

        target_col = None
        if z_metric_choice == "Selected Subject" and selected_subj:
            target_col = selected_subj
        elif z_metric_choice == "Selected GPA Metric" and selected_gpa:
            target_col = selected_gpa

        if target_col:
            st.markdown(f"#### 🔍 Z-Score Analysis for: **{format_subject(target_col)}**")
            try:
                z_df = calculate_z_scores(display_df, target_col)
                if not z_df.empty:
                    st.write("**Filter Learners by Performance Category:**")
                    with st.expander("💡 What is Z-Score Analysis & Why does it matter?"):
                        st.markdown("""
                        **Z-Score** is a statistical measurement that tells us how far a student's score is from the class average, measured in standard deviations. 

                        **The Formula:** $$Z = \\frac{(X - \\mu)}{\\sigma}$$  
                        *(Where $X$ is the student's score, $\\mu$ is the class mean, and $\\sigma$ is the standard deviation).*

                        **How it helps us here:**
                        Raw marks don't always tell the whole story. For example, scoring a 7 in a notoriously difficult subject where the class average is a 5 is a massive achievement. Conversely, scoring an 8 in an easy subject where everyone scored a 9 means the student actually underperformed relative to their peers.
                        
                        By converting grades to Z-Scores, we can:
                        * **Standardize Performance:** Compare a student's true performance across *different subjects* with varying difficulty levels.
                        * **Find True Outliers:** Accurately identify **Strong Performers** ($Z > +1$) and those who **Need Attention** ($Z < -1$), regardless of how hard or easy the question paper was.
                        """)
                    st.caption(" Students who fall under the > +1σ category are refered to as strong learners while those who fall under the < -1σ category are refered to as the weak learners category and the rest are categorised as decent. (*Note*: Discrimination is done only on mathematical basis and no personal biasness is involved in the process)")
                    perf_categories = ["Strong (> +1σ)", "Decent (-1σ to +1σ)", "Weak (< -1σ)"]
                    
                    selected_perfs = st.multiselect(
                        "Select categories to display (These will also be exported to the PDF)",
                        options=perf_categories,
                        default=["Strong (> +1σ)", "Weak (< -1σ)"],
                        label_visibility="collapsed"
                    )
                    
                    filtered_z_df = z_df[z_df["Performance"].isin(selected_perfs)]
                    
                    z_summary_df = filtered_z_df[["ROLL NO", "NAME", "NUMERIC_VAL", "Z-Score", "Performance"]].copy()
                    z_summary_df.columns = ["ROLL NO", "NAME", "VALUE", "Z-SCORE", "CATEGORY"]
                    st.dataframe(z_summary_df, width='stretch', hide_index=True)

                    st.write("") 
                    c_top, c_worst = st.columns(2)
                    if len(z_df) > 0:
                        c_top.success(f"🏆 **Top Performer (Overall):** {z_df.iloc[0]['NAME']}  \n*(Z-Score: +{z_df.iloc[0]['Z-Score']:.2f}, Value: {z_df.iloc[0]['NUMERIC_VAL']})*")
                        c_worst.error(f"⚠️ **Needs Attention (Overall):** {z_df.iloc[-1]['NAME']}  \n*(Z-Score: {z_df.iloc[-1]['Z-Score']:.2f}, Value: {z_df.iloc[-1]['NUMERIC_VAL']})*")
                else:
                    st.warning(f"Not enough valid numerical data to calculate Z-Scores for {format_subject(target_col)}.")
            except Exception as e:
                st.error(f"Could not calculate Z-scores for {format_subject(target_col)}. Error: {e}")

    with tab4:
        st.subheader("📥 Export Master PDF Report")
        st.info("💡 **What this does:** Compiles the Executive Summary, the FULL Statistical Matrix, background-generates distribution curves for **every valid subject**, includes the Z-Score Table, and optionally attaches the Semester Comparison graph.")
        st.caption("Click **Generate Master Report PDF** below. Once the PDF is ready, a download button will appear. The process may take a few seconds for large datasets.")
        
        course_name_string = str(course_df["COURSENAME"].iloc[0]) if not course_df.empty else "Unknown Course"
        
        saved_comp_fig = st.session_state.get("comparison_fig")
        include_comp = False
        
        if saved_comp_fig:
            include_comp = st.checkbox("Include Semester Comparison Graph in PDF", value=True)
        else:
            st.info("💡 To include a comparison graph, visit the 'Semester Comparison' page and generate one first.")
        include_stat_visuals = st.checkbox("Include Statistical Matrix visual charts in PDF", value=True)

        if st.button("Generate Master Report PDF"):
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

                        curve_fig, pie_fig = plot_normal_curve(
                            full_subj_num,
                            reg_subj_num,
                            title=f"{format_subject(subj)} Distribution",
                            is_grade_scale=True,
                        )
                        if curve_fig is not None:
                            all_subject_figs.append((curve_fig, pie_fig))

                    # Generate bell curves for all valid GPA columns
                    all_gpa_figs = []
                    for gpa_col in valid_gpa_cols:
                        full_gpa_data = pd.to_numeric(filtered_df[gpa_col], errors='coerce')
                        reg_gpa_data = pd.to_numeric(filtered_df[current_class_mask][gpa_col], errors='coerce') if not exclude_old_batch_state else None
                        gpa_buckets = plot_gpa_bucket_distribution(full_gpa_data, title=f"{gpa_col} Bucket Distribution")
                        gpa_curve = plot_normal_distribution_stats(
                            reg_gpa_data if reg_gpa_data is not None else full_gpa_data,
                            title=f"{gpa_col} Normal Distribution Stats",
                            is_grade_scale=False,
                        )
                        all_gpa_figs.append((gpa_buckets, gpa_curve))

                    all_stat_grade_figs = []
                    all_stat_metric_figs = []
                    if include_stat_visuals and not stats_df.empty:
                        for subject_name in stats_df["Subject"].astype(str).tolist():
                            all_stat_grade_figs.append(
                                plot_subject_grade_distribution_bars(stats_df, selected_subject=subject_name)
                            )
                        for metric_name in [m for m in ["Mean", "Median", "Std Dev (σ)", "Pass %"] if m in stats_df.columns]:
                            all_stat_metric_figs.append(
                                plot_subject_metric_comparison_bars(
                                    stats_df,
                                    selected_metric=metric_name,
                                    use_subject_codes=True,
                                )
                            )

                    summary = {
                        "Total Evaluated": len(filtered_df),
                        "Course": course_name_string,
                        "Semester": selected_semester,
                        "Current Batch (Total)": int(total_current),
                        "Current Batch Pass %": f"{current_pass_pct:.1f}%",
                        "Old Batch Students": int(old_batch_count)
                    }

                    # Build detailed batch overview table rows for the PDF
                    batch_overview_data = []
                    _status_display = {
                        "Current Batch": "Current Batch (All Clear)",
                        "Backlog (Current Batch)": "Current Batch (Backlogs)",
                    }
                    for s, c in filtered_df["STATUS"].value_counts().items():
                        display_name = _status_display.get(s, s)
                        batch_overview_data.append({
                            "Status Category": display_name,
                            "Count": int(c),
                            "% of Class": f"{(c / len(filtered_df) * 100):.1f}%",
                        })

                    # Resolve logo path
                    logo_path = None
                    for candidate in LOGO_CANDIDATE_PATHS:
                        if os.path.exists(candidate):
                            logo_path = candidate
                            break
                    
                    sem_order = get_semester_order(selected_semester)
                    if sem_order != 999:
                        year_num = (sem_order + 1) // 2
                        suffixes = {1: 'st', 2: 'nd', 3: 'rd'}
                        suffix = suffixes.get(year_num if year_num <= 3 else 0, 'th')
                        year_name_str = f"{year_num}{suffix} Year"
                    else:
                        year_name_str = "Unknown Year"

                    # 2. Get the Exam Year/Session
                    exam_session_str = ""
                    if "EXAM SESSION" in filtered_df.columns:
                        mode_val = filtered_df["EXAM SESSION"].mode()
                        if not mode_val.empty:
                            exam_session_str = str(mode_val.iloc[0])

                    # 3. Update the create_master_report_pdf call
                    pdf_bytes = create_master_report_pdf(
                        college_name=COLLEGE_NAME,
                        course_name=course_name_string,
                        semester=selected_semester,
                        year_name=year_name_str,       # New parameter
                        exam_session=exam_session_str, # New parameter
                        summary_table=summary,
                        status_fig=status_fig, 
                        subject_stats_df=stats_df, 
                        gpa_curve_figs=all_gpa_figs, 
                        subject_curve_figs=all_subject_figs, 
                        z_score_df=z_summary_df, 
                        comparison_fig=saved_comp_fig if include_comp else None,
                        overview_fig=overview_fig,
                        batch_overview_data=batch_overview_data,
                        logo_path=logo_path,
                        stat_grade_figs=all_stat_grade_figs if include_stat_visuals else None,
                        stat_metric_figs=all_stat_metric_figs if include_stat_visuals else None,
                    )
                    
                    for curve_fig, pie_fig in all_subject_figs:
                        plt.close(curve_fig)
                        if pie_fig is not None:
                            plt.close(pie_fig)
                    for bucket_fig, curve_fig in all_gpa_figs:
                        plt.close(bucket_fig)
                        if curve_fig is not None:
                            plt.close(curve_fig)
                    for fig in all_stat_grade_figs:
                        plt.close(fig)
                    for fig in all_stat_metric_figs:
                        plt.close(fig)
                    if subject_grade_bars_fig is not None:
                        plt.close(subject_grade_bars_fig)
                    if subject_metric_comp_fig is not None:
                        plt.close(subject_metric_comp_fig)
                    
                    st.download_button(
                        label="Download Full Report",
                        data=pdf_bytes,
                        file_name=f"Result_Analysis_{selected_semester}.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error generating PDF. Details: {e}")

render_footer()
