from datetime import datetime

import pandas as pd
import streamlit as st

from src.data_loader import (
  download_market_data,
  get_sp500_tickers,
)
from src.factors import calculate_out_of_sample_factor_scores
from src.metrics import (
  build_risk_return_chart,
  calculate_asset_metrics,
  normalize_prices,
)
from src.portfolio import (
  build_portfolio_diagnosis,
  calculate_evaluation_period_portfolio,
)
from src.ranking import (
  RankingUnavailableError,
  get_latest_complete_nyse_session,
  load_home_ranking_with_fallback,
)


# ============================================================
# Configuração geral
# ============================================================

st.set_page_config(
  page_title="US Quant Factor Dashboard",
  page_icon="📊",
  layout="wide",
)


HOME_RANKING_OPTIONS = [10, 20, 50]
HOME_RANKING_MAX = max(HOME_RANKING_OPTIONS)
HOME_RANKING_CACHE_TTL = 3600


# ============================================================
# Cache do ranking atual
# ============================================================

@st.cache_data(
  ttl=HOME_RANKING_CACHE_TTL,
  show_spinner=False,
)
def get_cached_home_ranking(session_key):
  """
  Calcula e mantém em cache o ranking multifatorial atual.

  O ranking máximo retornado é Top 50.
  A interface pode derivar Top 10 e Top 20 sem recalcular
  fatores ou baixar novamente os dados.
  """

  return load_home_ranking_with_fallback(
    max_top_n=HOME_RANKING_MAX,
  )


# ============================================================
# Ranking Multifatorial Atual
# ============================================================

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
    get_cached_home_ranking.clear()
    download_market_data.clear()
    st.rerun()

  try:
    # A chave muda após cada fechamento da NYSE, invalidando também
    # um cache ainda válido quando a página for executada novamente.
    session_key = get_latest_complete_nyse_session().date().isoformat()
    with st.spinner("Calculando ranking multifatorial mais recente..."):
      latest_ranking, ranking_info = get_cached_home_ranking(session_key)
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


# ============================================================
# Sidebar da análise personalizada
# ============================================================

