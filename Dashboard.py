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
    navigation = st.navigation(
        {
            "": [
                st.Page(
                    main,
                    title="Visão Geral",
                    icon=":material/dashboard:",
                    default=True,
                ),
            ],
            "Pesquisa": [
                st.Page(
                    "pages/1_Ranking_Multifatorial.py",
                    title="Ranking Multifatorial",
                    icon=":material/leaderboard:",
                ),
                st.Page(
                    "pages/2_Analise_Ativo.py",
                    title="Análise do Ativo",
                    icon=":material/search:",
                ),
                st.Page(
                    "pages/2_Analise_Personalizada.py",
                    title="Análise Personalizada",
                    icon=":material/tune:",
                ),
            ],
            "Estratégias": [
                st.Page(
                    "pages/3_Backtest.py",
                    title="Backtest",
                    icon=":material/query_stats:",
                ),
                st.Page(
                    "pages/5_Painel_Estrategico.py",
                    title="Painel Estratégico",
                    icon=":material/monitoring:",
                ),
            ],
            "Sobre": [
                st.Page(
                    "pages/4_Metodologia.py",
                    title="Metodologia",
                    icon=":material/menu_book:",
                ),
            ],
        },
    )

    navigation.run()
