# utils/analytics.py
import pandas as pd
import numpy as np
import re
from typing import List, Optional
from scipy.stats import skew
from utils.processor import parse_grade_value, normalize_token

SEMESTER_WORD_TO_NUM = {
    "FIRST": 1, "1ST": 1, "ONE": 1, "I": 1,
    "SECOND": 2, "2ND": 2, "TWO": 2, "II": 2,
    "THIRD": 3, "3RD": 3, "THREE": 3, "III": 3,
    "FOURTH": 4, "4TH": 4, "FOUR": 4, "IV": 4,
    "FIFTH": 5, "5TH": 5, "FIVE": 5, "V": 5,
    "SIXTH": 6, "6TH": 6, "SIX": 6, "VI": 6,
    "SEVENTH": 7, "7TH": 7, "SEVEN": 7, "VII": 7,
    "EIGHTH": 8, "8TH": 8, "EIGHT": 8, "VIII": 8,
    "NINTH": 9, "9TH": 9, "NINE": 9, "IX": 9,
    "TENTH": 10, "10TH": 10, "TEN": 10, "X": 10,
}
# Assumes roll format like XXXCCCYYNNN..., where YY is the two-digit admission year at indices [6:8].
ROLL_YEAR_START_INDEX = 6
ROLL_YEAR_END_INDEX = 8
# Sentinel value used throughout to indicate "semester order unknown / unparseable".
UNKNOWN_SEMESTER_ORDER = 999

def normalize_semester_label(semester_value: object) -> str:
    text = str(semester_value).strip() if semester_value is not None else ""
    if not text:
        return "Unknown Semester"
    upper_text = text.upper()

    number_match = re.search(r"\b(\d{1,2})\b", upper_text)
    if number_match:
        sem_num = int(number_match.group(1))
        return f"Semester {sem_num}"

    for token, sem_num in SEMESTER_WORD_TO_NUM.items():
        if re.search(rf"\b{re.escape(token)}\b", upper_text):
            return f"Semester {sem_num}"

    return text

def get_semester_order(semester_value: object) -> int:
    label = normalize_semester_label(semester_value).upper()
    number_match = re.search(r"\b(\d{1,2})\b", label)
    if number_match:
        return int(number_match.group(1))
    return UNKNOWN_SEMESTER_ORDER

def infer_academic_year_from_roll(roll_value: object) -> Optional[int]:
    roll = str(roll_value).strip()
    if len(roll) < ROLL_YEAR_END_INDEX:
        return None
    year_token = roll[ROLL_YEAR_START_INDEX:ROLL_YEAR_END_INDEX]
    if not year_token.isdigit():
        return None
    year_num = int(year_token)
    current_two_digit_year = pd.Timestamp.utcnow().year % 100
    pivot = (current_two_digit_year + 5) % 100
    return (2000 + year_num) if year_num <= pivot else (1900 + year_num)

def format_semester_group_label(semester_label: object, academic_year: object) -> str:
    if pd.notna(academic_year):
        return f"{semester_label} | AY {int(academic_year)}"
    return f"{semester_label} | AY Unknown"

def build_semester_year_groups(df: pd.DataFrame, semester_col: str = "SEMESTER", roll_col: str = "ROLL NO") -> pd.DataFrame:
    frame = df.copy()
    frame["SEMESTER_LABEL"] = frame.get(semester_col, pd.Series(index=frame.index, dtype=object)).apply(normalize_semester_label)
    frame["SEMESTER_ORDER"] = frame["SEMESTER_LABEL"].apply(get_semester_order)
    frame["ACADEMIC_YEAR"] = frame.get(roll_col, pd.Series(index=frame.index, dtype=object)).apply(infer_academic_year_from_roll)

    has_any_year_data = frame["ACADEMIC_YEAR"].notna().any()
    max_years_in_any_semester = frame.groupby("SEMESTER_LABEL")["ACADEMIC_YEAR"].nunique(dropna=True).max()
    has_year_split = has_any_year_data and max_years_in_any_semester > 1
    if has_year_split:
        frame["GROUP_LABEL"] = frame.apply(
            lambda row: format_semester_group_label(row["SEMESTER_LABEL"], row["ACADEMIC_YEAR"]),
            axis=1,
        )
    else:
        frame["GROUP_LABEL"] = frame["SEMESTER_LABEL"]

    return frame

