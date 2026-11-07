"""Universo técnico inicial. La selección no constituye recomendación financiera."""

from dataclasses import dataclass
import re
import unicodedata


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
# KO is supported for individual quotes only; it is deliberately excluded from
# the 20-instrument historical feature and clustering universe.
QUERY_ONLY_INSTRUMENTS = (
    InstrumentSpec("KO", "Coca-Cola", "equity", "Consumer Staples"),
)
QUERY_ONLY_BY_SYMBOL = {item.symbol: item for item in QUERY_ONLY_INSTRUMENTS}
QUOTE_INSTRUMENT_BY_SYMBOL = {**INSTRUMENT_BY_SYMBOL, **QUERY_ONLY_BY_SYMBOL}
COMPANY_ALIASES = {
    "JNJ": ("Johnson and Johnson", "J&J", "Jhonson & Jhonson", "Jhonson and Jhonson"),
    "KO": ("Coca Cola", "CocaCola", "Coke", "The Coca-Cola Company"),
}
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
        if _mentions_company_name(query, item):
            covered.append(item.symbol)
    return list(dict.fromkeys(covered))


def _normalized_company_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def _mentions_company_name(query: str, item: InstrumentSpec) -> bool:
    words = f" {_normalized_company_text(query)} "
    return any(f" {_normalized_company_text(name)} " in words
               for name in (item.name, *COMPANY_ALIASES.get(item.symbol, ()))
               if _normalized_company_text(name))


def query_only_company_symbols(query: str) -> list[str]:
    """Resolve names and tickers enabled only for individual quote lookups."""
    found = [item.symbol for item in QUERY_ONLY_INSTRUMENTS if _mentions_company_name(query, item)]
    tokens = re.finditer(r"(?<!\w)[A-Z]{1,5}(?!\w)", query, re.IGNORECASE)
    found.extend(match.group().upper() for match in tokens if match.group().upper() in QUERY_ONLY_BY_SYMBOL)
    return list(dict.fromkeys(found))
