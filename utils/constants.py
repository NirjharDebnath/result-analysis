# utils/constants.py

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

# Colors kept as is for now, will update later
SOFT_COLORS = {
    "pass": "#9ECF9B",
    "fail": "#E7A7A7",
    "primary": "#A7C7E7",
    "grid": "#E6DCCF",
    "accent": "#E5B97A",
    "bg": "#FFF9F2",
}

LOGO_CANDIDATE_PATHS = [
    "assets/kgec_logo.png",
    "kgec_logo.png",
]