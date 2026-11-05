# Fuentes de fondos, criptoactivos e indicadores

Revisión editorial: **2026-11-04**. Esta ampliación añade **32 documentos y 29 referencias** a la biblioteca. Los IDs corresponden a `src/investiq/knowledge/data/cripto-indicadores.json`. La fecha identifica la revisión, no la publicación ni una actualización automática.

Se consultaron fuentes originales: Investor.gov/SEC, Reserva Federal, documentación de Bitcoin y Ethereum, el centro educativo de Fidelity, FINRA, CME y State Street. Las páginas de protocolos explican su funcionamiento desde sus propios autores; no son una evaluación independiente ni una recomendación de adquirir sus activos. Los textos de la biblioteca son explicaciones propias en español y ejemplos conceptuales.

Los indicadores se presentan con sus limitaciones, sin señales automáticas de compra o venta. El documento ETF/acciones no sostiene superioridad universal ni promete rendimientos. No se copian requisitos regulatorios actuales de day trading, cotizaciones, condiciones de staking ni rentabilidades recientes de las páginas consultadas.

La fuente de sectores permite estudiar cómo se comparan: no se ha incorporado su tabla de resultados ni conectado un proveedor de ranking en vivo. La app reconoce esa falta de datos. La investigación web durante desarrollo no verifica una integración real del agente.

## Inventario

| ID | Fuente original | Autor |
| --- | --- | --- |
| `cme:position-size` | [Proper Position Size](https://www.cmegroup.com/education/courses/trade-and-risk-management/proper-position-size) | CME Group |
| `crypto:bitcoin-basics` | [How does Bitcoin work?](https://bitcoin.org/en/how-it-works) | Bitcoin.org |
| `crypto:custody-sec` | [Crypto Asset Custody Basics for Retail Investors](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/crypto-asset-custody-basics-retail-investors-investor-bulletin-0) | SEC / Investor.gov |
| `crypto:ethereum` | [What is Ethereum?](https://ethereum.org/what-is-ethereum/) | Ethereum.org |
| `crypto:smart-contracts` | [Introduction to smart contracts](https://ethereum.org/smart-contracts/) | Ethereum.org |
| `crypto:stablecoins-fed` | [Primary and Secondary Markets for Stablecoins](https://www.federalreserve.gov/econres/notes/feds-notes/primary-and-secondary-markets-for-stablecoins-20240223.html) | Federal Reserve Board |
| `crypto:staking` | [Ethereum staking](https://ethereum.org/staking/) | Ethereum.org |
| `fidelity:backtesting` | [About Strategy Testing](https://www.fidelity.com/research/backtesting/about.html) | Fidelity Investments |
| `fidelity:backtesting-glossary` | [Strategy Testing glossary](https://www.fidelity.com/research/backtesting/glossary.html) | Fidelity Investments |
| `fidelity:candlesticks` | [How to read a crypto chart](https://www.fidelity.com/learning-center/trading-investing/crypto/how-to-read-a-crypto-chart) | Fidelity Investments |
| `fidelity:fundamentals-learning` | [Fundamental analysis](https://www.fidelity.com/learning-center/trading-investing/fundamental-analysis/analyzing-stock-fundamentals) | Fidelity Investments |
| `fidelity:indicator:adx` | [ADX: How strong is the current trend in stocks?](https://www.fidelity.com/viewpoints/active-investor/average-directional-index-ADX) | Fidelity Investments |
| `fidelity:indicator:atr` | [Average True Range — Fidelity](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/atr) | Fidelity Investments |
| `fidelity:indicator:bollinger-bands` | [Bollinger Bands — Fidelity](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/bollinger-bands) | Fidelity Investments |
| `fidelity:indicator:cci` | [Commodity Channel Index — Fidelity](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/cci) | Fidelity Investments |
| `fidelity:indicator:ema` | [Exponential Moving Average — Fidelity](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/ema) | Fidelity Investments |
| `fidelity:indicator:fast-stochastic` | [Fast Stochastic Oscillator — Fidelity](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/fast-stochastic) | Fidelity Investments |
| `fidelity:indicator:macd` | [Moving Average Convergence/Divergence — Fidelity](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/macd) | Fidelity Investments |
| `fidelity:indicator:obv` | [On Balance Volume — Fidelity](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/obv) | Fidelity Investments |
| `fidelity:indicator:overview` | [Technical Analysis Indicator Guide — Fidelity](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/overview) | Fidelity Investments |
| `fidelity:indicator:rsi` | [Relative Strength Index — Fidelity](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/rsi) | Fidelity Investments |
| `fidelity:indicator:sma` | [Simple Moving Average — Fidelity](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/sma) | Fidelity Investments |
| `fidelity:support-resistance` | [Support and Resistance](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/support-and-resistance) | Fidelity Investments |
| `fidelity:vwap` | [Technical Analysis Session 2 — transcript](https://media.fidelity.com/assets/Fidelity.com_VMS/756/898/TA_Session_2_Transcript.pdf) | Fidelity Investments |
| `finra:intraday-basics` | [Frequent Intraday Trading: Understanding the Basics](https://syndication.finra.org/content/frequent-intraday-trading-understanding-basics) | FINRA |
| `learning:allocation-long-term` | [Asset Allocation and Diversification](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) | SEC / Investor.gov |
| `learning:funds-sec` | [Mutual Funds and ETFs](https://www.investor.gov/sites/investorgov/files/2023-09/mutual-funds-ETFs_2_0.pdf) | SEC / Investor.gov |
| `sec:ratios-learning` | [Beginners Guide to Financial Statements](https://www.sec.gov/reportspubs/investor-publications/investorpubsbegfinstmtguidehtm.html) | U.S. SEC |
| `ssga:sector-tracker-learning` | [Sector tracker](https://www.ssga.com/us/en/intermediary/resources/sector-tracker) | State Street Investment Management |

## Verificación

`python -m investiq.knowledge validate` comprueba estructura, referencias e identidades, sin acceder a Internet. Las pruebas de recuperación y diálogo están en `tests/unit/test_trading_education.py`; requisitos y evidencia en [formacion-trading](../specs/formacion-trading/tasks.md). La verificación con el modelo NVIDIA real sigue pendiente.
