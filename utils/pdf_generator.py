# utils/pdf_generator.py
from fpdf import FPDF
import tempfile
import os
import pandas as pd

def clean_text(text):
    """Sanitizes text to prevent FPDF Unicode crashes."""
    if pd.isna(text): return ""
    text_str = str(text).replace("\u03c3", "SD") 
    return text_str.encode('latin-1', 'ignore').decode('latin-1')

def create_master_report_pdf(
    college_name, 
    course_name, 
    semester, 
    summary_table, 
    status_fig, 
    subject_stats_df,
    gpa_curve_fig,
    subject_curve_figs,
    z_score_df,
    comparison_fig=None
):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    tmp_files_to_clean = []
    
    # --- Page 1: Header & Overall Status ---
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, clean_text(college_name), ln=True, align="C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, clean_text(f"Master Result Analysis Report - {course_name}"), ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 8, clean_text(f"Semester: {semester}"), ln=True, align="C")
    pdf.ln(5)

    if status_fig is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            status_fig.savefig(tmp.name, format="png", bbox_inches="tight", dpi=150)
            pdf.image(tmp.name, x=10, y=None, w=190)
            tmp_files_to_clean.append(tmp.name)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 10, "Executive Summary", ln=True)
    pdf.set_font("Arial", "", 9)
    for key, val in summary_table.items():
        pdf.cell(95, 7, clean_text(f"{key}:"), border=1)
        pdf.cell(95, 7, clean_text(f"{val}"), border=1, ln=True)

    # --- Page 2: FULL Subject Statistics Matrix ---
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "Subject Performance Statistics", ln=True)
    pdf.ln(5)
    
    # REBALANCED COLUMN WIDTHS TO FIT "Pass %" perfectly on the page
    pdf.set_font("Arial", "B", 8)
    headers = ["Subject", "Mean", "Med", "SD", "Skew", "Pass %", "O", "E", "A", "B", "C", "D", "F"]
    col_widths = [54, 11, 11, 11, 11, 14, 11, 11, 11, 11, 11, 11, 12] # Exactly 190mm total width
    
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, clean_text(h), border=1, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 7)
    for _, row in subject_stats_df.iterrows():
        # Truncate subject string slightly to fit the new 54mm width
        pdf.cell(54, 7, clean_text(str(row["Subject"])[:38]), border=1)
        pdf.cell(11, 7, clean_text(str(row.get("Mean", ""))), border=1, align="C")
        pdf.cell(11, 7, clean_text(str(row.get("Median", ""))), border=1, align="C")
        pdf.cell(11, 7, clean_text(str(row.get("Std Dev (\u03c3)", ""))), border=1, align="C")
        pdf.cell(11, 7, clean_text(str(row.get("Skewness", ""))), border=1, align="C")
        pdf.cell(14, 7, clean_text(str(row.get("Pass %", ""))), border=1, align="C")
        pdf.cell(11, 7, clean_text(str(int(row.get("O", 0)))), border=1, align="C")
        pdf.cell(11, 7, clean_text(str(int(row.get("E", 0)))), border=1, align="C")
        pdf.cell(11, 7, clean_text(str(int(row.get("A", 0)))), border=1, align="C")
        pdf.cell(11, 7, clean_text(str(int(row.get("B", 0)))), border=1, align="C")
        pdf.cell(11, 7, clean_text(str(int(row.get("C", 0)))), border=1, align="C")
        pdf.cell(11, 7, clean_text(str(int(row.get("D", 0)))), border=1, align="C")
        pdf.cell(12, 7, clean_text(str(int(row.get("F", 0)))), border=1, align="C")
        pdf.ln()

    # --- Page 3: GPA Distribution Curve ---
    if gpa_curve_fig:
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(190, 10, "GPA Distribution Curve", ln=True)
        pdf.ln(5)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            gpa_curve_fig.savefig(tmp.name, format="png", bbox_inches="tight", dpi=150)
            pdf.image(tmp.name, x=10, w=180)
            tmp_files_to_clean.append(tmp.name)

    # --- Pages 4+: All Subject Curves (Stacked 2 per page) ---
    if subject_curve_figs:
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(190, 10, "Subject Distribution Curves", ln=True)
        pdf.ln(5)
        
        y_offset = pdf.get_y()
        for i, fig in enumerate(subject_curve_figs):
            if i > 0 and i % 2 == 0: 
                pdf.add_page()
                y_offset = 20
                
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                fig.savefig(tmp.name, format="png", bbox_inches="tight", dpi=150)
                pdf.image(tmp.name, x=10, y=y_offset, w=180)
                tmp_files_to_clean.append(tmp.name)
            
            y_offset += 120 

    # --- Z-Score Table ---
    if not z_score_df.empty:
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(190, 10, "Z-Score Analysis Table (Selected Metric)", ln=True)
        pdf.ln(2)
        
        pdf.set_font("Arial", "B", 9)
        pdf.cell(30, 8, "Roll No", border=1)
        pdf.cell(70, 8, "Name", border=1)
        pdf.cell(20, 8, "Value", border=1, align="C")
        pdf.cell(20, 8, "Z-Score", border=1, align="C")
        pdf.cell(50, 8, "Category", border=1, align="C")
        pdf.ln()
        
        pdf.set_font("Arial", "", 8)
        for _, row in z_score_df.iterrows():
            pdf.cell(30, 7, clean_text(str(row.iloc[0])[:15]), border=1)
            pdf.cell(70, 7, clean_text(str(row.iloc[1])[:35]), border=1)
            pdf.cell(20, 7, clean_text(str(row.iloc[2])), border=1, align="C")
            
            try: z_val = f"{float(row.iloc[3]):.2f}"
            except: z_val = str(row.iloc[3])
            pdf.cell(20, 7, clean_text(z_val), border=1, align="C")
            
            pdf.cell(50, 7, clean_text(str(row.iloc[4])), border=1, align="C")
            pdf.ln()

    # --- Semester Comparison (Optional) ---
    if comparison_fig is not None:
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(190, 15, "Inter-Semester Comparison Analysis", ln=True, align="C")
        pdf.ln(5)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            comparison_fig.savefig(tmp.name, format="png", bbox_inches="tight", dpi=150)
            pdf.image(tmp.name, x=10, w=190)
            tmp_files_to_clean.append(tmp.name)
        pdf.ln(10)
        pdf.set_font("Arial", "I", 9)
        pdf.multi_cell(190, 6, "Note: This chart compares performance metrics across the selected academic sessions and semesters.")

    # Cleanup temp files
    for f in tmp_files_to_clean:
        if os.path.exists(f): os.remove(f)

    pdf_out = pdf.output(dest="S")
    if isinstance(pdf_out, str):
        return pdf_out.encode("latin-1")
    return bytes(pdf_out)