def aggregate_gpa_comparison(df: pd.DataFrame, gpa_columns: list) -> pd.DataFrame:
    if df.empty or not gpa_columns:
        return pd.DataFrame()

    grouped_df = build_semester_year_groups(df)
    rows = []
    for metric in gpa_columns:
        if metric not in grouped_df.columns:
            continue
        working = grouped_df[["SEMESTER_LABEL", "SEMESTER_ORDER", "ACADEMIC_YEAR", "GROUP_LABEL", metric]].copy()
        working["METRIC_VALUE"] = pd.to_numeric(working[metric], errors="coerce")
        summary = (
            working.dropna(subset=["METRIC_VALUE"])
            .groupby(["SEMESTER_LABEL", "SEMESTER_ORDER", "ACADEMIC_YEAR", "GROUP_LABEL"], dropna=False)["METRIC_VALUE"]
            .agg(["mean", "count"])
            .reset_index()
        )
        for _, row in summary.iterrows():
            rows.append(
                {
                    "SEMESTER_LABEL": row["SEMESTER_LABEL"],
                    "SEMESTER_ORDER": int(row["SEMESTER_ORDER"]) if pd.notna(row["SEMESTER_ORDER"]) else 999,
                    "ACADEMIC_YEAR": int(row["ACADEMIC_YEAR"]) if pd.notna(row["ACADEMIC_YEAR"]) else None,
                    "GROUP_LABEL": row["GROUP_LABEL"],
                    "METRIC": metric,
                    "AVG_VALUE": round(float(row["mean"]), 3),
                    "STUDENT_COUNT": int(row["count"]),
                }
            )

    result_df = pd.DataFrame(rows)
    if result_df.empty:
        return result_df
    return result_df.sort_values(["SEMESTER_ORDER", "ACADEMIC_YEAR", "GROUP_LABEL", "METRIC"], na_position="last").reset_index(drop=True)

def get_primary_sgpa_col(file_df: pd.DataFrame, sem_order: int) -> Optional[str]:
    """
    Return the column name holding the current-semester SGPA for a group of students.

    Priority:
    1. ``SGPA{sem_order}`` (even-sem files store per-sem GPAs as SGPA3/SGPA4, SGPA7/SGPA8, …)
    2. Plain ``SGPA`` column (odd-sem files use a single SGPA column)
    3. Any column whose normalised name contains ``SGPA`` and has numeric data

    Returns ``None`` when no suitable column can be found.
    ``sem_order=UNKNOWN_SEMESTER_ORDER`` (999) skips step 1 and falls through to steps 2–3.
    """
    # Try SGPA{N} (even-sem files store previous+current sem SGPAs as SGPA3/SGPA4, SGPA7/SGPA8, …)
    if sem_order != UNKNOWN_SEMESTER_ORDER:
        candidate = f"SGPA{sem_order}"
        col_upper = {c.upper(): c for c in file_df.columns}
        if candidate.upper() in col_upper:
            col = col_upper[candidate.upper()]
            if pd.to_numeric(file_df[col], errors="coerce").notna().any():
                return col
    # Plain SGPA (odd-sem files)
    for col in file_df.columns:
        if normalize_token(col) == "SGPA":
            if pd.to_numeric(file_df[col], errors="coerce").notna().any():
                return col
    # Fall back to any SGPA-like column with data
    for col in file_df.columns:
        if "SGPA" in normalize_token(col):
            if pd.to_numeric(file_df[col], errors="coerce").notna().any():
                return col
    return None


