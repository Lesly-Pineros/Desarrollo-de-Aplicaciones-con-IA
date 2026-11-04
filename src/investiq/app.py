from sqlmodel import Session
import streamlit as st

from investiq.conversation import WELCOME_MESSAGE, answer_turn
from investiq.data.database import create_db, make_engine, seed_instruments
from investiq.domain import ConversationState
from investiq.instruments import INSTRUMENTS
from investiq.settings import get_settings
from investiq.memory import forget_memory, load_memory, save_memory, set_memory_enabled

LOCAL_USER_ID = "local"


@st.cache_resource
def _get_engine(database_url: str):
    """Initialize the database once and reuse its engine across Streamlit reruns."""
    return create_db(make_engine(database_url))


def _sidebar(session: Session, state: ConversationState, snapshot, settings) -> None:
    with st.sidebar:
        st.title("Conoce InvestiQ")
        st.write("Un espacio para entender acciones y ETF, paso a paso y en tus palabras.")
        st.markdown(
            "Podemos explorar juntos:\n\n"
            "- Qué significa un concepto financiero.\n"
            "- Cómo se ha movido un instrumento, con sus fuentes.\n"
            "- Qué instrumentos se parecen entre sí.\n"
            "- Cómo compararlos según lo que te interesa."
        )
        st.write(
            "Cuéntame tus preferencias cuando quieras. Si hace falta aclarar algo "
            "para una comparación, te lo preguntaré en el chat."
        )
        by_symbol = {item.symbol: item for item in INSTRUMENTS}
        selected = st.selectbox(
            "Símbolos disponibles para consultar",
            options=list(by_symbol),
            format_func=lambda symbol: f"{symbol} · {by_symbol[symbol].name}",
            index=None,
            placeholder="Busca un símbolo o nombre",
            key="investiq_available_symbol",
        )
        if selected:
            st.caption(
                f"Puedes escribir «cuéntame sobre {selected}» o "
                f"«busca instrumentos similares a {selected}» en el chat."
            )
        else:
            st.caption("Elige uno para ver cómo puedes consultarlo. Puedes escribir el símbolo directamente en el chat.")
        with st.expander("Lo que recuerdo"):
            st.write(snapshot.summary)
            st.caption("Guardo un resumen del contexto, sin el chat literal. Este recuerdo pertenece a esta instalación.")
            enabled = st.toggle("Recordar contexto entre visitas", value=snapshot.enabled, key="investiq_memory_enabled")
            if enabled != snapshot.enabled:
                set_memory_enabled(session, LOCAL_USER_ID, enabled)
                st.session_state["investiq_memory_record_enabled"] = enabled
                if enabled:
                    save_memory(session, LOCAL_USER_ID, state, settings.conversation_memory_days)
                st.rerun()
            st.caption("Puedes decir «prefiero explicaciones sencillas», «qué recuerdas de mí» u «olvida el contexto».")
            if st.button("Olvidar el contexto", key="investiq_forget_context"):
                forget_memory(session, LOCAL_USER_ID)
                st.session_state.pop("investiq_conversation", None)
                st.session_state.pop("investiq_messages", None)
                st.rerun()
        st.caption("InvestiQ es educativo. No es asesoría financiera.")


def _render_message(item: dict, *, show_diagnostics: bool = False) -> None:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])
        for source in item.get("sources", []):
            if source["url"].startswith("https://"):
                st.markdown(f"[{source['title']}]({source['url']}) · {source['provider']}")
            else:
                st.caption(f"Fuente local: {source['title']} ({source['provider']})")
        if show_diagnostics and item.get("diagnostics"):
            with st.expander("Diagnóstico de respuesta"):
                st.json(item["diagnostics"])


def main() -> None:
    st.set_page_config(page_title="InvestiQ", page_icon="📊", layout="wide")
    settings = get_settings()
    engine = _get_engine(settings.database_url)
    with Session(engine) as session:
        seed_instruments(session)

        st.title("InvestiQ")
        st.caption("Aprende, pregunta y compara con fuentes a mano. No es asesoría financiera.")
        snapshot = load_memory(session, LOCAL_USER_ID, settings.conversation_memory_days)
        if st.session_state.get("investiq_memory_record_enabled") != snapshot.enabled:
            st.session_state["investiq_memory_enabled"] = snapshot.enabled
            st.session_state["investiq_memory_record_enabled"] = snapshot.enabled
        state = ConversationState.model_validate(st.session_state.get("investiq_conversation", snapshot.state.model_dump()))
        if "investiq_conversation" not in st.session_state:
            st.session_state["investiq_conversation"] = state.model_dump(mode="json")
        _sidebar(session, state, snapshot, settings)

        if not settings.has_nvidia_key:
            st.info(
                "Estoy en modo local: puedo explicar conceptos y explorar los datos ya cargados. "
                "Algunas respuestas tendrán menos detalle."
            )
        welcome = WELCOME_MESSAGE
        if snapshot.updated_at:
            welcome = "Hola de nuevo. " + snapshot.summary + " Podemos retomarlo o hablar de otra cosa.\n\nNo es asesoría financiera."
        messages = st.session_state.setdefault(
            "investiq_messages", [{"role": "assistant", "content": welcome, "sources": []}]
        )
        for item in messages:
            _render_message(item, show_diagnostics=settings.show_diagnostics)
        query = st.chat_input("Cuéntame qué te gustaría entender o comparar")
        if query:
            messages.append({"role": "user", "content": query})
            _render_message(messages[-1])
            with st.spinner("Déjame revisarlo…"):
                response = answer_turn(session, LOCAL_USER_ID, query, settings, state=state)
            if response.clear_history:
                messages.clear()
            st.session_state["investiq_conversation"] = state.model_dump(mode="json")
            messages.append({"role": "assistant", "content": response.answer,
                             "sources": [source.model_dump(mode="json") for source in response.sources],
                             "diagnostics": response.diagnostics.model_dump()})
            st.rerun()


if __name__ == "__main__":
    main()
