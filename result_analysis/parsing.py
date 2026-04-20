import re
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .constants import KNOWN_NON_SUBJECT_COLUMNS, PASSING_GRADES, REQUIRED_COLUMNS


def normalize_token(text: object) -> str:
    if pd.isna(text):
        return ""
    return re.sub(r"[^A-Z0-9]+", "", str(text).strip().upper())


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().upper() for c in out.columns]
    unnamed = [c for c in out.columns if c.startswith("UNNAMED") or c == ""]
    if unnamed:
        out = out.drop(columns=unnamed)
    return out


def canonicalize_header(value: object) -> Optional[str]:
    text = "" if pd.isna(value) else str(value).strip().upper()
    if not text:
        return None
    token = normalize_token(text)

    if token in {"ROLL", "ROLLNO", "ROLLNUMBER", "ROLLNUM"}:
        return "ROLL NO"
    if token in {"NAME", "STUDENTNAME"}:
        return "NAME"
    if token in {"COLLEGENAME", "INSTITUTENAME"}:
        return "COLLEGE NAME"
    if token in {"SEMESTER", "SEM"}:
        return "SEMESTER"
    if token in {"ACADEMICYEAR", "ACADEMICYR", "ACYEAR", "YEAR"}:
        return "ACADEMIC YEAR"
    if token in {"COURSECODE", "COURSEID"}:
        return "COURSE CODE"
    if token in {"COURSE", "COURSENAME", "PROGRAMME", "PROGRAM", "DEPARTMENT"}:
        return "COURSENAME"
    if token in {"STREAM", "BRANCH", "SPECIALIZATION", "SPECIALISATION"}:
        return "STREAM"
    if "SGPA" in token:
        return "SGPA"
    if "YGPA" in token:
        return "YGPA"
    if "DGPA" in token:
        return "DGPA"
    if "RESULT" in token and "SEM" in token:
        return "SEMESTER RESULT"
    if token in {"PASSFAIL", "RESULT"}:
        return "SEMESTER RESULT"
    if "MARPOINT" in token or "MARKPOINT" in token:
        return "TOTAL MARK POINTS"
    return text


def is_section_header_row(cells: List[str]) -> bool:
    tokens = [normalize_token(v) for v in cells if str(v).strip()]
    if not tokens:
        return False
    has_roll = any(t in {"ROLL", "ROLLNO", "ROLLNUMBER", "ROLLNUM"} for t in tokens)
    has_name = any(t in {"NAME", "STUDENTNAME"} for t in tokens)
    has_course = any(
        t.startswith("COURSE") or t in {"COURSENAME", "STREAM", "BRANCH", "PROGRAMME", "PROGRAM"}
        for t in tokens
    )
    return has_roll and has_name and has_course


def parse_multisection_rows(raw_df: pd.DataFrame) -> pd.DataFrame:
    rows = raw_df.fillna("").astype(str).values.tolist()
    current_header: Dict[int, str] = {}
    records: List[Dict[str, str]] = []

    for row in rows:
        cells = [str(v).strip() for v in row]
        if not any(cells):
            continue

        if is_section_header_row(cells):
            mapped: Dict[int, str] = {}
            seen_subjects: Dict[str, int] = {}
            for idx, cell in enumerate(cells):
                col = canonicalize_header(cell)
                if not col:
                    continue
                if col in KNOWN_NON_SUBJECT_COLUMNS:
                    if col not in mapped.values():
                        mapped[idx] = col
                else:
                    seen_subjects[col] = seen_subjects.get(col, 0) + 1
                    mapped[idx] = col if seen_subjects[col] == 1 else f"{col} ({seen_subjects[col]})"
            current_header = mapped
            continue

        if not current_header:
            continue

        record: Dict[str, str] = {}
        for idx, col in current_header.items():
            if idx < len(cells) and cells[idx] != "":
                record[col] = cells[idx]

        roll_no = str(record.get("ROLL NO", "")).strip().upper()
        if not record or roll_no in {"", "ROLL NO"}:
            continue
        records.append(record)

    out = pd.DataFrame(records)
    if out.empty:
        return out

    if "COURSE" in out.columns and "COURSENAME" not in out.columns:
        out = out.rename(columns={"COURSE": "COURSENAME"})

    for col, default_val in {
        "COLLEGE NAME": "",
        "SEMESTER": "UNKNOWN",
        "COURSE CODE": "",
    }.items():
        if col not in out.columns:
            out[col] = default_val
    return out


