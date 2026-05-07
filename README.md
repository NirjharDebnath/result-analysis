# 🎓 Result Analysis — Student Exam Performance Dashboard

A multi-page **Streamlit** web application for analysing engineering college exam results.  
Upload one or more semester result files (CSV / Excel), and the tool produces pass-rate
breakdowns, grade statistics, distribution curves, student rankings, individual profiles,
and a downloadable PDF master report — all in the browser.

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Project Structure](#project-structure)
3. [App Entry Point — `app.py`](#app-entry-point--apppy)
4. [Pages](#pages)
   - [1 — Course Insights](#1--course-insights-pages1_course_insightspy)
   - [2 — Rankings](#2--rankings-pages2_rankingspy)
   - [3 — Student Profile](#3--student-profile-pages3_student_profilepy)
   - [4 — Semester Comparison](#4--semester-comparison-pages4_semester_comparisonpy)
5. [Utilities](#utilities)
   - [constants.py](#utilsconstantspy)
   - [processor.py](#utilsprocessorpy)
   - [analytics.py](#utilsanalyticspy)
   - [charts.py](#utilschartspy)
   - [visualizer.py](#utilsvisualizerpy)
   - [pdf_generator.py](#utilspdf_generatorpy)
6. [Data Format](#data-format)
7. [Color Theme](#color-theme)
8. [How the PDF is Built](#how-the-pdf-is-built)
9. [Adding a New Page](#adding-a-new-page)
10. [Dependencies](#dependencies)

---

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the URL shown in your terminal (default `http://localhost:8501`).

---

## Project Structure

```
result-analysis/
├── app.py                          # Entry point — file upload & validation
├── requirements.txt
├── assets/
│   └── kgec_logo.png               # Sidebar logo
├── pages/
│   ├── 1_📊_Course_Insights.py     # Pass rates, subject stats, bell curves, PDF export
│   ├── 2_🏆_Rankings.py            # Student rankings by GPA / subject / marks
│   ├── 3_👤_Student_Profile.py     # Per-student grade card
│   └── 4_🔁_Semester_Comparison.py # Cross-semester GPA trend chart
└── utils/
    ├── constants.py                # Shared constants and color palette
    ├── processor.py                # File reading, column normalisation, validation
    ├── analytics.py                # Status detection, stats, z-scores, grouping
    ├── charts.py                   # All matplotlib/seaborn chart functions
    ├── visualizer.py               # Streamlit sidebar branding, footer, axis helpers
    └── pdf_generator.py            # FPDF-based multi-page PDF builder
```

---

## App Entry Point — `app.py`

`app.py` is the **home / upload page**.  It is the first page Streamlit loads.

### What it does
1. Renders the sidebar branding (logo + college name + designer credit).
2. Offers a "Download sample CSV template" button so users know the expected column layout.
3. Accepts one or more uploaded CSV/XLS/XLSX files via `st.file_uploader`.
4. For each uploaded file, asks the user to pick an **exam month and year** — these values
   are injected as `EXAM MONTH` / `EXAM YEAR` columns and are used by the analytics layer
   to distinguish *current-batch* students from *re-appearing (old-batch)* students.
5. Calls `read_uploaded_datasets` → `validate_dataset` from `utils/processor.py`.
6. On success, saves the merged DataFrame and subject column list to
   `st.session_state["validated_df"]` and `st.session_state["subject_cols"]` so every
   other page can read them without re-uploading.
7. Reports how many semesters were detected and suggests the right page to use.

---

## Pages

### 1 — Course Insights (`pages/1_📊_Course_Insights.py`)

The main analysis page.  It is split into **four tabs**.

#### Sidebar filters
- **Course filter** — `apply_course_stream_filters` lets the user pick a course name
  (or "All Courses") and optionally a stream / branch / specialisation.
- **Semester filter** — dropdown showing every unique semester in the filtered data.

#### Tab 1 — Executive Summary
Shows four KPI metric cards (total students, current batch size, pass %, old-batch count)
followed by the **executive overview figure** (five charts):

| Chart | What it shows |
|-------|--------------|
| Donut 1 | Current-year students vs re-appearing (old batch) |
| Donut 2 | Current-year students: passed (all clear) vs failed/backlog |
| Donut 3 | Reappearing students: cleared backlogs vs still-backlog |
| Horizontal bar | Lateral-entry vs regular students (current batch only) |
| Donut 5 | Overall pass vs fail across the whole cohort |

Below the chart, a detailed status breakdown table is shown alongside a performance
verdict (Excellent / Average / Attention Needed) based on the pass percentage.

#### Tab 2 — Statistical Matrix
A `pandas` DataFrame table with one row per subject, showing:
- **Mean**, **Median**, **Std Dev (σ)**, **Skewness** — computed by `calculate_subject_stats`
- **Pass %** — computed inline from the grade columns O/E/A/B/C/D/F counts
- **Grade counts** — O (Outstanding, 10), E (Excellent, 9), A (8), B (7), C (6), D (5), F (Fail, 0)

A high positive **skewness** flag warns the user that a subject had many below-average scores.

#### Tab 3 — Distribution Curves
- User picks a **GPA metric** and/or a **subject** from dropdowns.
- `plot_normal_curve` renders a histogram + overlaid normal (bell) curve for both the full
  class and the current-batch subset.
- Below the curves, **Z-Score analysis** lets the user rank students by their standard-score
  deviation.  `calculate_z_scores` returns each student's z-score and a category label
  (Top Performer / Above Average / Average / Below Average / Needs Attention).

#### Tab 4 — Export PDF
Triggers `create_master_report_pdf` with all pre-generated figures.  The result is a
multi-page PDF that the user can download.

---

### 2 — Rankings (`pages/2_🏆_Rankings.py`)

Ranks students within the selected course + semester.

**Ranking modes:**
- **GPA Metrics** — select any numeric GPA column (SGPA, CGPA, etc.) detected by
  `get_gpa_columns`; ranks by that column.
- **By Subject** — select a subject column; `parse_grade_value` extracts the numeric marks
  from strings like `"A(32)"`, then ranks by those marks.
- **Total Marks** — sums all parsed subject marks per student and ranks by the total.

**Ranking types:**
- `Standard` (`min` method) — tied students share the lowest rank in the group.
- `Dense` — tied students share the same rank; no gaps in the rank sequence.

The result is a `pandas` DataFrame with a `RANK` column, displayed via `st.dataframe` and
downloadable as CSV.

---

### 3 — Student Profile (`pages/3_👤_Student_Profile.py`)

Individual grade card for any student in the dataset.

1. The user selects a student by "ROLL NO — NAME" display string.
2. Personal details (name, roll, course) and GPA metrics are shown in two columns.
3. Subject-wise grades are shown in a table.  `parse_grade_value` decodes the
   `"Grade(Marks)"` cell format into separate grade and marks values.
4. A backlog count and the overall semester result status (from the `OVERALL RESULT` column)
   are highlighted at the bottom.

---

### 4 — Semester Comparison (`pages/4_🔁_Semester_Comparison.py`)

Compares average GPA metrics across multiple exam sessions or semesters.

1. The user picks **one or more GPA metrics** to compare.
2. They choose how failing grades are handled (counted as 0.0 for a strict class average, or
   ignored so the average only covers students who actually received a numeric score).
3. `build_file_comparison_data` groups the data by `GROUP_LABEL` (which encodes the
   semester + exam session) and computes the average value and student count for each
   metric/group combination.
4. `plot_grouped_multi_metric_bars` renders a grouped bar chart (one bar cluster per group,
   one bar per metric).
5. The generated figure is stored in `st.session_state["comparison_fig"]` so the PDF export
   on the Course Insights page can optionally include it.

---

## Utilities

### `utils/constants.py`

Centralised configuration — **edit this file to change shared settings**.

| Constant | Purpose |
|----------|---------|
| `COLLEGE_NAME` | College name shown in every page header |
| `REQUIRED_COLUMNS` | Minimum columns a result file must contain |
| `KNOWN_NON_SUBJECT_COLUMNS` | Set of column names that are *metadata*, not subjects |
| `PASSING_GRADES` | Set of grade letters considered a pass (`O E A B C D`) |
| `SOFT_COLORS` | Palette used by `visualizer.py` axis styling |
| `LOGO_CANDIDATE_PATHS` | Paths where the tool looks for the sidebar logo |

---

### `utils/processor.py`

Handles everything from raw file bytes to a clean, validated `pandas` DataFrame.

**Key functions:**

| Function | What it does |
|----------|-------------|
| `get_sample_template_csv()` | Returns bytes for the downloadable example CSV |
| `normalize_columns(df)` | Strips whitespace, uppercases all column names, drops unnamed columns |
| `canonicalize_header(value)` | Maps common header aliases to a canonical name (e.g. `"SEM"` → `"SEMESTER"`) |
| `parse_grade_value(cell)` | Decodes a cell like `"A(32)"` into `(grade="A", marks=32)`.  Returns `(None, None)` for empty/invalid cells |
| `get_gpa_columns(df)` | Returns column names that look like GPA/SGPA/CGPA metrics (heuristic: numeric-heavy, not in the non-subject set) |
| `read_uploaded_datasets(files, ...)` | Reads one or more uploaded files, normalises headers, injects exam month/year, merges into one DataFrame, deduplicates rows |
| `validate_dataset(df)` | Checks required columns exist, detects metadata vs subject columns, returns a list of error strings |
| `apply_course_stream_filters(df, ...)` | Renders sidebar dropdowns for course name + optional stream/branch filter; returns the filtered DataFrame |
| `require_data()` | Reads `st.session_state["validated_df"]`; displays an upload prompt and calls `st.stop()` if not present |

**`parse_grade_value` logic:**
The cell value can be:
- A plain grade letter: `"A"` → `("A", None)`
- `"Grade(Marks)"` format: `"A(32)"` → `("A", 32)`
- A plain number (some colleges write marks directly): `"32"` → `(None, 32)`
- NaN or empty → `(None, None)`

---

### `utils/analytics.py`

Statistical and grouping logic.

**Key functions:**

| Function | What it does |
|----------|-------------|
| `normalize_semester_label(value)` | Converts any semester representation (e.g. `"2nd"`, `"SECOND"`, `"II"`) to `"Semester N"` |
| `get_semester_order(value)` | Returns the integer semester number for sorting |
| `infer_academic_year_from_roll(roll)` | Extracts the two-digit admission year from the roll number (indices 6–7 by convention) and maps it to a full year |
| `determine_student_status(df, semester)` | Adds a `STATUS` column: `"Current Batch"` (all clear), `"Backlog (Current Batch)"`, `"Old Batch (Re-appearing)"`, or `"Year Lag"`.  The logic compares the exam year to the expected graduation year inferred from the roll number and semester |
| `get_class_masks(df)` | Returns two boolean Series: `current_class_mask` (True for current-year students) and `old_batch_mask` |
| `get_lateral_mask(df)` | Detects lateral-entry students by matching roll number patterns (e.g. a `"L"` in the roll, or enrolment year that implies 3-year entry) |
| `calculate_subject_stats(df, subjects)` | For each subject column, computes mean, median, std dev, skewness, and grade distribution counts.  Uses `parse_grade_value` to extract numeric grade points |
| `calculate_z_scores(df, col)` | Converts a column to numeric, computes z-scores, categorises each student, and returns a sorted DataFrame |
| `build_semester_year_groups(df)` | Creates `SEMESTER_LABEL` and `GROUP_LABEL` columns used by the comparison page |
| `build_file_comparison_data(df, metrics)` | Groups by `GROUP_LABEL`, computes average and student count for each selected metric |

**Status assignment logic (`determine_student_status`):**
1. Parse the two-digit admission year from each student's roll number.
2. Derive the expected batch year: `admission_year + (semester_number / 2)` rounded to semester boundaries.
3. Compare the file's exam year to the expected graduation year.
4. Students in the correct cohort for this semester are *Current Batch*; those who lag by one sitting are *Backlog (Current Batch)*; those from an earlier cohort are *Old Batch (Re-appearing)*.

---

### `utils/charts.py`

All chart-drawing functions. Most return a single `matplotlib.figure.Figure`; `plot_normal_curve`
returns a pair `(curve_figure, pie_figure_or_none)`.

**Shared theme (`THEME` dict):**
A summer/ocean colour palette used across all charts:
- `primary` — deep ocean blue (axes, mean line)
- `accent` — amber/sunflower (+1σ line, current-batch curve)
- `secondary` — sky blue (histogram fill)
- `bg` — light summer sky (background)
- `pass` — summer green, `backlog` — alert red, `lag` — warm orange

**Functions:**

| Function | Chart type | Used by |
|----------|-----------|---------|
| `plot_status_bars(status_counts, total)` | Vertical bar chart with count + percentage annotations | Page 1 Tab 1 (PDF only) |
| `plot_executive_overview(df, current_mask, lateral_mask)` | 5-subplot figure: 3 donut pies + 1 horizontal bar + 1 donut | Page 1 Tab 1, PDF Page 2 |
| `plot_normal_curve(full_data, reg_data, title, is_grade_scale)` | Histogram + bell curve + separate grade-split donut figure | Page 1 Tab 3, PDF Pages 3+ |
| `plot_z_score_distribution(z_df, title)` | Histogram of z-scores with σ reference lines | (available, not currently shown in a tab) |
| `plot_semester_metric_bars(comparison_df, metric, ...)` | Single-metric grouped bar chart | (available, not used in current flow — superseded by `plot_grouped_multi_metric_bars`) |
| `plot_grouped_multi_metric_bars(comparison_df, metrics, groups, title)` | Seaborn grouped bar chart, one cluster per group | Page 4 |

**`plot_normal_curve` logic:**
1. Drops NaN values from the full-class series.
2. Builds a histogram with `stat="density"` (area = 1) so the bell curve overlays correctly.
3. Fits a normal distribution (mean, std) to the full-class data and plots it as a dashed curve.
4. If `regular_data` is provided (current-batch only), fits and overlays a second curve in accent colour.
5. For grade-scale plots (`is_grade_scale=True`), fixes bins at grade-point boundaries (0, 5, 6, 7, 8, 9, 10) and labels the x-axis with grade letters.

---

### `utils/visualizer.py`

Small helpers for Streamlit UI chrome.

| Function | What it does |
|----------|-------------|
| `render_sidebar_branding()` | Shows the college logo and name at the top of the sidebar and keeps the "Designed by Nirjhar Debnath" credit pinned to the bottom |
| `render_footer()` | Adds a `---` divider at the bottom of a page |
| `downloadable_plot(fig, filename)` | Renders a figure with `st.pyplot` and adds a PNG download button directly below it |
| `download_table_button(df, label, filename)` | Renders a CSV download button for a DataFrame |
| `style_axis(ax, xlabel, ylabel, rotate_x)` | Applies shared axis styling (background, grid, font sizes) using `SOFT_COLORS` |
| `resolve_logo_path()` | Searches `LOGO_CANDIDATE_PATHS` relative to the repo root; returns the first path that exists |

---

### `utils/pdf_generator.py`

Builds a multi-page PDF using the `fpdf2` library.

**`create_master_report_pdf(...)` — page layout:**

| Page | Content |
|------|---------|
| 1 | College name + title + semester header, batch-status bar chart, executive summary key-value table |
| 2 | Executive batch overview (the 5-panel chart from Tab 1 of Course Insights) |
| 3 | Subject Performance Statistics matrix (all subjects, same columns as Tab 2) |
| 4+ | GPA Distribution Curves (2 per page) |
| Next | Subject Distribution Curves (2 per page) |
| Next | Z-Score Analysis Table |
| Last (optional) | Semester Comparison chart (included if the user generated one on Page 4 and checked the option) |

**`clean_text(text)`** sanitises any string before writing to the PDF — replaces the
Unicode sigma character (σ) with "SD" and encodes to Latin-1 (FPDF's native encoding),
ignoring any characters that cannot be represented.

**Temp-file pattern:** matplotlib figures are saved to temporary PNG files, embedded in the
PDF via `pdf.image(path, ...)`, then deleted after the PDF bytes are produced.

---

## Data Format

The tool expects a flat table where each row is one student's result for one semester.
Minimum required columns (case-insensitive, normalised on load):

| Column | Example value |
|--------|--------------|
| `ROLL NO` | `10271025001` |
| `NAME` | `Rahul Das` |
| `COURSENAME` | `Master of Computer Application` |
| `SEMESTER` | `First Semester` |
| `SGPA` | `8.50` |
| `SEMETER RESULT` or `SEMESTER RESULT` | `PASS` |
| Subject columns (any name not in the non-subject set) | `A(32)` or `B` or `28` |

Download the in-app sample template for a ready-to-fill example.

---

## Color Theme

The app uses a **Summer / Ocean** palette defined in `utils/constants.py` (`SOFT_COLORS`)
and `utils/charts.py` (`THEME`):

| Role | Hex | Use |
|------|-----|-----|
| Deep ocean blue | `#1565C0` | Primary buttons, active tabs, axis lines |
| Amber / sunflower | `#FF8F00` | Accent elements, +1σ line |
| Sky blue | `#4FC3F7` | Histogram fill |
| Summer green | `#66BB6A` | Pass / positive outcomes |
| Alert red | `#EF5350` | Fail / backlog / negative outcomes |
| Warm orange | `#FFA726` | Year-lag / lag line |
| Light sky background | `#F0F7FF` | Chart backgrounds |

To change the theme, update the `THEME` dict in `utils/charts.py` and `SOFT_COLORS` in
`utils/constants.py`, then update the `background-color` values in the `<style>` blocks
inside the page files.

---

## How the PDF is Built

1. **Before clicking "Generate"**, the application has already computed `overview_fig`
   (Tab 1 chart) and `stats_df` (Tab 2 matrix) as part of the page load.
2. When the button is pressed, the PDF tab **re-generates** bell curves for **every valid
   subject** and every valid GPA column in the background (not just the ones selected in
   Tab 3).
3. `create_master_report_pdf` receives all figures as `matplotlib.figure.Figure` objects,
   writes each to a temp PNG, embeds it in the FPDF document, then deletes the temp file.
4. The final PDF is returned as `bytes` and passed to a `st.download_button`.
5. All matplotlib figures created during PDF generation are explicitly closed
   (`plt.close(fig)`) to avoid memory leaks.

---

## Adding a New Page

1. Create a file in the `pages/` directory following the naming convention
   `N_EMOJI_Page_Name.py` (Streamlit uses this for sidebar ordering and icons).
2. At the top, call `st.set_page_config(...)` and then `render_sidebar_branding()`.
3. Call `require_data()` to get the validated DataFrame; it handles the "no data uploaded"
   case automatically.
4. Add `render_footer()` at the bottom.
5. If you need a new chart, add a function to `utils/charts.py` that returns a
   `matplotlib.figure.Figure`.

---

## Dependencies

```
streamlit
pandas
openpyxl
xlrd
matplotlib
seaborn
scipy
numpy
fpdf2
```

See `requirements.txt` for pinned versions.

---

*Designed by **Nirjhar Debnath**, Dept. of CSE, Kalyani Government Engineering College.*
