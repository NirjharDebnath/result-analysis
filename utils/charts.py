# utils/charts.py
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy.stats import norm
import pandas as pd
from typing import Optional, List
from utils.constants import SOFT_COLORS

# Cool color theme requested
THEME = {
    "primary": "#2E4053",    # Deep Slate
    "accent": "#D35400",     # Burnt Orange
    "secondary": "#F4A261",  # Light Slate
    "bg": "#FDFEFE",         # Clean White
    "pass": "#FAD6A5",       # Green
    "backlog": "#9C3F0F",    # Yellow
    "lag": "#E76F51"         # Red
}

# Replace this specific function inside utils/charts.py
def plot_status_bars(status_counts: pd.Series, total_students: int = None):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.patch.set_facecolor(THEME["bg"])
    ax.set_facecolor(THEME["bg"])
    
    # Order categories logically
    base_categories = ["Current Batch", "Backlog (Current Batch)", "Old Batch (Re-appearing)", "Year Lag"]
    ordered_categories = [c for c in base_categories if c in status_counts.index]
    ordered_categories += [c for c in status_counts.index if c not in base_categories]
    
    status_counts = status_counts.reindex(ordered_categories, fill_value=0)
    categories = status_counts.index.tolist()
    counts = status_counts.values.tolist()
    
    colors = []
    for cat in categories:
        cat_upper = cat.upper()
        if cat_upper == "CURRENT BATCH": colors.append(THEME["pass"]) # All Clear
        elif "BACKLOG" in cat_upper: colors.append(THEME["backlog"])
        elif "OLD" in cat_upper: colors.append(THEME["secondary"])
        elif "LAG" in cat_upper: colors.append(THEME["lag"])
        else: colors.append(THEME["primary"])
    
    bars = ax.bar(categories, counts, color=colors, edgecolor='black', alpha=0.85)
    
    # Calculate percentages for the annotations
    total = total_students if total_students else sum(counts)
    
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        percentage = (count / total) * 100 if total > 0 else 0
        
        # Two-line annotation: Count and Percentage
        label_text = f'{int(count)}\n({percentage:.1f}%)' if count > 0 else '0'
        
        ax.annotate(label_text,
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 4),  
                    textcoords="offset points",
                    ha='center', va='bottom', fontweight='bold', fontsize=9)
                    
    # Make X-Axis labels much cleaner and wrap the text
    display_labels = []
    for cat in categories:
        if cat == "Current Batch": display_labels.append("Current Batch\n(All Clear)")
        elif cat == "Backlog (Current Batch)": display_labels.append("Current Batch\n(Backlog)")
        else: display_labels.append(cat.replace(" (", "\n(")) # wrap text automatically
        
    ax.set_xticks(range(len(display_labels)))
    ax.set_xticklabels(display_labels, rotation=0, ha='center', fontsize=9, fontweight='semibold')
    
    ax.set_ylabel("Number of Students")
    ax.set_title("Overall Batch Status Breakdown", fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Extend Y-axis slightly to make room for the two-line text annotations
    ax.set_ylim(0, max(counts) * 1.25 if counts else 10)
    
    plt.tight_layout()
    return fig

def plot_z_score_distribution(z_df: pd.DataFrame, title: str = "Z-Score Distribution"):
    fig, ax = plt.subplots(figsize=(5, 2.5))
    fig.patch.set_facecolor(THEME["bg"])
    ax.set_facecolor(THEME["bg"])

    if z_df.empty or "Z-Score" not in z_df.columns:
        ax.text(0.5, 0.5, "No Z-score data available", ha="center", va="center")
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Z-Score")
        ax.set_ylabel("Number of Students")
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        return fig

    sns.histplot(
        z_df["Z-Score"],
        bins=12,
        color=THEME["secondary"],
        edgecolor="black",
        alpha=0.6,
        ax=ax,
    )
    ax.axvline(0, color=THEME["primary"], linestyle="--", linewidth=1.5, label="Mean (0σ)")
    ax.axvline(-1, color=THEME["lag"], linestyle=":", linewidth=1.5, label="-1σ")
    ax.axvline(1, color=THEME["accent"], linestyle=":", linewidth=1.5, label="+1σ")
    ax.set_title(title, fontweight="bold")
    ax.set_xlabel("Z-Score", fontsize=8)
    ax.set_ylabel("Number of Students", fontsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.legend()
    plt.tight_layout()
    return fig

def plot_normal_curve(full_data: pd.Series, regular_data: pd.Series = None, title: str = "Distribution", is_grade_scale: bool = False):
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor(THEME["bg"])
    ax.set_facecolor(THEME["bg"])
    
    full_clean = full_data.dropna()
    
    if full_clean.empty or full_clean.std() == 0:
        ax.text(0.5, 0.5, "Not enough variance for curve", ha='center', va='center')
        return fig
        
    # If plotting grades, force bins to align nicely with the 0-10 scale
    bins = [-0.5, 0.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5] if is_grade_scale else 15
    sns.histplot(full_clean, stat="density", color=THEME["secondary"], alpha=0.4, label="Full Class", bins=bins, ax=ax)
    
    # Calculate Bell Curve
    xmin, xmax = ax.get_xlim()
    if is_grade_scale: 
        xmin, xmax = -1, 11 # Fix axis range for grades
        
    x = np.linspace(xmin, xmax, 100)
    p = norm.pdf(x, full_clean.mean(), full_clean.std())
    ax.plot(x, p, 'k--', linewidth=2, label=f"Old Batch (\u03bc={full_clean.mean():.2f})")
    ax.axvline(full_clean.mean(), color=THEME["primary"], linestyle="--", linewidth=1.5, label="Mean (0σ)")
    ax.axvline(full_clean.mean() - full_clean.std(), color=THEME["lag"], linestyle=":", linewidth=1.5, label="-1σ")
    ax.axvline(full_clean.mean() + full_clean.std(), color=THEME["accent"], linestyle=":", linewidth=1.5, label="+1σ")
    
    if regular_data is not None:
        reg_clean = regular_data.dropna()
        if not reg_clean.empty and reg_clean.std() > 0:
            p_reg = norm.pdf(x, reg_clean.mean(), reg_clean.std())
            ax.plot(x, p_reg, color=THEME["accent"], linewidth=2.5, label=f"Current Batch (\u03bc={reg_clean.mean():.2f})")
            
    ax.set_title(title, fontweight='bold')
    
    # --- The Fix: Injecting the Grade Letters ---
    if is_grade_scale:
        ax.set_xlabel("Grades", fontweight='bold')
        ax.set_xticks([0, 5, 6, 7, 8, 9, 10])
        # ax.set_xticklabels(['F', 'D', 'C', 'B', 'A', 'E', 'O'], fontweight='bold')
        ax.set_xticklabels(['F(0)', 'D(5)', 'C(6)', 'B(7)', 'A(8)', 'E(9)', 'O(0)'])
        ax.set_xlim(-1, 11)
    else:
        ax.set_xlabel("GPA Metric", fontweight='bold')
        
    ax.set_ylabel("Density")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    return fig

def plot_semester_metric_bars(
    comparison_df: pd.DataFrame,
    metric: str,
    selected_groups: Optional[List[str]] = None,
    title: Optional[str] = None,
):
    # Autumn colour palette — one distinct colour per comparison group
    AUTUMN_PALETTE = [
        "#D35400",  # Burnt Orange
        "#F4A261",  # Sandy Orange
        "#E76F51",  # Terra Cotta
        "#9C3F0F",  # Dark Rust
        "#FAD6A5",  # Light Peach
        "#C0392B",  # Deep Red
        "#F0B429",  # Amber
        "#2E4053",  # Deep Slate (contrast anchor)
    ]

    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor(THEME["bg"])
    ax.set_facecolor(THEME["bg"])

    if comparison_df.empty or "METRIC" not in comparison_df.columns:
        ax.text(0.5, 0.5, "No comparison data available", ha="center", va="center")
        ax.set_title(title or f"{metric} Comparison", fontweight="bold")
        return fig

    metric_df = comparison_df[comparison_df["METRIC"] == metric].copy()
    if selected_groups:
        metric_df = metric_df[metric_df["GROUP_LABEL"].isin(selected_groups)].copy()

    if metric_df.empty:
        ax.text(0.5, 0.5, "No data for selected groups", ha="center", va="center")
        ax.set_title(title or f"{metric} Comparison", fontweight="bold")
        return fig

    # Sort bars by semester order then group label
    sort_cols = ["SEMESTER_ORDER", "GROUP_LABEL"] if "SEMESTER_ORDER" in metric_df.columns else ["GROUP_LABEL"]
    metric_df = metric_df.sort_values(sort_cols)

    x_labels = metric_df["GROUP_LABEL"].astype(str).tolist()
    y_vals = metric_df["AVG_VALUE"].astype(float).tolist()
    counts = metric_df["STUDENT_COUNT"].astype(int).tolist()
    colors = [AUTUMN_PALETTE[i % len(AUTUMN_PALETTE)] for i in range(len(x_labels))]

    bars = ax.bar(x_labels, y_vals, color=colors, edgecolor="black", alpha=0.85)
    for bar, count, y in zip(bars, counts, y_vals):
        ax.annotate(
            f"{y:.2f}\n(n={count})",
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    ax.set_title(title or f"{metric} — Average Comparison", fontweight="bold")
    ax.set_ylabel(f"Average {metric}")
    ax.set_xlabel("Group")
    ax.set_ylim(bottom=0, top=(max(y_vals) * 1.2) if y_vals else 10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    return fig

def plot_grouped_multi_metric_bars(
    comparison_df: pd.DataFrame,
    selected_metrics: list,
    selected_groups: list,
    title: str = "Multi-Metric Comparison"
):
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(THEME["bg"])
    ax.set_facecolor(THEME["bg"])

    # Filter data for selected metrics and groups
    df_filtered = comparison_df[
        (comparison_df["METRIC"].isin(selected_metrics)) &
        (comparison_df["GROUP_LABEL"].isin(selected_groups))
    ]

    if df_filtered.empty:
        ax.text(0.5, 0.5, "No data available for the selected combination", ha="center", va="center")
        ax.set_title(title, fontweight="bold")
        return fig

    # Autumn colour palette — one distinct colour per metric
    AUTUMN_PALETTE = [
        "#8C3B0F",  # deep burnt sienna
        "#C05621",  # rust orange
        "#DD6B20",  # warm pumpkin
        "#ED8936",  # soft orange
        "#D69E2E",  # golden amber
        "#B7791F",  # muted mustard
        "#744210",  # earthy brown
        "#5A2E0C"   # dark chocolate brown
    ]
    # Use seaborn's barplot for grouped bars
    sns.barplot(
        data=df_filtered,
        x="GROUP_LABEL",
        y="AVG_VALUE",
        hue="METRIC",
        palette=AUTUMN_PALETTE[:len(selected_metrics)],
        edgecolor="black",
        alpha=0.85,
        ax=ax
    )

    # Add value annotations on top of each bar
    for container in ax.containers:
        ax.bar_label(
            container,
            fmt='%.2f',
            padding=6,
            fontsize=9,
            color="black",
            bbox=dict(
                facecolor="white",
                edgecolor="none",
                alpha=0.7,
                boxstyle="round,pad=0.2"
            ),
            rotation=90
        )

    ax.set_title(title, fontweight="bold")
    ax.set_ylabel("Average Score")
    ax.set_xlabel("Semester / Exam Session")
    
    # Dynamic Y-limit to make room for the legend
    max_val = df_filtered["AVG_VALUE"].max()
    ax.set_ylim(bottom=0, top=(max_val * 1.3) if max_val else 10)
    
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    # Move legend outside the plot so it doesn't cover bars
    ax.legend(title="GPA Metrics", bbox_to_anchor=(1.01, 1), loc='upper left')
    
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    return fig
