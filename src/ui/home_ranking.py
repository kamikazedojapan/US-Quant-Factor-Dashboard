"""Ranking automático e componentes da página principal."""

import pandas as pd
import streamlit as st

from src.data_loader import download_market_data
from src.ranking import (
    RankingUnavailableError,
    get_latest_complete_nyse_session,
    load_home_ranking_with_fallback,
)

HOME_RANKING_OPTIONS = [10, 20, 50]
HOME_RANKING_MAX = max(HOME_RANKING_OPTIONS)
HOME_RANKING_CACHE_TTL = 3600


@st.cache_data(
  ttl=HOME_RANKING_CACHE_TTL,
  show_spinner=False,
)
def get_cached_home_ranking(session_key, force_refresh=False):
  """
  Calcula e mantém em cache o ranking multifatorial atual.

  O ranking máximo retornado é Top 50.
  A interface pode derivar Top 10 e Top 20 sem recalcular
  fatores ou baixar novamente os dados.
  """

  return load_home_ranking_with_fallback(
    max_top_n=HOME_RANKING_MAX,
    force_refresh=force_refresh,
  )


@st.fragment(run_every="15m")
def render_latest_ranking_section():
  """
  Exibe na página principal o ranking multifatorial mais
  recente do universo atual do S&P 500.

  O usuário pode visualizar Top 10, Top 20 ou Top 50.
  """

  st.subheader("Ranking Multifatorial Atual")

  st.caption(
    "Ranking automático do universo atual do S&P 500, "
    "baseado em Momentum, Baixo Risco e Liquidez."
  )

  col_selector, col_refresh = st.columns(
    [3, 1],
    vertical_alignment="bottom",
  )

  with col_selector:
    ranking_top_n = st.selectbox(
      "Quantidade de ações no ranking",
      options=HOME_RANKING_OPTIONS,
      index=0,
      format_func=lambda value: f"Top {value}",
      key="home_latest_ranking_top_n",
    )

  with col_refresh:
    refresh_ranking = st.button(
      "Atualizar ranking agora",
      use_container_width=True,
      key="refresh_home_ranking",
    )

  if refresh_ranking:
    # Ignora snapshot na chamada abaixo, mas preserva o último válido para
    # recuperação caso o fornecedor esteja indisponível.
    get_cached_home_ranking.clear()
    download_market_data.clear()

  try:
    # A chave muda após cada fechamento da NYSE, invalidando também
    # um cache ainda válido quando a página for executada novamente.
    session_key = get_latest_complete_nyse_session().date().isoformat()
    with st.spinner("Calculando ranking multifatorial mais recente..."):
      latest_ranking, ranking_info = get_cached_home_ranking(
        session_key, force_refresh=refresh_ranking
      )
  except (ValueError, RankingUnavailableError) as error:
    st.warning(f"Ranking atual indisponível: {error}")
    return

  if ranking_info.get("source") == "snapshot":
    st.warning(
      "Não foi possível obter dados atualizados. Exibindo o último "
      "ranking salvo; a data de referência está indicada abaixo."
    )
  elif ranking_info.get("snapshot_save_failed"):
    st.info(
      "Ranking atual calculado, mas não foi possível salvar uma "
      "cópia para recuperação em caso de falha futura."
    )

  if latest_ranking.empty:
    st.warning(
      "Nenhuma ação elegível foi encontrada "
      "para o ranking atual."
    )
    return

  ranking_display = latest_ranking.head(
    ranking_top_n
  ).copy()

  # ----------------------------------------------------------
  # Resumo do ranking
  # ----------------------------------------------------------

  as_of_date = ranking_info.get("as_of_date")

  if as_of_date is not None:
    as_of_date = pd.Timestamp(
      as_of_date
    ).strftime("%d/%m/%Y")
  else:
    as_of_date = "N/D"

  universe_size = ranking_info.get(
    "universe_size",
    0,
  )

  eligible_count = ranking_info.get(
    "eligible_count",
    0,
  )

  col1, col2, col3, col4 = st.columns(4)

  col1.metric(
    "Dados até",
    as_of_date,
  )

  col2.metric(
    "Universo",
    universe_size,
  )

  col3.metric(
    "Ações elegíveis",
    eligible_count,
  )

  col4.metric(
    "Ranking exibido",
    f"Top {len(ranking_display)}",
  )

  # ----------------------------------------------------------
  # Colunas exibidas
  # ----------------------------------------------------------

  ranking_columns = [
    "rank",
    "ticker",
    "company",
    "sector",
    "score_preliminar",
    "score_momentum",
    "score_risco",
    "score_liquidez",
  ]

  available_ranking_columns = [
    column
    for column in ranking_columns
    if column in ranking_display.columns
  ]

  st.dataframe(
    ranking_display[
      available_ranking_columns
    ],
    use_container_width=True,
    hide_index=True,
    column_config={
      "rank": st.column_config.NumberColumn(
        "Posição",
        format="%d",
      ),
      "ticker": st.column_config.TextColumn(
        "Ticker",
      ),
      "company": st.column_config.TextColumn(
        "Empresa",
      ),
      "sector": st.column_config.TextColumn(
        "Setor",
      ),
      "score_preliminar": (
        st.column_config.NumberColumn(
          "Score",
          format="%.2f",
        )
      ),
      "score_momentum": (
        st.column_config.NumberColumn(
          "Momentum",
          format="%.2f",
        )
      ),
      "score_risco": (
        st.column_config.NumberColumn(
          "Baixo Risco",
          format="%.2f",
        )
      ),
      "score_liquidez": (
        st.column_config.NumberColumn(
          "Liquidez",
          format="%.2f",
        )
      ),
    },
  )

  st.caption(
    "Pesos atuais: Momentum 40% | "
    "Baixo Risco 35% | Liquidez 25%."
  )

  st.caption(
    "O ranking usa a última sessão completa da NYSE e permanece "
    "em cache por até 1 hora. Com a sessão aberta, a seção "
    "verifica automaticamente novos fechamentos a cada 15 minutos. "
    "Também é possível atualizar manualmente."
  )
