"""Análise personalizada: download, formação de carteiras e visualização.

Executada somente quando o usuário acessa esta página no Streamlit.
"""

import streamlit as st

st.set_page_config(
    page_title="Análise Personalizada | US Quant Factor Dashboard",
    page_icon="📈",
    layout="wide",
)

from src.data_loader import get_sp500_tickers
from src.ui.personalized_analysis import render_personalized_analysis
from src.ui.sidebar import render_sidebar


def main():
    st.title("Análise Personalizada")

    sp500_df = get_sp500_tickers().copy()
    sp500_df["sector"] = sp500_df["sector"].fillna("Sem setor")

    config = render_sidebar(sp500_df)
    render_personalized_analysis(config, sp500_df)


if __name__ == "__main__":
    main()
