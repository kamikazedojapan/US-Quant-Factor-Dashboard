# US Quant Factor Dashboard

Dashboard quantitativo multifatorial para análise e seleção de ações americanas com base em fatores como **valor**, **qualidade**, **momentum**, **baixo risco** e **liquidez**.

O objetivo do projeto é construir uma ferramenta visual e analítica para ranquear ações do mercado americano, especialmente do universo do **S&P 500**, utilizando uma metodologia baseada em evidências acadêmicas de finanças quantitativas e asset pricing.

> Este projeto tem finalidade educacional e não representa recomendação de investimento.

---

## Objetivo do Projeto

O **US Quant Factor Dashboard** busca transformar dados financeiros em um sistema simples de tomada de decisão quantitativa.

Em vez de escolher ações com base em opinião, notícias ou intuição, o projeto utiliza uma abordagem sistemática:

1. Coletar dados históricos de preços e fundamentos.
2. Calcular indicadores financeiros e estatísticos.
3. Transformar os indicadores em scores padronizados.
4. Combinar os scores em um modelo multifatorial.
5. Gerar um ranking das ações mais atrativas.
6. Montar uma carteira teórica.
7. Comparar o desempenho com um benchmark, como o S&P 500 ou o ETF SPY.

---

## Fundamentação Teórica

A análise quantitativa multifatorial parte da ideia de que certas características das ações estão associadas a retornos esperados superiores no longo prazo.

Este projeto se inspira em estudos clássicos de finanças, como:

* Fama e French — fatores de mercado, tamanho, valor, lucratividade e investimento.
* Jegadeesh e Titman — fator momentum.
* Asness, Moskowitz e Pedersen — valor e momentum em diferentes mercados.
* Asness, Frazzini e Pedersen — fator qualidade.
* Ang, Hodrick, Xing e Zhang — relação entre volatilidade e retorno esperado.
* Harvey, Liu e Zhu — riscos de data mining e excesso de fatores na literatura financeira.

A proposta não é prever exatamente o preço futuro de uma ação, mas construir um ranking baseado em fatores historicamente relevantes.

---

## Fatores Utilizados

O modelo inicial utiliza cinco fatores principais:

| Fator       | Peso | Objetivo                                                              |
| ----------- | ---: | --------------------------------------------------------------------- |
| Valor       |  25% | Encontrar ações baratas em relação aos fundamentos                    |
| Qualidade   |  25% | Identificar empresas lucrativas, eficientes e financeiramente sólidas |
| Momentum    |  25% | Capturar ações com força recente de preço                             |
| Baixo Risco |  15% | Priorizar ativos com menor volatilidade e menores quedas              |
| Liquidez    |  10% | Evitar ações difíceis de negociar                                     |

---

## Fórmula do Score Final

O score final de cada ação será calculado da seguinte forma:

```text
Score Final =
0.25 × Score Valor
+ 0.25 × Score Qualidade
+ 0.25 × Score Momentum
+ 0.15 × Score Baixo Risco
+ 0.10 × Score Liquidez
```

Cada fator será normalizado em uma escala de 0 a 100 usando ranking percentil.

Quanto maior o score final, mais atrativa a ação será considerada pelo modelo.

---

## Indicadores por Fator

### 1. Valor

O fator valor busca identificar ações negociadas a preços baixos em relação aos seus fundamentos.

Indicadores sugeridos:

* P/E — Price to Earnings
* P/B — Price to Book
* EV/EBITDA
* Free Cash Flow Yield
* Dividend Yield

Quanto menor o múltiplo de valuation, melhor o score.
No caso de yields, quanto maior, melhor.

---

### 2. Qualidade

O fator qualidade busca empresas com boa rentabilidade, eficiência operacional e estrutura financeira saudável.

Indicadores sugeridos:

* ROE — Return on Equity
* ROA — Return on Assets
* ROIC — Return on Invested Capital
* Operating Margin
* Net Margin
* Debt to Equity
* Free Cash Flow positivo

Quanto maior a rentabilidade e menor o endividamento, melhor o score.

---

### 3. Momentum

O fator momentum mede a força recente do preço da ação.

Indicadores sugeridos:

* Retorno dos últimos 3 meses
* Retorno dos últimos 6 meses
* Retorno dos últimos 12 meses
* Retorno 12-1 meses, excluindo o último mês

Quanto maior o retorno recente, melhor o score.

---

### 4. Baixo Risco

O fator baixo risco busca reduzir exposição a ações muito instáveis.

Indicadores sugeridos:

* Volatilidade anualizada
* Beta em relação ao S&P 500
* Max Drawdown
* Volatilidade dos últimos 252 pregões

Quanto menor o risco, melhor o score.

---

### 5. Liquidez

O fator liquidez evita ações com baixo volume de negociação.

Indicadores sugeridos:

* Volume médio negociado
* Dollar Volume
* Market Cap
* Número de dias negociados

Quanto maior a liquidez, melhor o score.

---

## Universo Inicial

A primeira versão do projeto utilizará ações do mercado americano, com foco no universo do:

```text
S&P 500
```

O benchmark inicial será:

```text
SPY — SPDR S&P 500 ETF Trust
```

Essa escolha foi feita porque o mercado americano possui melhor disponibilidade de dados, maior liquidez e maior proximidade com a literatura acadêmica usada como base teórica.

---

## Tecnologias Utilizadas

O projeto será desenvolvido em Python com as seguintes bibliotecas:

