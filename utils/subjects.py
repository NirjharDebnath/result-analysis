import re
from typing import Dict, Optional

import pandas as pd
import streamlit as st


subjects = {
    # ================= SEMESTER 1 =================
    "BS-M101": "Mathematics-IA",
    "BS-PH101": "Physics-I",
    "ES-EE101": "Basic Electrical Engineering",
    "BS-PH191": "Physics-I Laboratory",
    "ES-EE191": "Basic Electrical Engineering Lab",
    "ES-ME192": "Workshop",

    # ================= SEMESTER 2 =================
    "BS-CH201": "Chemistry-I",
    "BS-M201": "Mathematics-IIA",
    "ES-CS201": "Programming for Problem Solving",
    "HM-HU201": "English",
    "BS-CH291": "Chemistry-I Laboratory",
    "ES-CS291": "Programming for Problem Solving Lab",
    "ES-ME291": "Engineering Graphics & Design",
    "HM-HU291": "Language Laboratory",

    # ================= SEMESTER 3 =================
    "ESC301": "Analog and Digital Electronics",
    "PCC-CS301": "Data Structure & Algorithms",
    "PCC-CS302": "Computer Organization",
    "BSC301": "Mathematics-III",
    "HSMC301": "Economics for Engineers",
    "PCC-CS391": "Data Structure & Algorithm Lab",
    "PCC-CS392": "Computer Organization Lab",

    # ================= SEMESTER 4 =================
    "PCC-CS401": "Design & Analysis of Algorithms",
    "PCC-CS402": "Database Management Systems",
    "PCC-CS403": "Discrete Mathematics",
    "PCC-CS404": "Formal Language & Automata Theory",
    "PCC-CS491": "Database Management Systems Lab",
    "PCC-CS492": "Discrete Mathematics Lab",
    "PCC-CS493": "Formal Language & Automata Theory Lab",
    "PCC-CS494": "Design & Analysis Algorithm Lab",

    # ================= SEMESTER 5 =================
    "ESC501": "Software Engineering",
    "PCC-CS501": "Compiler Design",
    "PCC-CS502": "Operating Systems",
    "PCC-CS503": "Object Oriented Programming",
    "ESC591": "Software Engineering Lab",
    "PCC-CS592": "Operating Systems Lab",
    "PCC-CS593": "Object Oriented Programming Lab",

    # ================= SEMESTER 6 =================
    "PCC-CS601": "Computer Networks",
    "PCC-CS602": "Machine Learning",
    "PCC-CS603": "Cryptography and Network Security",
    "PCC-CS691": "Machine Learning Lab",
    "PCC-CS692": "Computer Networks Lab",

    # ================= SEMESTER 7 =================
    "OEC-CS701A": "Operation Research",
    "OEC-CS701B": "Multimedia Technology",
    "PEC-CS701E": "Machine Learning Advanced Topics",
    "HSMC701": "Entrepreneurship Development",
    "PROJ-CS781": "Project-II",

    # ================= SEMESTER 8 =================
    "PROJ-CS881": "Project / Dissertation",
    "INT-CS881": "Internship"
}

SUBJECT_MAPPING_STATE_KEY = "subject_mapping"
SUBJECT_CODE_COLUMN = "Subject Code"
SUBJECT_NAME_COLUMN = "Subject Name"
_DUPLICATE_NUMBER_SUFFIX_PATTERN = re.compile(r"^(.*?)(\s*\(\d+\))?$")


def normalize_subject_code(code: object) -> str:
    if code is None:
        return ""
    return str(code).strip().upper()


def normalize_subject_mapping(mapping: Optional[Dict[object, object]]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for code, name in (mapping or {}).items():
        normalized_code = normalize_subject_code(code)
        normalized_name = str(name).strip() if name is not None else ""
        if normalized_code and normalized_name:
            normalized[normalized_code] = normalized_name
    return dict(sorted(normalized.items()))


DEFAULT_SUBJECTS = normalize_subject_mapping(subjects)


def get_subject_mapping() -> Dict[str, str]:
    current_mapping = st.session_state.get(SUBJECT_MAPPING_STATE_KEY)
    normalized_mapping = (
        normalize_subject_mapping(current_mapping)
        if isinstance(current_mapping, dict)
        else DEFAULT_SUBJECTS.copy()
    )
    if current_mapping != normalized_mapping:
        st.session_state[SUBJECT_MAPPING_STATE_KEY] = normalized_mapping.copy()
    return normalized_mapping


def subject_mapping_to_dataframe(mapping: Optional[Dict[object, object]] = None) -> pd.DataFrame:
    active_mapping = normalize_subject_mapping(mapping) if mapping is not None else get_subject_mapping()
    rows = [
        {SUBJECT_CODE_COLUMN: code, SUBJECT_NAME_COLUMN: name}
        for code, name in active_mapping.items()
    ]
    return pd.DataFrame(rows, columns=[SUBJECT_CODE_COLUMN, SUBJECT_NAME_COLUMN])


def subject_mapping_from_dataframe(df: Optional[pd.DataFrame]) -> Dict[str, str]:
    if df is None or df.empty:
        return {}

    mapping: Dict[str, str] = {}
    for row in df.to_dict("records"):
        code = normalize_subject_code(row.get(SUBJECT_CODE_COLUMN))
        name = str(row.get(SUBJECT_NAME_COLUMN, "")).strip()
        if code and name:
            mapping[code] = name
    return dict(sorted(mapping.items()))


def format_subject_label(subject_code: object, mapping: Optional[Dict[object, object]] = None) -> str:
    raw_subject = "" if subject_code is None else str(subject_code).strip()
    if not raw_subject:
        return raw_subject

    match = _DUPLICATE_NUMBER_SUFFIX_PATTERN.match(raw_subject)
    base_code = match.group(1).strip() if match else raw_subject
    suffix = match.group(2) or ""

    active_mapping = normalize_subject_mapping(mapping) if mapping is not None else get_subject_mapping()
    subject_name = active_mapping.get(normalize_subject_code(base_code))
    if not subject_name:
        return raw_subject

    return f"{base_code}{suffix} - {subject_name}"


def subject_label_formatter(mapping: Optional[Dict[object, object]] = None):
    return lambda subject_code: format_subject_label(subject_code, mapping)
