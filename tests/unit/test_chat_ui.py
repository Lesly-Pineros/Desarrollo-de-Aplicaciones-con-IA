from pathlib import Path

import pytest
from sqlmodel import Session, select

from investiq.data.database import make_engine
from investiq.data.models import QueryLog, UserPreference
from investiq.instruments import INSTRUMENTS

AppTest = pytest.importorskip("streamlit.testing.v1", reason="Interfaz heredada opcional: instala .[legacy-ui]").AppTest


def test_sidebar_explains_the_agent_and_symbol_selection_is_informational(tmp_path, monkeypatch):
    # A temporary cwd prevents Settings from reading a developer's real .env.
    monkeypatch.chdir(tmp_path)
    database_url = f"sqlite:///{tmp_path / 'ui.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    for variable in ("NVIDIA_API_KEY", "TWELVE_DATA_API_KEY", "MARKETAUX_API_KEY", "SEC_USER_AGENT"):
        monkeypatch.setenv(variable, "")

    def unexpected_turn(*args, **kwargs):
        raise AssertionError("Selecting the catalog must not execute a conversation or call providers")

    monkeypatch.setattr("investiq.conversation.answer_turn", unexpected_turn)
    app_path = Path(__file__).resolve().parents[2] / "src/investiq/app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    assert len(app.chat_input) == 1
    assert len(app.chat_message) >= 1
    assert not app.sidebar.text_input
    assert not app.sidebar.number_input
    assert not app.get("form")
    assert len(app.sidebar.selectbox) == 1

    catalog = app.sidebar.selectbox[0]
    assert catalog.label == "Símbolos disponibles para consultar"
    assert catalog.options == [f"{item.symbol} · {item.name}" for item in INSTRUMENTS]
    assert len(catalog.options) == 20
    assert app.info and "modo local" in app.info[0].value.casefold()

    app.sidebar.selectbox[0].set_value("NVDA").run()
    assert not app.exception
    engine = make_engine(database_url)
    with Session(engine) as session:
        assert session.get(UserPreference, "local") is None
        assert session.exec(select(QueryLog)).all() == []
    engine.dispose()

    rendered = " ".join(element.value for element in app.markdown)
    assert "NVIDIA_API_KEY" not in rendered
    assert "preferencias" in rendered.casefold()