def get_primary_ygpa_col(file_df: pd.DataFrame, sem_order: int) -> Optional[str]:
    """
    Return the column name holding the year GPA for the current semester group.

    Priority:
    1. ``YGPA{sem_order}`` (even-sem files store year GPA as YGPA4, YGPA8, …)
    2. Plain ``YGPA`` column
    3. Any column whose normalised name contains ``YGPA`` and has numeric data

    Returns ``None`` when no suitable column can be found.
    """
    if sem_order != UNKNOWN_SEMESTER_ORDER:
        candidate = f"YGPA{sem_order}"
        col_upper = {c.upper(): c for c in file_df.columns}
        if candidate.upper() in col_upper:
            col = col_upper[candidate.upper()]
            if pd.to_numeric(file_df[col], errors="coerce").notna().any():
                return col
    for col in file_df.columns:
        if normalize_token(col) == "YGPA":
            if pd.to_numeric(file_df[col], errors="coerce").notna().any():
                return col
    for col in file_df.columns:
        if "YGPA" in normalize_token(col):
            if pd.to_numeric(file_df[col], errors="coerce").notna().any():
                return col
    return None


def build_file_comparison_data(df: pd.DataFrame, gpa_columns: List[str]) -> pd.DataFrame:
    """
    Builds comparison data for the semester comparison page.

    Groups students by SOURCE FILE (one group per uploaded file) and computes the
    average of each GPA metric.  Does NOT use roll-number admission-year logic to
    split students — all students from the same course in the same file are treated
    as one group.

    Group labels:
    - Same semester across files → labelled by EXAM SESSION (e.g. "April 2025")
    - Different semesters → labelled by semester name (e.g. "Semester 4")
    - Both differ → "Semester N | Month YYYY"

    Returns a DataFrame with columns:
        GROUP_LABEL, SEMESTER_LABEL, SEMESTER_ORDER, METRIC, AVG_VALUE, STUDENT_COUNT
    """
    if df.empty or not gpa_columns:
        return pd.DataFrame()

    working = df.copy()

    # Normalise semester
    if "SEMESTER" in working.columns:
        working["SEMESTER_LABEL"] = working["SEMESTER"].apply(normalize_semester_label)
        working["SEMESTER_ORDER"] = working["SEMESTER_LABEL"].apply(get_semester_order)
    else:
        working["SEMESTER_LABEL"] = "Unknown Semester"
        working["SEMESTER_ORDER"] = UNKNOWN_SEMESTER_ORDER

    if "SOURCE FILE" not in working.columns:
        working["SOURCE FILE"] = "Uploaded File"
    if "EXAM SESSION" not in working.columns:
        working["EXAM SESSION"] = ""

    # Per-file dominant semester and exam-session
    file_meta = (
        working.groupby("SOURCE FILE", sort=False)
        .agg(
            SEM_LABEL=("SEMESTER_LABEL", lambda x: x.mode().iloc[0] if not x.mode().empty else "Unknown"),
            EXAM_SESS=("EXAM SESSION", lambda x: x.mode().iloc[0] if not x.mode().empty else ""),
            SEM_ORDER=("SEMESTER_ORDER", lambda x: int(x.mode().iloc[0]) if not x.mode().empty else UNKNOWN_SEMESTER_ORDER),
        )
        .reset_index()
    )

    all_same_sem = file_meta["SEM_LABEL"].nunique() == 1
    all_same_exam = file_meta["EXAM_SESS"].replace("", pd.NA).dropna().nunique() <= 1

    def make_label(row):
        sem = row["SEM_LABEL"]
        exam = str(row["EXAM_SESS"]).strip()
        if all_same_sem:
            # Distinguish files by exam session only
            return exam if exam else sem
        elif all_same_exam or not exam:
            # Distinguish files by semester only
            return sem
        else:
            return f"{sem} | {exam}"

    file_meta["GROUP_LABEL"] = file_meta.apply(make_label, axis=1)

    # Merge group labels back into working df
    working = working.merge(
        file_meta[["SOURCE FILE", "GROUP_LABEL", "SEM_LABEL", "SEM_ORDER"]],
        on="SOURCE FILE",
        how="left",
    )

    # ---- Normalize per-file numbered SGPA/YGPA columns into unified metrics ----
    # When files contain semester-specific columns (SGPA3, SGPA4, YGPA4, …), each
    # column only has data for one file, so the comparison chart ends up with a
    # single bar.  We map each file's "current-semester" SGPA/YGPA into plain
    # "SGPA"/"YGPA" columns so every file contributes to the same metric bar.
    _UNIFIED_SGPA = "SGPA"
    _UNIFIED_YGPA = "YGPA"

    numbered_sgpa = [c for c in gpa_columns if re.search(r"SGPA\d", normalize_token(c))]
    numbered_ygpa = [c for c in gpa_columns if re.search(r"YGPA\d", normalize_token(c))]

    effective_metrics = list(gpa_columns)

    if numbered_sgpa:
        file_sgpa_map = {}
        for _, frow in file_meta.iterrows():
            src = frow["SOURCE FILE"]
            sem_order = int(frow["SEM_ORDER"]) if pd.notna(frow["SEM_ORDER"]) else UNKNOWN_SEMESTER_ORDER
            file_sgpa_map[src] = get_primary_sgpa_col(working[working["SOURCE FILE"] == src], sem_order)

        working[_UNIFIED_SGPA] = None
        for src, col in file_sgpa_map.items():
            mask = working["SOURCE FILE"] == src
            if col and col in working.columns:
                working.loc[mask, _UNIFIED_SGPA] = working.loc[mask, col].values

        effective_metrics = [c for c in effective_metrics if c not in numbered_sgpa]
        if _UNIFIED_SGPA not in effective_metrics:
            effective_metrics = [_UNIFIED_SGPA] + effective_metrics

    if numbered_ygpa:
        file_ygpa_map = {}
        for _, frow in file_meta.iterrows():
            src = frow["SOURCE FILE"]
            sem_order = int(frow["SEM_ORDER"]) if pd.notna(frow["SEM_ORDER"]) else UNKNOWN_SEMESTER_ORDER
            file_ygpa_map[src] = get_primary_ygpa_col(working[working["SOURCE FILE"] == src], sem_order)

        working[_UNIFIED_YGPA] = None
        for src, col in file_ygpa_map.items():
            mask = working["SOURCE FILE"] == src
            if col and col in working.columns:
                working.loc[mask, _UNIFIED_YGPA] = working.loc[mask, col].values

        effective_metrics = [c for c in effective_metrics if c not in numbered_ygpa]
        if _UNIFIED_YGPA not in effective_metrics:
            effective_metrics = [_UNIFIED_YGPA] + effective_metrics
    # ---- End normalization ----

    rows = []
    for metric in effective_metrics:
        if metric not in working.columns:
            continue
        metric_df = working[["GROUP_LABEL", "SEM_LABEL", "SEM_ORDER", metric]].copy()
        metric_df["METRIC_VALUE"] = pd.to_numeric(metric_df[metric], errors="coerce")
        summary = (
            metric_df.dropna(subset=["METRIC_VALUE"])
            .groupby(["GROUP_LABEL", "SEM_LABEL", "SEM_ORDER"])["METRIC_VALUE"]
            .agg(["mean", "count"])
            .reset_index()
        )
        for _, row in summary.iterrows():
            rows.append(
                {
                    "GROUP_LABEL": str(row["GROUP_LABEL"]),
                    "SEMESTER_LABEL": str(row["SEM_LABEL"]),
                    "SEMESTER_ORDER": int(row["SEM_ORDER"]) if pd.notna(row["SEM_ORDER"]) else UNKNOWN_SEMESTER_ORDER,
                    "METRIC": metric,
                    "AVG_VALUE": round(float(row["mean"]), 3),
                    "STUDENT_COUNT": int(row["count"]),
                }
            )

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values(["SEMESTER_ORDER", "GROUP_LABEL", "METRIC"]).reset_index(drop=True)


