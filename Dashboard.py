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


def main():
    st.title("US Quant Factor Dashboard")
    render_latest_ranking_section()
    st.divider()
    st.page_link(
        "pages/2_Analise_Personalizada.py",
        label="Abrir análise personalizada",
        icon="📈",
    )


if __name__ == "__main__":
    main()
