# app.py
import streamlit as st
from utils.constants import COLLEGE_NAME
from utils.processor import read_uploaded_dataset, validate_dataset, get_sample_template_csv
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

uploaded_file = st.file_uploader("Upload result file", type=["csv", "xls", "xlsx"])

if uploaded_file:
    try:
        df = read_uploaded_dataset(uploaded_file)
        errors, metadata_cols, subject_cols = validate_dataset(df)

        if errors:
            st.error("Validation failed")
            for err in errors:
                st.write(f"- {err}")
        else:
            st.success("Dataset validated successfully.")
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