def get_class_masks(df: pd.DataFrame, roll_col: str = "ROLL NO"):
    """
    Identifies the Current Class (Regulars + Laterals) vs Old Batches.
    """
    if roll_col not in df.columns:
        return pd.Series(True, index=df.index), pd.Series(False, index=df.index)

    rolls = df[roll_col].astype(str).str.strip()
    # Minimum length 8 is required because this logic expects roll format where:
    # [0:3] is a prefix/institute token, [3:6] is course code, and admission year is inferred from roll[6:8].
    valid_rolls = rolls[rolls.str.len() >= 8]

    # Default: do not penalize rows that cannot be reliably parsed; keep them in current class
    # so malformed roll values do not get incorrectly flagged as old-batch reappearing students.
    current_class_mask = pd.Series(True, index=df.index, dtype=bool)
    old_batch_mask = pd.Series(False, index=df.index, dtype=bool)

    if valid_rolls.empty:
        return current_class_mask, old_batch_mask

    parsed = pd.DataFrame(index=valid_rolls.index)
    parsed["ROLL_COURSE"] = valid_rolls.str[3:6]
    parsed["ENTRY_YEAR"] = valid_rolls.apply(infer_academic_year_from_roll)
    parsed = parsed.dropna(subset=["ENTRY_YEAR"])

    if parsed.empty:
        return current_class_mask, old_batch_mask

    parsed["ENTRY_YEAR"] = parsed["ENTRY_YEAR"].astype(int)

    # Prefer COURSE CODE column when present so we don't rely solely on roll slices.
    roll_course_mode = parsed["ROLL_COURSE"].mode()
    fallback_course = str(roll_course_mode.iloc[0]) if not roll_course_mode.empty else ""
    target_course = fallback_course

    if "COURSE CODE" in df.columns:
        course_code_series = (
            df["COURSE CODE"]
            .astype(str)
            .str.strip()
            .replace({"": pd.NA})
            .dropna()
            .str.upper()
            .replace({"NAN": pd.NA, "NONE": pd.NA, "NULL": pd.NA})
            .dropna()
        )
        if not course_code_series.empty:
            course_mode = course_code_series.mode()
            if not course_mode.empty:
                target_course = str(course_mode.iloc[0])

    if not target_course:
        return current_class_mask, old_batch_mask

    parsed = parsed[parsed["ROLL_COURSE"] == target_course]
    if parsed.empty:
        return current_class_mask, old_batch_mask

    year_counts = parsed["ENTRY_YEAR"].value_counts()
    top_count = year_counts.max()
    tied_top_years = year_counts[year_counts == top_count].index
    # Tie-break toward the latest admission year to avoid pulling older repeating cohorts as "current".
    regular_year = int(tied_top_years.max())

    is_regular = (parsed["ENTRY_YEAR"] == regular_year)
    is_lateral = (parsed["ENTRY_YEAR"] == regular_year + 1)
    is_current = is_regular | is_lateral

    current_class_mask.loc[parsed.index] = is_current
    old_batch_mask.loc[parsed.index] = ~is_current
    return current_class_mask, old_batch_mask

