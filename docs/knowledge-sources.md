# Fuentes de la biblioteca educativa

Revisión editorial: **2026-11-04**. La biblioteca incluye **119 documentos**, en **16 categorías**, con **113 referencias** de organismos, emisores y autores originales. Esta fecha indica cuándo se revisó el contenido y su trazabilidad; no es la fecha de publicación de las páginas ni una garantía de actualización posterior. El inventario original de 84 referencias está a continuación; las 29 referencias añadidas para fondos, criptoactivos e indicadores están en [trading-sources.md](trading-sources.md).

Los textos en `src/investiq/knowledge/data/*.json` son explicaciones propias en español y ejemplos conceptuales. No contienen cotizaciones actuales, resultados empresariales actuales ni titulares. Las páginas de origen se consultaron mediante navegación o resultados de búsqueda del dominio oficial; no se realizaron llamadas a proveedores financieros ni al modelo con credenciales reales.

## Criterios editoriales

- Se usan reguladores, organismos públicos, bolsas, administradores de índices, emisores y centros educativos propios de instituciones financieras. Cada sección de un documento hereda sus fuentes explícitas.
- Los materiales comerciales de brókers sirven para confirmar que existen y describir qué consultar. No son rankings independientes ni una recomendación; publicidad y condiciones de la entidad requieren una lectura crítica.
- Las fichas de acciones apuntan a relaciones con inversores y las de ETF a sus emisores. Identifican el instrumento y explican dónde estudiar su documentación; no almacenan valoraciones actuales, pesos, rentabilidades, noticias ni composición vigente.
- Los índices y los ETF son entidades distintas. SPY y QQQ tienen fichas propias; Nasdaq como bolsa se distingue de Nasdaq-100 y Nasdaq Composite.
- Los ejemplos son didácticos, no operaciones reales. La biblioteca no reemplaza los informes, folletos, reguladores ni autoridades fiscales aplicables.

## Límites y mantenimiento

Las condiciones de apertura, tarifas, admisión por país, registros y autorización de intermediarios pueden cambiar. Los ejemplos Interactive Brokers, Charles Schwab y Fidelity deben verificarse para la residencia y entidad legal concretas. BrokerCheck corresponde al ámbito de FINRA en Estados Unidos: no prueba autorización en todos los países. No se infieren el país ni la residencia fiscal de una persona.

No se ofrecen tipos impositivos, mínimos universales para invertir ni selecciones de compra. Las fichas de empresas no prueban su solvencia ni anticipan resultados. El contenido recuperado se trata como información, nunca como instrucciones para el agente. Todas las respuestas de la app conservan «No es asesoría financiera».

Para ampliar o corregir la biblioteca se editan los JSON, se añaden preguntas, fuentes y una fecha de revisión verdadera, y se ejecuta `python -m investiq.knowledge validate`. La validación comprueba el contrato local y las referencias, no vuelve a consultar Internet ni certifica que una página siga disponible. No hay actualización automática de esta biblioteca.

Las fuentes que devolvieron errores o no ofrecían una definición sustantiva no se utilizaron. No se guardaron copias extensas de artículos. Para la correlación se usa la explicación estadística de NIST sobre asociación y causalidad, evitando equiparar correlación negativa con una asociación débil.

## Inventario de fuentes consultadas

Todos los enlaces siguientes son HTTPS y su revisión corresponde al **2026-11-04**. Los IDs coinciden con `sources[].source_id` en los documentos.

### ASIC / Moneysmart

