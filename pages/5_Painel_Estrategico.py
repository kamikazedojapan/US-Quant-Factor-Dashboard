"""Painel executivo de histórico: estratégia walk-forward versus SPY.

Esta página só executa downloads e backtest após o usuário clicar em Executar.
"""

from datetime import date

import pandas as pd
import streamlit as st

from src.backtester import run_walk_forward_backtest
from src.data_loader import download_market_data, get_sp500_tickers
from src.strategic_analytics import (
    BENCHMARK,
    STRATEGY,
    align_returns,
    summary_metrics,
)
from src.ui.strategic_charts import (
    drawdown_chart,
    monthly_heatmap,
    performance_chart,
    volatility_chart,
)
from src.universe import select_balanced_tickers_by_sector


st.title("Painel Estratégico | Evidência Histórica")
st.caption(
    "Visão para tomada de decisão: desempenho relativo, risco de perda, "
    "volatilidade e consistência histórica de uma simulação walk-forward."
)

with st.sidebar.expander("Configurar cenário histórico", expanded=True):
    with st.form("strategic_historical_parameters"):
        start_date = st.date_input("Início da avaliação", date(2021, 1, 1))
        end_date = st.date_input("Fim da avaliação", date.today())
        universe_size = st.selectbox("Universo exploratório", [10, 25, 50], index=0)
        top_n = st.slider("Ativos selecionados", min_value=1, max_value=10, value=5)
        frequency_label = st.selectbox("Rebalanceamento", ["Mensal", "Trimestral"])
        transaction_cost_pct = st.number_input(
            "Custo de transação (%)", min_value=0.0, max_value=5.0, value=0.10, step=0.05
        )
        slippage_pct = st.number_input(
            "Slippage (%)", min_value=0.0, max_value=5.0, value=0.10, step=0.05
        )
        submitted = st.form_submit_button("Executar análise histórica", type="primary")

if submitted:
    if end_date <= start_date:
        st.error("O fim deve ser posterior ao início da avaliação.")
        st.stop()
    if end_date > date.today():
        st.error("Não é possível avaliar datas futuras.")
        st.stop()
    try:
        universe = get_sp500_tickers().copy()
        universe["sector"] = universe["sector"].fillna("Sem setor")
        selected_tickers = select_balanced_tickers_by_sector(universe, universe_size)
        if len(selected_tickers) < top_n:
            raise ValueError("Universo insuficiente para a quantidade de ativos solicitada.")

        # End date do yfinance é exclusivo. Baixamos 18 meses de formação
        # antes do início da avaliação sem contar esse histórico como resultado.
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
        formation_start = start - pd.DateOffset(months=18)
        with st.spinner("Baixando preços e executando a simulação fora da amostra..."):
            prices, volumes = download_market_data(
                tickers=selected_tickers + [BENCHMARK],
                start_date=formation_start,
                end_date=end + pd.Timedelta(days=1),
            )
            if prices.empty:
                raise ValueError("Nenhum preço histórico foi encontrado.")
            result = run_walk_forward_backtest(
                prices=prices,
                volumes=volumes,
                start_date=start,
                end_date=end,
                benchmark=BENCHMARK,
                top_n=top_n,
                frequency="M" if frequency_label == "Mensal" else "Q",
                transaction_cost=transaction_cost_pct / 100.0,
                slippage=slippage_pct / 100.0,
                momentum_weight=40,
                risk_weight=35,
                liquidity_weight=25,
            )
            aligned = align_returns(
                result["strategy_returns"], result["benchmark_returns"]
            )
            if len(aligned) < 63:
                raise ValueError(
                    "O histórico comparável tem menos de 63 pregões; "
                    "selecione um intervalo maior."
                )
        # Persistência apenas na sessão atual. Não grava resultados em disco,
        # não reexecuta backtest quando usuário alterna o heatmap.
        st.session_state["strategic_executive_result"] = {
            "returns": aligned,
            "rebalance_log": result["rebalance_log"],
            "universe_size": len(selected_tickers),
            "top_n": top_n,
            "frequency": frequency_label,
            "cost": transaction_cost_pct,
            "slippage": slippage_pct,
        }
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        st.session_state.pop("strategic_executive_result", None)
        st.error(f"Não foi possível concluir a análise: {exc}")
        st.stop()

