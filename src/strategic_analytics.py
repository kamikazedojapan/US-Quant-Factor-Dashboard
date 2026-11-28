"""Métricas históricas para decisões estratégicas, sem dependência da interface.

Os retornos diários devem provir de uma simulação temporal legítima ou
séries observadas. Este módulo não produz sinais nem inferência causal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

STRATEGY = "Estratégia Quant"
BENCHMARK = "SPY"
TRADING_DAYS = 252


def align_returns(strategy: pd.Series, benchmark: pd.Series) -> pd.DataFrame:
    """Alinha por pregão; períodos sem dados em ambos são explicitamente excluídos."""
    if not isinstance(strategy, pd.Series) or not isinstance(benchmark, pd.Series):
        raise TypeError("Estratégia e benchmark precisam ser séries pandas.")
    for series in (strategy, benchmark):
        if not isinstance(series.index, pd.DatetimeIndex):
            raise TypeError("O índice dos retornos deve ser DatetimeIndex.")
        if series.index.has_duplicates:
            raise ValueError("Existem datas duplicadas nos retornos.")
    frame = pd.concat(
        [strategy.rename(STRATEGY), benchmark.rename(BENCHMARK)],
        axis=1,
        join="inner",
    ).sort_index()
    for col in frame.columns:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if len(frame) < 2:
        raise ValueError("É necessário ter pelo menos dois pregões comparáveis.")
    if (frame < -1).any().any():
        raise ValueError("Foram encontrados retornos inferiores a -100%.")
    return frame


def growth_index(returns: pd.DataFrame) -> pd.DataFrame:
    """Capital inicial de 100 *antes* do primeiro retorno mostrado."""
    return 100.0 * (1.0 + returns).cumprod()


def drawdown_series(returns: pd.DataFrame) -> pd.DataFrame:
    """Queda ante pico anterior, incluindo o capital inicial de 100."""
    growth = growth_index(returns)
    running_high = growth.cummax().clip(lower=100.0)
    return growth.div(running_high).sub(1.0)


def rolling_volatility(returns: pd.DataFrame, window: int = 63) -> pd.DataFrame:
    """Volatilidade histórica anualizada, com janela integral de pregões."""
    if window < 2:
        raise ValueError("A janela de volatilidade deve ser >= 2.")
    return returns.rolling(window=window, min_periods=window).std() * np.sqrt(
        TRADING_DAYS
    )


def monthly_compounded_returns(returns: pd.DataFrame) -> pd.DataFrame:
    """Retornos mensais compostos; meses sem observações permanecem ausentes."""
    counts = returns.resample("ME").count()
    result = (1 + returns).resample("ME").prod() - 1
    return result.where(counts > 0)


def summary_metrics(returns: pd.DataFrame) -> pd.DataFrame:
    """Resumo comparável sobre *as mesmas datas*, taxa livre de risco assumida 0."""
    dd = drawdown_series(returns)
    rows = {}
    for column in returns.columns:
        series = returns[column]
        n = len(series)
        ending = float((1 + series).prod())
        cagr = ending ** (TRADING_DAYS / n) - 1 if ending > 0 else -1.0
        vol = float(series.std(ddof=1) * np.sqrt(TRADING_DAYS))
        sharpe = float(series.mean() * TRADING_DAYS / vol) if vol > 0 else np.nan
        rows[column] = {
            "Retorno total": ending - 1,
            "CAGR (252 pregões)": cagr,
            "Volatilidade anual": vol,
            "Sharpe (rf=0)": sharpe,
            "Máximo drawdown": float(dd[column].min()),
        }
    return pd.DataFrame.from_dict(rows, orient="index")
