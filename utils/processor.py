# utils/processor.py
import re
from typing import Dict, List, Optional, Tuple
import pandas as pd
import streamlit as st
from utils.constants import REQUIRED_COLUMNS, KNOWN_NON_SUBJECT_COLUMNS, PASSING_GRADES

@st.cache_data
def get_sample_template_csv() -> bytes:
    sample = pd.DataFrame({
        "ROLL NO": ["10271025001"],
        "NAME": ["STUDENT NAME"],
        "College Name": ["COLLEGE NAME"],
        "Semester": ["First Semester"],
        "COURSE CODE": ["710"],
        "COURSENAME": ["Master of Computer Application"],
        "SUBJ-101": ["A(32)"],
        "SUBJ-102": ["B(28)"],
        "SGPA": ["8.00"],
        "SEMETER RESULT": ["PASS"],
        "TOTAL MAR POINTS": ["0"],
    })
    return sample.to_csv(index=False).encode("utf-8")

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    unnamed_cols = [c for c in df.columns if c.startswith("UNNAMED") or c == ""]
    if unnamed_cols:
        df = df.drop(columns=unnamed_cols)
    return df

def normalize_token(text: object) -> str:
    if pd.isna(text):
        return ""
    return re.sub(r"[^A-Z0-9]+", "", str(text).strip().upper())

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
    if token in {"COURSECODE", "COURSEID"}:
        return "COURSE CODE"
    if token in {"COURSE", "COURSENAME", "PROGRAMME", "PROGRAM", "DEPARTMENT"}:
        return "COURSENAME"
    if token in {"STREAM", "BRANCH", "SPECIALIZATION", "SPECIALISATION"}:
        return "STREAM"
        
    # --- THE FIX FOR SGPA BUG ---
    # Return the exact text (e.g. "SGPA7", "SGPA8") so they remain distinct columns
    if any(gpa_type in token for gpa_type in ["SGPA", "YGPA", "CGPA", "DGPA", "GPA"]):
        return text 
        
    if "RESULT" in token and ("SEM" in token or "SEME" in token):
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
    has_course = any(t.startswith("COURSE") or t in {"COURSENAME", "STREAM", "BRANCH", "PROGRAMME", "PROGRAM"} for t in tokens)
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
                # Ensure SGPA/YGPA are treated as metadata mappings during row generation
                if col in KNOWN_NON_SUBJECT_COLUMNS or any(gpa_type in normalize_token(col) for gpa_type in ["SGPA", "YGPA", "CGPA", "DGPA", "GPA"]):
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

    parsed_df = pd.DataFrame(records)
    if parsed_df.empty:
        return parsed_df

    if "COURSE" in parsed_df.columns and "COURSENAME" not in parsed_df.columns:
        parsed_df = parsed_df.rename(columns={"COURSE": "COURSENAME"})

    for col, default_val in {"COLLEGE NAME": "", "SEMESTER": "UNKNOWN", "COURSE CODE": ""}.items():
        if col not in parsed_df.columns:
            parsed_df[col] = default_val
    return parsed_df

def clean_uploaded_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "ROLL NO" in df.columns:
        roll_series = df["ROLL NO"].astype(str).str.strip().str.upper()
        df = df[roll_series != "ROLL NO"]
    return df.dropna(how="all").reset_index(drop=True)