```text
streamlit
pandas
numpy
yfinance
plotly
scipy
openpyxl
```

Possíveis bibliotecas futuras:

```text
quantstats
statsmodels
scikit-learn
duckdb
sqlalchemy
```

---

## Estrutura do Projeto

```text
us_quant_factor_dashboard/
│
├── app.py
├── requirements.txt
│
├── data/
│   ├── tickers_sp500.csv
│   ├── fundamentals_sample.csv
│   └── cache/
│
├── src/
│   ├── data_loader.py
│   ├── preprocessing.py
│   ├── factors.py
│   ├── scoring.py
│   ├── portfolio.py
│   ├── backtest.py
│   └── metrics.py
│
├── pages/
│   ├── 1_Ranking_Multifatorial.py
│   ├── 2_Analise_Ativo.py
│   ├── 3_Backtest.py
│   └── 4_Metodologia.py
│
└── README.md
```

---

## Funcionalidades Planejadas

### Versão 1.0

* Coleta de preços históricos com `yfinance`.
* Seleção de ações do S&P 500.
* Cálculo de retorno acumulado.
* Cálculo de volatilidade anualizada.
* Cálculo de Sharpe Ratio.
* Cálculo de Max Drawdown.
* Comparação com SPY.
* Gráfico de desempenho relativo.
* Gráfico de risco x retorno.

### Versão 1.1

* Cálculo do fator momentum.
* Cálculo do fator baixo risco.
* Cálculo do fator liquidez.
* Ranking quantitativo parcial.
* Seleção automática das melhores ações por score.

### Versão 1.2

* Inclusão de indicadores fundamentalistas.
* Cálculo do fator valor.
* Cálculo do fator qualidade.
* Score final multifatorial.
* Carteira Top 10 ou Top 20.

### Versão 1.3

* Backtest com rebalanceamento mensal.
* Comparação com benchmark.
* Cálculo de CAGR.
* Cálculo de Sortino Ratio.
* Cálculo de Alpha e Beta.
* Controle de custos de transação.

### Versão 2.0

* Comparação com ETFs fatoriais.
* Validação fora da amostra.
* Análise por setores.
* Exportação dos rankings em CSV ou Excel.
* Dashboard mais completo com múltiplas páginas.

---

## Metodologia

O projeto seguirá a seguinte metodologia:

1. Definir o universo de ações.
2. Coletar dados históricos.
3. Calcular indicadores por fator.
4. Padronizar os indicadores usando percentis.
5. Calcular o score de cada fator.
6. Combinar os fatores no score final.
7. Ordenar as ações pelo score final.
8. Selecionar as ações mais bem classificadas.
9. Montar uma carteira teórica com pesos iguais.
10. Comparar a carteira com o benchmark.
11. Avaliar retorno, risco e drawdown.
12. Documentar limitações e resultados.

---

## Métricas de Performance

As principais métricas avaliadas serão:

| Métrica       | Descrição                                    |
| ------------- | -------------------------------------------- |
| Retorno Total | Retorno acumulado no período                 |
| CAGR          | Retorno anual composto                       |
| Volatilidade  | Oscilação anualizada dos retornos            |
| Sharpe Ratio  | Retorno ajustado ao risco                    |
| Sortino Ratio | Retorno ajustado ao risco negativo           |
| Max Drawdown  | Maior queda acumulada                        |
| Alpha         | Retorno acima do benchmark ajustado ao risco |
| Beta          | Sensibilidade da carteira ao benchmark       |
| Turnover      | Frequência de troca dos ativos               |

---

## Como Rodar o Projeto

Clone o repositório:

```bash
git clone https://github.com/seu-usuario/us_quant_factor_dashboard.git
```

Acesse a pasta do projeto:

```bash
cd us_quant_factor_dashboard
```

Crie e ative um ambiente virtual:

```bash
python -m venv venv
```

No Windows:

```bash
venv\Scripts\activate
```

No Linux ou macOS:

```bash
source venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute o dashboard:

```bash
streamlit run app.py
```

---

## Exemplo de Saída Esperada

O dashboard deverá exibir:

* Ranking multifatorial das ações.
* Score individual por fator.
* Score final.
* Carteira teórica selecionada.
* Retorno acumulado da carteira.
* Comparação com SPY.
* Métricas de risco e retorno.
* Gráficos interativos.

---

## Limitações do Projeto

Esta primeira versão possui algumas limitações importantes:

1. O uso da lista atual do S&P 500 pode gerar survivorship bias.
2. Dados gratuitos podem conter falhas ou lacunas.
3. Indicadores fundamentalistas atuais não substituem dados históricos ponto a ponto.
4. O backtest inicial pode não refletir custos reais de mercado.
5. Resultados passados não garantem retornos futuros.
6. O modelo não considera eventos macroeconômicos, notícias ou mudanças regulatórias.
7. O modelo não deve ser usado isoladamente para decisões reais de investimento.

---

## Aviso Legal

Este projeto é exclusivamente educacional.

Nenhuma informação apresentada neste dashboard deve ser interpretada como recomendação de compra, venda ou manutenção de ativos financeiros.

Antes de tomar decisões de investimento, consulte um profissional qualificado e realize sua própria análise.

---

## Licença

Este projeto pode ser distribuído sob a licença MIT.

---

## Autor

Desenvolvido por Márcio Reis.

Projeto criado como estudo prático de programação, análise quantitativa, finanças e construção de dashboards com Python.
