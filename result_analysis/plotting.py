from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .constants import AUTUMN_COLORS


def base_style(ax, xlabel: Optional[str] = None, ylabel: Optional[str] = None, rotate_x: int = 0):
    ax.set_facecolor(AUTUMN_COLORS["bg"])
    ax.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.4, color=AUTUMN_COLORS["grid"])
    ax.tick_params(axis="x", labelsize=9)
    ax.tick_params(axis="y", labelsize=9)
    for tick in ax.get_xticklabels():
        tick.set_rotation(rotate_x)
        tick.set_ha("right" if rotate_x else "center")
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10, fontweight="bold")
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10, fontweight="bold")


def bar_with_labels(data: pd.DataFrame, x_col: str, y_col: str, title: str, colors) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(data[x_col], data[y_col], color=colors)
    ax.bar_label(bars, padding=4, fontsize=9)
    ax.set_title(title, fontsize=12, fontweight="bold")
    base_style(ax, xlabel=x_col, ylabel=y_col)
    fig.tight_layout()
    return fig


def normal_curve_figure(series: pd.Series, x: np.ndarray, y: np.ndarray, mean: float, std: float, title: str, xlabel: str) -> plt.Figure:
    fig, ax1 = plt.subplots(figsize=(9, 4.8))
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        ax1.text(0.5, 0.5, "No valid numeric values found", transform=ax1.transAxes, ha="center", va="center")
    else:
        bins = min(12, max(4, numeric.nunique()))
        ax1.hist(
            numeric,
            bins=bins,
            density=True,
            alpha=0.35,
            color=AUTUMN_COLORS["secondary"],
            edgecolor="black",
            linewidth=0.6,
        )
    if len(x):
        ax1.plot(
            x,
            y,
            color=AUTUMN_COLORS["year_lag"],
            linewidth=2.2,
            label=f"Normal Curve (μ={mean:.2f}, σ={std:.2f})",
        )
        ax1.axvline(mean, color=AUTUMN_COLORS["primary"], linestyle="--", linewidth=1.8, label=f"Mean {mean:.2f}")
    ax1.set_title(title, fontsize=12, fontweight="bold")
    base_style(ax1, xlabel=xlabel, ylabel="Density")
    handles, labels = ax1.get_legend_handles_labels()
    if handles:
        ax1.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    return fig


def metric_distribution_bar(series: pd.Series, metric_name: str) -> plt.Figure:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    fig, ax = plt.subplots(figsize=(9, 4.8))
    if numeric.empty:
        ax.text(0.5, 0.5, f"No valid {metric_name} values", transform=ax.transAxes, ha="center", va="center")
        fig.tight_layout()
        return fig

    bins = np.linspace(numeric.min(), numeric.max(), 8 if numeric.nunique() > 5 else max(4, numeric.nunique() + 1))
    counts, edges = np.histogram(numeric, bins=bins)
    labels = [f"{edges[i]:.2f}-{edges[i+1]:.2f}" for i in range(len(edges) - 1)]
    bars = ax.bar(labels, counts, color=AUTUMN_COLORS["accent"])
    ax.bar_label(bars, padding=3, fontsize=8)
    ax.set_title(f"{metric_name} Distribution", fontsize=12, fontweight="bold")
    base_style(ax, xlabel=f"{metric_name} Range", ylabel="Students", rotate_x=20)
    fig.tight_layout()
    return fig


def table_figure(df: pd.DataFrame, title: str, max_rows: int = 24) -> plt.Figure:
    show = df.head(max_rows).copy()
    fig_h = max(3.5, min(11, 1.0 + 0.33 * (len(show) + 1)))
    fig, ax = plt.subplots(figsize=(14, fig_h))
    ax.axis("off")
    ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
    table = ax.table(cellText=show.values, colLabels=show.columns, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(1, 1.2)
    fig.tight_layout()
    return fig
