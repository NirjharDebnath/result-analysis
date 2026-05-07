# utils/charts.py
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy.stats import norm
import pandas as pd
from matplotlib.gridspec import GridSpec
from typing import Optional, List, Dict, Tuple
from utils.constants import SOFT_COLORS

# Active theme
THEME = SOFT_COLORS

# Semantic color mapping
PASS_COLOR = THEME["pass"]
FAIL_COLOR = THEME["fail"]
BACKLOG_COLOR = THEME["backlog"]
LAG_COLOR = THEME["lag"]

PRIMARY_COLOR = THEME["primary"]
ACCENT_COLOR = THEME["accent"]
GRID_COLOR = THEME["grid"]
BG_COLOR = THEME["bg"]

CURRENT_COLOR = PRIMARY_COLOR
REAPP_COLOR = LAG_COLOR
LATERAL_COLOR = ACCENT_COLOR
REGULAR_COLOR = GRID_COLOR

# Reusable palette
SEASON_PALETTE = [
    PRIMARY_COLOR,
    ACCENT_COLOR,
    PASS_COLOR,
    FAIL_COLOR,
    BACKLOG_COLOR,
    LAG_COLOR,
    GRID_COLOR,
    ACCENT_COLOR,
]

GRADE_ORDER = ["O", "E", "A", "B", "C", "D", "F"]
GRADE_COLORS = {
    "O": PRIMARY_COLOR,
    "E": ACCENT_COLOR,
    "A": PASS_COLOR,
    "B": "#AFC7B6",
    "C": BACKLOG_COLOR,
    "D": LAG_COLOR,
    "F": FAIL_COLOR,
}


def _subject_code_label(subject_label: str) -> str:
    """Extract the short subject code from a 'CODE - Subject Name' label."""
    return str(subject_label).split(" - ", 1)[0].strip()


def map_numeric_to_grade(value: float) -> Optional[str]:
    if pd.isna(value):
        return None
    if value >= 9:
        return "O"
    if value >= 8:
        return "E"
    if value >= 7:
        return "A"
    if value >= 6:
        return "B"
    if value >= 5:
        return "C"
    if value >= 4:
        return "D"
    return "F"


def _grade_counts_from_numeric(series: pd.Series) -> Dict[str, int]:
    mapped = series.dropna().apply(map_numeric_to_grade)
    counts = mapped.value_counts().to_dict()
    return {grade: int(counts.get(grade, 0)) for grade in GRADE_ORDER}


def plot_grade_distribution_donut(grade_counts: Dict[str, int], title: str = "Grade Distribution"):
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    counts = [int(grade_counts.get(g, 0)) for g in GRADE_ORDER]
    total = sum(counts)

    if total == 0:
        ax.text(0.5, 0.5, "No grade data available", ha="center", va="center", fontsize=11)
        ax.axis("off")
        return fig

    colors = [GRADE_COLORS[g] for g in GRADE_ORDER]
    labels = [f"{g}: {c} ({(c / total * 100):.1f}%)" for g, c in zip(GRADE_ORDER, counts)]

    wedges, _, autotexts = ax.pie(
        counts,
        colors=colors,
        startangle=90,
        wedgeprops=dict(width=0.45, edgecolor="white"),
        autopct=lambda p: f"{p:.1f}%" if p > 0 else "",
        pctdistance=0.75,
    )
    for t in autotexts:
        t.set_fontsize(9)
        t.set_fontweight("bold")

    ax.legend(
        wedges,
        labels,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
        fontsize=9,
    )
    ax.set_title(title, fontweight="bold", fontsize=11)
    plt.tight_layout()
    return fig


