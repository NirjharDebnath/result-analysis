import streamlit as st
from utils.constants import COLLEGE_NAME
from utils.processor import require_data, apply_course_stream_filters, get_gpa_columns
from utils.visualizer import render_sidebar_branding, render_footer
from utils.analytics import build_file_comparison_data
from utils.charts import plot_semester_metric_bars

st.set_page_config(page_title="Semester Comparison", page_icon="🔁", layout="wide")
render_sidebar_branding()

st.header(COLLEGE_NAME)
st.title("🔁 Semester / File Comparison")

data = require_data()
if data:
    df, _ = data

    # --- Duplicate / single-file guard ---
    source_files = df["SOURCE FILE"].unique().tolist() if "SOURCE FILE" in df.columns else []
    if len(source_files) < 2:
        st.info(
            "Only one result file is loaded. Upload **two or more** semester files from the "
            "home page to enable side-by-side comparison."
        )

    course_df = apply_course_stream_filters(df, "Select Course", "comparison_course")

    # Inform if a course exists in only one of the uploaded files
    if "SOURCE FILE" in course_df.columns:
        course_files = course_df["SOURCE FILE"].unique().tolist()
        if len(course_files) < 2:
            st.info(
                f"This course appears in only **one** of the uploaded files "
                f"(`{course_files[0] if course_files else '—'}`). "
                "Upload another file containing the same course to compare."
            )

    gpa_columns = get_gpa_columns(course_df)
    if not gpa_columns:
        st.warning("No GPA columns detected for this course.")
        st.stop()

    comparison_df = build_file_comparison_data(course_df, gpa_columns)

    if comparison_df.empty:
        st.warning("No comparable GPA data found for this course.")
        st.stop()

    sorted_groups = (
        comparison_df
        .drop_duplicates(subset=["GROUP_LABEL"])
        .sort_values(["SEMESTER_ORDER", "GROUP_LABEL"])["GROUP_LABEL"]
        .tolist()
    )
    metric_options = sorted(comparison_df["METRIC"].dropna().astype(str).unique().tolist())

    unique_sems = comparison_df["SEMESTER_LABEL"].nunique()
    mode_label = "exam session" if unique_sems == 1 else "semester"
    st.caption(
        f"Comparing **{len(sorted_groups)}** group(s) across **{len(metric_options)}** GPA metric(s) "
        f"(groups labelled by {mode_label})."
    )
    if len(sorted_groups) <= 1:
        st.info(
            "Only one group is detected for this course. Upload result files from different "
            "semesters or different exam sessions for richer comparison."
        )

    selected_groups = st.multiselect("Select groups to compare", sorted_groups, default=sorted_groups)
    selected_metrics = st.multiselect(
        "Select GPA metrics to compare",
        metric_options,
        default=metric_options[: min(2, len(metric_options))],
    )

    if not selected_metrics:
        st.warning("Please select at least one GPA metric.")
        st.stop()

    for metric in selected_metrics:
        st.pyplot(
            plot_semester_metric_bars(comparison_df, metric, selected_groups),
            use_container_width=True,
        )

    shown_df = comparison_df.copy()
    if selected_groups:
        shown_df = shown_df[shown_df["GROUP_LABEL"].isin(selected_groups)]
    shown_df = shown_df[shown_df["METRIC"].isin(selected_metrics)]
    st.dataframe(
        shown_df[["GROUP_LABEL", "SEMESTER_LABEL", "METRIC", "AVG_VALUE", "STUDENT_COUNT"]]
        .sort_values(["SEMESTER_ORDER", "GROUP_LABEL", "METRIC"]),
        use_container_width=True,
        hide_index=True,
    )

render_footer()
