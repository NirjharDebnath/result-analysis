import io
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="College Result Analysis", page_icon="📊", layout="wide")

COLLEGE_NAME = "Kalyani Government Engineering College"

REQUIRED_COLUMNS = [
    "ROLL NO",
    "NAME",
    "COURSENAME",
]

KNOWN_NON_SUBJECT_COLUMNS = {
    "ROLL NO",
    "NAME",
    "COLLEGE NAME",
    "SEMESTER",
    "COURSE CODE",
    "COURSENAME",
    "SGPA",
    "SEMETER RESULT",
    "SEMESTER RESULT",
    "TOTAL MAR POINTS",
    "TOTAL MARK POINTS",
    "STREAM",
    "BRANCH",
    "SPECIALIZATION",
}

PASSING_GRADES = {"O", "E", "A", "B", "C", "D", "P", "S"}
SOFT_COLORS = {
    "pass": "#6BBF9F",
    "fail": "#E5989B",
    "primary": "#8AB6D6",
    "grid": "#D9E3F0",
}
LOGO_CANDIDATE_PATHS = [
    "assets/kgec_logo.png",
    "assets/kgec-logo.png",
    "kgec_logo.png",
    "kgec-logo.png",
    "logo.png",
]


@st.cache_data
def get_sample_template_csv() -> bytes:
    sample = pd.DataFrame(
        {
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
        }
    )
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
    if "SGPA" in token or token == "GPA":
        return "SGPA"
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

    parsed_df = pd.DataFrame(records)
    if parsed_df.empty:
        return parsed_df

    if "COURSE" in parsed_df.columns and "COURSENAME" not in parsed_df.columns:
        parsed_df = parsed_df.rename(columns={"COURSE": "COURSENAME"})

    for col, default_val in {
        "COLLEGE NAME": "",
        "SEMESTER": "UNKNOWN",
        "COURSE CODE": "",
    }.items():
        if col not in parsed_df.columns:
            parsed_df[col] = default_val
    return parsed_df


def clean_uploaded_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "ROLL NO" in df.columns:
        roll_series = df["ROLL NO"].astype(str).str.strip().str.upper()
        df = df[roll_series != "ROLL NO"]
    return df.dropna(how="all").reset_index(drop=True)


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
    if token in {"SEM", "SEMESTER", "SGPA", "GPA", "PASSFAIL", "RESULT"}:
        return True
    if "MARKPOINT" in token or "MARPOINT" in token:
        return True
    return False


