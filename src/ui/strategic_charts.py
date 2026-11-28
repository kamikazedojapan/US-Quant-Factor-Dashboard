"""Gráficos executivos (Plotly), separados de dados e de Streamlit."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.strategic_analytics import (
    BENCHMARK,
    STRATEGY,
    drawdown_series,
    growth_index,
    monthly_compounded_returns,
    rolling_volatility,
)

PURPLE = "#A78BFA"
BLUE = "#38BDF8"
PALETTE = {STRATEGY: PURPLE, BENCHMARK: BLUE}
BG = "#0B1220"
TEXT = "#F8FAFC"
GRID = "#27344A"


def _style(fig: go.Figure, *, height: int = 350, percent: bool = False) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(color=TEXT),
        margin=dict(l=12, r=12, t=30, b=30),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.15, x=0),
        xaxis=dict(gridcolor=GRID),
        yaxis=dict(gridcolor=GRID, tickformat=".0%" if percent else None),
    )
    return fig


def performance_chart(returns: pd.DataFrame) -> go.Figure:
    series = growth_index(returns)
    fig = go.Figure()
    for column in series.columns:
        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series[column],
                mode="lines",
                name=column,
                line=dict(color=PALETTE.get(column, "#CBD5E1"), width=2.5),
                hovertemplate="%{x|%d/%m/%Y}<br>Índice: %{y:.2f}<extra>%{fullData.name}</extra>",
            )
        )
    fig.update_yaxes(title_text="Patrimônio hipotético (base 100)")
    return _style(fig)


def drawdown_chart(returns: pd.DataFrame) -> go.Figure:
    series = drawdown_series(returns)
    fig = go.Figure()
    for column in series.columns:
        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series[column],
                mode="lines",
                name=column,
                line=dict(color=PALETTE.get(column, "#CBD5E1"), width=2),
                fill="tozeroy" if column == STRATEGY else None,
                hovertemplate="%{x|%d/%m/%Y}<br>Drawdown: %{y:.2%}<extra>%{fullData.name}</extra>",
            )
        )
    fig.update_yaxes(title_text="Queda desde o pico")
    return _style(fig, percent=True)


def volatility_chart(returns: pd.DataFrame, window: int = 63) -> go.Figure:
    series = rolling_volatility(returns, window=window)
    fig = go.Figure()
    for column in series.columns:
        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series[column],
                mode="lines",
                name=column,
                line=dict(color=PALETTE.get(column, "#CBD5E1"), width=2),
                hovertemplate="%{x|%d/%m/%Y}<br>Volatilidade: %{y:.1%}<extra>%{fullData.name}</extra>",
            )
        )
    fig.update_yaxes(title_text=f"Volatilidade anualizada ({window} pregões)")
    return _style(fig, percent=True)


def monthly_heatmap(returns: pd.DataFrame, asset: str = STRATEGY) -> go.Figure:
    if asset not in returns.columns:
        raise ValueError(f"Série não encontrada: {asset}")
    monthly = monthly_compounded_returns(returns)[asset]
    grid = pd.DataFrame(
        {"ano": monthly.index.year, "mes": monthly.index.month, "retorno": monthly.to_numpy()}
    ).pivot(index="ano", columns="mes", values="retorno")
    grid = grid.reindex(columns=range(1, 13))
    months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    z = grid.to_numpy(dtype=float)
    fig = go.Figure(
        go.Heatmap(
            x=months,
            y=[str(v) for v in grid.index],
            z=z,
            zmid=0,
            colorscale=[[0, "#BE123C"], [0.5, "#243047"], [1, "#0D9488"]],
            colorbar=dict(title="Retorno", tickformat=".0%"),
            hovertemplate="%{y} · %{x}<br>Retorno: %{z:.2%}<extra></extra>",
            xgap=3,
            ygap=3,
        )
    )
    fig.update_yaxes(title_text="Ano", autorange="reversed")
    return _style(fig, height=max(260, 70 + 40 * len(grid.index)))
