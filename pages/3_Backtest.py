from datetime import datetime

import pandas as pd
import streamlit as st

from src.backtester import run_walk_forward_backtest
from src.data_loader import download_market_data, get_sp500_tickers
from src.universe import select_balanced_tickers_by_sector

st.set_page_config(
  page_title="Backtest",
  page_icon="🧪",
  layout="wide",
)

st.title("Backtest Walk-Forward")
st.caption(
  "Simulação histórica do modelo quantitativo com ranking fora da amostra, "
  "rebalanceamento periódico, custos, slippage e comparação com o benchmark (SPY)"
)

sp500_df = get_sp500_tickers()
sp500_df["sector"] = sp500_df["sector"].fillna("Sem setor")

sector_options = ["Todos"] + sorted(sp500_df["sector"].dropna().unique().tolist())

with st.sidebar:
  universe_size_options = {
    "Manual": None,
    "Rápido - 10 ações": 10,
    "Médio - 25 ações": 25,
    "Amplo - 50 ações": 50,
    "Grande - 100 ações": 100,
    "Enorme - 150 ações": 150,
    "Institucional - 200 ações": 200,
    "S&P amplo - 300 ações": 300,
    "S&P quase completo - 400 ações": 400,
    "S&P 500 - todas": "all",
  }

  st.header("Configurações de Backtest")
  selected_sector = st.selectbox(
    "Filtrar por setor",
    options=sector_options,
    key="backtest_selected_sector",
  )

  if selected_sector == "Todos":
    filtered_sp500_df = sp500_df.copy()
  else:
    filtered_sp500_df = sp500_df[sp500_df["sector"] == selected_sector].copy()

  tickers_list = filtered_sp500_df["ticker"].dropna().astype(str).tolist()

  if not tickers_list:
    st.warning("Nenhuma ação foi encontrada para o setor selecionado.")
    st.stop()

  default_tickers = [
    ticker
    for ticker in [
      "AAPL",
      "MSFT",
      "NVDA",
      "AMZN",
      "GOOGL",
      "META",
      "AVGO",
      "JPM",
      "LLY",
      "V",
    ]
    if ticker in tickers_list
  ]

  if not default_tickers:
    default_tickers = tickers_list[:10]

  universe_mode = st.selectbox(
    "Tamanho do universo",
    options=list(universe_size_options.keys()),
    key="backtest_universe_mode",
  )

  selected_universe_size = universe_size_options[universe_mode]

  if selected_universe_size is None:
    selected_tickers = st.multiselect(
      "Selecione as ações do universo",
      options=tickers_list,
      default=default_tickers,
      key=f"backtest_selected_tickers_{selected_sector}",
    )

  elif selected_universe_size == "all":
    selected_tickers = tickers_list

  else:
    selected_tickers = select_balanced_tickers_by_sector(
      stocks_df=filtered_sp500_df,
      max_tickers=selected_universe_size,
    )

  st.caption(f"{len(selected_tickers)} ações no universo selecionado.")

  if len(selected_tickers) >= 100:
    st.warning(
      "Universos com 100 ou mais ações podem deixar o download e o backtest "
      "mais lentos, mesmo com cache e download em blocos."
    )

  st.markdown("---")

  start_date = st.date_input(
    "Data inicial do backtest",
    value=datetime(2020, 1, 1),
    key="backtest_start_date",
  )

  end_date = st.date_input(
    "Data final do backtest",
    value=datetime.today(),
    key="backtest_end_date",
  )

  frequency_option = st.selectbox(
    "Frequência do rebalanceamento",
    options=[
      "Mensal",
      "Trimestral",
    ],
    key="backtest_frequency_option",
  )

  frequency = "M" if frequency_option == "Mensal" else "Q"

  st.markdown("---")

  selected_count = len(selected_tickers)

  if selected_count == 0:
    top_n = 1
    st.info("Informe pelo menos uma ação para executar o backtest.")
  elif selected_count == 1:
    top_n = 1
    st.info("Apenas uma ação selecionada. O top N será 1.")
  else:
    top_n = st.slider(
      "Quantidade de ações na carteira Top N",
      min_value=1,
      max_value=selected_count,
      value=min(10, selected_count),
      key=f"backtest_top_n_{selected_sector}_{selected_count}",
    )

  st.markdown("---")
  st.subheader("Peso dos fatores")

  momentum_weight = st.slider(
    "Peso Momentum",
    min_value=0,
    max_value=100,
    value=40,
    key="backtest_momentum_weight",
  )

  risk_weight = st.slider(
    "Peso Baixo Risco",
    min_value=0,
    max_value=100,
    value=35,
    key="backtest_risk_weight",
  )

  liquidity_weight = st.slider(
    "Peso Liquidez",
    min_value=0,
    max_value=100,
    value=25,
    key="backtest_liquidity_weight",
  )

  total_weight = momentum_weight + risk_weight + liquidity_weight

  if total_weight == 0:
    st.warning("Defina pelo menos um peso maior do que zero.")
    st.stop()

  st.caption(
    f"Distribuição atual: "
    f"Momentum {momentum_weight / total_weight:.0%} | "
    f"Risco {risk_weight / total_weight:.0%} | "
    f"Liquidez {liquidity_weight / total_weight:.0%}"
  )

  st.subheader("Custos")

  transaction_cost_pct = st.number_input(
    "Custo de transação (%)",
    min_value=0.0,
    max_value=5.0,
    value=0.10,
    step=0.05,
    key="backtest_transaction_cost_pct",
  )

  slippage_pct = st.number_input(
    "Slippage (%)",
    min_value=0.0,
    max_value=5.0,
    value=0.10,
    step=0.05,
    key="backtest_slippage_pct",
  )

  run_backtest = st.button(
    "Executar backtest",
    type="primary",
    key="run_backtest_button",
  )