def deduplicate_exact_rows(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    if df.empty:
        return df.copy(), 0

    canonical = df.copy()
    for col in canonical.columns:
        series = canonical[col]
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            canonical[col] = series.fillna("").astype(str).str.strip()
        else:
            canonical[col] = series.fillna("")

    row_hash = pd.util.hash_pandas_object(canonical, index=False)
    duplicate_mask = row_hash.duplicated(keep="first")
    duplicate_count = int(duplicate_mask.sum())
    deduped_df = df.loc[~duplicate_mask].copy().reset_index(drop=True)
    return deduped_df, duplicate_count

def is_metadata_column(col: str) -> bool:
    token = normalize_token(col)
    if col in KNOWN_NON_SUBJECT_COLUMNS:
        return True
    if token.startswith("ROLL") or token == "NAME" or "COURSE" in token or "COLLEGE" in token:
        return True
    if "SEM" in token and "RESULT" in token:
        return True
        
    # --- THE FIX ---
    # Detect SGPA7, SGPA8, YGPA, etc., dynamically
    if any(gpa_type in token for gpa_type in ["SGPA", "YGPA", "CGPA", "DGPA", "GPA"]):
        return True
        
    if token in {"SEM", "SEMESTER", "PASSFAIL", "RESULT"}:
        return True
    if "MARKPOINT" in token or "MARPOINT" in token:
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

def parse_grade_value(value: object) -> Tuple[Optional[str], Optional[float]]:
    if pd.isna(value):
        return None, None
    text = str(value).strip().upper()
    if text in {"", "---", "NA", "N/A", "ABSENT", "AB"}:
        return None, None
    if text == "F":
        return "F", 0.0

    match = re.match(r"^([A-Z]+)\s*\(([-+]?[0-9]*\.?[0-9]+)\)$", text)
    if match:
        return match.group(1), float(match.group(2))

    numeric_match = re.match(r"^[-+]?[0-9]*\.?[0-9]+$", text)
    if numeric_match:
        return None, float(text)
    return text, None

# --- NEW FUNCTION FOR DYNAMIC GPA GATHERING ---
def get_gpa_columns(df: pd.DataFrame) -> List[str]:
    """Detects all GPA-related columns like SGPA1, SGPA2, YGPA, CGPA, etc."""
    gpa_cols = []
    for c in df.columns:
        token = normalize_token(c)
        if any(keyword in token for keyword in ["SGPA", "GPA", "YGPA", "DGPA", "CGPA"]):
            gpa_cols.append(c)
    return gpa_cols

def read_uploaded_dataset(uploaded_file) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()
    if file_name.endswith(".csv"):
        raw_df = pd.read_csv(uploaded_file, dtype=str, header=None)
    elif file_name.endswith(".xlsx") or file_name.endswith(".xls"):
        raw_df = pd.read_excel(uploaded_file, dtype=str, header=None)
    else:
        raise ValueError("Unsupported file format.")

    parsed_df = parse_multisection_rows(raw_df)
    if parsed_df.empty:
        raise ValueError("No valid student rows found.")
    return clean_uploaded_data(normalize_columns(parsed_df))

def read_uploaded_datasets(uploaded_files) -> pd.DataFrame:
    if not uploaded_files:
        raise ValueError("No files uploaded.")

    files = uploaded_files if isinstance(uploaded_files, list) else [uploaded_files]
    datasets: List[pd.DataFrame] = []
    file_errors: List[str] = []

    expected_errors = (ValueError, pd.errors.ParserError, UnicodeDecodeError, OSError)
    for uploaded_file in files:
        try:
            datasets.append(read_uploaded_dataset(uploaded_file))
        except expected_errors as exc:
            file_name = getattr(uploaded_file, "name", "Unknown file")
            file_errors.append(f"{file_name}: {exc}")

    if file_errors:
        raise ValueError("One or more files failed to process:\n- " + "\n- ".join(file_errors))
    if not datasets:
        raise ValueError("No valid student rows found across uploaded files.")

    combined_df = pd.concat(datasets, ignore_index=True)
    combined_df, duplicate_count = deduplicate_exact_rows(combined_df)
    combined_df.attrs["dropped_duplicate_rows"] = duplicate_count
    return combined_df

def apply_course_stream_filters(df: pd.DataFrame, course_label: str, course_key: str):
    courses = sorted(df["COURSENAME"].dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique().tolist())
    selected_course = st.selectbox(course_label, courses, key=course_key)
    filtered = df[df["COURSENAME"].astype(str).str.strip() == str(selected_course).strip()].copy()
    
    stream_col = next((c for c in ["STREAM", "BRANCH", "SPECIALIZATION"] if c in filtered.columns), None)
    if stream_col:
        stream_options = sorted(filtered[stream_col].dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique().tolist())
        if stream_options:
            selected_stream = st.selectbox(f"Select {stream_col.title()}", stream_options, key=f"{course_key}_stream")
            filtered = filtered[filtered[stream_col].astype(str).str.strip() == str(selected_stream).strip()].copy()

    return filtered

def require_data() -> Optional[Tuple[pd.DataFrame, List[str]]]:
    df = st.session_state.get("validated_df")
    subject_cols = st.session_state.get("subject_cols")
    if df is None or subject_cols is None:
        st.warning("Please upload and validate a dataset on the Upload Page first.")
        return None
    return df, subject_cols
