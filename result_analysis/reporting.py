import io
from typing import Dict, List

import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from .analytics import (
    backlog_lists,
    classify_students,
    consolidated_subject_matrix,
    normal_curve_points,
    status_summary_table,
    top_and_lowest_by_subject,
)
from .constants import AUTUMN_COLORS
from .plotting import bar_with_labels, metric_distribution_bar, normal_curve_figure, table_figure


def build_pdf_summary(
    filtered_df: pd.DataFrame,
    subjects: List[str],
    gpa_metric: str,
    include_regular_only: bool,
    subject_for_curve: str,
    title_meta: Dict[str, str],
) -> bytes:
    student_status_df, fail_entries = classify_students(filtered_df, subjects)
    status_table = status_summary_table(student_status_df)
    consolidated = consolidated_subject_matrix(filtered_df, subjects)
    toppers = top_and_lowest_by_subject(filtered_df, subjects)
    backlog_students, most_backlog_subjects = backlog_lists(student_status_df, fail_entries)

    series_df = filtered_df.copy()
    if include_regular_only and "IS_REGULAR" in series_df.columns:
        series_df = series_df[series_df["IS_REGULAR"]]

    sgpa_series = pd.to_numeric(series_df.get("SGPA", pd.Series(dtype=float)), errors="coerce")
    x1, y1, m1, s1 = normal_curve_points(sgpa_series)
    if subject_for_curve in series_df.columns:
        from .parsing import parse_grade_value

        subject_marks = series_df[subject_for_curve].apply(lambda v: parse_grade_value(v)[1])
    else:
        subject_marks = pd.Series(dtype=float)
    x2, y2, m2, s2 = normal_curve_points(subject_marks)

    buffer = io.BytesIO()
    with PdfPages(buffer) as pdf:
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(11.69, 8.27))
        fig.patch.set_facecolor("white")
        fig.text(0.05, 0.90, "Result Analysis Summary", fontsize=22, fontweight="bold", color=AUTUMN_COLORS["primary"])
        fig.text(
            0.05,
            0.82,
            f"Course: {title_meta['course']}\nAcademic Year: {title_meta['academic_year']}\nSemester: {title_meta['semester']}",
            fontsize=13,
        )
        fig.text(0.05, 0.67, f"Students considered: {len(filtered_df)}", fontsize=11)
        fig.text(0.05, 0.62, f"Metric selected: {gpa_metric}", fontsize=11)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        pdf.savefig(bar_with_labels(status_table, "STUDENT_STATUS", "Students", "Passed / Backlog / Year Lag", [AUTUMN_COLORS["pass"], AUTUMN_COLORS["backlog"], AUTUMN_COLORS["year_lag"]]))
        pdf.savefig(normal_curve_figure(sgpa_series, x1, y1, m1, s1, "SGPA Normal Curve", "SGPA"))
        pdf.savefig(normal_curve_figure(subject_marks, x2, y2, m2, s2, f"{subject_for_curve} Normal Curve", subject_for_curve))
        pdf.savefig(metric_distribution_bar(series_df.get(gpa_metric, pd.Series(dtype=float)), gpa_metric))
        pdf.savefig(table_figure(status_table, "Student Status Table"))
        pdf.savefig(table_figure(consolidated.round(3), "Consolidated Analysis Matrix"))
        pdf.savefig(table_figure(toppers.round(2), "Subject Top & Lowest Scorers"))
        pdf.savefig(table_figure(backlog_students, "Backlog and Year Lag Students"))
        pdf.savefig(table_figure(most_backlog_subjects, "Subjects with Most Backlogs"))

    return buffer.getvalue()
