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
# ===========================
# Palette 1: Soft Autumn
# ===========================
SOFT_AUTUMN = {
    "pass": "#A8CFA8",
    "fail": "#D8A39D",
    "lag": "#D9B67A",
    "backlog": "#B7AFA3",

    "primary": "#8FAFC7",
    "button_hover": "#7D9FB9",
    "accent": "#D8B48A",

    "grid": "#D6CFC7",
    "bg": "#F8F4EE",
    "sidebar": "#F3ECE4",

    "success_bg": "#EEF5EC",
    "info_bg": "#EEF4F8",
    "warning_bg": "#FAF3E6",
    "error_bg": "#F8ECEA",
}


# ===========================
# Palette 2: Winter Mist
# ===========================
WINTER_MIST = {
    "pass": "#A8D5BA",
    "fail": "#E6A4A4",
    "lag": "#D8C08C",
    "backlog": "#B8BDC9",

    "primary": "#8FAFD9",
    "button_hover": "#7B9CC9",
    "accent": "#C8B6E2",

    "grid": "#D5DCE6",
    "bg": "#F7FAFC",
    "sidebar": "#EEF3F8",

    "success_bg": "#EDF7F0",
    "info_bg": "#EEF5FC",
    "warning_bg": "#FAF5EA",
    "error_bg": "#FAEEEE",
}


# ===========================
# Palette 3: Sage + Dusty Blue
# (Recommended)
# ===========================
SAGE_DUSTY = {
    "pass": "#B7D3B0",
    "fail": "#D9A7A7",
    "lag": "#D7C18F",
    "backlog": "#B8BEC8",

    "primary": "#9BB7D4",
    "button_hover": "#88A6C5",
    "accent": "#DCC7A1",

    "grid": "#D9E1E8",
    "bg": "#FAFBF8",
    "sidebar": "#F3F6F2",

    "success_bg": "#EDF6EA",
    "info_bg": "#EEF4FA",
    "warning_bg": "#FAF4E8",
    "error_bg": "#F8ECEC",
}


# ===========================
# Palette 4: Spring Meadow
# ===========================
SPRING_MEADOW = {
    "pass": "#B9E4C9",
    "fail": "#F0B7B7",
    "lag": "#E7D09A",
    "backlog": "#C5CCD6",

    "primary": "#A8D8EA",
    "button_hover": "#91C7DC",
    "accent": "#F6D7A7",

    "grid": "#DDE7EF",
    "bg": "#FCFFFA",
    "sidebar": "#F5FBF7",

    "success_bg": "#F0FAF3",
    "info_bg": "#EEF8FC",
    "warning_bg": "#FCF7EC",
    "error_bg": "#FCF0F0",
}


# ===========================
# Palette 5: Monsoon Calm
# ===========================
MONSOON_CALM = {
    "pass": "#9FC5B8",
    "fail": "#CFA4A4",
    "lag": "#C9B38A",
    "backlog": "#AEB7BF",

    "primary": "#7F9BB3",
    "button_hover": "#6E8CA6",
    "accent": "#C7B299",

    "grid": "#C8D2DB",
    "bg": "#F4F7F8",
    "sidebar": "#EDF2F4",

    "success_bg": "#EAF3F0",
    "info_bg": "#EDF3F7",
    "warning_bg": "#F7F2E9",
    "error_bg": "#F5ECEC",
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
