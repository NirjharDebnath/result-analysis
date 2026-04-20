from typing import Dict

COLLEGE_NAME = "Kalyani Government Engineering College"

REQUIRED_COLUMNS = ["ROLL NO", "NAME", "COURSENAME"]

KNOWN_NON_SUBJECT_COLUMNS = {
    "ROLL NO",
    "NAME",
    "COLLEGE NAME",
    "SEMESTER",
    "COURSE CODE",
    "COURSENAME",
    "ACADEMIC YEAR",
    "SGPA",
    "YGPA",
    "DGPA",
    "SEMETER RESULT",
    "SEMESTER RESULT",
    "TOTAL MAR POINTS",
    "TOTAL MARK POINTS",
    "STREAM",
    "BRANCH",
    "SPECIALIZATION",
}

PASSING_GRADES = {"O", "E", "A", "B", "C", "D", "P", "S"}

GRADE_ORDER = ["O", "E", "A", "B", "C", "D", "F", "ABSENT"]

REGULAR_ROLL_PATTERN = r"^10200\d240\d{2}$"

PRACTICAL_HINTS = (
    "PRAC",
    "PRACT",
    "LAB",
    "PW",
    "381",
    "382",
    "383",
    "384",
    "391",
    "392",
    "393",
    "394",
)

AUTUMN_COLORS: Dict[str, str] = {
    "bg": "#FFF6EA",
    "card": "#F8EAD8",
    "text": "#4A3427",
    "pass": "#6D9F71",
    "backlog": "#D17B49",
    "year_lag": "#B24B36",
    "primary": "#9A6B3A",
    "secondary": "#C99255",
    "accent": "#E8B16A",
    "grid": "#D7BFA1",
}