def plot_status_bars(status_counts: pd.Series, total_students: int = None):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    base_categories = ["Current Batch", "Backlog (Current Batch)", "Old Batch (Re-appearing)", "Year Lag"]
    ordered_categories = [c for c in base_categories if c in status_counts.index]
    ordered_categories += [c for c in status_counts.index if c not in base_categories]

    status_counts = status_counts.reindex(ordered_categories, fill_value=0)
    categories = status_counts.index.tolist()
    counts = status_counts.values.tolist()

    colors = []
    for cat in categories:
        cat_upper = cat.upper()
        if cat_upper == "CURRENT BATCH":
            colors.append(PASS_COLOR)
        elif "BACKLOG" in cat_upper:
            colors.append(BACKLOG_COLOR)
        elif "OLD" in cat_upper:
            colors.append(REAPP_COLOR)
        elif "LAG" in cat_upper:
            colors.append(LAG_COLOR)
        else:
            colors.append(PRIMARY_COLOR)

    bars = ax.bar(categories, counts, color=colors, edgecolor='black', alpha=0.85)

    total = total_students if total_students else sum(counts)

    for bar, count in zip(bars, counts):
        height = bar.get_height()
        percentage = (count / total) * 100 if total > 0 else 0

        label_text = f'{int(count)}\n({percentage:.1f}%)' if count > 0 else '0'

        ax.annotate(
            label_text,
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 4),
            textcoords="offset points",
            ha='center',
            va='bottom',
            fontweight='bold',
            fontsize=9
        )

    display_labels = []
    for cat in categories:
        if cat == "Current Batch":
            display_labels.append("Current Batch\n(All Clear)")
        elif cat == "Backlog (Current Batch)":
            display_labels.append("Current Batch\n(Backlog)")
        else:
            display_labels.append(cat.replace(" (", "\n("))

    ax.set_xticks(range(len(display_labels)))
    ax.set_xticklabels(display_labels, rotation=0, ha='center', fontsize=9, fontweight='semibold')

    ax.set_ylabel("Number of Students")
    ax.set_title("Overall Batch Status Breakdown", fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    ax.set_ylim(0, max(counts) * 1.25 if counts else 10)

    plt.tight_layout()
    return fig


def plot_executive_overview(filtered_df: pd.DataFrame, current_class_mask: pd.Series, lateral_mask: pd.Series):
    total = len(filtered_df)

    if total == 0:
        fig, ax = plt.subplots(1, 1, figsize=(8, 4))
        fig.patch.set_facecolor(BG_COLOR)
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")
        return fig

    current_df = filtered_df[current_class_mask]
    reappearing_df = filtered_df[~current_class_mask]

    n_current = len(current_df)
    n_reappearing = len(reappearing_df)

    current_passed = int((current_df["STATUS"] == "Current Batch").sum())
    current_failed = n_current - current_passed

    if n_reappearing > 0 and "SEMESTER RESULT" in reappearing_df.columns:
        reapp_passed = int(
            reappearing_df["SEMESTER RESULT"].str.upper().str.contains("PASS", na=False).sum()
        )
    else:
        reapp_passed = 0

    reapp_failed = n_reappearing - reapp_passed

    lateral_in_current = current_class_mask & lateral_mask
    n_lateral = int(lateral_in_current.sum())
    n_regular = n_current - n_lateral

    total_passed = current_passed + reapp_passed
    total_failed = total - total_passed

    fig = plt.figure(figsize=(12, 8))
    fig.patch.set_facecolor(BG_COLOR)
    gs = GridSpec(2, 6, figure=fig, hspace=0.55, wspace=0.5)

    ax1 = fig.add_subplot(gs[0, 0:2])
    ax2 = fig.add_subplot(gs[0, 2:4])
    ax3 = fig.add_subplot(gs[0, 4:6])
    ax4 = fig.add_subplot(gs[1, 0:4])
    ax5 = fig.add_subplot(gs[1, 4:6])

    for ax in (ax1, ax2, ax3, ax4, ax5):
        ax.set_facecolor(BG_COLOR)

    def _donut(ax, values, labels, colors, title):
        nonzero = [v for v in values if v > 0]
        if not nonzero:
            ax.text(0.5, 0.5, "No Data", ha="center", va="center", transform=ax.transAxes, fontsize=11)
            ax.set_title(title, fontweight="bold", fontsize=10)
            ax.axis("off")
            return

        wedges, _, autotexts = ax.pie(
            values,
            labels=None,
            colors=colors,
            autopct=lambda p: f"{p:.1f}%" if p > 0 else "",
            startangle=90,
            wedgeprops=dict(width=0.5),
            pctdistance=0.75,
        )

        for at in autotexts:
            at.set_fontsize(9)
            at.set_fontweight("bold")

        ax.legend(
            wedges,
            [f"{l}  ({v})" for l, v in zip(labels, values)],
            loc="lower center",
            bbox_to_anchor=(0.5, -0.22),
            ncol=1,
            fontsize=8,
            frameon=False,
        )

        ax.set_title(title, fontweight="bold", fontsize=10)

    _donut(
        ax1,
        [n_current, n_reappearing],
        ["Current Year", "Reappearing (Old Batch)"],
        [CURRENT_COLOR, REAPP_COLOR],
        "Current Year vs\nReappearing Students",
    )

    _donut(
        ax2,
        [current_passed, current_failed],
        ["Passed (All Clear)", "Failed / Backlog"],
        [PASS_COLOR, FAIL_COLOR],
        "Current Year Students\nPass vs Fail",
    )

    _donut(
        ax3,
        [reapp_passed, reapp_failed],
        ["Cleared Backlogs", "Still Backlog"],
        [PASS_COLOR, FAIL_COLOR],
        "Reappearing Students\nPass vs Fail",
    )

    categories = ["Regular Students", "Lateral Entry"]
    counts = [n_regular, n_lateral]
    bar_colors = [REGULAR_COLOR, LATERAL_COLOR]

    bars = ax4.barh(categories, counts, color=bar_colors, edgecolor="black", alpha=0.85, height=0.4)

    for bar, count in zip(bars, counts):
        pct = (count / n_current * 100) if n_current > 0 else 0
        ax4.annotate(
            f"{count} ({pct:.1f}% of current batch)",
            xy=(bar.get_width(), bar.get_y() + bar.get_height() / 2),
            xytext=(5, 0),
            textcoords="offset points",
            va="center",
            ha="left",
            fontweight="bold",
            fontsize=10,
        )

    ax4.set_title(
        "Lateral Entry vs Regular Students\n(Current Batch Only — Reappearing excluded)",
        fontweight="bold",
        fontsize=10,
    )

    ax4.set_xlabel("Number of Students")
    ax4.set_xlim(0, (max(counts) * 1.55) if max(counts) > 0 else 10)
    ax4.spines["top"].set_visible(False)
    ax4.spines["right"].set_visible(False)
    ax4.grid(axis="x", linestyle="--", alpha=0.4)

    _donut(
        ax5,
        [total_passed, total_failed],
        ["Passed", "Failed"],
        [PASS_COLOR, FAIL_COLOR],
        "Overall Pass vs Fail\n(All Students)",
    )

    fig.suptitle("Executive Batch Overview — Comprehensive Analysis", fontsize=13, fontweight="bold")
    plt.tight_layout()
    return fig


def plot_z_score_distribution(z_df: pd.DataFrame, title: str = "Z-Score Distribution"):
    fig, ax = plt.subplots(figsize=(5, 2.5))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    if z_df.empty or "Z-Score" not in z_df.columns:
        ax.text(0.5, 0.5, "No Z-score data available", ha="center", va="center")
        return fig

    sns.histplot(
        z_df["Z-Score"],
        bins=12,
        color=ACCENT_COLOR,
        edgecolor="black",
        alpha=0.6,
        ax=ax,
    )

    ax.axvline(0, color=PRIMARY_COLOR, linestyle="--", linewidth=1.5)
    ax.axvline(-1, color=BACKLOG_COLOR, linestyle=":", linewidth=1.5)
    ax.axvline(1, color=ACCENT_COLOR, linestyle=":", linewidth=1.5)

    plt.tight_layout()
    return fig


def _plot_grade_split_pie(full_clean: pd.Series, title: str = "Grade Split (O/E/A/B/C/D/F)"):
    """Render a donut-style grade split pie chart from numeric grade-point values."""
    fig, ax_grade = plt.subplots(figsize=(6.8, 5.8))
    fig.patch.set_facecolor(BG_COLOR)
    ax_grade.set_facecolor(BG_COLOR)

    grade_counts = _grade_counts_from_numeric(full_clean)
    grade_values = [grade_counts[g] for g in GRADE_ORDER]
    total_grades = sum(grade_values)
    if total_grades == 0:
        ax_grade.text(0.5, 0.5, "No grade distribution available", ha="center", va="center")
        ax_grade.axis("off")
    else:
        donut_colors = [GRADE_COLORS[g] for g in GRADE_ORDER]
        grade_labels = [f"{g}: {c} ({(c / total_grades * 100):.1f}%)" for g, c in zip(GRADE_ORDER, grade_values)]
        wedges, _, autotexts = ax_grade.pie(
            grade_values,
            colors=donut_colors,
            startangle=90,
            wedgeprops=dict(width=0.45, edgecolor="white"),
            autopct=lambda p: f"{p:.1f}%" if p > 0 else "",
            pctdistance=0.75,
        )
        for at in autotexts:
            at.set_fontsize(9)
            at.set_fontweight("bold")
        ax_grade.legend(
            wedges,
            grade_labels,
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            frameon=False,
            fontsize=9,
        )
        ax_grade.set_title(title, fontsize=11, fontweight="bold")

    plt.tight_layout()
    return fig


def plot_normal_curve(full_data: pd.Series, regular_data: pd.Series = None,
                      title: str = "Distribution", is_grade_scale: bool = False) -> Tuple[plt.Figure, Optional[plt.Figure]]:
    """Return the distribution curve figure and an optional grade-split donut figure."""
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    full_clean = full_data.dropna()

    if full_clean.empty or full_clean.std() == 0:
        ax.text(0.5, 0.5, "Not enough variance for curve",
                ha='center', va='center', fontsize=14)
        ax.grid(alpha=0.2)
        return fig, None

    bins = [-0.5, 0.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5] if is_grade_scale else 15

    sns.histplot(
        full_clean,
        stat="density",
        color=ACCENT_COLOR,
        alpha=0.4,
        bins=bins,
        ax=ax
    )

    xmin, xmax = ax.get_xlim()
    if is_grade_scale:
        xmin, xmax = -1, 11

    x = np.linspace(xmin, xmax, 300)
    mean = full_clean.mean()
    std = full_clean.std()
    p = norm.pdf(x, mean, std)

    ax.plot(x, p, 'k--', linewidth=2, label="Normal Curve")
    ax.axvline(mean, color=PRIMARY_COLOR, linestyle="--", linewidth=2)
    ax.axvline(mean - std, color=BACKLOG_COLOR, linestyle=":", linewidth=2)
    ax.axvline(mean + std, color=ACCENT_COLOR, linestyle=":", linewidth=2)

    label_y = 1.02
    ax.text(mean, label_y, f"Mean = {mean:.2f}", transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=10, color="black")
    ax.text(mean - std, label_y, f"-1σ = {mean-std:.2f}", transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=9, color="black")
    ax.text(mean + std, label_y, f"+1σ = {mean+std:.2f}", transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=9, color="black")

    ax.set_title(title, fontsize=16, pad=20)
    ax.set_xlabel("Values", fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.legend(loc="upper right")
    ax.grid(alpha=0.2)
    plt.tight_layout()

    pie_fig = _plot_grade_split_pie(full_clean) if is_grade_scale else None
    return fig, pie_fig


def plot_gpa_bucket_distribution(full_data: pd.Series, title: str = "GPA Bucket Distribution (0-10)"):
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    clean = pd.to_numeric(full_data, errors="coerce").dropna()
    if clean.empty:
        ax.text(0.5, 0.5, "No GPA data available", ha="center", va="center", fontsize=12)
        ax.axis("off")
        return fig

    bucket_ids = np.floor(np.clip(clean, 0, 9.999)).astype(int)
    counts = bucket_ids.value_counts().reindex(range(10), fill_value=0)
    labels = [f"{i}-{i+1}" for i in range(10)]

    bars = ax.bar(labels, counts.values, color=ACCENT_COLOR, edgecolor="black", alpha=0.85)
    for bar, count in zip(bars, counts.values):
        ax.annotate(
            str(int(count)),
            (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.set_title(title, fontsize=14, pad=12)
    ax.set_xlabel("GPA Range")
    ax.set_ylabel("Students")
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    return fig


def plot_normal_distribution_stats(
    full_data: pd.Series,
    title: str = "Normal Distribution Analysis",
    is_grade_scale: bool = False,
):
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    clean = pd.to_numeric(full_data, errors="coerce").dropna()
    if clean.empty or clean.std() == 0:
        ax.text(0.5, 0.5, "Not enough variance for distribution analysis", ha="center", va="center", fontsize=12)
        ax.axis("off")
        return fig

    mean = clean.mean()
    std = clean.std()

    if is_grade_scale:
        xmin, xmax = -1, 11
    else:
        span = max(3 * std, 0.5)
        xmin = max(0, mean - span)
        xmax = min(10, mean + span)
        if xmax - xmin < 1:
            xmin = max(0, mean - 0.5)
            xmax = min(10, mean + 0.5)

    x = np.linspace(xmin, xmax, 400)
    p = norm.pdf(x, mean, std)

    ax.plot(x, p, color="black", linewidth=2.2, label="Normal Curve")
    ax.fill_between(x, 0, p, where=(x >= mean - std) & (x <= mean + std), color=PASS_COLOR, alpha=0.18, label="±1σ region")
    ax.fill_between(x, 0, p, where=((x >= mean - 2 * std) & (x < mean - std)) | ((x > mean + std) & (x <= mean + 2 * std)),
                    color=ACCENT_COLOR, alpha=0.12, label="1σ to 2σ region")

    ax.axvline(mean, color=PRIMARY_COLOR, linestyle="--", linewidth=2)
    ax.axvline(mean - std, color=BACKLOG_COLOR, linestyle=":", linewidth=2)
    ax.axvline(mean + std, color=ACCENT_COLOR, linestyle=":", linewidth=2)
    ax.axvline(mean - 2 * std, color=GRID_COLOR, linestyle=":", linewidth=1.5)
    ax.axvline(mean + 2 * std, color=GRID_COLOR, linestyle=":", linewidth=1.5)

    within_1 = ((clean >= (mean - std)) & (clean <= (mean + std))).mean() * 100
    within_2 = ((clean >= (mean - 2 * std)) & (clean <= (mean + 2 * std))).mean() * 100
    below_1 = (clean < (mean - std)).mean() * 100
    above_1 = (clean > (mean + std)).mean() * 100

    summary_text = (
        f"μ = {mean:.2f}, σ = {std:.2f}\n"
        f"Within ±1σ: {within_1:.1f}%\n"
        f"Within ±2σ: {within_2:.1f}%\n"
        f"Below μ-σ: {below_1:.1f}% | Above μ+σ: {above_1:.1f}%"
    )
    ax.text(
        0.02,
        0.97,
        summary_text,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white", alpha=0.85, edgecolor=GRID_COLOR),
    )

    ax.set_title(title, fontsize=14, pad=12)
    ax.set_xlabel("Values")
    ax.set_ylabel("Density")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper right")
    plt.tight_layout()
    return fig


def plot_subject_grade_distribution_bars(stats_df: pd.DataFrame, selected_subject: Optional[str] = None):
    if stats_df.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        fig.patch.set_facecolor(BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        ax.text(0.5, 0.5, "No statistics available", ha="center", va="center")
        ax.axis("off")
        return fig

    target_df = stats_df.copy()
    if selected_subject is not None and "Subject" in target_df.columns:
        target_df = target_df[target_df["Subject"].astype(str) == str(selected_subject)]

    subject_count = len(target_df)
    if subject_count == 0:
        fig, ax = plt.subplots(figsize=(10, 4))
        fig.patch.set_facecolor(BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        ax.text(0.5, 0.5, "No statistics available", ha="center", va="center")
        ax.axis("off")
        return fig

    if selected_subject is not None:
        fig, ax = plt.subplots(figsize=(9, 4.8))
        fig.patch.set_facecolor(BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        row = target_df.iloc[0]
        counts = [int(row.get(g, 0) or 0) for g in GRADE_ORDER]
        colors = [GRADE_COLORS[g] for g in GRADE_ORDER]
        bars = ax.bar(GRADE_ORDER, counts, color=colors, edgecolor="black", alpha=0.9)
        for bar, count in zip(bars, counts):
            ax.annotate(str(count), (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)
        ax.set_title(str(row.get("Subject", "Subject")), fontsize=11, fontweight="bold")
        ax.set_ylabel("Students")
        ax.grid(axis="y", linestyle="--", alpha=0.25)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout()
        return fig

    n_cols = 2
    n_rows = int(np.ceil(subject_count / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, max(4.8 * n_rows, 5.5)))
    fig.patch.set_facecolor(BG_COLOR)
    axes = np.array(axes).reshape(-1)

    for idx, (_, row) in enumerate(target_df.iterrows()):
        ax = axes[idx]
        ax.set_facecolor(BG_COLOR)
        counts = [int(row.get(g, 0) or 0) for g in GRADE_ORDER]
        colors = [GRADE_COLORS[g] for g in GRADE_ORDER]
        bars = ax.bar(GRADE_ORDER, counts, color=colors, edgecolor="black", alpha=0.9)
        for bar, count in zip(bars, counts):
            ax.annotate(str(count), (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)
        ax.set_title(str(row.get("Subject", "Subject")), fontsize=10, fontweight="bold")
        ax.set_ylabel("Students")
        ax.grid(axis="y", linestyle="--", alpha=0.25)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    for idx in range(subject_count, len(axes)):
        axes[idx].axis("off")

    fig.suptitle("Subject-wise Grade Distribution (O/E/A/B/C/D/F)\n\n", fontsize=13, fontweight="bold")
    plt.tight_layout()
    return fig


def plot_subject_metric_comparison_bars(
    stats_df: pd.DataFrame,
    selected_metric: Optional[str] = None,
    use_subject_codes: bool = True,
):
    def _parse_metric_values(metric_series: pd.Series, metric_name: str) -> pd.Series:
        if metric_name == "Pass %":
            metric_series = (
                metric_series
                .astype(str)
                .str.replace("%", "", regex=False)
                .str.strip()
            )
        return pd.to_numeric(metric_series, errors="coerce")

    metric_cols = ["Mean", "Median", "Std Dev (σ)", "Pass %"]
    available_metrics = [m for m in metric_cols if m in stats_df.columns]
    if stats_df.empty or not available_metrics:
        fig, ax = plt.subplots(figsize=(10, 4))
        fig.patch.set_facecolor(BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        ax.text(0.5, 0.5, "No metric data available", ha="center", va="center")
        ax.axis("off")
        return fig

    metrics_to_plot = [selected_metric] if selected_metric else metric_cols
    if selected_metric and selected_metric not in available_metrics:
        fig, ax = plt.subplots(figsize=(10, 4))
        fig.patch.set_facecolor(BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        ax.text(0.5, 0.5, f"No data for {selected_metric}", ha="center", va="center")
        ax.axis("off")
        return fig

    if selected_metric:
        fig, axes = plt.subplots(1, 1, figsize=(10, 5))
        fig.patch.set_facecolor(BG_COLOR)
        axes = [axes]
    else:
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.patch.set_facecolor(BG_COLOR)
        axes = axes.flatten()

    for i, metric in enumerate(metrics_to_plot):
        ax = axes[i]
        ax.set_facecolor(BG_COLOR)
        metric_df = stats_df[["Subject", metric]].copy()
        metric_df[metric] = _parse_metric_values(metric_df[metric], metric)
        metric_df = metric_df.dropna(subset=[metric]).sort_values(metric, ascending=False)
        if metric_df.empty:
            ax.text(0.5, 0.5, f"No data for {metric}", ha="center", va="center")
            ax.axis("off")
            continue

        x_labels = metric_df["Subject"].astype(str).tolist()
        if use_subject_codes:
            x_labels = [_subject_code_label(label) for label in x_labels]
        y_vals = metric_df[metric].astype(float).tolist()
        colors = [SEASON_PALETTE[j % len(SEASON_PALETTE)] for j in range(len(x_labels))]
        bars = ax.bar(x_labels, y_vals, color=colors, edgecolor="black", alpha=0.9)
        for bar, val in zip(bars, y_vals):
            ax.annotate(f"{val:.2f}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, rotation=90)
        ax.set_title(metric, fontweight="bold")
        ax.tick_params(axis="x", rotation=35, labelsize=8)
        ax.grid(axis="y", linestyle="--", alpha=0.25)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    if not selected_metric:
        for idx in range(len(metrics_to_plot), len(axes)):
            axes[idx].axis("off")
        fig.suptitle("Comparative Subject Metrics (Mean, Median, Std Dev, Pass %)\n\n", fontsize=13, fontweight="bold")
    else:
        fig.suptitle(f"Comparative Subject Metric — {selected_metric}\n", fontsize=13, fontweight="bold")

    plt.tight_layout()
    return fig


def plot_semester_metric_bars(comparison_df: pd.DataFrame, metric: str, selected_groups: Optional[List[str]] = None, title: Optional[str] = None):
    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    metric_df = comparison_df[comparison_df["METRIC"] == metric].copy()

    if selected_groups:
        metric_df = metric_df[metric_df["GROUP_LABEL"].isin(selected_groups)].copy()

    x_labels = metric_df["GROUP_LABEL"].astype(str).tolist()
    y_vals = metric_df["AVG_VALUE"].astype(float).tolist()

    colors = [SEASON_PALETTE[i % len(SEASON_PALETTE)] for i in range(len(x_labels))]

    ax.bar(x_labels, y_vals, color=colors, edgecolor="black", alpha=0.85)

    plt.tight_layout()
    return fig


def plot_grouped_multi_metric_bars(comparison_df: pd.DataFrame, selected_metrics: list, selected_groups: list, title: str = "Multi-Metric Comparison"):
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    df_filtered = comparison_df[
        (comparison_df["METRIC"].isin(selected_metrics)) &
        (comparison_df["GROUP_LABEL"].isin(selected_groups))
    ]

    sns.barplot(
        data=df_filtered,
        x="GROUP_LABEL",
        y="AVG_VALUE",
        hue="METRIC",
        palette=SEASON_PALETTE[:len(selected_metrics)],
        edgecolor="black",
        alpha=0.85,
        ax=ax
    )

    plt.tight_layout()
    return fig
