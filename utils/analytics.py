# utils/analytics.py
import pandas as pd
import numpy as np
from scipy.stats import skew
from utils.processor import parse_grade_value

def get_class_masks(df: pd.DataFrame, roll_col: str = "ROLL NO"):
    """
    Identifies the Current Class (Regulars + Laterals) vs Old Batches.
    """
    rolls = df[roll_col].astype(str).str.strip()
    valid_rolls = rolls[rolls.str.len() >= 10]
    
    if valid_rolls.empty:
        return pd.Series(True, index=df.index), pd.Series(False, index=df.index)
        
    course_codes = valid_rolls.str[3:6]
    entry_years = valid_rolls.str[6:8].astype(int)
    
    # The majority entry year defines the "Regular" batch of this file
    regular_year = int(entry_years.mode()[0])
    target_course = course_codes.mode()[0]
    
    # Regulars entered in the regular_year, Laterals entered one year later
    is_regular = (entry_years == regular_year) & (course_codes == target_course)
    is_lateral = (entry_years == regular_year + 1) & (course_codes == target_course)
    
    # Combined "Current Class" 
    current_class_mask = is_regular | is_lateral
    # Everyone else is from an older batch re-appearing
    old_batch_mask = ~current_class_mask
    
    return current_class_mask, old_batch_mask

def determine_student_status(df: pd.DataFrame, semester_name: str) -> pd.DataFrame:
    df = df.copy()
    even_keywords = ["SECOND", "FOURTH", "SIXTH", "EIGHT", "EIGHTH", "TENTH"]
    is_even_sem = any(k in str(semester_name).upper() for k in even_keywords)
    
    current_class_mask, _ = get_class_masks(df)
    
    statuses = []
    for idx, row in df.iterrows():
        sem_result = str(row.get("SEMESTER RESULT", "")).upper()
        has_ygpa = pd.notna(row.get("YGPA")) and str(row.get("YGPA")).strip() != ""
        
        # 1. Year Lag check
        if is_even_sem and not has_ygpa and "PASS" not in sem_result:
            statuses.append("Year Lag")
        # 2. Old Batch check (If they aren't current class, they are old batch backlogs)
        elif not current_class_mask[idx]:
            statuses.append("Old Batch (Re-appearing)")
        # 3. Current Batch Pass
        elif "PASS" in sem_result:
            statuses.append("Current Batch")
        # 4. Current Batch Fail/Backlog
        else:
            statuses.append("Backlog (Current Batch)")
            
    df["STATUS"] = statuses
    return df

def calculate_subject_stats(df: pd.DataFrame, subject_cols: list) -> pd.DataFrame:
    stats_list = []
    for subj in subject_cols:
        if subj not in df.columns: continue
            
        parsed = df[subj].apply(parse_grade_value)
        grades = [p[0] for p in parsed if p[0] is not None]
        marks = [p[1] for p in parsed if p[1] is not None]
        
        if not marks: continue
        marks_series = pd.Series(marks).dropna()
        grade_counts = pd.Series(grades).value_counts().to_dict()
        
        stat_row = {
            "Subject": subj,
            "Mean": round(marks_series.mean(), 2),
            "Median": round(marks_series.median(), 2),
            "Std Dev (\u03c3)": round(marks_series.std(), 2) if len(marks_series) > 1 else 0,
            "Skewness": round(skew(marks_series), 2) if len(marks_series) > 2 else 0,
            "O": grade_counts.get("O", 0), "E": grade_counts.get("E", 0),
            "A": grade_counts.get("A", 0), "B": grade_counts.get("B", 0),
            "C": grade_counts.get("C", 0), "D": grade_counts.get("D", 0),
            "F": grade_counts.get("F", 0) + grade_counts.get("---", 0),
        }
        stats_list.append(stat_row)
    return pd.DataFrame(stats_list)

def calculate_z_scores(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df_clean = df.copy()
    
    def extract_numeric(val):
        _, marks = parse_grade_value(val)
        return marks

    if df_clean[col].dtype == 'object':
        df_clean['NUMERIC_VAL'] = df_clean[col].apply(extract_numeric)
    else:
        df_clean['NUMERIC_VAL'] = pd.to_numeric(df_clean[col], errors='coerce')
    
    df_clean = df_clean.dropna(subset=['NUMERIC_VAL'])
    if df_clean.empty: return df_clean

    mean, std = df_clean['NUMERIC_VAL'].mean(), df_clean['NUMERIC_VAL'].std()
    df_clean["Z-Score"] = (df_clean['NUMERIC_VAL'] - mean) / std if std > 0 else 0
    
    conditions = [(df_clean["Z-Score"] > 1), (df_clean["Z-Score"] < -1)]
    choices = ["Strong (> +1\u03c3)", "Weak (< -1\u03c3)"]
    df_clean["Performance"] = np.select(conditions, choices, default="Decent (-1\u03c3 to +1\u03c3)")
    
    return df_clean.sort_values("Z-Score", ascending=False)