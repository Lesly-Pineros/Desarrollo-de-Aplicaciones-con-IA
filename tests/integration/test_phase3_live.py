import pytest
from investiq.settings import Settings

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not Settings().has_nvidia_key, reason="NVIDIA_API_KEY no configurada en entorno/.env")
def test_chatnvidia_structured_output_live():
    from investiq.llm import ChatNVIDIAClient
    from investiq.settings import Settings

    result = ChatNVIDIAClient(Settings()).classify("¿Qué es la volatilidad?")
    assert result.intent in {"education", "unknown"}


@pytest.mark.skipif(not Settings().sec_user_agent.strip() or "@" not in Settings().sec_user_agent,
                    reason="SEC_USER_AGENT con contacto real no configurado")
def test_sec_edgar_live():
    from investiq.data.database import create_db, make_engine
    from investiq.providers.sec import sec_docs
    from investiq.settings import Settings
    from sqlmodel import Session

    engine = create_db(make_engine("sqlite:///:memory:"))
    with Session(engine) as session:
        filings, reason = sec_docs(session, "AAPL", Settings())
    assert filings, reason or "SEC EDGAR no devolvió filings verificables."
