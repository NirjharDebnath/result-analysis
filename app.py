import io
from pathlib import Path

import pandas as pd
import streamlit as st

from result_analysis.analytics import (
    backlog_lists,
    classify_students,
    consolidated_subject_matrix,
    grade_only_subject_table,
    is_regular_roll,
    normal_curve_points,
    status_summary_table,
    top_and_lowest_by_subject,
)
from result_analysis.constants import AUTUMN_COLORS, COLLEGE_NAME
from result_analysis.parsing import (
    get_gpa_columns,
    parse_grade_value,
    read_uploaded_dataset,
    validate_dataset,
)
from result_analysis.plotting import (
    bar_with_labels,
    metric_distribution_bar,
    normal_curve_figure,
)
from result_analysis.reporting import build_pdf_summary

st.set_page_config(page_title="Result Analysis", page_icon="📊", layout="wide")


@st.cache_data
def get_sample_template_csv() -> bytes:
    sample_path = Path(__file__).resolve().parent / "example_input" / "newresult - ResultCollegeLogin.csv"
    if sample_path.exists():
        return sample_path.read_bytes()

    sample = pd.DataFrame(
        {
            "ROLL NO": ["10271025001"],
            "NAME": ["STUDENT NAME"],
            "College Name": ["COLLEGE NAME"],
            "Semester": ["Third Semester"],
            "COURSE CODE": ["710"],
            "COURSENAME": ["Master of Computer Application"],
            "SUBJ-101": ["A(32)"],
            "SUBJ-102": ["B(28)"],
            "SGPA": ["8.00"],
            "SEMETER RESULT": ["PASS"],
            "TOTAL MAR POINTS": ["0"],
        }
    )
    return sample.to_csv(index=False).encode("utf-8")


