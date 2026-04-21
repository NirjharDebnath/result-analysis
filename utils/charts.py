# utils/charts.py
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy.stats import norm
import pandas as pd
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

def plot_status_bars(status_counts: pd.Series):
    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor(THEME["bg"])
    ax.set_facecolor(THEME["bg"])
    
    base_categories = [
        "Current Batch",
        "Backlog (Current Batch)",
        "Old Batch (Re-appearing)",
        "Year Lag",
    ]
    incoming_categories = status_counts.index.tolist()
    ordered_categories = base_categories + [c for c in incoming_categories if c not in base_categories]
    status_counts = status_counts.reindex(ordered_categories, fill_value=0)
    categories = status_counts.index.tolist()
    counts = status_counts.values.tolist()
    
    colors = []
    for cat in categories:
        cat_upper = cat.upper()
        if "PASS" in cat_upper: colors.append(THEME["pass"])
        elif "LAG" in cat_upper: colors.append(THEME["lag"])
        elif "OLD" in cat_upper: colors.append(THEME["secondary"])
        else: colors.append(THEME["backlog"])
    
    bars = ax.bar(categories, counts, color=colors, edgecolor='black', alpha=0.8)
    
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{int(height)}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  
                    textcoords="offset points",
                    ha='center', va='bottom', fontweight='bold')
                    
    plt.xticks(rotation=15, ha='right', fontsize=9)
    ax.set_ylabel("Number of Students")
    ax.set_title("Overall Batch Status", fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
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
        ax.set_xticklabels(['F', 'D', 'C', 'B', 'A', 'E', 'O'], fontweight='bold')
        ax.set_xlim(-1, 11)
    else:
        ax.set_xlabel("GPA Metric", fontweight='bold')
        
    ax.set_ylabel("Density")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    return fig
