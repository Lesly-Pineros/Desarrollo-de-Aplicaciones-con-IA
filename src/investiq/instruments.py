"""Universo técnico inicial. La selección no constituye recomendación financiera."""

from dataclasses import dataclass
import re


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

_MARKET_CONTEXT = re.compile(
    r"\b(?:precio|cotizaci[oó]n|acci[oó]n|acciones|instrumentos?|empresa|"
    r"compara\w*|diferencias?|similar\w*|parecid\w*|referencia|consulta\w*|"
    r"cu[eé]ntame sobre|habla\w* (?:de|sobre)|qu[eé] pas[oó] con)\b",
    re.IGNORECASE,
)


def _is_meta_mention(query: str, match: re.Match) -> bool:
    """Disambiguate the company from the Spanish word for a goal."""
    before = query[:match.start()]
    if re.search(r"\b(?:mi|tu|su|nuestra|una|la|esta|esa|como)\s+$", before, re.IGNORECASE):
        return False
    return bool(
        query.strip(" ¿?¡!.,").upper() == "META"
        or before.endswith("$")
        or match.group() == "META"
        or _MARKET_CONTEXT.search(query)
        or re.search(r"\b(?:y|ahora|tambi[eé]n)\s+$", before, re.IGNORECASE)
    )


def mentioned_symbols(query: str) -> list[str]:
    """Resolve only symbols and company names present in the covered catalog."""
    tokens = re.finditer(r"(?<!\w)(?:BRK-B|[A-Z]{1,5})(?!\w)", query, re.IGNORECASE)
    covered = []
    for match in tokens:
        symbol = match.group().upper()
        if symbol in INSTRUMENT_BY_SYMBOL and (symbol != "META" or _is_meta_mention(query, match)):
            covered.append(symbol)
    for item in INSTRUMENTS:
        if re.search(r"(?<!\w)" + re.escape(item.name) + r"(?!\w)", query, re.IGNORECASE):
            covered.append(item.symbol)
    return list(dict.fromkeys(covered))