def validate_dataset(df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
    errors: List[str] = []
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        errors.append(
            "Missing required column(s): " + ", ".join(missing)
        )

    if "ROLL NO" in df.columns and df["ROLL NO"].astype(str).str.strip().eq("").all():
        errors.append("ROLL NO appears empty for all rows.")

    if "NAME" in df.columns and df["NAME"].astype(str).str.strip().eq("").all():
        errors.append("NAME appears empty for all rows.")

    metadata_cols = [c for c in df.columns if is_metadata_column(c)]
    subject_cols = [c for c in df.columns if not is_metadata_column(c)]
    subject_cols = [c for c in subject_cols if df[c].astype(str).str.strip().ne("").any()]

    if not subject_cols:
        errors.append(
            "No subject columns detected. Add at least one subject column beyond metadata columns."
        )

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
        grade = match.group(1)
        marks = float(match.group(2))
        return grade, marks

    numeric_match = re.match(r"^[-+]?[0-9]*\.?[0-9]+$", text)
    if numeric_match:
        return None, float(text)

    return text, None


def marks_frame(df: pd.DataFrame, subjects: List[str]) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        for subject in subjects:
            grade, marks = parse_grade_value(row.get(subject))
            if grade == "F":
                status = "Fail"
            elif grade in PASSING_GRADES:
                status = "Pass"
            elif marks is None:
                status = "Unknown"
            else:
                status = "Pass" if marks > 0 else "Fail"

            rows.append(
                {
                    "ROLL NO": row.get("ROLL NO"),
                    "NAME": row.get("NAME"),
                    "COURSE CODE": row.get("COURSE CODE"),
                    "COURSENAME": row.get("COURSENAME"),
                    "SEMESTER": row.get("SEMESTER"),
                    "SUBJECT": subject,
                    "RAW": row.get(subject),
                    "GRADE": grade,
                    "MARKS": marks,
                    "STATUS": status,
                }
            )

    return pd.DataFrame(rows)


def get_sgpa_column(df: pd.DataFrame) -> Optional[str]:
    for c in df.columns:
        token = normalize_token(c)
        if "SGPA" in token or token == "GPA":
            return c
    return None


def read_uploaded_dataset(uploaded_file) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()
    if file_name.endswith(".csv"):
        raw_df = pd.read_csv(uploaded_file, dtype=str, header=None)
    elif file_name.endswith(".xlsx") or file_name.endswith(".xls"):
        raw_df = pd.read_excel(uploaded_file, dtype=str, header=None)
    else:
        raise ValueError("Unsupported file format. Please upload CSV, XLS, or XLSX.")

    parsed_df = parse_multisection_rows(raw_df)
    if parsed_df.empty:
        raise ValueError(
            "No valid student rows found. Ensure each section starts with a header like Roll/Name/Course."
        )
    return clean_uploaded_data(normalize_columns(parsed_df))


def apply_course_stream_filters(df: pd.DataFrame, course_label: str, course_key: str):
    courses = sorted(
        df["COURSENAME"]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .unique()
        .tolist()
    )
    selected_course = st.selectbox(course_label, courses, key=course_key)
    filtered = df[df["COURSENAME"].astype(str).str.strip() == str(selected_course).strip()].copy()

    stream_col = next(
        (c for c in ["STREAM", "BRANCH", "SPECIALIZATION"] if c in filtered.columns),
        None,
    )
    if stream_col:
        stream_options = sorted(
            filtered[stream_col]
            .dropna()
            .astype(str)
            .str.strip()
            .replace("", pd.NA)
            .dropna()
            .unique()
            .tolist()
        )
        if stream_options:
            selected_stream = st.selectbox(f"Select {stream_col.title()}", stream_options, key=f"{course_key}_stream")
            filtered = filtered[filtered[stream_col].astype(str).str.strip() == str(selected_stream).strip()].copy()

    return filtered


def downloadable_plot(fig, filename: str):
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=150)
    st.download_button(
        label=f"Download {filename}",
        data=buffer.getvalue(),
        file_name=filename,
        mime="image/png",
        use_container_width=True,
    )
    plt.close(fig)


def download_table_button(df: pd.DataFrame, label: str, filename: str):
    st.download_button(
        label=label,
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )


def resolve_logo_path() -> Optional[str]:
    base_path = Path(__file__).resolve().parent
    for relative_path in LOGO_CANDIDATE_PATHS:
        logo_path = base_path / relative_path
        if logo_path.exists():
            return str(logo_path)
    return None


def render_sidebar_branding():
    logo_path = resolve_logo_path()
    if logo_path:
        st.sidebar.image(logo_path, width=120)
    st.sidebar.markdown("**Kalyani Government Engineering College**")


def style_axis(ax, xlabel: Optional[str] = None, ylabel: Optional[str] = None, rotate_x: int = 0):
    ax.set_facecolor("#F8FAFC")
    ax.grid(axis="y", linestyle="--", alpha=0.35, color=SOFT_COLORS["grid"])
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10, fontweight="semibold")
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10, fontweight="semibold")
    ax.tick_params(axis="x", labelsize=9)
    ax.tick_params(axis="y", labelsize=9)
    for tick in ax.get_xticklabels():
        tick.set_rotation(rotate_x)
        tick.set_ha("right" if rotate_x else "center")


def render_footer():
    st.markdown("---")
    st.caption(
        "© Designed by Nirjhar Debnath, Dept of CSE, Kalyani Government Engineering College."
    )