| ID | Fuente oficial |
| --- | --- |
| `asic:return` | [Return — Moneysmart](https://moneysmart.gov.au/glossary/return) |

### Alphabet

| ID | Fuente oficial |
| --- | --- |
| `issuer:googl` | [Alphabet Investor Relations](https://abc.xyz/investor/) |

### Amazon

| ID | Fuente oficial |
| --- | --- |
| `issuer:amzn` | [Amazon.com Investor Relations](https://ir.aboutamazon.com/overview/default.aspx) |

### Apple

| ID | Fuente oficial |
| --- | --- |
| `issuer:aapl` | [Apple Investor Relations](https://investor.apple.com/investor-relations/default.aspx) |

### Berkshire Hathaway

| ID | Fuente oficial |
| --- | --- |
| `issuer:brk-b` | [Berkshire Hathaway sitio corporativo](https://www.berkshirehathaway.com/) |

### BlackRock / iShares

| ID | Fuente oficial |
| --- | --- |
| `issuer:iwm` | [IWM — iShares](https://www.ishares.com/us/products/239710/ishares-russell-2000-etf) |

### Broadcom

| ID | Fuente oficial |
| --- | --- |
| `issuer:avgo` | [Broadcom Investor Center](https://investors.broadcom.com/) |

### CFA Institute

| ID | Fuente oficial |
| --- | --- |
| `cfa:equity-valuation` | [Equity Valuation: Concepts and Basic Tools](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/equity-valuation-concepts-basic-tools) |

### Charles Schwab

| ID | Fuente oficial |
| --- | --- |
| `broker:schwab` | [Schwab brokerage account — sitio oficial](https://www.schwab.com/brokerage) |

### Costco

| ID | Fuente oficial |
| --- | --- |
| `issuer:cost` | [Costco Investor Relations](https://investor.costco.com/overview/default.aspx) |

### ExxonMobil

| ID | Fuente oficial |
| --- | --- |
| `issuer:xom` | [ExxonMobil Investor Relations](https://investor.exxonmobil.com/) |

### FINRA

| ID | Fuente oficial |
| --- | --- |
| `finra:brokercheck` | [BrokerCheck — FINRA](https://brokercheck.finra.org/) |
| `inv:selecting` | [The Basics of Selecting Investments](https://syndication.finra.org/content/basics-selecting-investments) |

### Fidelity

| ID | Fuente oficial |
| --- | --- |
| `broker:fidelity` | [Fidelity brokerage account — sitio oficial](https://www.fidelity.com/investing/brokerage-account) |

### Fondo Monetario Internacional

| ID | Fuente oficial |
| --- | --- |
| `imf:inflation` | [Inflation: Prices on the Rise](https://www.imf.org/en/Publications/fandd/issues/Series/Back-to-Basics/Inflation) |

### Interactive Brokers

| ID | Fuente oficial |
| --- | --- |
| `broker:ibkr` | [Interactive Brokers — sitio oficial](https://www.interactivebrokers.com/en/home.php) |
| `ibkr:beta` | [Beta — IBKR Campus](https://www.interactivebrokers.com/campus/glossary-terms/beta/) |
| `ibkr:volatility` | [Volatility — IBKR Campus](https://www.interactivebrokers.com/campus/glossary-terms/volatility/) |

### Invesco

| ID | Fuente oficial |
| --- | --- |
| `issuer:qqq` | [Invesco QQQ sitio oficial](https://www.invesco.com/qqq-etf/en/home.html) |

### JPMorgan Chase

| ID | Fuente oficial |
| --- | --- |
| `issuer:jpm` | [JPMorgan Chase Investor Relations](https://www.jpmorganchase.com/ir) |

### Johnson & Johnson

| ID | Fuente oficial |
| --- | --- |
| `issuer:jnj` | [Johnson & Johnson Investor Relations](https://www.investor.jnj.com/overview/default.aspx) |

### Meta Platforms

| ID | Fuente oficial |
| --- | --- |
| `issuer:meta` | [Meta Investor Relations](https://investor.atmeta.com/home/default.aspx) |

### Microsoft

| ID | Fuente oficial |
| --- | --- |
| `issuer:msft` | [Microsoft Investor Relations](https://www.microsoft.com/en-us/investor/default) |

### NIST

| ID | Fuente oficial |
| --- | --- |
| `nist:association` | [Scatter Plot: association and causality](https://www.itl.nist.gov/div898/handbook/eda/section3/scatterp.htm) |

### NVIDIA

| ID | Fuente oficial |
| --- | --- |
| `issuer:nvda` | [NVIDIA Investor Relations](https://investor.nvidia.com/home/default.aspx) |

### NYSE

| ID | Fuente oficial |
| --- | --- |
| `nyse:markets` | [Trading at NYSE](https://www.nyse.com/trade) |

### Nasdaq

| ID | Fuente oficial |
| --- | --- |
| `nasdaq:composite-vs-100` | [Nasdaq Composite vs. Nasdaq-100: What Investors Should Know](https://www.nasdaq.com/newsroom/nasdaq-composite-vs-nasdaq-100-what-investors-should-know) |
| `nasdaq:nasdaq-100` | [Nasdaq-100 Index](https://www.nasdaq.com/products/global-indexes/nasdaq-100) |

### S&P Dow Jones Indices

| ID | Fuente oficial |
| --- | --- |
| `spdj:dow-jones` | [Dow Jones Industrial Average](https://www.spglobal.com/spdji/en/indices/equity/dow-jones-industrial-average/) |
| `spdj:sp-500` | [S&P 500 — S&P Dow Jones Indices](https://www.spglobal.com/spdji/en/indices/equity/sp-500/) |

### SEC

| ID | Fuente oficial |
| --- | --- |
| `sec:financial-statements` | [Beginners Guide to Financial Statements](https://www.sec.gov/investor/pubs/begfinstmtguide.htm) |

### SEC / Investor.gov

| ID | Fuente oficial |
| --- | --- |
| `inv:10k` | [Form 10-K — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/form-10-k) |
| `inv:account-types` | [Types of Brokerage Accounts](https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work/types-brokerage-accounts) |
| `inv:asset-allocation` | [Asset Allocation — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/asset-allocation) |
| `inv:bid-ask` | [Bid Price/Ask Price](https://www.investor.gov/introduction-investing/investing-basics/glossary/ask-price) |
| `inv:bonds` | [Bonds — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds) |
| `inv:brokers` | [Brokers — Investor.gov](https://www.investor.gov/introduction-investing/getting-started/working-investment-professional/brokers) |
| `inv:compound-interest` | [Compound Interest — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/compound-interest) |
| `inv:diversification` | [Diversification — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/diversification) |
| `inv:dividend` | [Dividend — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/dividend) |
| `inv:informes-sec` | [Investor.gov: información sobre documentos públicos](https://www.investor.gov/introduction-investing/investing-basics/glossary/edgar) |
| `inv:eps` | [Earnings Per Share](https://www.investor.gov/introduction-investing/investing-basics/glossary/earnings-share) |
| `inv:etf` | [Exchange-Traded Fund — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/exchange-traded-fund-etf) |
| `inv:expense-ratio` | [Expense Ratio — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/expense-ratio) |
| `inv:fraud-red-flags` | [Red Flags of Investment Fraud Checklist](https://www.investor.gov/protect-your-investments/fraud/how-avoid-fraud/red-flags-investment-fraud-checklist) |
| `inv:fund-characteristics` | [Characteristics of Mutual Funds and ETFs — Investor.gov](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/characteristics-mutual-funds-exchange-traded-funds) |
| `inv:fund-fees` | [Mutual Fund and ETF Fees and Expenses — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/mutual-fund-fees-and-expenses) |
| `inv:futures` | [Futures contract — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/futures-contract) |
| `inv:holding` | [Holding Your Securities](https://www.investor.gov/introduction-investing/investing-basics/glossary/holding-your-securities) |
| `inv:index-fund` | [Index Fund — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/index-fund) |
| `inv:indices` | [Market Indices — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/market-indices) |
| `inv:international` | [International Investing — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/investment-products/international-investing) |
| `inv:investment-fees` | [How Fees and Expenses Affect Your Investment Portfolio](https://www.investor.gov/sites/default/files/ib_fees_expenses.pdf) |
| `inv:ipo` | [Initial Public Offering — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/initial-public-offering-ipo) |
| `inv:leveraged-inverse` | [Leveraged and Inverse ETFs — Investor.gov](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-alerts/sec) |
| `inv:limit-order` | [Limit Orders](https://www.investor.gov/introduction-investing/investing-basics/glossary/limit-orders) |
| `inv:liquidity` | [Liquidity — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/liquidity-or-marketability) |
| `inv:margin` | [Understanding Margin Accounts](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-29) |
| `inv:market-cap` | [Market Capitalization — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/market-capitalization) |
| `inv:market-order` | [Market Order](https://www.investor.gov/introduction-investing/investing-basics/glossary/market-order) |
| `inv:markets` | [How Stock Markets Work — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work) |
| `inv:mutual-funds` | [Mutual Funds — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-funds-etfs/mutual-funds) |
| `inv:nav` | [Net Asset Value — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/net-asset-value) |
| `inv:options` | [Options — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/options) |
| `inv:orders` | [Types of Orders](https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work/types-orders) |
| `inv:ponzi` | [Ponzi Scheme](https://www.investor.gov/protect-your-investments/fraud/types-fraud/ponzi-scheme) |
| `inv:primary-market` | [Primary Market — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/primary-market) |
| `inv:prospectus` | [Prospectus — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/prospectus) |
| `inv:reits` | [REITs — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/investment-products/real-estate-investment-trusts-reits) |
| `inv:risk` | [Risk — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/risk) |
| `inv:risk-tolerance` | [Risk Tolerance — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/risk-tolerance) |
| `inv:secondary-market` | [Secondary Market — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/secondary-market) |
| `inv:select-professional` | [How to Select an Investment Professional](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/investor-0) |
| `inv:stock-split` | [Stock Split — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/stock-split) |
| `inv:stocks` | [Stocks — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/investment-products/stocks) |
| `inv:stop-order` | [Stop Order](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order) |
| `inv:tax-questions` | [Tax Questions — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/tax-questions) |
| `inv:time-horizon` | [Time Horizon — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/time-horizon) |

### State Street

| ID | Fuente oficial |
| --- | --- |
| `issuer:spy` | [SPY — State Street](https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy) |
| `issuer:xlf` | [XLF — State Street](https://www.ssga.com/us/en/individual/etfs/state-street-financial-select-sector-spdr-etf-xlf) |
| `issuer:xlk` | [XLK — State Street](https://www.ssga.com/us/en/individual/etfs/state-street-technology-select-sector-spdr-etf-xlk) |

### Tesla

| ID | Fuente oficial |
| --- | --- |
| `issuer:tsla` | [Tesla Investor Relations](https://ir.tesla.com/) |

### UnitedHealth Group

| ID | Fuente oficial |
| --- | --- |
| `issuer:unh` | [UnitedHealth Group Investor Information](https://www.unitedhealthgroup.com/investors.html) |

### Walmart

| ID | Fuente oficial |
| --- | --- |
| `issuer:wmt` | [Walmart Investor Relations](https://stock.walmart.com/) |
