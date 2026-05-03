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
    "SOURCE FILE",
    "EXAM MONTH",
    "EXAM YEAR",
    "EXAM SESSION",
    "EXAM TIMELINE",
    "SGPA",
    "SEMETER RESULT",
    "SEMESTER RESULT",
    "TOTAL MAR POINTS",
    "TOTAL MARK POINTS",
    "STREAM",
    "BRANCH",
    "SPECIALIZATION",
}

PASSING_GRADES = {"O", "E", "A", "B", "C", "D"}

# Summer/Ocean color palette — fresh, high-contrast, accessible
SOFT_COLORS = {
    "pass": "#A5D6A7",    # soft summer green
    "fail": "#EF9A9A",    # soft warm red
    "primary": "#81D4FA", # sky blue
    "grid": "#B0C4DE",    # steel blue grid
    "accent": "#FFCC80",  # golden sand
    "bg": "#F0F7FF",      # light summer sky
}

LOGO_CANDIDATE_PATHS = [
    "assets/kgec_logo.png",
    "kgec_logo.png",
]