def render_sidebar(sp500_df):
  """
  Renderiza as configurações utilizadas pela análise
  personalizada existente no dashboard.
  """

  sector_options = [
    "Todos",
    *sorted(
      sp500_df["sector"]
      .dropna()
      .unique()
      .tolist()
    ),
  ]

  with st.sidebar:
    st.header("Configurações")

    selected_sector = st.selectbox(
      "Filtrar por setor",
      options=sector_options,
      key="selected_sector",
    )

    if selected_sector == "Todos":
      filtered_sp500_df = sp500_df.copy()

    else:
      filtered_sp500_df = sp500_df[
        sp500_df["sector"]
        == selected_sector
      ].copy()

    tickers_list = (
      filtered_sp500_df["ticker"]
      .dropna()
      .astype(str)
      .tolist()
    )

    default_tickers = [
      ticker
      for ticker in [
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "GOOGL",
      ]
      if ticker in tickers_list
    ]

    if not default_tickers:
      default_tickers = tickers_list[:5]

    selected_tickers = st.multiselect(
      "Selecione as ações",
      options=tickers_list,
      default=default_tickers,
      key=(
        f"selected_tickers_"
        f"{selected_sector}"
      ),
    )

    start_date = st.date_input(
      "Data inicial da avaliação",
      value=datetime(2020, 1, 1),
    )

    end_date = st.date_input(
      "Data final da avaliação",
      value=datetime.today(),
    )

    st.caption(
      "O ranking Top N será formado usando dados "
      "anteriores à data inicial da avaliação."
    )

    show_spy = st.checkbox(
      "Exibir SPY no gráfico",
      value=True,
    )

    st.markdown("---")

    # --------------------------------------------------------
    # Top N da análise personalizada
    # --------------------------------------------------------

    selected_count = len(
      selected_tickers
    )

    if selected_count == 0:
      top_n_quant = 1

      st.info(
        "Selecione pelo menos uma ação "
        "para calcular o Top Ranking."
      )

    elif selected_count == 1:
      top_n_quant = 1

      st.info(
        "Apenas uma ação disponível no setor. "
        "O Top Ranking será 1."
      )

    else:
      top_n_quant = st.slider(
        "Quantidade de ações no Top Ranking",
        min_value=1,
        max_value=selected_count,
        value=min(
          10,
          selected_count,
        ),
        key=(
          f"top_n_quant_"
          f"{selected_sector}_"
          f"{selected_count}"
        ),
      )

    # --------------------------------------------------------
    # Pesos
    # --------------------------------------------------------

    st.markdown("---")
    st.subheader("Pesos dos Fatores")

    momentum_weight = st.slider(
      "Peso Momentum",
      min_value=0,
      max_value=100,
      value=40,
    )

    risk_weight = st.slider(
      "Peso Baixo Risco",
      min_value=0,
      max_value=100,
      value=35,
    )

    liquidity_weight = st.slider(
      "Peso Liquidez",
      min_value=0,
      max_value=100,
      value=25,
    )

    total_weight = (
      momentum_weight
      + risk_weight
      + liquidity_weight
    )

    weights_are_valid = (
      total_weight > 0
    )

    if not weights_are_valid:
      st.warning(
        "Defina pelo menos um peso "
        "maior do que zero."
      )

    else:
      st.caption(
        f"Distribuição atual: "
        f"Momentum "
        f"{momentum_weight / total_weight:.0%} | "
        f"Risco "
        f"{risk_weight / total_weight:.0%} | "
        f"Liquidez "
        f"{liquidity_weight / total_weight:.0%}"
      )

    # --------------------------------------------------------
    # Visualização
    # --------------------------------------------------------

    st.markdown("---")
    st.subheader("Visualização")

    chart_mode = st.selectbox(
      "Modo gráfico",
      options=[
        "Apenas carteiras e SPY",
        "Carteiras + ações do Top Ranking",
        (
          "Carteiras + todas as ações "
          "selecionadas"
        ),
      ],
    )

  return {
    "selected_sector": selected_sector,
    "selected_tickers": selected_tickers,
    "start_date": start_date,
    "end_date": end_date,
    "show_spy": show_spy,
    "top_n_quant": top_n_quant,
    "momentum_weight": momentum_weight,
    "risk_weight": risk_weight,
    "liquidity_weight": liquidity_weight,
    "weights_are_valid": weights_are_valid,
    "chart_mode": chart_mode,
  }


# ============================================================
# Resumo de carteira
# ============================================================

def render_portfolio_summary(
  title,
  portfolio,
  count_label,
  count_value,
  empty_message,
):
  """
  Exibe as métricas principais de uma carteira.
  """

  st.subheader(title)

  if not portfolio:
    st.warning(
      empty_message
    )
    return

  col1, col2, col3, col4 = (
    st.columns(4)
  )

  col1.metric(
    "Retorno Total",
    f"{portfolio['total_return']:.2%}",
  )

  col2.metric(
    "CAGR",
    f"{portfolio['cagr']:.2%}",
  )

  col3.metric(
    "Volatilidade",
    f"{portfolio['volatility']:.2%}",
  )

  col4.metric(
    "Max Drawdown",
    f"{portfolio['max_drawdown']:.2%}",
  )

  col5, col6 = st.columns(2)

  col5.metric(
    "Sharpe Ratio",
    f"{portfolio['sharpe']:.2f}",
  )

  col6.metric(
    count_label,
    count_value,
  )


# ============================================================
# Diagnóstico da carteira quantitativa
# ============================================================

