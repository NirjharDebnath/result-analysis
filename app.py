# app.py
import streamlit as st
from datetime import datetime, timezone
from utils.constants import COLLEGE_NAME, SOFT_COLORS, UI_THEME
from utils.processor import (
    read_uploaded_datasets,
    validate_dataset,
    get_sample_template_csv,
    render_clear_session_button,
    get_or_create_session_id,
)
from utils.subjects import (
    SUBJECT_CODE_COLUMN,
    SUBJECT_NAME_COLUMN,
    SUBJECT_MAPPING_STATE_KEY,
    get_subject_mapping,
    save_subject_mapping,
    subject_label_formatter,
    subject_mapping_from_dataframe,
    subject_mapping_to_dataframe,
)
from utils.analytics import build_semester_year_groups
from utils.visualizer import render_sidebar_branding, render_footer

st.set_page_config(page_title="Result Analysis", page_icon="🎓", layout="wide")

THEME = SOFT_COLORS

st.markdown(f"""
    <style>

        /* Main buttons */
        .stButton>button, .stDownloadButton>button {{
            background-color: {THEME["primary"]} !important;
            color: white !important;
            border-radius: 8px !important;
            border: none !important;
            padding: 10px 24px !important;
            font-weight: 600 !important;
            transition: 0.3s ease-in-out !important;
        }}

        .stButton>button:hover, .stDownloadButton>button:hover {{
            background-color: {THEME["button_hover"]} !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 10px {THEME["grid"]} !important;
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 10px;
        }}

        .stTabs [data-baseweb="tab"] {{
            background-color: {THEME["bg"]};
            border-radius: 6px 6px 0 0;
            padding: 10px 20px;
            border: 1px solid {THEME["grid"]};
            border-bottom: none;
            color: #2F3A45;
        }}

        .stTabs [aria-selected="true"] {{
            background-color: {THEME["primary"]} !important;
            color: white !important;
            font-weight: bold;
        }}

        /* Selectbox text wrapping */
        div[data-baseweb="select"] > div {{
            white-space: normal !important;
            word-wrap: break-word !important;
        }}

        /* Main app background */
        .stApp {{
            background-color: {THEME["bg"]};
        }}

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background-color: {THEME["sidebar"]} !important;
        }}

        /* Caption */
        div[data-testid="stCaptionContainer"] {{
            color: {UI_THEME["text"]} !important;
            opacity: 0.85;
        }}

        /* Success box */
        div[data-testid="stAlert"][kind="success"] {{
            background-color: {THEME["success_bg"]} !important;
            border-left: 5px solid {THEME["pass"]} !important;
            color: #2F3A45 !important;
        }}

        /* Info box */
        div[data-testid="stAlert"][kind="info"] {{
            background-color: {THEME["info_bg"]} !important;
            border-left: 5px solid {THEME["primary"]} !important;
            color: #2F3A45 !important;
        }}

        /* Warning box */
        div[data-testid="stAlert"][kind="warning"] {{
            background-color: {THEME["warning_bg"]} !important;
            border-left: 5px solid {THEME["lag"]} !important;
            color: #2F3A45 !important;
        }}

        /* Error box */
        div[data-testid="stAlert"][kind="error"] {{
            background-color: {THEME["error_bg"]} !important;
            border-left: 5px solid {THEME["fail"]} !important;
            color: #2F3A45 !important;
        }}
        
        /* Selectbox selected item */
        div[data-baseweb="select"] > div {{
            # background-color: {THEME["bg"]} !important;
            border: 1px solid {THEME["grid"]} !important;
            color: #2F3A45 !important;
        }}

        /* Dropdown hover */
        div[data-baseweb="option"]:hover {{
            background-color: {THEME["accent"]} !important;
            color: #2F3A45 !important;
        }}

        /* Selected dropdown option */
        div[aria-selected="true"][role="option"] {{
            background-color: {THEME["primary"]} !important;
            color: white !important;
        }}
    </style>
""", unsafe_allow_html=True)

render_sidebar_branding()
render_clear_session_button()
get_or_create_session_id()
subject_mapping = get_subject_mapping()
format_subject = subject_label_formatter(subject_mapping)

st.header(COLLEGE_NAME)
st.title("📁 Upload Your Result Dataset")
st.markdown(
    "Welcome! This tool helps you analyse student exam results — pass rates, subject statistics, "
    "grade distributions, rankings, and inter-semester comparisons. **Start by uploading your result file below.**"
)

st.info(
    "📌 **Steps to get started:**\n"
    "1. Download the sample CSV template to see the required column format.\n"
    "2. Upload your result file(s) in CSV or Excel format.\n"
    "3. Set the exam month and year for each file.\n"
    "4. Once validated, use the **sidebar** to navigate to Course Insights, Rankings, Student Profiles, or Semester Comparison."
)

st.download_button(
    "⬇️ Download sample CSV template",
    data=get_sample_template_csv(),
    file_name="result_analysis_sample_template.csv",
    mime="text/csv",
)

