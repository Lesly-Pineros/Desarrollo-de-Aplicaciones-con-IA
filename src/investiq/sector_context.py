"""Distinguish current sector performance from static educational knowledge."""

from html import unescape
import re

from investiq.language import plain

MARKETS = {
    "Estados Unidos": ("estados unidos", "estadounidense", "eeuu", "ee.uu", "ee uu", "usa", "wall street", "nasdaq", "s&p 500", "s&p500", "sp 500", "sp500"),
    "Colombia": ("colombia", "colcap"),
    "España": ("espana", "ibex"),
    "Europa": ("europa", "europeo", "europea"),
    "global": ("global", "mundial", "mundo"),
}


def _clauses(query: str) -> list[str]:
    text = unescape(query).replace("\xa0", " ").strip(" *\n")
    return [part.strip() for part in re.split(r"(?<=[?!.;])\s*|[\r\n]+", text) if part.strip()]


def is_current_sector_query(query: str) -> bool:
    for clause in _clauses(query):
        text = plain(clause)
        if re.search(r"\b(?:noticias?|titulares?)\b", text):
            continue
        if not re.search(r"\b(?:sectores?|sectorial\w*)\b", text):
            continue
        if re.search(r"\b(?:que (?:es|son|significa)|define\w*)\s+(?:el |la |los |las |un |una )?(?:liderazgo|rotacion|sector|sectores)\b", text):
            continue
        leaders = re.search(r"\b(?:lidera\w*|lideres|mejor\w*|ganador\w*|destaca\w*|mayor\w* rendimiento\w*)\b", text)
        recent = re.search(r"\b(?:hoy|ahora|actual\w*|esta semana|este mes|este ano|ultim\w*)\b", text)
        everyday_performance = re.search(r"\b(?:como van|como les fue|como se movieron)\b", text)
        if leaders or recent or everyday_performance:
            return True
    return False


def sector_market(query: str) -> str | None:
    if sector_universe(query) is not None:
        return "Estados Unidos"
    text = plain(unescape(query))
    matched = [market for market, aliases in MARKETS.items() if any(
        re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text) for alias in aliases
    )]
    return matched[0] if len(matched) == 1 else None


def sector_universe(query: str) -> str | None:
    text = plain(unescape(query))
    nasdaq = bool(re.search(r"\bnasdaq\b", text))
    sp500 = bool(re.search(r"\bs\s*&\s*p\s*[-.]?\s*500\b|\bs\s+p\s+500\b|\bsp\s*[-.]?\s*500\b|\bspx\b", text))
    return "NASDAQ" if nasdaq and not sp500 else "S&P 500" if sp500 and not nasdaq else None


def educational_part(query: str) -> str | None:
    if not is_current_sector_query(query):
        return None
    parts = [part for part in _clauses(query) if not is_current_sector_query(part)
             and re.search(r"\b(?:que|como|cual|explica\w*|diferencia\w*)\b", plain(part))]
    return " ".join(parts) or None


def sector_limitation(market: str | None) -> str:
    if market is None:
        return (
            "Puedo mostrarte el ranking de NASDAQ o un resumen por sectores de las empresas del S&P 500. "
            "¿Cuál quieres consultar?"
        )
    return (
        f"Todavía no hay una fuente sectorial numérica habilitada para {market}. "
        "Puedes consultar NASDAQ o el resumen por sectores de las empresas del S&P 500."
    )
