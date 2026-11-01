from sqlmodel import Session, select
import streamlit as st

from investiq.auth import authenticate, logout, validate_session
from investiq.data.database import create_db, make_engine, seed_instruments
from investiq.data.models import UserPreference
from investiq.domain import PreferenceInput
from investiq.instruments import INSTRUMENTS
from investiq.orchestration import answer_query
from investiq.settings import get_settings


def _login(session: Session, configured_email: str) -> bool:
    st.title("InvestiQ · acceso local")
    if not configured_email:
        st.error("Configura INVESTIQ_EMAIL en .env antes de iniciar sesión.")
        return False
    with st.form("login"):
        email = st.text_input("Correo configurado")
        password = st.text_input("Contraseña (la primera vez crea la cuenta única)", type="password")
        submitted = st.form_submit_button("Entrar")
    if submitted:
        token = authenticate(session, email, password, configured_email)
        if token:
            st.session_state["investiq_session_token"] = token
            st.rerun()
        st.error("No se pudo autenticar. Verifica el correo configurado y la contraseña.")
    return False


def main() -> None:
    st.set_page_config(page_title="InvestiQ", page_icon="📊", layout="wide")
    settings = get_settings()
    engine = create_db(make_engine(settings.database_url))
    with Session(engine) as session:
        seed_instruments(session)
        token = st.session_state.get("investiq_session_token")
        email = validate_session(session, token, settings.login_email)
        if not email:
            st.session_state.pop("investiq_session_token", None)
            _login(session, settings.login_email)
            return

        st.title("InvestiQ")
        st.caption("Educación financiera con datos trazables. No es asesoría financiera.")
        with st.sidebar:
            st.subheader("Preferencias")
            saved = session.get(UserPreference, email)
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
                session.merge(UserPreference(email=email, **preferences.model_dump()))
                session.commit()
                st.success("Preferencias guardadas.")
            if st.button("Cerrar sesión"):
                logout(session, token)
                st.session_state.pop("investiq_session_token", None)
                st.rerun()

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
            response = answer_query(session, email, query, settings)
            messages = st.session_state.setdefault("investiq_messages", [])
            messages.append({"role": "user", "content": query})
            messages.append({"role": "assistant", "content": response.answer,
                             "sources": [source.model_dump(mode="json") for source in response.sources]})
            st.rerun()


if __name__ == "__main__":
    main()