def clean_uploaded_data(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "ROLL NO" in out.columns:
        roll_series = out["ROLL NO"].astype(str).str.strip().str.upper()
        out = out[roll_series != "ROLL NO"]
    return out.dropna(how="all").reset_index(drop=True)


def infer_academic_year(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "ACADEMIC YEAR" in out.columns:
        ay = out["ACADEMIC YEAR"].astype(str).str.strip()
        if ay.ne("").any():
            return out

    extracted = (
        out.get("ROLL NO", pd.Series(index=out.index, dtype=str))
        .astype(str)
        .str.extract(r"^\d{6}(\d{2})\d{3}$")[0]
    )

    def make_ay(token: object) -> str:
        if pd.isna(token):
            return "Unknown"
        yy = int(str(token))
        start_year = 2000 + yy
        end_year = start_year + 1
        return f"{start_year}-{end_year}"

    out["ACADEMIC YEAR"] = extracted.apply(make_ay)
    return out


def is_metadata_column(col: str) -> bool:
    token = normalize_token(col)
    if col in KNOWN_NON_SUBJECT_COLUMNS:
        return True
    if token.startswith("ROLL") or token == "NAME":
        return True
    if "COURSE" in token or "COLLEGE" in token:
        return True
    if "SEM" in token and "RESULT" in token:
        return True
    if token in {"SEM", "SEMESTER", "SGPA", "YGPA", "DGPA", "GPA", "PASSFAIL", "RESULT"}:
        return True
    if "MARKPOINT" in token or "MARPOINT" in token:
        return True
    if token in {"ACADEMICYEAR", "YEAR"}:
        return True
    return False


def validate_dataset(df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
    errors: List[str] = []
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        errors.append("Missing required column(s): " + ", ".join(missing))

    if "ROLL NO" in df.columns and df["ROLL NO"].astype(str).str.strip().eq("").all():
        errors.append("ROLL NO appears empty for all rows.")

    if "NAME" in df.columns and df["NAME"].astype(str).str.strip().eq("").all():
        errors.append("NAME appears empty for all rows.")

    metadata_cols = [c for c in df.columns if is_metadata_column(c)]
    subject_cols = [c for c in df.columns if not is_metadata_column(c)]
    subject_cols = [c for c in subject_cols if df[c].astype(str).str.strip().ne("").any()]

    if not subject_cols:
        errors.append("No subject columns detected. Add at least one subject column beyond metadata columns.")

    return errors, metadata_cols, subject_cols


def parse_grade_value(value: object) -> Tuple[Optional[str], Optional[float], str]:
    if pd.isna(value):
        return None, None, "Unknown"

    text = str(value).strip().upper()
    if text in {"", "---", "NA", "N/A"}:
        return None, None, "Unknown"
    if text in {"AB", "ABSENT"}:
        return "ABSENT", 0.0, "Fail"
    if text == "F":
        return "F", 0.0, "Fail"

    match = re.match(r"^([A-Z]+)\s*\(([-+]?[0-9]*\.?[0-9]+)\)$", text)
    if match:
        grade = match.group(1)
        marks = float(match.group(2))
        if grade in PASSING_GRADES:
            return grade, marks, "Pass"
        if grade == "F":
            return grade, marks, "Fail"
        return grade, marks, "Unknown"

    numeric_match = re.match(r"^[-+]?[0-9]*\.?[0-9]+$", text)
    if numeric_match:
        marks = float(text)
        return None, marks, "Pass" if marks > 0 else "Fail"

    if text in PASSING_GRADES:
        return text, None, "Pass"

    return text, None, "Unknown"


def marks_frame(df: pd.DataFrame, subjects: List[str]) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        for subject in subjects:
            grade, marks, status = parse_grade_value(row.get(subject))
            rows.append(
                {
                    "ROLL NO": row.get("ROLL NO"),
                    "NAME": row.get("NAME"),
                    "COURSE CODE": row.get("COURSE CODE"),
                    "COURSENAME": row.get("COURSENAME"),
                    "ACADEMIC YEAR": row.get("ACADEMIC YEAR"),
                    "SEMESTER": row.get("SEMESTER"),
                    "SUBJECT": subject,
                    "RAW": row.get(subject),
                    "GRADE": grade,
                    "MARKS": marks,
                    "STATUS": status,
                }
            )
    return pd.DataFrame(rows)


def read_uploaded_dataset(uploaded_file) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()
    if file_name.endswith(".csv"):
        raw_df = pd.read_csv(uploaded_file, dtype=str, header=None)
    elif file_name.endswith((".xlsx", ".xls")):
        raw_df = pd.read_excel(uploaded_file, dtype=str, header=None)
    else:
        raise ValueError("Unsupported file format. Please upload CSV, XLS, or XLSX.")

    parsed_df = parse_multisection_rows(raw_df)
    if parsed_df.empty:
        raise ValueError("No valid student rows found. Ensure each section starts with a header like Roll/Name/Course.")

    out = clean_uploaded_data(normalize_columns(parsed_df))
    out = infer_academic_year(out)
    return out


def get_gpa_columns(df: pd.DataFrame) -> List[str]:
    cols = []
    for c in df.columns:
        token = normalize_token(c)
        if token in {"SGPA", "YGPA", "DGPA", "GPA"} or token.endswith("SGPA"):
            cols.append(c)
    ordered = []
    for key in ["SGPA", "YGPA", "DGPA"]:
        exact = [c for c in cols if normalize_token(c) == key]
        ordered.extend(exact)
    ordered.extend([c for c in cols if c not in ordered])
    return ordered