if "strategic_executive_result" not in st.session_state:
    st.info(
        "Defina um cenário na barra lateral e clique em 'Executar análise histórica'. "
        "Nenhum download ou backtest é iniciado automaticamente."
    )
    st.stop()

saved = st.session_state["strategic_executive_result"]
returns = saved["returns"]
metrics = summary_metrics(returns)
strategy = metrics.loc[STRATEGY]
benchmark = metrics.loc[BENCHMARK]

st.caption(
    f"Período efetivamente comparável: {returns.index.min():%d/%m/%Y}–"
    f"{returns.index.max():%d/%m/%Y} | {len(returns)} pregões | "
    f"Universo: {saved['universe_size']} ativos atuais | Top {saved['top_n']} | "
    f"Rebalanceamento: {saved['frequency']} | Custos: "
    f"{saved['cost']:.2f}% + {saved['slippage']:.2f}% de slippage."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("CAGR estratégia", f"{strategy['CAGR (252 pregões)']:.1%}",
          delta=f"{strategy['CAGR (252 pregões)'] - benchmark['CAGR (252 pregões)']:+.1%} vs SPY")
c2.metric("Sharpe (rf = 0)", f"{strategy['Sharpe (rf=0)']:.2f}")
c3.metric("Pior drawdown", f"{strategy['Máximo drawdown']:.1%}",
          delta=f"{strategy['Máximo drawdown'] - benchmark['Máximo drawdown']:+.1%} vs SPY")
c4.metric("Volatilidade anual", f"{strategy['Volatilidade anual']:.1%}",
          delta=f"{strategy['Volatilidade anual'] - benchmark['Volatilidade anual']:+.1%} vs SPY",
          delta_color="inverse")

st.subheader("1 · Crescimento relativo — a estratégia compensou o risco assumido?")
st.plotly_chart(performance_chart(returns), width="stretch")
st.caption("Séries calculadas dos mesmos pregões; índice 100 antes do primeiro retorno disponível.")

st.subheader("2 · Drawdown — qual foi a profundidade das perdas históricas?")
st.plotly_chart(drawdown_chart(returns), width="stretch")

st.subheader("3 · Volatilidade móvel — quando o risco se intensificou?")
st.plotly_chart(volatility_chart(returns, window=63), width="stretch")

st.subheader("4 · Consistência mensal — em quais períodos ocorreram perdas?")
selected_series = st.radio(
    "Série do mapa mensal", [STRATEGY, BENCHMARK], horizontal=True,
    key="strategic_monthly_series",
)
st.plotly_chart(monthly_heatmap(returns, selected_series), width="stretch")
st.caption("O primeiro e o último mês podem conter apenas parte dos pregões.")

with st.expander("Diagnóstico e rastreabilidade"):
    st.dataframe(metrics.T, width="stretch")
    rebalances = saved["rebalance_log"]
    if not rebalances.empty:
        st.metric("Número de rebalanceamentos", len(rebalances))
        st.metric("Turnover médio (aproximado)",
                  f"{rebalances['turnover'].mean():.1%}")
        st.dataframe(rebalances, width="stretch", hide_index=True)

st.warning(
    "Uso exploratório, não recomendação. A simulação usa constituintes atuais "
    "do S&P 500 (risco de survivorship bias), custos/slippage simplificados, "
    "peso igual e seleção sistemática. O walk-forward reduz vazamento temporal, "
    "mas não elimina seleção ex-post de fatores, sobreajuste ou limitações do "
    "motor de backtest. Não interprete estes resultados como expectativa futura."
)
