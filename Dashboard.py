"""Página principal do US Quant Factor Dashboard.

A Home renderiza somente o ranking automático.
A análise personalizada é uma página separada, aberta sob demanda.
"""

import streamlit as st

st.set_page_config(
    page_title="US Quant Factor Dashboard",
    page_icon="📊",
    layout="wide",
)

from src.ui.home_ranking import render_latest_ranking_section
from src.ui.branding import render_page_header

def main():
    render_page_header(
        title="US Quant Factor",
        description=(
            "Explore o mercado americano com uma abordagem "
            "quantitativa, sistemática e baseada em fatores."
        ),
        label="Market Intelligence | S&P 500",
    )
    render_latest_ranking_section()


if __name__ == "__main__":
    main()
