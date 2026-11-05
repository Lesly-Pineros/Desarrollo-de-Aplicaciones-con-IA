"""Bounded Spanish filters for financial headlines; no network or user profile."""

import re

from investiq.domain import RouterDecision
from investiq.instruments import mentioned_symbols
from investiq.language import plain

NEWS_SECTORS = {
    "Technology": ("tecnologia", "tecnologico", "tecnologica", "tecnologicas"),
    "Financial Services": ("financiero", "financiera", "finanzas", "bancario", "bancos"),
    "Energy": ("energia", "energetico", "energetica", "petroleo"),
    "Healthcare": ("salud", "sanitario", "farmaceutico"),
    "Industrials": ("industrial", "industriales"),
    "Real Estate": ("inmobiliario", "inmobiliaria"),
    "Utilities": ("servicios publicos", "utilities"),
    "Basic Materials": ("materiales", "materias primas", "mineria"),
    "Consumer Cyclical": ("consumo discrecional", "consumo ciclico"),
    "Consumer Defensive": ("consumo basico", "consumo defensivo"),
    "Communication Services": ("comunicaciones", "telecomunicaciones"),
}
NEWS_COUNTRIES = {
    "us": ("estados unidos", "eeuu", "usa", "estadounidense"),
    "co": ("colombia", "colombiano", "colombiana"),
    "es": ("espana", "espanol", "espanola"),
    "mx": ("mexico", "mexicano", "mexicana"),
    "ar": ("argentina", "argentino"), "cl": ("chile", "chileno"),
    "pe": ("peru", "peruano"), "br": ("brasil", "brasileno"),
    "gb": ("reino unido", "britanico"), "de": ("alemania", "aleman"),
    "fr": ("francia", "frances"), "ca": ("canada", "canadiense"),
    "jp": ("japon", "japones"),
}


def matched_filters(text: str, catalogue: dict) -> list[str]:
    return [key for key, aliases in catalogue.items() if any(
        re.search(r"(?<!\w)" + re.escape(plain(alias)) + r"(?!\w)", plain(text))
        for alias in ((key, *aliases) if len(key) > 2 else aliases))]


def matching_filter(text: str, catalogue: dict) -> str | None:
    found = matched_filters(text, catalogue)
    return found[0] if len(found) == 1 else None


def news_decision(query: str, *, scope_reply: bool = False) -> RouterDecision | None:
    text = plain(query)
    if re.search(r"\b(?:la noticia|el titular) (?:dice|afirma|indica|menciona)\b", text):
        return None  # A quoted report is data, not a request to fetch headlines.
    selection = re.search(r"\b(?:resume|resumeme|resumen|amplia|ampliame)\b", text)
    if selection and (re.search(r"\b(?:noticia|titular|primera|segunda|tercera|ultima|[123])\b", text)
                      or text in {"resume", "un resumen", "mas sobre esa noticia"}):
        identifier = re.search(r"news:[a-z0-9:-]+", text)
        ordinal = next((str(n) for n, word in enumerate(("primera", "segunda", "tercera"), 1)
                        if word in text), None)
        number = re.search(r"\b([123])\b", text)
        return RouterDecision(intent="market_news", news_selection=(identifier[0] if identifier else
                              ordinal or (number[1] if number else "ask")))
    if not scope_reply and not re.search(r"\b(?:noticias?|titulares?|actualidad (?:del|de los) mercado)\b", text):
        return None
    if re.search(r"\b(?:que (?:es|son)|define|significa)\b", text) and not scope_reply:
        return None
    sector = matching_filter(query, NEWS_SECTORS)
    country = matching_filter(query, NEWS_COUNTRIES)
    symbols = mentioned_symbols(query)
    unknown_scope = (("sector" in text and sector is None) or
                     (re.search(r"\b(?:pais|paises)\b", text) and country is None)
                     or len(matched_filters(query, NEWS_COUNTRIES)) > 1
                     or len(matched_filters(query, NEWS_SECTORS)) > 1)
    if scope_reply and not (sector or country or symbols or re.search(r"\b(?:global|todo|general)\b", text)):
        unknown_scope = True
    return RouterDecision(intent="market_news", news_sector=sector, news_country=country,
                          symbol=symbols[0] if len(symbols) == 1 else None,
                          needs_clarification=bool(unknown_scope))