def determine_student_status(df: pd.DataFrame, semester_name: str) -> pd.DataFrame:
    df = df.copy()
    even_keywords = ["SECOND", "FOURTH", "SIXTH", "EIGHT", "EIGHTH", "TENTH"]
    is_even_sem = any(k in str(semester_name).upper() for k in even_keywords)
    semester_order = get_semester_order(semester_name)
    # get_semester_order returns 999 when semester text cannot be parsed into a numeric order.
    expected_elapsed_years = max(0, (semester_order - 1) // 2) if semester_order != 999 else None
    
    current_class_mask, _ = get_class_masks(df)
    
    statuses = []
    timeline_statuses = []
    for idx, row in df.iterrows():
        sem_result = str(row.get("SEMESTER RESULT", "")).upper()
        has_ygpa = pd.notna(row.get("YGPA")) and str(row.get("YGPA")).strip() != ""
        
        # 1. Year Lag check
        if is_even_sem and not has_ygpa and "PASS" not in sem_result:
            statuses.append("Year Lag")
        # 2. Old Batch check (If they aren't current class, they are old batch backlogs)
        elif not current_class_mask[idx]:
            statuses.append("Old Batch (Re-appearing)")
        # 3. Current Batch Pass
        elif "PASS" in sem_result:
            statuses.append("Current Batch")
        # 4. Current Batch Fail/Backlog
        else:
            statuses.append("Backlog (Current Batch)")

        exam_year = pd.to_numeric(row.get("EXAM YEAR"), errors="coerce")
        admission_year = infer_academic_year_from_roll(row.get("ROLL NO"))
        if pd.isna(exam_year) or admission_year is None or expected_elapsed_years is None:
            timeline_statuses.append("Unknown")
        else:
            elapsed_years = exam_year - admission_year
            if elapsed_years < 0:
                timeline_statuses.append("Unknown")
            # expected_elapsed_years is the normal admission-to-exam gap for the selected semester.
            # same/less => current cohort, +1 => older (past year), beyond +1 => reappearing backlog.
            elif elapsed_years <= expected_elapsed_years:
                timeline_statuses.append("Current Year Students")
            elif elapsed_years == expected_elapsed_years + 1:
                timeline_statuses.append("Past Year Students")
            else:
                timeline_statuses.append("Reappearing Students")
            
    df["STATUS"] = statuses
    df["EXAM TIMELINE"] = timeline_statuses
    return df

def calculate_subject_stats(df: pd.DataFrame, subject_cols: list) -> pd.DataFrame:
    stats_list = []
    for subj in subject_cols:
        if subj not in df.columns: continue
            
        parsed = df[subj].apply(parse_grade_value)
        grades = [p[0] for p in parsed if p[0] is not None]
        marks = [p[1] for p in parsed if p[1] is not None]
        
        if not marks: continue
        marks_series = pd.Series(marks).dropna()
        grade_counts = pd.Series(grades).value_counts().to_dict()
        
        stat_row = {
            "Subject": subj,
            "Mean": round(marks_series.mean(), 2),
            "Median": round(marks_series.median(), 2),
            "Std Dev (\u03c3)": round(marks_series.std(), 2) if len(marks_series) > 1 else 0,
            "Skewness": round(skew(marks_series), 2) if len(marks_series) > 2 else 0,
            "O": grade_counts.get("O", 0), "E": grade_counts.get("E", 0),
            "A": grade_counts.get("A", 0), "B": grade_counts.get("B", 0),
            "C": grade_counts.get("C", 0), "D": grade_counts.get("D", 0),
            "F": grade_counts.get("F", 0) + grade_counts.get("---", 0),
        }
        stats_list.append(stat_row)
    return pd.DataFrame(stats_list)

def calculate_z_scores(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df_clean = df.copy()
    
    def extract_numeric(val):
        grade, marks = parse_grade_value(val)
        
        # 1. If we have the numeric points (e.g., from "A(32)"), use them!
        if marks is not None:
            return marks
            
        # 2. THE FALLBACK: If we only have a grade (e.g., "A"), map it to the strict KGEC scale
        grade_to_point = {'O': 10, 'E': 9, 'A': 8, 'B': 7, 'C': 6, 'D': 5, 'F': 0}
        if grade in grade_to_point:
            return grade_to_point[grade]
            
        # 3. If it's empty, absent, or "---", return None
        return None

    if df_clean[col].dtype == 'object':
        df_clean['NUMERIC_VAL'] = df_clean[col].apply(extract_numeric)
    else:
        df_clean['NUMERIC_VAL'] = pd.to_numeric(df_clean[col], errors='coerce')
    
    # Drop anyone who doesn't have a valid number or grade point
    df_clean = df_clean.dropna(subset=['NUMERIC_VAL'])
    
    # If the data frame is empty OR the standard deviation is 0 (everyone got the exact same mark)
    if df_clean.empty or df_clean['NUMERIC_VAL'].std() == 0:
        return pd.DataFrame() # Return empty to trigger the safe warning in the UI

    mean = df_clean['NUMERIC_VAL'].mean()
    std = df_clean['NUMERIC_VAL'].std()
    
    # Calculate Z-Score safely
    df_clean["Z-Score"] = (df_clean['NUMERIC_VAL'] - mean) / std
    
    conditions = [(df_clean["Z-Score"] > 1), (df_clean["Z-Score"] < -1)]
    choices = ["Strong (> +1\u03c3)", "Weak (< -1\u03c3)"]
    df_clean["Performance"] = np.select(conditions, choices, default="Decent (-1\u03c3 to +1\u03c3)")
    
    return df_clean.sort_values("Z-Score", ascending=False)
