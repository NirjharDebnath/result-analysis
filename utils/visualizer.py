# utils/visualizer.py
import io
from pathlib import Path
from typing import Optional
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
from utils.constants import LOGO_CANDIDATE_PATHS, SOFT_COLORS

def downloadable_plot(fig, filename: str):
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=150)
    st.download_button(
        label=f"Download {filename}",
        data=buffer.getvalue(),
        file_name=filename,
        mime="image/png",
        use_container_width=True,
    )
    plt.close(fig)

def download_table_button(df: pd.DataFrame, label: str, filename: str):
    st.download_button(
        label=label,
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )

def resolve_logo_path() -> Optional[str]:
    base_path = Path(__file__).resolve().parent.parent
    for relative_path in LOGO_CANDIDATE_PATHS:
        logo_path = base_path / relative_path
        if logo_path.exists():
            return str(logo_path)
    return None

def render_sidebar_branding():
    logo_path = resolve_logo_path()
    if logo_path:
        st.sidebar.image(logo_path, width=120)
    st.sidebar.markdown("**Kalyani Government Engineering College**")

def style_axis(ax, xlabel: Optional[str] = None, ylabel: Optional[str] = None, rotate_x: int = 0):
    ax.set_facecolor(SOFT_COLORS["bg"])
    ax.grid(axis="y", linestyle="--", alpha=0.35, color=SOFT_COLORS["grid"])
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10, fontweight="semibold")
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10, fontweight="semibold")
    ax.tick_params(axis="x", labelsize=9)
    ax.tick_params(axis="y", labelsize=9)
    for tick in ax.get_xticklabels():
        tick.set_rotation(rotate_x)
        tick.set_ha("right" if rotate_x else "center")

def render_footer():
    st.markdown("---")
    st.caption("© Designed by Nirjhar Debnath, Dept of CSE, Kalyani Government Engineering College.")
    
