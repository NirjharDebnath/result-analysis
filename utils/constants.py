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
#SOFT_COLORS = {
#    "pass": "#A5D6A7",    # soft summer green
#    "fail": "#EF9A9A",    # soft warm red
#    "primary": "#81D4FA", # sky blue
#    "grid": "#B0C4DE",    # steel blue grid
#    "accent": "#FFCC80",  # golden sand
#    "bg": "#F0F7FF",      # light summer sky
#}

# ===========================
# Palette 1: Soft Autumn
# ===========================
SOFT_AUTUMN = {
    "pass": "#A8CFA8",
    "fail": "#D8A39D",
    "primary": "#8FAFC7",
    "grid": "#D6CFC7",
    "accent": "#D8B48A",
    "bg": "#F8F4EE",
}

# ===========================
# Palette 2: Winter Mist
# ===========================
WINTER_MIST = {
    "pass": "#A8D5BA",
    "fail": "#E6A4A4",
    "primary": "#8FAFD9",
    "grid": "#D5DCE6",
    "accent": "#C8B6E2",
    "bg": "#F7FAFC",
}

# ===========================
# Palette 3: Sage + Dusty Blue
# (Recommended)
# ===========================
SAGE_DUSTY = {
    "pass": "#B7D3B0",
    "fail": "#D9A7A7",
    "primary": "#9BB7D4",
    "grid": "#D9E1E8",
    "accent": "#DCC7A1",
    "bg": "#FAFBF8",
}

# ===========================
# Palette 4: Spring Meadow
# ===========================
SPRING_MEADOW = {
    "pass": "#B9E4C9",
    "fail": "#F0B7B7",
    "primary": "#A8D8EA",
    "grid": "#DDE7EF",
    "accent": "#F6D7A7",
    "bg": "#FCFFFA",
}

# ===========================
# Palette 5: Monsoon Calm
# ===========================
MONSOON_CALM = {
    "pass": "#9FC5B8",
    "fail": "#CFA4A4",
    "primary": "#7F9BB3",
    "grid": "#C8D2DB",
    "accent": "#C7B299",
    "bg": "#F4F7F8",
}

# ===========================
# Common UI Colors
# ===========================
UI_THEME = {
    "text": "#2F3A45",
    "subtext": "#66727F",
    "card": "#FFFFFF",
    "border": "#E7ECEF",
}

SOFT_COLORS = SAGE_DUSTY

LOGO_CANDIDATE_PATHS = [
    "assets/kgec_logo.png",
    "kgec_logo.png",
]