if not run_backtest:
  st.info(
    "Configure o universo, o período, pesos, custos e clique em "
    "'Executar backtest' para iniciar a simulação."
  )
  st.stop()

if not selected_tickers:
  st.info("Selecione pelo menos uma ação na barra lateral.")
  st.stop()

backtest_start = pd.Timestamp(start_date)
backtest_end = pd.Timestamp(end_date)

if backtest_end <= backtest_start:
  st.error("A data final deve ser posterior à data inicial.")
  st.stop()

download_tickers = sorted(set(selected_tickers + ["SPY"]))

formation_download_start = backtest_start - pd.DateOffset(months=18)

with st.spinner("Baixando os dados de mercado..."):
  prices, volumes = download_market_data(
    tickers=download_tickers,
    start_date=formation_download_start,
    end_date=backtest_end,
  )

if prices.empty:
  st.error(
    "Não foi possível baixar os dados. Verifique os tickers ou o período escolhido."
  )
  st.stop()

available_selected_tickers = [
  ticker for ticker in selected_tickers if ticker in prices.columns
]

if not available_selected_tickers:
  st.error("Nenhum dos tickers selecionados retornou dados válidos")
  st.stop()

if "SPY" not in prices.columns:
  st.error(
    "Não foi possível obter os dados do SPY. O benchmark é necessário para o backtest."
  )
  st.stop()

top_n = min(top_n, len(available_selected_tickers))

transaction_cost = transaction_cost_pct / 100
slippage = slippage_pct / 100

with st.spinner("Executando o backtest walk-forward..."):
  try:
    result = run_walk_forward_backtest(
      prices=prices,
      volumes=volumes,
      start_date=backtest_start,
      end_date=backtest_end,
      top_n=top_n,
      benchmark="SPY",
      frequency=frequency,
      transaction_cost=transaction_cost,
      slippage=slippage,
      momentum_weight=momentum_weight,
      risk_weight=risk_weight,
      liquidity_weight=liquidity_weight,
    )
  except ValueError as error:
    st.error(str(error))
    st.stop()

performance = result["performance"]
strategy_metrics = result["strategy_metrics"]
benchmark_metrics = result["benchmark_metrics"]
rebalance_log = result["rebalance_log"]

st.subheader("Resumo do Backtest")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Ações do universo", len(available_selected_tickers))
col2.metric("Top N", top_n)
col3.metric("Rebalanceamento", frequency_option)
col4.metric("Benchmark", "SPY")

st.caption(
  f"Ranking calculado fora da amostra usando dados anteriores a cada "
  f"Rebalanceamento. Período testado: "
  f"{backtest_start.strftime('%d/%m/%Y')} até "
  f"{backtest_end.strftime('%d/%m/%Y')}."
)

st.markdown("---")

st.subheader("Estratégia Quant vs SPY")