def apply_autumn_style():
    st.markdown(
        f"""
        <style>
            .stApp {{ background: linear-gradient(180deg, {AUTUMN_COLORS['bg']} 0%, #FFFDF9 100%); color: {AUTUMN_COLORS['text']}; }}
            .block-container {{ padding-top: 1rem; }}
            .stMetric {{ background: {AUTUMN_COLORS['card']}; border-radius: 10px; padding: 6px 10px; }}
            .stButton > button, .stDownloadButton > button {{
                background: {AUTUMN_COLORS['primary']}; color: white; border-radius: 8px; border: none;
            }}
            .stButton > button:hover, .stDownloadButton > button:hover {{ background: {AUTUMN_COLORS['secondary']}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def plot_download(fig, filename: str):
    st.pyplot(fig, use_container_width=True)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=160)
    st.download_button(
        label=f"Download {filename}",
        data=buf.getvalue(),
        file_name=filename,
        mime="image/png",
        use_container_width=True,
    )


def render_upload():
    st.header(COLLEGE_NAME)
    st.title("📄 Upload Result File")
    st.info("Upload CSV/XLS/XLSX, then choose course, academic year, and semester for focused analysis.")

    st.download_button(
        "Download example input file",
        data=get_sample_template_csv(),
        file_name="example_result_input.csv",
        mime="text/csv",
        use_container_width=True,
    )

    uploaded_file = st.file_uploader("Upload result file", type=["csv", "xls", "xlsx"])
    if not uploaded_file:
        return

    try:
        df = read_uploaded_dataset(uploaded_file)
    except Exception as exc:
        st.error(f"Unable to read file: {exc}")
        return

    errors, metadata_cols, subject_cols = validate_dataset(df)
    if errors:
        st.error("Validation failed")
        for err in errors:
            st.write(f"- {err}")
        return

    df["IS_REGULAR"] = df["ROLL NO"].astype(str).apply(is_regular_roll)
    st.session_state["validated_df"] = df
    st.session_state["subject_cols"] = subject_cols
    st.session_state["previous_backlog_students"] = df.loc[~df["IS_REGULAR"], ["ROLL NO", "NAME"]].drop_duplicates().to_dict("records")

    st.success("Dataset validated successfully.")
    c1, c2 = st.columns(2)
    with c1:
        st.write("Metadata columns")
        st.code(", ".join(metadata_cols))
    with c2:
        st.write("Detected subject columns")
        st.code(", ".join(subject_cols))
    st.dataframe(df.head(50), use_container_width=True)


def get_filtered_scope():
    df = st.session_state.get("validated_df")
    subject_cols = st.session_state.get("subject_cols")
    if df is None or subject_cols is None:
        st.warning("Please upload and validate a dataset first.")
        return None

    courses = sorted(df["COURSENAME"].dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique())
    if not courses:
        st.warning("No course values found in uploaded file.")
        return None

    col1, col2, col3 = st.columns(3)
    selected_course = col1.selectbox("Course", courses)
    course_df = df[df["COURSENAME"].astype(str).str.strip() == selected_course].copy()

    academic_years = sorted(course_df["ACADEMIC YEAR"].fillna("Unknown").astype(str).str.strip().replace("", "Unknown").unique())
    selected_year = col2.selectbox("Academic Year", academic_years)
    year_df = course_df[course_df["ACADEMIC YEAR"].fillna("Unknown").astype(str).str.strip().replace("", "Unknown") == selected_year].copy()

    semesters = sorted(year_df["SEMESTER"].dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique())
    if not semesters:
        st.warning("No semester values found for selected course/year.")
        return None
    selected_sem = col3.selectbox("Semester", semesters)

    filtered_df = year_df[year_df["SEMESTER"].astype(str).str.strip() == selected_sem].copy()
    available_subjects = [c for c in subject_cols if c in filtered_df.columns and filtered_df[c].astype(str).str.strip().ne("").any()]
    return filtered_df, available_subjects, selected_course, selected_year, selected_sem


def render_main_analysis():
    st.header(COLLEGE_NAME)
    st.title("📊 Main Result Analysis")

    scoped = get_filtered_scope()
    if scoped is None:
        return

    filtered_df, subjects, selected_course, selected_year, selected_sem = scoped
    if not subjects:
        st.warning("No subject columns available for selected scope.")
        return

    st.subheader("Overview")
    student_status_df, fail_entries = classify_students(filtered_df, subjects)
    status_table = status_summary_table(student_status_df)

    c1, c2, c3 = st.columns(3)
    c1.metric("Students", len(filtered_df))
    c2.metric("Backlog / Year Lag Students", int((student_status_df["STUDENT_STATUS"] != "Passed").sum()))
    c3.metric("Previous Backlog Roll Nos", len(st.session_state.get("previous_backlog_students", [])))

    fig_status = bar_with_labels(
        status_table,
        "STUDENT_STATUS",
        "Students",
        "Students with Passed / Backlog / Year Lag",
        [AUTUMN_COLORS["pass"], AUTUMN_COLORS["backlog"], AUTUMN_COLORS["year_lag"]],
    )
    plot_download(fig_status, "student_status_bar.png")
    st.dataframe(status_table, use_container_width=True)
    pass_count = int(status_table.loc[status_table["STUDENT_STATUS"] == "Passed", "Students"].sum())
    back_count = int(status_table.loc[status_table["STUDENT_STATUS"] == "Backlog", "Students"].sum())
    year_lag_count = int(status_table.loc[status_table["STUDENT_STATUS"] == "Year Lag", "Students"].sum())
    st.info(
        f"Passed: {pass_count} students ({status_table.loc[status_table['STUDENT_STATUS']=='Passed', 'Percent'].sum():.2f}%) | "
        f"Backlog: {back_count} students | Year Lag: {year_lag_count} students"
    )

    st.subheader("SGPA Standard Deviation / Normal Curve")
    use_regular_only_sgpa = st.toggle("Exclude previous backlog roll numbers for SGPA curve", value=False)
    sgpa_base = filtered_df[filtered_df["IS_REGULAR"]].copy() if use_regular_only_sgpa else filtered_df
    sgpa_series = pd.to_numeric(sgpa_base.get("SGPA", pd.Series(dtype=float)), errors="coerce")
    x, y, mean, std = normal_curve_points(sgpa_series)
    fig_sgpa = normal_curve_figure(sgpa_series, x, y, mean, std, "SGPA Distribution with Normal Curve", "SGPA")
    plot_download(fig_sgpa, "sgpa_normal_curve.png")

    st.subheader("Per Subject Standard Deviation / Normal Curve")
    selected_subject = st.selectbox("Select subject", subjects)
    use_regular_only_subject = st.toggle("Exclude previous backlog roll numbers for subject curve", value=False)
    subject_base = filtered_df[filtered_df["IS_REGULAR"]].copy() if use_regular_only_subject else filtered_df
    subject_marks = subject_base[selected_subject].apply(lambda v: parse_grade_value(v)[1])
    sx, sy, sm, ss = normal_curve_points(subject_marks)
    fig_subject = normal_curve_figure(subject_marks, sx, sy, sm, ss, f"{selected_subject} Distribution with Normal Curve", selected_subject)
    plot_download(fig_subject, f"{selected_subject}_normal_curve.png")

    st.subheader("GPA Distribution Bar Graph")
    gpa_metrics = [c for c in get_gpa_columns(filtered_df) if c in filtered_df.columns]
    if not gpa_metrics:
        st.warning("No SGPA/YGPA/DGPA column found for this selection.")
    else:
        metric = st.selectbox("Select metric", gpa_metrics)
        fig_metric = metric_distribution_bar(filtered_df[metric], metric)
        plot_download(fig_metric, f"{metric.lower()}_distribution.png")

    st.subheader("Consolidated Tabular Result Analysis")
    consolidated = consolidated_subject_matrix(filtered_df, subjects)
    st.dataframe(consolidated.round(3), use_container_width=True)
    st.download_button(
        "Download consolidated matrix",
        consolidated.to_csv(index=False).encode("utf-8"),
        file_name="consolidated_matrix.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.subheader("Subject Top Scorers and Lowest Scorers")
    top_low = top_and_lowest_by_subject(filtered_df, subjects)
    if top_low.empty:
        st.info("No numeric marks available for topper/lowest analysis.")
    else:
        for _, row in top_low.iterrows():
            st.write(f"**{row['SUBJECT']}** → Topper: {row['TOPPER']} ({row['TOPPER_SCORE']:.2f}), Lowest: {row['LOWEST']} ({row['LOWEST_SCORE']:.2f})")

    st.subheader("Backlog / Year Lag Details")
    backlog_students, most_backlog_subjects = backlog_lists(student_status_df, fail_entries)
    st.write("Students with backlog or year lag")
    st.dataframe(backlog_students, use_container_width=True)
    st.write("Subjects where most students got backlog")
    st.dataframe(most_backlog_subjects, use_container_width=True)

    with st.expander("Grade-only student subject table (no numeric grade points shown)"):
        grade_table = grade_only_subject_table(filtered_df, subjects)
        st.dataframe(grade_table, use_container_width=True)

    st.subheader("Download complete summary")
    summary_pdf = build_pdf_summary(
        filtered_df=filtered_df,
        subjects=subjects,
        gpa_metric=(gpa_metrics[0] if gpa_metrics else "SGPA"),
        include_regular_only=use_regular_only_sgpa,
        subject_for_curve=selected_subject,
        title_meta={
            "course": selected_course,
            "academic_year": selected_year,
            "semester": selected_sem,
        },
    )
    st.download_button(
        "Download one-file analysis summary (PDF)",
        data=summary_pdf,
        file_name="result_analysis_summary.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


def render_sidebar():
    st.sidebar.title("Result Analysis")
    page = st.sidebar.radio("Navigate", ["Upload Result Dataset", "Main Result Analysis"])
    return page


apply_autumn_style()
selected_page = render_sidebar()

if selected_page == "Upload Result Dataset":
    render_upload()
else:
    render_main_analysis()

st.markdown("---")
st.caption("© Designed by Nirjhar Debnath, Dept of CSE, Kalyani Government Engineering College.")
