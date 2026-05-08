# utils/pdf_generator.py
from fpdf import FPDF
import tempfile
import os
import pandas as pd

class KGEC_PDF(FPDF):
    def __init__(self, logo_path=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logo_path = logo_path

    def header(self):
        # 1. Subtle Watermark Logo (Appears on every page behind text)
        if self.logo_path and os.path.exists(self.logo_path):
            with self.local_context(fill_opacity=0.08):  # Subtle 8% opacity
                # Centers the logo: A4 width is 210mm. (210-120)/2 = 45
                self.image(self.logo_path, x=45, y=90, w=120)

def clean_text(text):
    """Sanitizes text to prevent FPDF Unicode crashes."""
    if pd.isna(text): return ""
    text_str = str(text).replace("\u03c3", "SD").replace("\u2014", " - ").replace("\u2013", " - ")
    return text_str.encode('latin-1', 'ignore').decode('latin-1')

def create_master_report_pdf(
    college_name, 
    course_name, 
    semester, 
    year_name,      # Added
    exam_session,   # Added
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
    teacher_names=None,
    subject_codes=None,
):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    tmp_files_to_clean = []
    PAGE_CONTENT_LIMIT_Y = pdf.h - 17  # Keep visual pairs above bottom margin for A4 portrait.
    TOP_FIG_HEIGHT_EST = 88  # Approximate height for full-width tab-3 chart exports.
    BOTTOM_FIG_HEIGHT_EST = 82  # Approximate height for secondary stacked charts.
    STACK_VERTICAL_GAP = 8
    TOP_TO_BOTTOM_OFFSET = 4
    SINGLE_CHART_BOTTOM_PADDING = 6
    STACK_BOTTOM_PADDING = 10
    TEACHER_LABEL_HEIGHT = 6  # cell(h=5) + ln(1)

    # --- Page 1: Header + Batch Overview Graph ---
    pdf = KGEC_PDF(logo_path=logo_path)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # College name centered at the top
    pdf.set_font("Arial", "B", 15)
    pdf.cell(190, 8, clean_text(college_name), ln=True, align="C")
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 7, clean_text(f"{course_name} | {year_name}"), ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    session_info = f"Semester: {semester}"
    if exam_session:
        session_info += f" | Exam Session: {exam_session}"
    pdf.cell(190, 6, clean_text(session_info), ln=True, align="C")
    
    pdf.ln(10)
    # Logo centered below college name
    if logo_path and os.path.exists(logo_path):
        logo_w = 22  # mm
        pdf.image(logo_path, x=(210 - logo_w) / 2, y=pdf.get_y(), w=logo_w)
        pdf.ln(logo_w + 2)

    # Course and semester lines
    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 7, clean_text(f"Combined Result Analysis Report - {course_name}"), ln=True, align="C")
    pdf.set_font("Arial", "", 9)
    pdf.cell(190, 6, clean_text(f"Semester: {semester} | {year_name}"), ln=True, align="C")
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

    # Determine whether to include a Teacher column
    has_teachers = bool(teacher_names and any(teacher_names.values()))
    if has_teachers:
        # Widths sum to 190mm; Subject narrowed to 38, Teacher at 22
        pdf.set_font("Arial", "B", 8)
        headers = ["Subject", "Teacher", "Mean", "Med", "SD", "Skew", "Pass %", "O", "E", "A", "B", "C", "D", "F"]
        col_widths = [38, 22, 11, 11, 11, 11, 14, 9, 9, 9, 9, 9, 9, 9]  # 190mm total
    else:
        # REBALANCED COLUMN WIDTHS TO FIT "Pass %" perfectly on the page
        pdf.set_font("Arial", "B", 8)
        headers = ["Subject", "Mean", "Med", "SD", "Skew", "Pass %", "O", "E", "A", "B", "C", "D", "F"]
        col_widths = [54, 11, 11, 11, 11, 14, 11, 11, 11, 11, 11, 11, 12]  # Exactly 190mm total width
    
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, clean_text(h), border=1, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 7)
    for _, row in subject_stats_df.iterrows():
        if has_teachers:
            pdf.cell(38, 7, clean_text(str(row["Subject"])[:28]), border=1)
            _teacher_val = clean_text(str(row.get("Teacher", ""))[:18])
            pdf.cell(22, 7, _teacher_val, border=1)
            pdf.cell(11, 7, clean_text(str(row.get("Mean", ""))), border=1, align="C")
            pdf.cell(11, 7, clean_text(str(row.get("Median", ""))), border=1, align="C")
            pdf.cell(11, 7, clean_text(str(row.get("Std Dev (\u03c3)", ""))), border=1, align="C")
            pdf.cell(11, 7, clean_text(str(row.get("Skewness", ""))), border=1, align="C")
            pdf.cell(14, 7, clean_text(str(row.get("Pass %", ""))), border=1, align="C")
            pdf.cell(9, 7, clean_text(str(int(row.get("O", 0)))), border=1, align="C")
            pdf.cell(9, 7, clean_text(str(int(row.get("E", 0)))), border=1, align="C")
            pdf.cell(9, 7, clean_text(str(int(row.get("A", 0)))), border=1, align="C")
            pdf.cell(9, 7, clean_text(str(int(row.get("B", 0)))), border=1, align="C")
            pdf.cell(9, 7, clean_text(str(int(row.get("C", 0)))), border=1, align="C")
            pdf.cell(9, 7, clean_text(str(int(row.get("D", 0)))), border=1, align="C")
            pdf.cell(9, 7, clean_text(str(int(row.get("F", 0)))), border=1, align="C")
        else:
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

    def _draw_vertical_pair(top_fig, bottom_fig=None, top_width=152, bottom_width=110):
        """Render one figure on top and optional second figure below it."""
        top_height_est = TOP_FIG_HEIGHT_EST
        bottom_height_est = BOTTOM_FIG_HEIGHT_EST if bottom_fig is not None else 0
        required = top_height_est + (bottom_height_est + STACK_VERTICAL_GAP if bottom_fig is not None else 0)
        if pdf.get_y() + required > PAGE_CONTENT_LIMIT_Y:
            pdf.add_page()

        y_start = pdf.get_y()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_top:
            top_fig.savefig(tmp_top.name, format="png", bbox_inches="tight", dpi=150)
            pdf.image(tmp_top.name, x=(210 - top_width) / 2, y=y_start, w=top_width)
            tmp_files_to_clean.append(tmp_top.name)

        y_after_top = y_start + top_height_est
        if bottom_fig is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_bottom:
                bottom_fig.savefig(tmp_bottom.name, format="png", bbox_inches="tight", dpi=150)
                pdf.image(tmp_bottom.name, x=(210 - bottom_width) / 2, y=y_after_top + TOP_TO_BOTTOM_OFFSET, w=bottom_width)
                tmp_files_to_clean.append(tmp_bottom.name)
            pdf.set_y(y_after_top + bottom_height_est + STACK_BOTTOM_PADDING)
        else:
            pdf.set_y(y_after_top + SINGLE_CHART_BOTTOM_PADDING)
        pdf.ln(2)

    # --- Pages 4+: GPA Distribution Curves ---
    if gpa_curve_figs:
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(190, 10, "GPA Distribution Curves", ln=True)
        pdf.ln(5)

        for figure_entry in gpa_curve_figs:
            if isinstance(figure_entry, (list, tuple)):
                top_fig = figure_entry[0] if len(figure_entry) > 0 else None
                bottom_fig = figure_entry[1] if len(figure_entry) > 1 else None
            else:
                top_fig = figure_entry
                bottom_fig = None
            if top_fig is None:
                continue
            _draw_vertical_pair(top_fig, bottom_fig, top_width=152, bottom_width=152)

    # --- Pages 4+: All Subject Curves (Stacked 2 per page) ---
    if subject_curve_figs:
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(190, 10, "Subject Distribution Curves", ln=True)
        pdf.ln(5)

        # Build a list of (subject_code, teacher_name) parallel to subject_curve_figs
        subj_teacher_list = []
        if subject_codes:
            for subject_code in subject_codes:
                teacher_name = (teacher_names or {}).get(subject_code, "")
                subj_teacher_list.append((subject_code, teacher_name))
        # Pad if needed (shouldn't be necessary in normal flow)
        while len(subj_teacher_list) < len(subject_curve_figs):
            subj_teacher_list.append(("", ""))

        for idx, figure_entry in enumerate(subject_curve_figs):
            if isinstance(figure_entry, (list, tuple)):
                top_fig = figure_entry[0] if len(figure_entry) > 0 else None
                bottom_fig = figure_entry[1] if len(figure_entry) > 1 else None
            else:
                top_fig = figure_entry
                bottom_fig = None
            if top_fig is None:
                continue
            # Print teacher name label before each subject's pair of charts,
            # ensuring the label and charts land on the same page.
            if idx < len(subj_teacher_list):
                _, teacher_name = subj_teacher_list[idx]
                if teacher_name:
                    top_figure_height = TOP_FIG_HEIGHT_EST
                    bottom_figure_height = (BOTTOM_FIG_HEIGHT_EST + STACK_VERTICAL_GAP) if bottom_fig is not None else 0
                    if pdf.get_y() + TEACHER_LABEL_HEIGHT + top_figure_height + bottom_figure_height > PAGE_CONTENT_LIMIT_Y:
                        pdf.add_page()
                    pdf.set_font("Arial", "I", 9)
                    pdf.cell(190, 5, clean_text(f"Teacher: {teacher_name}"), ln=True)
                    pdf.ln(1)
            _draw_vertical_pair(top_fig, bottom_fig, top_width=152, bottom_width=110)

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
