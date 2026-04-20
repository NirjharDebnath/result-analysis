import re
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from .constants import GRADE_ORDER, PRACTICAL_HINTS, REGULAR_ROLL_PATTERN
from .parsing import marks_frame, normalize_token


def is_regular_roll(roll_no: object) -> bool:
    return bool(re.match(REGULAR_ROLL_PATTERN, str(roll_no).strip()))


def is_practical_subject(subject: str) -> bool:
    token = normalize_token(subject)
    return any(hint in token for hint in PRACTICAL_HINTS)


def classify_students(df: pd.DataFrame, subjects: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    long_df = marks_frame(df, subjects)
    valid = long_df[long_df["STATUS"].isin(["Pass", "Fail"])].copy()

    if valid.empty:
        empty_status = pd.DataFrame(columns=["ROLL NO", "NAME", "STUDENT_STATUS", "FAIL_COUNT", "PRACTICAL_FAIL_COUNT"])
        return empty_status, valid

    valid["IS_FAIL"] = valid["STATUS"].eq("Fail")
    valid["IS_PRACTICAL"] = valid["SUBJECT"].astype(str).apply(is_practical_subject)
    valid["IS_PRACTICAL_FAIL"] = valid["IS_FAIL"] & valid["IS_PRACTICAL"]

    grouped = (
        valid.groupby(["ROLL NO", "NAME"], as_index=False)
        .agg(
            FAIL_COUNT=("IS_FAIL", "sum"),
            SUBJECT_COUNT=("SUBJECT", "count"),
            PRACTICAL_FAIL_COUNT=("IS_PRACTICAL_FAIL", "sum"),
            PRACTICAL_COUNT=("IS_PRACTICAL", "sum"),
        )
    )

    grouped["ALL_FAILED"] = grouped["FAIL_COUNT"] == grouped["SUBJECT_COUNT"]
    # Domain rule: classify as year lag if any practical is failed or all subjects are failed.
    grouped["YEAR_LAG"] = (grouped["PRACTICAL_FAIL_COUNT"] > 0) | grouped["ALL_FAILED"]

    grouped["STUDENT_STATUS"] = np.select(
        [grouped["FAIL_COUNT"].eq(0), grouped["YEAR_LAG"]],
        ["Passed", "Year Lag"],
        default="Backlog",
    )

    return grouped, valid


def status_summary_table(student_status_df: pd.DataFrame) -> pd.DataFrame:
    total = max(len(student_status_df), 1)
    base = (
        student_status_df.groupby("STUDENT_STATUS")
        .size()
        .reindex(["Passed", "Backlog", "Year Lag"], fill_value=0)
        .reset_index(name="Students")
    )
    base["Percent"] = (base["Students"] * 100 / total).round(2)
    return base


def normal_curve_points(series: pd.Series, points: int = 200) -> Tuple[np.ndarray, np.ndarray, float, float]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return np.array([]), np.array([]), np.nan, np.nan

    mean = float(values.mean())
    std = float(values.std(ddof=0))
    if std == 0:
        std = 0.001

    x = np.linspace(float(values.min()), float(values.max()), points)
    y = (1 / (std * np.sqrt(2 * np.pi))) * np.exp(-((x - mean) ** 2) / (2 * std**2))
    return x, y, mean, std


def consolidated_subject_matrix(df: pd.DataFrame, subjects: List[str]) -> pd.DataFrame:
    long_df = marks_frame(df, subjects)
    rows = []

    for subject in subjects:
        sub = long_df[long_df["SUBJECT"] == subject].copy()
        marks = pd.to_numeric(sub["MARKS"], errors="coerce").dropna()
        grade_counts = sub["GRADE"].fillna("UNKNOWN").astype(str).str.upper().replace({"NAN": "UNKNOWN"}).value_counts()

        mode_value = np.nan
        if not marks.empty:
            mode_series = marks.mode()
            if not mode_series.empty:
                mode_value = float(mode_series.iloc[0])

        row: Dict[str, object] = {
            "TYPE": "SUBJECT",
            "ITEM": subject,
            "MEAN": float(marks.mean()) if not marks.empty else np.nan,
            "MEDIAN": float(marks.median()) if not marks.empty else np.nan,
            "MODE": mode_value,
            "STD": float(marks.std(ddof=0)) if len(marks) else np.nan,
            "VARIANCE": float(marks.var(ddof=0)) if len(marks) else np.nan,
            "SKEWNESS": float(marks.skew()) if len(marks) > 2 else np.nan,
        }
        for g in GRADE_ORDER:
            row[g] = int(grade_counts.get(g, 0))
        rows.append(row)

    for metric in [c for c in ["SGPA", "YGPA", "DGPA"] if c in df.columns]:
        values = pd.to_numeric(df[metric], errors="coerce").dropna()
        mode_value = np.nan
        if not values.empty:
            mode_series = values.mode()
            if not mode_series.empty:
                mode_value = float(mode_series.iloc[0])

        rows.append(
            {
                "TYPE": "OVERALL",
                "ITEM": metric,
                "MEAN": float(values.mean()) if not values.empty else np.nan,
                "MEDIAN": float(values.median()) if not values.empty else np.nan,
                "MODE": mode_value,
                "STD": float(values.std(ddof=0)) if len(values) else np.nan,
                "VARIANCE": float(values.var(ddof=0)) if len(values) else np.nan,
                "SKEWNESS": float(values.skew()) if len(values) > 2 else np.nan,
                **{g: np.nan for g in GRADE_ORDER},
            }
        )

    return pd.DataFrame(rows)


def top_and_lowest_by_subject(df: pd.DataFrame, subjects: List[str]) -> pd.DataFrame:
    long_df = marks_frame(df, subjects)
    numeric = long_df.dropna(subset=["MARKS"]).copy()
    if numeric.empty:
        return pd.DataFrame(columns=["SUBJECT", "TOPPER", "TOPPER_SCORE", "LOWEST", "LOWEST_SCORE"])

    rows = []
    for subject, sub in numeric.groupby("SUBJECT"):
        sub_sorted = sub.sort_values(["MARKS", "NAME"], ascending=[False, True])
        top = sub_sorted.iloc[0]
        low = sub_sorted.sort_values(["MARKS", "NAME"], ascending=[True, True]).iloc[0]
        rows.append(
            {
                "SUBJECT": subject,
                "TOPPER": f"{top['NAME']} ({top['ROLL NO']})",
                "TOPPER_SCORE": float(top["MARKS"]),
                "LOWEST": f"{low['NAME']} ({low['ROLL NO']})",
                "LOWEST_SCORE": float(low["MARKS"]),
            }
        )
    return pd.DataFrame(rows).sort_values("SUBJECT")


def backlog_lists(student_status_df: pd.DataFrame, fail_entries: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    backlog_students = student_status_df[student_status_df["STUDENT_STATUS"].isin(["Backlog", "Year Lag"])].copy()
    most_backlog_subjects = (
        fail_entries[fail_entries["STATUS"] == "Fail"]
        .groupby("SUBJECT")
        .size()
        .sort_values(ascending=False)
        .reset_index(name="BACKLOG_COUNT")
    )
    return backlog_students, most_backlog_subjects


def grade_only_subject_table(df: pd.DataFrame, subjects: List[str]) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        record = {"ROLL NO": row.get("ROLL NO"), "NAME": row.get("NAME")}
        for subject in subjects:
            raw = row.get(subject)
            text = "" if pd.isna(raw) else str(raw).strip().upper()
            if "(" in text and ")" in text:
                record[subject] = text.split("(", 1)[0].strip()
            else:
                record[subject] = text
        rows.append(record)
    return pd.DataFrame(rows)