def render_quant_diagnosis(
  quant_portfolio,
  metrics,
):
  """
  Exibe o diagnóstico comparativo entre
  carteira quantitativa e SPY.
  """

  diagnosis_df, diagnosis_summary = (
    build_portfolio_diagnosis(
      portfolio=quant_portfolio,
      metrics=metrics,
      benchmark="SPY",
    )
  )

  if diagnosis_df is None:
    st.warning(
      diagnosis_summary
    )
    return

  st.info(
    diagnosis_summary
  )

  st.dataframe(
    diagnosis_df,
    use_container_width=True,
  )

  better_count = (
    diagnosis_df["Resultado"]
    == "Melhor"
  ).sum()

  if better_count >= 3:
    st.success(
      "A carteira quantitativa apresentou "
      "um resultado forte em relação ao SPY."
    )

  elif better_count == 2:
    st.warning(
      "A carteira quantitativa teve resultado "
      "equilibrado. Vale analisar o risco "
      "antes de decidir."
    )

  else:
    st.error(
      "A carteira quantitativa ficou fraca "
      "em relação ao SPY neste período."
    )


# ============================================================
# Aplicação
# ============================================================

def main():
  st.title(
    "US Quant Factor Dashboard"
  )

  # ----------------------------------------------------------
  # Universo
  # ----------------------------------------------------------

  sp500_df = get_sp500_tickers()

  sp500_df["sector"] = (
    sp500_df["sector"]
    .fillna("Sem setor")
  )

  # ----------------------------------------------------------
  # Sidebar
  # ----------------------------------------------------------

  config = render_sidebar(
    sp500_df
  )

  # ----------------------------------------------------------
  # Ranking automático da Home
  # ----------------------------------------------------------

  render_latest_ranking_section()

  st.markdown("---")

  st.header(
    "Análise Personalizada"
  )

  # ----------------------------------------------------------
  # Validações iniciais
  # ----------------------------------------------------------

  selected_tickers = (
    config["selected_tickers"]
  )

  if not selected_tickers:
    st.info(
      "Selecione pelo menos uma ação "
      "na barra lateral."
    )
    return

  if not config[
    "weights_are_valid"
  ]:
    st.warning(
      "A análise personalizada requer "
      "pelo menos um peso de fator "
      "maior que zero."
    )
    return

  evaluation_start = pd.Timestamp(
    config["start_date"]
  )

  evaluation_end = pd.Timestamp(
    config["end_date"]
  )

  if (
    evaluation_end
    <= evaluation_start
  ):
    st.error(
      "A data final deve ser posterior "
      "à data inicial."
    )
    return

  # ----------------------------------------------------------
  # Download da análise personalizada
  # ----------------------------------------------------------

  download_tickers = (
    selected_tickers.copy()
  )

  if "SPY" not in download_tickers:
    download_tickers.append(
      "SPY"
    )

  formation_download_start = (
    evaluation_start
    - pd.DateOffset(
      months=18
    )
  )

  prices, volumes = (
    download_market_data(
      tickers=download_tickers,
      start_date=formation_download_start,
      end_date=config["end_date"],
    )
  )

  if prices.empty:
    st.error(
      "Não foi possível baixar os dados. "
      "Verifique os tickers ou o "
      "período escolhido."
    )
    return

  # ----------------------------------------------------------
  # Período de avaliação
  # ----------------------------------------------------------

  evaluation_prices = prices.loc[
    (
      prices.index
      >= evaluation_start
    )
    & (
      prices.index
      <= evaluation_end
    )
  ].copy()

  if evaluation_prices.empty:
    st.error(
      "Não existem dados disponíveis "
      "no período de avaliação."
    )
    return

  available_selected_tickers = [
    ticker
    for ticker in selected_tickers
    if ticker in prices.columns
  ]

  if "SPY" not in prices.columns:
    st.error(
      "Não foi possível obter os dados "
      "do SPY. O benchmark é necessário "
      "para calcular o fator de baixo risco."
    )
    return

  if not available_selected_tickers:
    st.error(
      "Nenhum dos tickers selecionados "
      "retornou dados válidos."
    )
    return

  # ----------------------------------------------------------
  # Métricas
  # ----------------------------------------------------------

  metrics = calculate_asset_metrics(
    evaluation_prices
  )

  normalized_prices = (
    normalize_prices(
      evaluation_prices
    )
  )

  # ----------------------------------------------------------
  # Carteira manual
  # ----------------------------------------------------------

  manual_portfolio = (
    calculate_evaluation_period_portfolio(
      prices=prices,
      tickers=available_selected_tickers,
      evaluation_start=evaluation_start,
      evaluation_end=evaluation_end,
    )
  )

  # ----------------------------------------------------------
  # Ranking OOS personalizado
  # ----------------------------------------------------------

  try:
    factor_scores = (
      calculate_out_of_sample_factor_scores(
        prices=prices,
        volumes=volumes,
        evaluation_start=evaluation_start,
        benchmark="SPY",
        momentum_weight=(
          config["momentum_weight"]
        ),
        risk_weight=(
          config["risk_weight"]
        ),
        liquidity_weight=(
          config["liquidity_weight"]
        ),
      )
    )

  except ValueError as error:
    st.error(
      str(error)
    )
    return

  ranking_view = (
    factor_scores.copy()
  )

  ranking_view = ranking_view.drop(
    index="SPY",
    errors="ignore",
  )

  ranking_view = ranking_view.dropna(
    subset=[
      "score_preliminar"
    ]
  )

  if ranking_view.empty:
    st.warning(
      "O ranking não gerou ações válidas "
      "para os filtros atuais. "
      "Tente aumentar o período de análise, "
      "reduzir a quantidade de ações "
      "ou verificar os dados baixados."
    )

    with st.expander(
      "Diagnóstico dos dados"
    ):
      st.write(
        "Tickers selecionados:",
        selected_tickers,
      )

      st.write(
        "Colunas de preços baixadas:",
        list(
          prices.columns
        ),
      )

      st.write(
        "Colunas de volume baixadas:",
        list(
          volumes.columns
        ),
      )

      st.dataframe(
        factor_scores
      )

    return

  top_n_quant = min(
    config["top_n_quant"],
    len(ranking_view),
  )

  top_quant_tickers = (
    ranking_view
    .head(top_n_quant)
    .index
    .tolist()
  )

  top_quant_tickers = [
    str(ticker)
    for ticker in top_quant_tickers
    if isinstance(
      ticker,
      str,
    )
  ]

  # ----------------------------------------------------------
  # Carteira quantitativa
  # ----------------------------------------------------------

  quant_portfolio = (
    calculate_evaluation_period_portfolio(
      prices=prices,
      tickers=top_quant_tickers,
      evaluation_start=evaluation_start,
      evaluation_end=evaluation_end,
    )
  )

  st.caption(
    f"Ranking formado com dados anteriores a "
    f"{evaluation_start.strftime('%d/%m/%Y')} "
    f"| Avaliação: "
    f"{evaluation_start.strftime('%d/%m/%Y')} "
    f"até "
    f"{evaluation_end.strftime('%d/%m/%Y')} "
    f"| Top {top_n_quant} ações"
  )

  # ----------------------------------------------------------
  # Resumo das carteiras
  # ----------------------------------------------------------

  render_portfolio_summary(
    title=(
      "Resumo da Carteira Manual "
      "Equal Weight"
    ),
    portfolio=manual_portfolio,
    count_label=(
      "Quantidade de Ações"
    ),
    count_value=len(
      available_selected_tickers
    ),
    empty_message=(
      "Não foi possível calcular "
      "a carteira manual com "
      "os dados disponíveis."
    ),
  )

  render_portfolio_summary(
    title=(
      "Resumo da Carteira Quantitativa"
    ),
    portfolio=quant_portfolio,
    count_label=(
      "Ações no Top Ranking"
    ),
    count_value=len(
      top_quant_tickers
    ),
    empty_message=(
      "Não foi possível calcular "
      "a carteira quantitativa."
    ),
  )

  # ----------------------------------------------------------
  # Diagnóstico
  # ----------------------------------------------------------

  render_quant_diagnosis(
    quant_portfolio=quant_portfolio,
    metrics=metrics,
  )

  # ----------------------------------------------------------
  # Desempenho relativo
  # ----------------------------------------------------------

  st.subheader(
    "Desempenho Relativo"
  )

  performance_df = pd.DataFrame(
    index=normalized_prices.index
  )

  if (
    config["show_spy"]
    and "SPY"
    in normalized_prices.columns
  ):
    performance_df["SPY"] = (
      normalized_prices["SPY"]
    )

  chart_mode = (
    config["chart_mode"]
  )

  if (
    chart_mode
    == (
      "Carteiras + todas as ações "
      "selecionadas"
    )
  ):
    assets_columns = [
      ticker
      for ticker
      in available_selected_tickers
      if (
        isinstance(
          ticker,
          str,
        )
        and ticker
        in normalized_prices.columns
      )
    ]

    if assets_columns:
      performance_df = (
        performance_df.join(
          normalized_prices[
            assets_columns
          ],
          how="left",
        )
      )

  elif (
    chart_mode
    == (
      "Carteiras + ações "
      "do Top Ranking"
    )
  ):
    top_assets_columns = [
      ticker
      for ticker
      in top_quant_tickers
      if (
        isinstance(
          ticker,
          str,
        )
        and ticker
        in normalized_prices.columns
      )
    ]

    if top_assets_columns:
      performance_df = (
        performance_df.join(
          normalized_prices[
            top_assets_columns
          ],
          how="left",
        )
      )

  if manual_portfolio:
    performance_df[
      "Carteira Manual Equal Weight"
    ] = manual_portfolio["curve"]

  if quant_portfolio:
    performance_df[
      f"Carteira Quant Top "
      f"{top_n_quant}"
    ] = quant_portfolio["curve"]

  if performance_df.empty:
    st.warning(
      "Nenhum dado disponível "
      "para exibir no gráfico."
    )

  else:
    st.line_chart(
      performance_df
    )

  # ----------------------------------------------------------
  # Métricas por ativo
  # ----------------------------------------------------------

  st.subheader(
    "Métricas por Ativo"
  )

  st.dataframe(
    metrics.style.format(
      {
        "Retorno Total": "{:.2%}",
        "CAGR": "{:.2%}",
        "Volatilidade": "{:.2%}",
        "Sharpe": "{:.2f}",
        "Max Drawdown": "{:.2%}",
      }
    ),
    use_container_width=True,
  )

  # ----------------------------------------------------------
  # Risco x Retorno
  # ----------------------------------------------------------

  st.subheader(
    "Risco x Retorno"
  )

  fig = build_risk_return_chart(
    metrics
  )

  st.plotly_chart(
    fig,
    use_container_width=True,
  )

  # ----------------------------------------------------------
  # Empresas selecionadas
  # ----------------------------------------------------------

  st.subheader(
    "Empresas Selecionadas"
  )

  selected_info = sp500_df[
    sp500_df["ticker"].isin(
      available_selected_tickers
    )
  ]

  st.dataframe(
    selected_info,
    use_container_width=True,
  )

  # ----------------------------------------------------------
  # Aviso
  # ----------------------------------------------------------

  st.markdown("---")

  st.caption(
    "Aviso: este projeto é educacional e não representa "
    "recomendação de investimento. "
    "A lista atual de ações pode gerar survivorship bias "
    "em análises históricas. "
    "O ranking atual é preliminar e ainda não inclui "
    "fatores fundamentalistas como valor e qualidade."
  )


if __name__ == "__main__":
  main()