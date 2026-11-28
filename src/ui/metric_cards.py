"""Indicadores visuais responsivos da Home."""

from html import escape

import streamlit as st


def render_ranking_metrics(
    as_of_date,
    universe_size,
    eligible_count,
    displayed_count,
):
    """Exibe os KPIs sem alterar o cálculo do ranking."""

    metrics = [
        ("Dados até", as_of_date),
        ("Universo", universe_size),
        ("Ações elegíveis", eligible_count),
        ("Ranking exibido", f"Top {displayed_count}"),
    ]

    cards = "".join(
        f"""
        <article class="uqf-kpi">
            <span class="uqf-kpi__label">
                {escape(str(label))}
            </span>
            <strong class="uqf-kpi__value">
                {escape(str(value))}
            </strong>
        </article>
        """
        for label, value in metrics
    )

    st.html(
        """
        <style>
        .uqf-kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 14px;
            margin: 20px 0 24px;
        }

        .uqf-kpi {
            min-width: 0;
            padding: 22px;
            border: 1px solid #303850;
            border-radius: 16px;
            background: #142339;
            transition: border-color .2s ease,
                        transform .2s ease;
        }

        .uqf-kpi:hover {
            border-color: #8B5CF6;
            transform: translateY(-2px);
        }

        .uqf-kpi__label {
            display: block;
            color: #CBD5E1;
            font-size: .85rem;
            margin-bottom: 12px;
        }

        .uqf-kpi__value {
            display: block;
            color: #F8FAFC;
            font-size: clamp(1.3rem, 2vw, 1.9rem);
            font-weight: 700;
            overflow-wrap: anywhere;
        }

        @media (max-width: 1000px) {
            .uqf-kpi-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 600px) {
            .uqf-kpi-grid {
                grid-template-columns: 1fr;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            .uqf-kpi {
                transition: none;
            }

            .uqf-kpi:hover {
                transform: none;
            }
        }
        </style>
        """
        + f"""
        <section class="uqf-kpi-grid"
                 aria-label="Indicadores do ranking">
            {cards}
        </section>
        """
    )