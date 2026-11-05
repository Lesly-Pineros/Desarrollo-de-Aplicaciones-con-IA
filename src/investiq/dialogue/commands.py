"""Nonfinancial commands: memory, explanation level and conversational courtesy."""

import re
from dataclasses import dataclass

from sqlmodel import Session

from investiq.dialogue.state import clear_pending, set_pending
from investiq.domain import ConversationState, RouterDecision
from investiq.language import plain
from investiq.learning import lesson_request
from investiq.memory import forget_memory, load_memory, set_memory_enabled
from investiq.preferences import describe_preferences, get_preferences
from investiq.settings import Settings


@dataclass(frozen=True)
class ContextCommand:
    answer: str
    clear_history: bool = False


def handle_context_command(session: Session, user_id: str, query: str, settings: Settings,
                           state: ConversationState) -> ContextCommand | None:
    text = plain(query)
    if text in {"que recuerdas", "que recuerdas de mi", "que recuerdas de la conversacion", "ver memoria", "que recuerdas de nuestra conversacion"}:
        snapshot = load_memory(session, user_id, settings.conversation_memory_days)
        return ContextCommand(snapshot.summary + " Tus preferencias: " + describe_preferences(get_preferences(session, user_id))
                              + ". Puedes pedirme que olvide el contexto o que borre tus preferencias.")
    if text in {"olvida esta conversacion", "olvida lo conversado", "borra tu memoria", "borra la memoria", "olvida el contexto"}:
        forget_memory(session, user_id)
        empty = ConversationState()
        for field in ConversationState.model_fields:
            setattr(state, field, getattr(empty, field))
        return ContextCommand("Listo, olvidé el contexto de esta conversación. Tus preferencias guardadas siguen disponibles; puedes pedirme que las borre también.", clear_history=True)
    if text in {"desactiva la memoria", "desactiva memoria", "no recuerdes nuestras conversaciones"}:
        set_memory_enabled(session, user_id, False)
        return ContextCommand("De acuerdo. No guardaré el contexto para otra visita. Podemos seguir conversando en esta sesión.")
    if text in {"activa la memoria", "activa memoria", "recuerda el contexto"}:
        set_memory_enabled(session, user_id, True)
        return ContextCommand("De acuerdo, recordaré un resumen del contexto entre visitas. Puedes verlo o borrarlo cuando quieras.")
    levels = {
        "prefiero explicaciones sencillas": "basic", "prefiero explicaciones simples": "basic",
        "soy principiante": "basic", "estoy empezando": "basic",
        "prefiero explicaciones tecnicas": "advanced", "prefiero explicaciones detalladas": "advanced",
        "prefiero explicaciones normales": "standard",
    }
    if text in levels:
        state.explanation_level = levels[text]
        return ContextCommand("Lo tendré en cuenta. Usaré palabras sencillas y ejemplos paso a paso." if levels[text] == "basic"
                              else "Lo tendré en cuenta al explicar los próximos temas. Puedes pedirme más o menos detalle cuando quieras.")
    return None


def smalltalk_reply(query: str, state: ConversationState) -> str | None:
    text = plain(query)
    if not text:
        return "Cuéntame qué te gustaría explorar y empezamos por ahí."
    if re.fullmatch(r"(?:hola|buenas|buenos dias|buenas tardes|buenas noches|hey)(?: investiq)?", text):
        return "Hola. ¿Qué tienes en mente? Podemos empezar por una duda o por un instrumento que te interese."
    if re.fullmatch(r"(?:muchas )?gracias(?: por (?:todo|la ayuda))?|perfecto|genial|listo", text):
        return "Con gusto. Cuando quieras, seguimos explorando."
    if (state.last_decision is not None and state.last_decision.intent in {"education", "instrument_info"}
            and lesson_request(query)):
        # 'Cómo funciona esto' refers to the active lesson when one exists.
        # Without that context it can still explain the app's capabilities.
        return None
    if text in {"ayuda", "para que sirves", "para que sirve esto", "para que sirve el agente",
                "como funciona el agente", "como funciona esto", "en que me ayudas",
                "en que puedes ayudarme", "en que me puedes ayudar"} or re.fullmatch(
        r"(?:y )?que (?:mas )?puedes hacer(?: por mi)?", text,
    ):
        return (
            "Podemos aprender sobre acciones, ETF, bolsas, brókers, órdenes, costes y riesgos, "
            "explorar una empresa o comparar instrumentos. Cuando consulte movimientos, "
            "te mostraré los datos disponibles y sus fuentes.\n\n"
            "Puedo explicarlo paso a paso o con un ejemplo. Puedes empezar con «qué es una acción» "
            "o «qué brókers existen». "
            "Las preferencias me las puedes contar sobre la marcha."
        )
    if re.fullmatch(
        r"(?:(?:quiero|quisiera|me gustaria) (?:saber|entender)|(?:puedes|podrias) explicarme|explicame)?"
        r"\s*(?:que (?:es|significa)|(?:la )?definicion de)(?: (?:el|la|un|una))?", text,
    ):
        set_pending(state, "education_topic", RouterDecision(intent="education"))
        return "¿Qué palabra o símbolo quieres entender?"
    if text in {"cancelar", "cancela", "olvidalo", "dejemos eso", "otra cosa"}:
        clear_pending(state)
        return "De acuerdo, dejamos esa consulta. ¿Qué te gustaría explorar ahora?"
    return None
