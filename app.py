# app.py
import streamlit as st
from datetime import datetime
from utils.constants import COLLEGE_NAME
from utils.processor import read_uploaded_datasets, validate_dataset, get_sample_template_csv
from utils.analytics import build_semester_year_groups
from utils.visualizer import render_sidebar_branding, render_footer

st.set_page_config(page_title="Result Analysis", page_icon="🎓", layout="wide")

render_sidebar_branding()

st.header(COLLEGE_NAME)
st.title("📁 Upload Your Result Dataset")

st.info("Start here: upload your result file, validate it, and then use the sidebar to navigate to Insights or Rankings.")

st.download_button(
    "Download sample CSV template",
    data=get_sample_template_csv(),
    file_name="result_analysis_sample_template.csv",
    mime="text/csv",
)

uploaded_files = st.file_uploader(
    "Upload result file(s)",
    type=["csv", "xls", "xlsx"],
    accept_multiple_files=True
)

if uploaded_files:
    try:
        month_options = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        current_year = datetime.utcnow().year
        current_month_index = datetime.utcnow().month - 1

        exam_session_by_file = {}
        with st.expander("🗓️ Exam Month/Year per Uploaded File", expanded=True):
            st.caption("Enter the exam month and year for each uploaded file. These values are added as columns for better current/past/reappearing separation.")
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
            st.error("Validation failed")
            for err in errors:
                st.write(f"- {err}")
        else:
            st.success("Dataset validated successfully.")
            st.caption(f"Processed {len(uploaded_files)} file(s).")
            dedup_removed = int(df.attrs.get("dropped_duplicate_rows", 0))
            if dedup_removed > 0:
                st.caption(f"Removed {dedup_removed} duplicate row(s) with exactly matching student data.")

            semester_groups_df = build_semester_year_groups(df)
            unique_semesters = sorted(semester_groups_df["SEMESTER_LABEL"].dropna().astype(str).unique().tolist())
            unique_groups = sorted(semester_groups_df["GROUP_LABEL"].dropna().astype(str).unique().tolist())
            if len(unique_semesters) > 1:
                st.info(f"Detected multiple semesters ({len(unique_semesters)}). Use the sidebar 'Semester Comparison' page for inter-sem analysis.")
            elif len(unique_groups) > 1:
                st.info(f"Detected multiple academic-year groups within the same semester ({len(unique_groups)}). Use 'Semester Comparison' for year-wise analysis.")
            else:
                st.warning("Only one semester/year group detected. Comparison features will be limited until more semester/year data is uploaded.")
            st.caption("Next step: choose a page from the left sidebar to explore insights, rankings, or student-level performance.")
            
            # Save to session state so other pages can access it
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
                
    except Exception as exc:
        st.error(f"Unable to read uploaded file. Details: {exc}")

render_footer()