def page_upload_and_validate():
    st.header(COLLEGE_NAME)
    st.title("📄 Upload Your Result Dataset")
    st.info(
        "Start here: upload your result file, validate it, and then use the sidebar to open Insights, Rankings, or Student Performance."
    )
    with st.expander("How to use this app", expanded=False):
        st.markdown(
            """
            1. Upload a **CSV/XLS/XLSX** result file.  
            2. Confirm successful validation and review detected columns.  
            3. Open **Course & Subject Insights** for trends and charts.  
            4. Open **Student Rankings** for merit lists.  
            5. Open **Student Performance Dashboard** for student-level details.
            """
        )
    st.download_button(
        "Download sample CSV template",
        data=get_sample_template_csv(),
        file_name="result_analysis_sample_template.csv",
        mime="text/csv",
    )

    uploaded_file = st.file_uploader("Upload result file", type=["csv", "xls", "xlsx"])
    if not uploaded_file:
        st.info("Upload a CSV, XLS, or XLSX file to begin analysis.")
        return

    try:
        df = read_uploaded_dataset(uploaded_file)
    except Exception as exc:
        st.error(
            f"Unable to read uploaded file. Please upload a valid CSV/XLS/XLSX with section headers. Details: {exc}"
        )
        return

    errors, metadata_cols, subject_cols = validate_dataset(df)

    if errors:
        st.error("Validation failed")
        for err in errors:
            st.write(f"- {err}")
        return

    st.success("Dataset validated successfully.")
    st.caption(
        "Next step: choose a page from the left sidebar to explore insights, rankings, or student-level performance."
    )
    st.session_state["validated_df"] = df
    st.session_state["subject_cols"] = subject_cols

    with st.expander("Preview dataset", expanded=True):
        st.dataframe(df.head(50), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Metadata columns")
        st.write(metadata_cols)
    with col2:
        st.subheader("Subject columns")
        st.write(subject_cols)


def require_data() -> Optional[Tuple[pd.DataFrame, List[str]]]:
    df = st.session_state.get("validated_df")
    subject_cols = st.session_state.get("subject_cols")
    if df is None or subject_cols is None:
        st.warning("Please upload and validate a dataset on Page 1 first.")
        return None
    return df, subject_cols


def page_course_subject_analysis():
    st.header(COLLEGE_NAME)
    st.title("📊 Course & Subject Insights")

    data = require_data()
    if data is None:
        return
    df, subject_cols = data

    course_df = apply_course_stream_filters(df, "Select Course", "course_analysis")
    semesters = sorted(course_df["SEMESTER"].dropna().astype(str).unique().tolist())
    selected_semester = st.selectbox("Select Semester", semesters)
    filtered_df = course_df[course_df["SEMESTER"].astype(str).str.strip() == str(selected_semester).strip()].copy()

    available_subjects = [
        c
        for c in subject_cols
        if c in filtered_df.columns and filtered_df[c].notna().any()
    ]
    selected_subjects = st.multiselect(
        "Select subject(s)", available_subjects, default=available_subjects
    )

    if not selected_subjects:
        st.info("Select at least one subject for analysis.")
        return

    long_df = marks_frame(filtered_df, selected_subjects)

    pass_fail = (
        long_df[long_df["STATUS"].isin(["Pass", "Fail"])]
        .groupby("STATUS")
        .size()
        .reindex(["Pass", "Fail"], fill_value=0)
        .reset_index(name="COUNT")
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Students", len(filtered_df))
    col2.metric("Pass Entries", int(pass_fail.loc[pass_fail["STATUS"] == "Pass", "COUNT"].sum()))
    col3.metric("Fail Entries", int(pass_fail.loc[pass_fail["STATUS"] == "Fail", "COUNT"].sum()))

    fig1, ax1 = plt.subplots(figsize=(5, 3.5))
    ax1.bar(pass_fail["STATUS"], pass_fail["COUNT"], color=[SOFT_COLORS["pass"], SOFT_COLORS["fail"]])
    ax1.set_title("Pass vs Fail Count")
    style_axis(ax1, xlabel="Result Status", ylabel="Count")
    downloadable_plot(fig1, "pass_vs_fail.png")

    failure_details = (
        long_df[long_df["STATUS"] == "Fail"]
        .groupby("SUBJECT")
        .agg(FAIL_COUNT=("ROLL NO", "count"))
        .reset_index()
        .sort_values("FAIL_COUNT", ascending=False)
    )
    st.subheader("Subject-wise failure details")
    st.dataframe(failure_details, use_container_width=True)
    download_table_button(failure_details, "Download failure details", "subject_failure_details.csv")

    sgpa_col = get_sgpa_column(filtered_df)
    if sgpa_col:
        sgpa_series = pd.to_numeric(filtered_df[sgpa_col], errors="coerce").dropna()
        if not sgpa_series.empty:
            fig2, ax2 = plt.subplots(figsize=(7, 3.5))
            ax2.hist(sgpa_series, bins=min(10, max(3, sgpa_series.nunique())), color=SOFT_COLORS["primary"])
            ax2.set_title(f"{sgpa_col} Distribution")
            style_axis(ax2, xlabel=sgpa_col, ylabel="Count")
            downloadable_plot(fig2, "sgpa_distribution.png")

    marks_numeric = long_df.dropna(subset=["MARKS"]).copy()

    if not marks_numeric.empty:
        topper_lowest = (
            marks_numeric.sort_values("MARKS", ascending=False)
            .groupby("SUBJECT")
            .agg(
                TOPPER=("NAME", "first"),
                TOPPER_MARKS=("MARKS", "first"),
                LOWEST=("NAME", "last"),
                LOWEST_MARKS=("MARKS", "last"),
            )
            .reset_index()
        )
        st.subheader("Topper vs Lowest (subject-wise)")
        st.dataframe(topper_lowest, use_container_width=True)
        download_table_button(topper_lowest, "Download topper vs lowest", "topper_vs_lowest.csv")

        subject_count = marks_numeric["SUBJECT"].nunique()
        fig3_width = min(16, max(8, subject_count * 0.65))
        fig3, ax3 = plt.subplots(figsize=(fig3_width, 4.2))
        marks_numeric.boxplot(column="MARKS", by="SUBJECT", ax=ax3)
        ax3.set_title("Marks Distribution by Subject")
        style_axis(ax3, xlabel="Subject", ylabel="Marks", rotate_x=45)
        plt.suptitle("")
        downloadable_plot(fig3, "subject_boxplot.png")


def page_ranking_system():
    st.header(COLLEGE_NAME)
    st.title("🏆 Student Rankings")

    data = require_data()
    if data is None:
        return
    df, subject_cols = data

    course_df = apply_course_stream_filters(df, "Select Course", "rank_course")
    semesters = sorted(course_df["SEMESTER"].dropna().astype(str).unique().tolist())
    selected_semester = st.selectbox("Select Semester", semesters, key="rank_sem")
    filtered_df = course_df[course_df["SEMESTER"].astype(str).str.strip() == str(selected_semester).strip()].copy()

    ranking_mode = st.radio("Ranking Basis", ["Overall GPA/Marks", "By Subject"], horizontal=True)
    rank_type = st.selectbox("Ranking Type", ["Standard", "Dense"])
    rank_method = "min" if rank_type == "Standard" else "dense"

    rank_df = filtered_df[["ROLL NO", "NAME", "COURSENAME", "SEMESTER"]].copy()

    if ranking_mode == "Overall GPA/Marks":
        sgpa_col = get_sgpa_column(filtered_df)
        if sgpa_col:
            metric_col = sgpa_col
            rank_df[metric_col] = pd.to_numeric(filtered_df[metric_col], errors="coerce")
        else:
            marks_df = marks_frame(filtered_df, [c for c in subject_cols if c in filtered_df.columns])
            overall = marks_df.groupby("ROLL NO")["MARKS"].sum(min_count=1)
            metric_col = "TOTAL_MARKS"
            rank_df = rank_df.merge(overall.rename(metric_col), on="ROLL NO", how="left")
    else:
        subject_choices = [c for c in subject_cols if c in filtered_df.columns]
        selected_subject = st.selectbox("Subject", subject_choices)
        metric_col = selected_subject
        rank_df[metric_col] = filtered_df[selected_subject].apply(
            lambda x: parse_grade_value(x)[1]
        )

    rank_df[metric_col] = pd.to_numeric(rank_df[metric_col], errors="coerce")
    rank_df = rank_df.dropna(subset=[metric_col]).copy()
    rank_df["RANK"] = rank_df[metric_col].rank(method=rank_method, ascending=False).astype(int)
    rank_df = rank_df.sort_values(["RANK", metric_col, "NAME"], ascending=[True, False, True])

    st.dataframe(rank_df, use_container_width=True)
    download_table_button(rank_df, "Download rank list", "rank_list.csv")


def page_student_drilldown():
    st.header(COLLEGE_NAME)
    st.title("👤 Student Performance Dashboard")

    data = require_data()
    if data is None:
        return
    df, subject_cols = data

    course_df = apply_course_stream_filters(df, "Select Course", "student_course")

    student_options = (
        course_df[["ROLL NO", "NAME"]]
        .dropna()
        .astype(str)
        .assign(DISPLAY=lambda d: d["ROLL NO"] + " - " + d["NAME"])
    )

    selected_display = st.selectbox(
        "Select Student (searchable)",
        sorted(student_options["DISPLAY"].unique().tolist()),
        key="student_select",
    )

    selected_roll = selected_display.split(" - ", 1)[0]
    student_row = course_df[course_df["ROLL NO"].astype(str) == selected_roll].head(1)

    if student_row.empty:
        st.error("Student not found in the selected course.")
        return

    sr = student_row.iloc[0]
    st.write(
        {
            "ROLL NO": str(sr.get("ROLL NO", "")),
            "NAME": str(sr.get("NAME", "")),
            "COURSENAME": str(sr.get("COURSENAME", "")),
            "SEMESTER": str(sr.get("SEMESTER", "")),
            "SGPA": str(sr.get(get_sgpa_column(course_df) or "SGPA", "N/A")),
        }
    )

    subject_rows = []
    backlog_count = 0
    for subject in [c for c in subject_cols if c in course_df.columns and course_df[c].notna().any()]:
        grade, marks = parse_grade_value(sr.get(subject))
        if grade == "F":
            status = "Fail"
            backlog_count += 1
        elif grade in PASSING_GRADES:
            status = "Pass"
        elif marks is None:
            status = "Unknown"
        else:
            status = "Pass" if marks > 0 else "Fail"
            if status == "Fail":
                backlog_count += 1

        subject_rows.append(
            {
                "SUBJECT": subject,
                "RAW": sr.get(subject),
                "GRADE": grade,
                "MARKS": marks,
                "STATUS": status,
            }
        )

    subject_df = pd.DataFrame(subject_rows)
    st.subheader("Subject-wise Performance")
    st.dataframe(subject_df, use_container_width=True)
    download_table_button(subject_df, "Download student performance", "student_performance.csv")

    total_subjects = int((subject_df["STATUS"] != "Unknown").sum())
    passed_subjects = int((subject_df["STATUS"] == "Pass").sum())
    st.info(
        f"Performance summary: Passed {passed_subjects}/{total_subjects} subjects | Backlogs: {backlog_count}"
    )


render_sidebar_branding()

page = st.sidebar.radio(
    "Navigate",
    [
        "Upload Result Dataset",
        "Course & Subject Insights",
        "Student Rankings",
        "Student Performance Dashboard",
    ],
)

if page == "Upload Result Dataset":
    page_upload_and_validate()
elif page == "Course & Subject Insights":
    page_course_subject_analysis()
elif page == "Student Rankings":
    page_ranking_system()
else:
    page_student_drilldown()

render_footer()
