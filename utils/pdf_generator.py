# utils/pdf_generator.py
from fpdf import FPDF
import tempfile
import os
import pandas as pd

def clean_text(text):
    """Sanitizes text to prevent FPDF Unicode crashes."""
    if pd.isna(text): return ""
    text_str = str(text).replace("\u03c3", "SD").replace("\u2014", " - ").replace("\u2013", " - ")
    return text_str.encode('latin-1', 'ignore').decode('latin-1')

def create_master_report_pdf(
    college_name, 
    course_name, 
    semester, 
    summary_table, 
    status_fig, 
    subject_stats_df,
    gpa_curve_figs,
    subject_curve_figs,
    z_score_df,
    comparison_fig=None,
    overview_fig=None,
    batch_overview_data=None,
    logo_path=None,
    stat_grade_fig=None,
    stat_metric_fig=None,
    stat_grade_figs=None,
    stat_metric_figs=None,
):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    tmp_files_to_clean = []

    # --- Page 1: Header + Batch Overview Graph ---
    pdf.add_page()

    # College name centered at the top
    pdf.set_font("Arial", "B", 15)
    pdf.cell(190, 8, clean_text(college_name), ln=True, align="C")

    # Logo centered below college name
    if logo_path and os.path.exists(logo_path):
        logo_w = 22  # mm
        pdf.image(logo_path, x=(210 - logo_w) / 2, y=pdf.get_y(), w=logo_w)
        pdf.ln(logo_w + 2)

    # Course and semester lines
    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 7, clean_text(f"Combined Result Analysis Report - {course_name}"), ln=True, align="C")
    pdf.set_font("Arial", "", 9)
    pdf.cell(190, 6, clean_text(f"Semester: {semester}"), ln=True, align="C")
    pdf.ln(4)

    # Overview graph
    if overview_fig is not None:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(190, 8, "Batch Overview", ln=True)
        pdf.set_font("Arial", "", 9)
        pdf.multi_cell(190, 5, "Complete breakdown of the current batch: pass/fail composition, lateral vs regular students, and reappearing student outcomes.")
        pdf.ln(2)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            overview_fig.savefig(tmp.name, format="png", bbox_inches="tight", dpi=150)
            pdf.image(tmp.name, x=5, y=None, w=200)
            tmp_files_to_clean.append(tmp.name)
        pdf.ln(4)

    # --- Page 2: Combined Batch Overview + Executive Summary table, then Subject Statistics ---
    pdf.add_page()

    # table format summary in one place
    #empty
    
    # Subject Statistics Matrix on the same page (con# Subject Statistics Matrix on the same page (continued)tinued)
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

    combined_grade_figs = list(stat_grade_figs or [])
    combined_metric_figs = list(stat_metric_figs or [])
    if stat_grade_fig is not None:
        combined_grade_figs.insert(0, stat_grade_fig)
    if stat_metric_fig is not None:
        combined_metric_figs.insert(0, stat_metric_fig)

    if combined_grade_figs or combined_metric_figs:
        pdf.ln(3)
        current_y = pdf.get_y()
        estimated_needed = 90
        if current_y + estimated_needed > 280:
            pdf.add_page()
        pdf.set_font("Arial", "B", 11)
        pdf.cell(190, 8, "Statistical Matrix Visual Summary", ln=True)
        pdf.set_font("Arial", "", 9)
        pdf.multi_cell(190, 5, "Subject-wise grade bars and comparative metric charts for quick performance benchmarking.")
        pdf.ln(2)

        if combined_grade_figs:
            pdf.set_font("Arial", "B", 10)
            pdf.cell(190, 6, "Per-Subject Grade Distribution", ln=True)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                combined_grade_figs[0].savefig(tmp.name, format="png", bbox_inches="tight", dpi=150)
                pdf.image(tmp.name, x=10, y=None, w=188)
                tmp_files_to_clean.append(tmp.name)
            pdf.ln(4)
            for idx, fig in enumerate(combined_grade_figs[1:], start=2):
                if pdf.get_y() > 170:
                    pdf.add_page()
                pdf.set_font("Arial", "", 9)
                pdf.cell(190, 5, f"Subject Grade Distribution {idx}", ln=True)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    fig.savefig(tmp.name, format="png", bbox_inches="tight", dpi=150)
                    pdf.image(tmp.name, x=10, y=None, w=188)
                    tmp_files_to_clean.append(tmp.name)
                pdf.ln(3)

        if combined_metric_figs:
            if pdf.get_y() > 130:
                pdf.add_page()
            pdf.set_font("Arial", "B", 10)
            pdf.cell(190, 6, "Comparative Metric Charts", ln=True)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                combined_metric_figs[0].savefig(tmp.name, format="png", bbox_inches="tight", dpi=150)
                pdf.image(tmp.name, x=10, y=None, w=188)
                tmp_files_to_clean.append(tmp.name)
            pdf.ln(4)
            for idx, fig in enumerate(combined_metric_figs[1:], start=2):
                if pdf.get_y() > 170:
                    pdf.add_page()
                pdf.set_font("Arial", "", 9)
                pdf.cell(190, 5, f"Comparative Metric Chart {idx}", ln=True)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    fig.savefig(tmp.name, format="png", bbox_inches="tight", dpi=150)
                    pdf.image(tmp.name, x=10, y=None, w=188)
                    tmp_files_to_clean.append(tmp.name)
                pdf.ln(3)

    def _draw_curve_pair(curve_fig, pie_fig):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_curve:
            curve_fig.savefig(tmp_curve.name, format="png", bbox_inches="tight", dpi=150)
            y_start = pdf.get_y()
            pdf.image(tmp_curve.name, x=8, y=y_start, w=118)
            tmp_files_to_clean.append(tmp_curve.name)
        if pie_fig is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_pie:
                pie_fig.savefig(tmp_pie.name, format="png", bbox_inches="tight", dpi=150)
                pdf.image(tmp_pie.name, x=130, y=y_start, w=74)
                tmp_files_to_clean.append(tmp_pie.name)
            row_height = 85
        else:
            row_height = 78
        pdf.set_y(y_start + row_height)
        pdf.ln(4)

    # --- Pages 4+: GPA Distribution Curves ---
    if gpa_curve_figs:
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(190, 10, "GPA Distribution Curves", ln=True)
        pdf.ln(5)

        for i, figure_entry in enumerate(gpa_curve_figs):
            if isinstance(figure_entry, (list, tuple)):
                curve_fig = figure_entry[0] if len(figure_entry) > 0 else None
                pie_fig = figure_entry[1] if len(figure_entry) > 1 else None
            else:
                curve_fig = figure_entry
                pie_fig = None
            if curve_fig is None:
                continue
            if i > 0 and pdf.get_y() > 180:
                pdf.add_page()
            _draw_curve_pair(curve_fig, pie_fig)

    # --- Pages 4+: All Subject Curves (Stacked 2 per page) ---
    if subject_curve_figs:
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(190, 10, "Subject Distribution Curves", ln=True)
        pdf.ln(5)
        
        for i, figure_entry in enumerate(subject_curve_figs):
            if isinstance(figure_entry, (list, tuple)):
                curve_fig = figure_entry[0] if len(figure_entry) > 0 else None
                pie_fig = figure_entry[1] if len(figure_entry) > 1 else None
            else:
                curve_fig = figure_entry
                pie_fig = None
            if curve_fig is None:
                continue
            if i > 0 and pdf.get_y() > 180: 
                pdf.add_page()
            _draw_curve_pair(curve_fig, pie_fig)

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
