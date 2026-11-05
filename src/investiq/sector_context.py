"""Distinguish current sector leadership from static educational knowledge.

The pilot has no verified, complete sector-performance feed. This module never
substitutes historical features or the two covered sector ETFs for such a feed.
"""

from html import unescape
import re

from investiq.language import plain

MARKETS = {
    "Estados Unidos": ("estados unidos", "estadounidense", "eeuu", "ee.uu", "ee uu", "usa", "wall street", "s&p 500", "s&p500", "sp 500", "sp500"),
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
        if leaders or recent:
            return True
    return False


def sector_market(query: str) -> str | None:
    text = plain(unescape(query))
    matched = [market for market, aliases in MARKETS.items() if any(
        re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text) for alias in aliases
    )]
    return matched[0] if len(matched) == 1 else None


def educational_part(query: str) -> str | None:
    if not is_current_sector_query(query):
        return None
    parts = [part for part in _clauses(query) if not is_current_sector_query(part)
             and re.search(r"\b(?:que|como|cual|explica\w*|diferencia\w*)\b", plain(part))]
    return " ".join(parts) or None


def sector_limitation(market: str | None) -> str:
    if market is None:
        return (
            "¿De qué mercado quieres hablar: Estados Unidos, Colombia, España, Europa o el global? "
            "Para identificar qué sectores lideran hace falta comparar el mismo período y contar con "
            "datos sectoriales completos, con fecha y hora. Aquí no tengo un ranking sectorial actual "
            "verificado; no sería correcto deducirlo de la biblioteca educativa ni de unos pocos instrumentos."
        )
    return (
        f"Para el mercado {market}, no tengo un ranking sectorial actual verificado con fecha y hora "
        "y cobertura suficiente. Por eso no puedo afirmar qué sectores lideran hoy ni dar porcentajes. "
        "La comparación necesitaría una fuente actual de ese mercado y un período común. "
        "Puedo explicarte cómo se mide el rendimiento de un sector y sus límites."
    )
