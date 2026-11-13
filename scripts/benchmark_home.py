"""Mede latencia do ranking da Home, com dados reais.

Uso (a partir da raiz do repositorio):
    python scripts/benchmark_home.py

Na primeira execucao, o cache dos downloads e limpo deliberadamente para medir
uma busca fria. Na segunda, os dados de mercado sao reutilizados do cache.
Nao cria commits nem modifica arquivos versionados.
"""

from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.ranking as ranking  # noqa: E402
from src.data_loader import download_market_data  # noqa: E402


def measure(label: str) -> bool:
    measurements: dict[str, float] = {"download": 0.0, "scoring": 0.0}
    original_download = ranking.download_market_data
    original_scoring = ranking.calculate_price_volume_factor_scores

    def measured_download(*args, **kwargs):
        start = perf_counter()
        try:
            return original_download(*args, **kwargs)
        finally:
            measurements["download"] += perf_counter() - start

    def measured_scoring(*args, **kwargs):
        start = perf_counter()
        try:
            return original_scoring(*args, **kwargs)
        finally:
            measurements["scoring"] += perf_counter() - start

    ranking.download_market_data = measured_download
    ranking.calculate_price_volume_factor_scores = measured_scoring

    total_start = perf_counter()
    failure: Exception | None = None
    try:
        result, info = ranking.load_latest_multifactor_ranking(max_top_n=50)
    except Exception as exc:  # reporta erros da fonte de dados sem mascarar
        failure = exc
    finally:
        total = perf_counter() - total_start
        ranking.download_market_data = original_download
        ranking.calculate_price_volume_factor_scores = original_scoring

    others = max(0.0, total - measurements["download"] - measurements["scoring"])
    print(f"\n{label}: {total:.2f}s")
    print(f"  download (incluindo cache): {measurements['download']:.2f}s")
    print(f"  scoring:                    {measurements['scoring']:.2f}s")
    print(f"  validacao/outros:           {others:.2f}s")

    if failure is not None:
        print(f"  ERRO: {type(failure).__name__}: {failure}")
        return False

    print(f"  data: {info['as_of_date']}")
    print(f"  universo: {info['universe_size']} | elegiveis: {info['eligible_count']}")
    print(f"  ranking retornado: {len(result)}")
    return True


def main() -> None:
    print("Benchmark do ranking da Home — dados reais")
    print("Limpando apenas o cache dos downloads para uma medicao fria...")
    download_market_data.clear()
    if not measure("1. Execucao fria (download sem cache)"):
        return
    measure("2. Execucao quente (download em cache)")
    print("\nNota: mede o backend do ranking, nao o tempo de renderizacao no navegador.")


if __name__ == "__main__":
    main()
