import streamlit as st
from utils.constants import COLLEGE_NAME
from utils.processor import require_data, apply_course_stream_filters, get_gpa_columns
from utils.visualizer import render_sidebar_branding, render_footer
from utils.analytics import aggregate_gpa_comparison
from utils.charts import plot_semester_metric_bars

st.set_page_config(page_title="Semester Comparison", page_icon="🔁", layout="wide")
render_sidebar_branding()

st.header(COLLEGE_NAME)
st.title("🔁 Semester / Academic-Year Comparison")

data = require_data()
if data:
    df, _ = data
    course_df = apply_course_stream_filters(df, "Select Course", "comparison_course")

    gpa_columns = get_gpa_columns(course_df)
    comparison_df = aggregate_gpa_comparison(course_df, gpa_columns)

    if comparison_df.empty:
        st.warning("No comparable GPA data found for this course.")
        st.stop()

    sorted_groups_df = comparison_df.sort_values(["SEMESTER_ORDER", "ACADEMIC_YEAR"], na_position="last")
    distinct_group_series = sorted_groups_df["GROUP_LABEL"].dropna().astype(str).drop_duplicates()
    group_options = distinct_group_series.tolist()
    metric_options = sorted(comparison_df["METRIC"].dropna().astype(str).unique().tolist())

    st.caption(f"Detected {len(group_options)} semester/year groups and {len(metric_options)} GPA metrics.")
    if len(group_options) <= 1:
        st.info("Only one semester/year group is available for this course. Upload more semester/year data for richer comparison.")

    selected_groups = st.multiselect("Select semester/year groups", group_options, default=group_options)
    selected_metrics = st.multiselect(
        "Select GPA metrics to compare",
        metric_options,
        default=metric_options[: min(2, len(metric_options))],
    )

    if not selected_metrics:
        st.warning("Please select at least one GPA metric.")
        st.stop()

    for metric in selected_metrics:
        st.pyplot(plot_semester_metric_bars(comparison_df, metric, selected_groups), width="stretch")

    shown_df = comparison_df.copy()
    if selected_groups:
        shown_df = shown_df[shown_df["GROUP_LABEL"].isin(selected_groups)]
    shown_df = shown_df[shown_df["METRIC"].isin(selected_metrics)]
    st.dataframe(
        shown_df[["GROUP_LABEL", "METRIC", "AVG_VALUE", "STUDENT_COUNT"]]
        .sort_values(["GROUP_LABEL", "METRIC"]),
        width="stretch",
        hide_index=True,
    )

render_footer()