uploaded_files = st.file_uploader(
    "Upload result file(s)  (CSV, XLS, or XLSX)",
    type=["csv", "xls", "xlsx"],
    accept_multiple_files=True
)

if uploaded_files:
    try:
        month_options = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        now_utc = datetime.now(timezone.utc)
        current_year = now_utc.year
        current_month_index = now_utc.month - 1

        exam_session_by_file = {}
        with st.expander("🗓️ Set Exam Month & Year for Each File", expanded=True):
            st.caption("These values are used to separate current-batch students from re-appearing (old batch) students. Make sure they are correct before proceeding.")
            for idx, uploaded_file in enumerate(uploaded_files):
                c1, c2, c3 = st.columns([3, 2, 2])
                with c1:
                    st.write(f"**{uploaded_file.name}**")
                with c2:
                    exam_month = st.selectbox(
                        "Month",
                        month_options,
                        index=current_month_index,
                        key=f"exam_month_{idx}_{uploaded_file.name}",
                        label_visibility="collapsed",
                    )
                with c3:
                    exam_year = st.number_input(
                        "Year",
                        min_value=1990,
                        max_value=2100,
                        value=current_year,
                        step=1,
                        key=f"exam_year_{idx}_{uploaded_file.name}",
                        label_visibility="collapsed",
                    )
                exam_session_by_file[str(uploaded_file.name)] = {
                    "EXAM MONTH": exam_month,
                    "EXAM YEAR": int(exam_year),
                }

        df = read_uploaded_datasets(uploaded_files, exam_session_by_file=exam_session_by_file)
        errors, metadata_cols, subject_cols = validate_dataset(df)

        if errors:
            st.error("Validation failed — please check your file format.")
            for err in errors:
                st.write(f"- {err}")
        else:
            st.success("✅ Dataset validated successfully.")
            st.caption(f"Processed {len(uploaded_files)} file(s).")
            dedup_removed = int(df.attrs.get("dropped_duplicate_rows", 0))
            if dedup_removed > 0:
                st.caption(f"Removed {dedup_removed} duplicate row(s) with exactly matching student data.")

            semester_groups_df = build_semester_year_groups(df)
            unique_semesters = sorted(semester_groups_df["SEMESTER_LABEL"].dropna().astype(str).unique().tolist())
            unique_groups = sorted(semester_groups_df["GROUP_LABEL"].dropna().astype(str).unique().tolist())
            if len(unique_semesters) > 1:
                st.info(f"📊 Detected **{len(unique_semesters)} semesters** in this dataset. Head to the **Semester Comparison** page in the sidebar to compare them side by side.")
            elif len(unique_groups) > 1:
                st.info(f"📊 Detected **{len(unique_groups)} academic-year groups** within the same semester. Use **Semester Comparison** for year-wise analysis.")
            else:
                st.warning("Only one semester/year group detected. Comparison features will be limited until more semester data is uploaded.")
            st.caption("✅ Next: choose a page from the left sidebar — **Course Insights**, **Rankings**, **Student Profile**, or **Semester Comparison**.")
            
            # Save to session state so other pages can access it
            st.session_state["validated_df"] = df
            st.session_state["subject_cols"] = subject_cols

            with st.expander("🔍 Preview Dataset (first 50 rows)", expanded=True):
                st.dataframe(df.head(50), width='stretch')

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Metadata Columns")
                st.caption("These columns describe the student and exam context.")
                st.write(metadata_cols)
            with col2:
                st.subheader("Subject Columns")
                st.caption("These columns contain subject-wise grades or marks.")
                st.write([format_subject(col) for col in subject_cols])
                
    except Exception as exc:
        st.error(f"Unable to read uploaded file. Details: {exc}")

st.divider()
st.subheader("🗂️ Subject Code Reference")
st.caption(
    "Preview and edit the subject labels used across tables, charts, and PDFs. "
    "Add or delete rows here when subject codes change, without editing the code."
)

edited_subject_mapping_df = st.data_editor(
    subject_mapping_to_dataframe(subject_mapping),
    key="subject_mapping_editor",
    hide_index=True,
    num_rows="dynamic",
    width="stretch",
    column_config={
        SUBJECT_CODE_COLUMN: st.column_config.TextColumn(SUBJECT_CODE_COLUMN, required=False),
        SUBJECT_NAME_COLUMN: st.column_config.TextColumn(SUBJECT_NAME_COLUMN, required=False, width="large"),
    },
)

updated_subject_mapping = subject_mapping_from_dataframe(edited_subject_mapping_df)
if updated_subject_mapping != subject_mapping:
    try:
        save_subject_mapping(updated_subject_mapping)
        st.session_state[SUBJECT_MAPPING_STATE_KEY] = updated_subject_mapping
        st.warning("⚠️ Subject code/name updates were saved permanently and will apply in future sessions.")
    except OSError as exc:
        st.error(f"Unable to save subject mapping permanently. Details: {exc}")

st.caption(f"{len(updated_subject_mapping)} subject mappings available in the current session.")

render_footer()
