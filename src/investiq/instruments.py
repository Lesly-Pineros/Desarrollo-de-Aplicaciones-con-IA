"""Universo técnico inicial. La selección no constituye recomendación financiera."""

from dataclasses import dataclass


@dataclass(frozen=True)
class InstrumentSpec:
    symbol: str
    name: str
    kind: str
    sector: str


INSTRUMENTS = (
    InstrumentSpec("AAPL", "Apple", "equity", "Technology"),
    InstrumentSpec("MSFT", "Microsoft", "equity", "Technology"),
    InstrumentSpec("NVDA", "NVIDIA", "equity", "Technology"),
    InstrumentSpec("AMZN", "Amazon", "equity", "Consumer Discretionary"),
    InstrumentSpec("GOOGL", "Alphabet", "equity", "Communication Services"),
    InstrumentSpec("META", "Meta Platforms", "equity", "Communication Services"),
    InstrumentSpec("JPM", "JPMorgan Chase", "equity", "Financials"),
    InstrumentSpec("XOM", "Exxon Mobil", "equity", "Energy"),
    InstrumentSpec("JNJ", "Johnson & Johnson", "equity", "Health Care"),
    InstrumentSpec("WMT", "Walmart", "equity", "Consumer Staples"),
    InstrumentSpec("COST", "Costco", "equity", "Consumer Staples"),
    InstrumentSpec("TSLA", "Tesla", "equity", "Consumer Discretionary"),
    InstrumentSpec("AVGO", "Broadcom", "equity", "Technology"),
    InstrumentSpec("BRK-B", "Berkshire Hathaway", "equity", "Financials"),
    InstrumentSpec("UNH", "UnitedHealth Group", "equity", "Health Care"),
    InstrumentSpec("SPY", "SPDR S&P 500 ETF", "ETF", "Broad Market"),
    InstrumentSpec("QQQ", "Invesco QQQ ETF", "ETF", "Technology"),
    InstrumentSpec("IWM", "iShares Russell 2000 ETF", "ETF", "Broad Market"),
    InstrumentSpec("XLK", "Technology Select Sector SPDR Fund", "ETF", "Technology"),
    InstrumentSpec("XLF", "Financial Select Sector SPDR Fund", "ETF", "Financials"),
)

INSTRUMENT_BY_SYMBOL = {item.symbol: item for item in INSTRUMENTS}
BENCHMARK_SYMBOL = "SPY"
