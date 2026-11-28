"""Componentes de identidade visual do Dashboard."""

from html import escape

import streamlit as st


HERO_STYLES = """
<style>
.uqf-hero {
    background: linear-gradient(
        120deg, #142339 0%, #17152F 100%
    );
    border: 1px solid #30304F;
    border-left: 4px solid #8B5CF6;
    border-radius: 18px;
    padding: clamp(20px, 4vw, 36px);
    margin-bottom: 24px;
    animation: uqf-enter 0.45s ease-out both;
}

.uqf-hero__label {
    color: #C4B5FD;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.uqf-hero h1 {
    color: #F8FAFC;
    font-size: clamp(1.8rem, 4vw, 2.6rem);
    line-height: 1.2;
    margin: 12px 0;
}

.uqf-hero p {
    color: #CBD5E1;
    font-size: 1rem;
    line-height: 1.6;
    margin: 0;
    max-width: 680px;
}

@keyframes uqf-enter {
    from {
        opacity: 0;
        transform: translateY(8px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@media (prefers-reduced-motion: reduce) {
    .uqf-hero {
        animation: none;
    }
}
</style>
"""


def render_page_header(title, description, label):
    """Renderiza cabeçalho reutilizável e responsivo."""
    st.html(
        HERO_STYLES
        + f"""
        <header class="uqf-hero">
            <div class="uqf-hero__label">
                {escape(label)}
            </div>
            <h1>{escape(title)}</h1>
            <p>{escape(description)}</p>
        </header>
        """
    )