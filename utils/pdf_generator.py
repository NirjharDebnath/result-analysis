# utils/pdf_generator.py
import os
import tempfile
import pandas as pd
from typing import Optional, List
from fpdf import FPDF
from utils.charts import plot_status_bars, plot_normal_curve, plot_semester_metric_bars
from utils.processor import parse_grade_value

class MasterReport(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(46, 64, 83) 
        self.cell(0, 10, "Kalyani Government Engineering College", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 12)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "Departmental Result Analysis Report", align="C", new_x="LMARGIN", new_y="NEXT")
        
        self.set_draw_color(211, 84, 0)
        self.set_line_width(1)
        self.line(10, 28, 200, 28)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def generate_master_pdf(course_name: str, semester: str, df: pd.DataFrame, 
                        valid_subjects: list, stats_df: pd.DataFrame, 
                        current_class_mask: pd.Series,
                        comparison_df: Optional[pd.DataFrame] = None,
                        comparison_metrics: Optional[List[str]] = None,
                        comparison_groups: Optional[List[str]] = None) -> bytes:
    
    pdf = MasterReport(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    temp_files = [] 

    try:
        # PAGE 1: EXECUTIVE SUMMARY
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, f"Course: {course_name}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Semester: {semester}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Total Students Evaluated: {len(df)}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(211, 84, 0) 
        pdf.cell(0, 10, "1. Executive Batch Summary", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        
        status_counts = df["STATUS"].value_counts()
        fig_status = plot_status_bars(status_counts)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            fig_status.savefig(tmp.name, bbox_inches='tight', dpi=150)
            temp_files.append(tmp.name)
            pdf.image(tmp.name, x=35, w=140) # Smaller, centered

        # PAGE 2: FULL STATISTICAL MATRIX
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(211, 84, 0)
        pdf.cell(0, 10, "2. Comprehensive Subject Matrix", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
        pdf.set_font("Helvetica", "B", 8) 
        pdf.set_fill_color(46, 64, 83) 
        pdf.set_text_color(255, 255, 255)
        
        cols = ["Subject", "Mean", "StdDev", "Skew", "O", "E", "A", "B", "C", "D", "F", "Pass%"]
        col_widths = [45, 14, 14, 14, 10, 10, 10, 10, 10, 10, 10, 15] 
        
        for i, col in enumerate(cols):
            pdf.cell(col_widths[i], 8, col, border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(245, 245, 245) 
        
        fill = False
        for _, row in stats_df.iterrows():
            total_grades = sum([row.get(g, 0) for g in ['O', 'E', 'A', 'B', 'C', 'D', 'F']])
            passed = total_grades - row.get('F', 0)
            pass_pct = f"{(passed/total_grades)*100:.1f}%" if total_grades > 0 else "N/A"
            subj_name = str(row['Subject'])[:28] 
            
            pdf.cell(col_widths[0], 7, subj_name, border=1, fill=fill)
            pdf.cell(col_widths[1], 7, str(row['Mean']), border=1, align="C", fill=fill)
            pdf.cell(col_widths[2], 7, str(row['Std Dev (\u03c3)']), border=1, align="C", fill=fill)
            pdf.cell(col_widths[3], 7, str(row['Skewness']), border=1, align="C", fill=fill)
            
            for idx, g in enumerate(['O', 'E', 'A', 'B', 'C', 'D', 'F']):
                pdf.cell(col_widths[4+idx], 7, str(row.get(g, 0)), border=1, align="C", fill=fill)
                
            pdf.cell(col_widths[11], 7, pass_pct, border=1, align="C", fill=fill)
            pdf.ln()
            fill = not fill 
            
        if "Skewness" in stats_df.columns:
            highest_skew = stats_df["Skewness"].max()
            if highest_skew > 0.5:
                hardest_subject = stats_df.loc[stats_df["Skewness"].idxmax()]["Subject"]
                pdf.ln(5)
                pdf.set_font("Helvetica", "BI", 10)
                pdf.set_text_color(192, 57, 43) 
                pdf.cell(0, 6, f"Anomaly Warning: {hardest_subject} has a high positive skew ({highest_skew}).", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "I", 9)
                pdf.cell(0, 6, "This indicates a difficult paper where the majority of the class scored below average.", new_x="LMARGIN", new_y="NEXT")

        # PAGE 3+: DISTRIBUTION CURVES
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(211, 84, 0)
        pdf.cell(0, 10, "3. Subject Distribution Curves", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, "(Orange Line: Current Batch | Grey Area: Full Class including Old Batch)", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        grade_to_point = {'O': 10, 'E': 9, 'A': 8, 'B': 7, 'C': 6, 'D': 5, 'F': 0}
        y_positions = [60, 160] # Updated coordinates
        
        for idx, subj in enumerate(valid_subjects):
            if idx > 0 and idx % 2 == 0:
                pdf.add_page()
                
            full_grades = df[subj].apply(lambda x: parse_grade_value(x)[0])
            full_subj = pd.to_numeric(full_grades.map(grade_to_point), errors='coerce')
            
            reg_grades = df[current_class_mask][subj].apply(lambda x: parse_grade_value(x)[0])
            reg_subj = pd.to_numeric(reg_grades.map(grade_to_point), errors='coerce')
            
            fig_curve = plot_normal_curve(full_subj, reg_subj, title=f"{subj} Distribution", is_grade_scale=True)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                fig_curve.savefig(tmp.name, bbox_inches='tight', dpi=150)
                temp_files.append(tmp.name)
                
                pos_index = idx % 2
                pdf.image(tmp.name, x=40, y=y_positions[pos_index], w=130) # Centered and smaller width

        if comparison_df is not None and not comparison_df.empty and comparison_metrics:
            for metric in comparison_metrics:
                metric_data = comparison_df[comparison_df["METRIC"] == metric]
                if comparison_groups:
                    metric_data = metric_data[metric_data["GROUP_LABEL"].isin(comparison_groups)]
                if metric_data.empty:
                    continue

                pdf.add_page()
                pdf.set_font("Helvetica", "B", 14)
                pdf.set_text_color(211, 84, 0)
                pdf.cell(0, 10, f"4. Semester Comparison - {metric}", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "I", 10)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 6, "Average GPA values across selected semester groups", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(4)

                fig_cmp = plot_semester_metric_bars(
                    comparison_df=comparison_df,
                    metric=metric,
                    selected_groups=comparison_groups,
                    title=f"{metric} Comparison",
                )
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    fig_cmp.savefig(tmp.name, bbox_inches='tight', dpi=150)
                    temp_files.append(tmp.name)
                    pdf.image(tmp.name, x=18, w=174)

        return bytes(pdf.output())

    finally:
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
