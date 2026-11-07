"""Distinguish current sector leadership from static educational knowledge.

The pilot has no verified, complete sector-performance feed. This module never
substitutes historical features or the two covered sector ETFs for such a feed.
"""

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
            "Por ahora puedes consultar el ranking numérico de Estados Unidos (NASDAQ): cubre once sectores "
            "y muestra sus variaciones cuando FMP está configurado y el snapshot está disponible. "
            "Colombia, España, Europa y el mercado global todavía no tienen una fuente conectada para ese ranking. "
            "¿Quieres consultar Estados Unidos/NASDAQ? Responde «sí» o «NASDAQ»."
        )
    return (
        f"Para el mercado {market}, no tengo un ranking sectorial actual verificado con fecha y hora "
        "y cobertura suficiente. Por eso no puedo afirmar qué sectores lideran hoy ni dar porcentajes. "
        "El ranking disponible en esta app cubre únicamente los once sectores de NASDAQ, Estados Unidos, "
        "y requiere una clave FMP con acceso al snapshot sectorial. Revisa FMP_API_KEY en .env y reinicia "
        "la app; el acceso también depende del plan de FMP. Puedes pedirme que explique cómo se mide "
        "el rendimiento sectorial y sus límites."
    )
