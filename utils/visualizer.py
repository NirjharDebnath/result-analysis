# utils/visualizer.py
import io
from pathlib import Path
from typing import Optional
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
from utils.constants import LOGO_CANDIDATE_PATHS, SOFT_COLORS, COLLEGE_NAME

def downloadable_plot(fig, filename: str):
    fig.tight_layout()
    st.pyplot(fig, width='stretch')
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=150)
    st.download_button(
        label=f"Download {filename}",
        data=buffer.getvalue(),
        file_name=filename,
        mime="image/png",
        width='stretch',
    )
    plt.close(fig)

def download_table_button(df: pd.DataFrame, label: str, filename: str):
    st.download_button(
        label=label,
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        width='stretch',
    )

def resolve_logo_path() -> Optional[str]:
    base_path = Path(__file__).resolve().parent.parent
    for relative_path in LOGO_CANDIDATE_PATHS:
        logo_path = base_path / relative_path
        if logo_path.exists():
            return str(logo_path)
    return None

def render_sidebar_branding():
    st.sidebar.markdown(
        """
        <style>
            [data-testid="stSidebarNav"]::before {{
                content: "{COLLEGE_NAME}";
                margin-left: 20px;
                margin-top: 20px;
                margin-bottom: 10px;
                font-size: 1.2rem;
                font-weight: 700;
                color: #2F3A45;
                display: block;
            }}
            div[data-testid="stSidebarUserContent"] {
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }
            .sidebar-author-credit {
                margin-top: auto;
                padding-top: 1rem;
                font-size: 0.85rem;
                opacity: 0.85;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    logo_path = resolve_logo_path()
    if logo_path:
        st.sidebar.image(logo_path, width=120)
    st.sidebar.markdown("**Kalyani Government Engineering College**")
    st.sidebar.markdown("---")
    st.sidebar.caption("🎓 Result Analysis Tool")
    st.sidebar.markdown("<div class='sidebar-author-credit'>Designed by <b>Nirjhar Debnath</b>, Dept of CSE, KGEC</div>", unsafe_allow_html=True)

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
    
