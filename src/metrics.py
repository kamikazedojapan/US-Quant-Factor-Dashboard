import numpy as np
import pandas as pd
import plotly.express as px

def calculate_asset_metrics(prices):
    """
    Calcula métricas individuais para cada ativo.
    """
    metrics = []

    for ticker in prices.columns:
        series = prices[ticker].dropna()

        if len(series) < 2:
            continue

        returns = series.pct_change().dropna()

        if returns.empty:
            continue

        first_price = series.iloc[0]
        last_price = series.iloc[-1]

        total_return = (last_price / first_price) - 1

        days = (series.index[-1] - series.index[0]).days
        years = days / 365 if days > 0 else np.nan

        if years and years > 0:
            cagr = (last_price / first_price) ** (1 / years) - 1
        else:
            cagr = np.nan

        return_mean = returns.mean()
        return_std = returns.std()

        volatility = returns.std() * np.sqrt(252)

        if pd.notna(return_std) and return_std != 0:
          sharpe = (
            return_mean
            / return_std
            * np.sqrt(252)
          )
        else:
          sharpe = np.nan

        normalized = series / first_price
        drawdown = normalized / normalized.cummax() - 1
        max_drawdown = drawdown.min()

        metrics.append(
            {
                "Ticker": ticker,
                "Retorno Total": total_return,
                "CAGR": cagr,
                "Volatilidade": volatility,
                "Sharpe": sharpe,
                "Max Drawdown": max_drawdown,
            }
        )

    return pd.DataFrame(metrics)


def normalize_prices(prices):
    """
    Normaliza os preços para base 100.
    """
    normalized = pd.DataFrame(index=prices.index)

    for ticker in prices.columns:
        series = prices[ticker].dropna()

        if series.empty:
            continue

        normalized[ticker] = 100 * prices[ticker] / series.iloc[0]

    return normalized

def build_risk_return_chart(metrics):
    """
    Cria gráfico de risco x retorno.
    """
    fig = px.scatter(
        metrics,
        x="Volatilidade",
        y="CAGR",
        text="Ticker",
        color="Sharpe",
        title="Risco x Retorno",
    )

    fig.update_traces(
        marker=dict(size=24),
        textposition="top center",
    )

    fig.update_layout(
        xaxis_tickformat=".0%",
        yaxis_tickformat=".0%",
        height=600,
    )

    return fig