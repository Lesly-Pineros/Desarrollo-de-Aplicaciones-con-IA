from sqlmodel import Session, select
import streamlit as st

from investiq.data.database import create_db, make_engine, seed_instruments
from investiq.data.models import UserPreference
from investiq.domain import PreferenceInput
from investiq.instruments import INSTRUMENTS
from investiq.orchestration import answer_query
from investiq.settings import get_settings

LOCAL_USER_ID = "local"


@st.cache_resource
def _get_engine(database_url: str):
    """Initialize the database once and reuse its engine across Streamlit reruns."""
    return create_db(make_engine(database_url))


def main() -> None:
    st.set_page_config(page_title="InvestiQ", page_icon="📊", layout="wide")
    settings = get_settings()
    engine = _get_engine(settings.database_url)
    with Session(engine) as session:
        seed_instruments(session)

        st.title("InvestiQ")
        st.caption("Educación financiera con datos trazables. No es asesoría financiera.")
        with st.sidebar:
            st.subheader("Preferencias")
            saved = session.get(UserPreference, LOCAL_USER_ID)
            with st.form("preferences"):
                volatility = st.selectbox("Volatilidad objetivo", ["(sin preferencia)", "baja", "media", "alta"],
                                          index=(["(sin preferencia)", "baja", "media", "alta"].index(saved.volatility_target) if saved and saved.volatility_target in {"baja", "media", "alta"} else 0))
                sector_options = ["(sin preferencia)"] + sorted({i.sector for i in INSTRUMENTS})
                sector = st.selectbox("Sector", sector_options, index=sector_options.index(saved.sector) if saved and saved.sector in sector_options else 0)
                symbols = ["(sin preferencia)"] + sorted(i.symbol for i in INSTRUMENTS)
                reference = st.selectbox("Símbolo de referencia", symbols, index=symbols.index(saved.reference_symbol) if saved and saved.reference_symbol in symbols else 0)
                beta = st.number_input("Beta objetivo (opcional)", min_value=-3.0, max_value=5.0,
                                       value=float(saved.beta_target or 0.0) if saved else 0.0, step=0.1)
                save = st.form_submit_button("Guardar preferencias")
            if save:
                preferences = PreferenceInput(volatility_target=None if volatility.startswith("(") else volatility,
                                             sector=None if sector.startswith("(") else sector,
                                             reference_symbol=None if reference.startswith("(") else reference,
                                             beta_target=beta if beta != 0 else None)
                session.merge(UserPreference(email=LOCAL_USER_ID, **preferences.model_dump()))
                session.commit()
                st.success("Preferencias guardadas.")

        if not settings.has_nvidia_key:
            st.info("NVIDIA_API_KEY no está configurada: las rutas deterministas siguen disponibles.")
        for item in st.session_state.get("investiq_messages", []):
            with st.chat_message(item["role"]):
                st.markdown(item["content"])
                for source in item.get("sources", []):
                    if source["url"].startswith("https://"):
                        st.markdown(f"[{source['title']}]({source['url']}) · {source['provider']}")
                    else:
                        st.caption(f"Fuente local: {source['title']} ({source['provider']})")
        query = st.chat_input("Pregunta por un precio, concepto o instrumentos similares")
        if query:
            response = answer_query(session, LOCAL_USER_ID, query, settings)
            messages = st.session_state.setdefault("investiq_messages", [])
            messages.append({"role": "user", "content": query})
            messages.append({"role": "assistant", "content": response.answer,
                             "sources": [source.model_dump(mode="json") for source in response.sources]})
            st.rerun()


if __name__ == "__main__":
    main()