comparison_df = pd.DataFrame(
  [
    {
      "Métrica": "Retorno Total",
      "Estratégia Quant": f"{strategy_metrics['total_return']:.2%}",
      "SPY": f"{benchmark_metrics['total_return']:.2%}",
    },
    {
      "Métrica": "CAGR",
      "Estratégia Quant": f"{strategy_metrics['cagr']:.2%}",
      "SPY": f"{benchmark_metrics['cagr']:.2%}",
    },
    {
      "Métrica": "Volatilidade",
      "Estratégia Quant": f"{strategy_metrics['volatility']:.2%}",
      "SPY": f"{benchmark_metrics['volatility']:.2%}",
    },
    {
      "Métrica": "Sharpe Ratio",
      "Estratégia Quant": f"{strategy_metrics['sharpe']:.2f}",
      "SPY": f"{benchmark_metrics['sharpe']:.2f}",
    },
    {
      "Métrica": "Max Drawdown",
      "Estratégia Quant": f"{strategy_metrics['max_drawdown']:.2%}",
      "SPY": f"{benchmark_metrics['max_drawdown']:.2%}",
    },
  ]
)

st.dataframe(
  comparison_df,
  use_container_width=True,
  hide_index=True,
)

better_count = 0

if strategy_metrics["cagr"] > benchmark_metrics["cagr"]:
  better_count += 1

if strategy_metrics["sharpe"] > benchmark_metrics["sharpe"]:
  better_count += 1

if strategy_metrics["volatility"] < benchmark_metrics["volatility"]:
  better_count += 1

if strategy_metrics["max_drawdown"] > benchmark_metrics["max_drawdown"]:
  better_count += 1

if better_count >= 3:
  st.success(
    "A estratégia quantitativa apresentou um resultado forte em relação ao SPY"
  )
elif better_count == 2:
  st.warning(
    "A estratégia teve resultado equilibrado. Vale a pena analisar o risco, "
    "turnover e consistência antes de concluir."
  )
else:
  st.error("A estratégia ficou fraca em relação ao SPY neste período.")

st.markdown("---")

st.subheader("Curva de performance")

if performance.empty:
  st.warning("Nenhum dado disponível para exibir no gráfico.")
else:
  st.line_chart(performance)

st.markdown("---")

st.subheader("Turnover e Custos")

if rebalance_log.empty:
  st.warning("Nenhum rebalanceamento foi registrado.")
else:
  average_turnover = rebalance_log["turnover"].mean()
  average_cost = rebalance_log["total_cost_applied"].mean()
  total_rebalances = len(rebalance_log)

  col1, col2, col3 = st.columns(3)

  col1.metric("Rebalanceamentos", total_rebalances)
  col2.metric("Turnover médio", f"{average_turnover:.2%}")
  col3.metric("Custo médio aplicado", f"{average_cost:.2%}")

  formatted_log = rebalance_log.copy()

  formatted_log["rebalance_date"] = pd.to_datetime(
    formatted_log["rebalance_date"]
  ).dt.strftime("%d/%m/%Y")

  formatted_log["next_rebalance_date"] = pd.to_datetime(
    formatted_log["next_rebalance_date"]
  ).dt.strftime("%d/%m/%Y")

  percent_columns = [
    "turnover",
    "transaction_cost",
    "slippage",
    "total_cost_applied",
  ]

  for column in percent_columns:
    if column in formatted_log.columns:
      formatted_log[column] = formatted_log[column].map(lambda value: f"{value:.2%}")

  st.dataframe(
    formatted_log,
    use_container_width=True,
    hide_index=True,
  )

st.markdown("---")

st.subheader("Interpretação")

st.write(
  "Este backtest simula uma estratégia walk-forward. Em cada data de "
  "rebalanceamento, o modelo calcula o ranking usando apenas dados anteriores, "
  "seleciona as ações com maior score preliminar e mantém a carteira até o "
  "próximo rebalanceamento."
)

st.write(
  "A comparação com o SPY mostra se a estratégia quantitativa entregou "
  "melhor retorno ajustado ao risco do que simplesmente acompanhar o índice."
)

st.warning(
  "Mesmo com backtest fora da amostra, esta simulação ainda possui limitações: "
  "usa a lista atual de ações, pode sofrer survivorship bias, usa custos "
  "simplificados e ainda não inclui fatores fundamentalistas como Valor e Qualidade."
)


st.markdown("---")

st.caption(
  "Aviso: este projeto é educacional e não representa recomendação de investimento. "
  "Resultados passados não garantem retornos futuros."
)
