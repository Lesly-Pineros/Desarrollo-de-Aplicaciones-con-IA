"""Actual fitted KMeans over synthetic fixtures; no investment or live data."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import hashlib

import pandas as pd
import pytest
import requests
from sqlmodel import Session

from investiq.conversation import answer_turn
from investiq.data.database import create_db, make_engine
from investiq.data.models import InstrumentFeature, MLClusterRun, UserPreference
from investiq.domain import ConversationState, RouterDecision
from investiq.instruments import INSTRUMENTS, INSTRUMENT_BY_SYMBOL
from investiq.memory import load_memory
from investiq.ml.exploration import rank_candidates
from investiq.ml.similarity import fit_similarity_model, save_model_artifact
from investiq.responses import DISCLAIMER
from investiq.routing import fallback_route
from investiq.settings import Settings
from investiq.tools import exploration_candidates


@pytest.fixture(scope="module")
def trained_fixture():
    # Three well separated synthetic groups. Values are never product data.
    frame = pd.DataFrame({item.symbol: {"volatility": .1 + (i // 7) * .2 + (i % 7) * .004,
        "mean_peer_correlation": .1 + (i // 7) * .3 + (i % 7) * .003,
        "beta": .3 + (i // 7) * .7 + (i % 7) * .006} for i, item in enumerate(INSTRUMENTS)}).T
    evaluation = fit_similarity_model(frame)
    assert evaluation.passed_thresholds
    fingerprint = hashlib.sha256(frame.sort_index().round(12).to_csv(float_format="%.12g").encode()).hexdigest()
    artifact = {**evaluation.model, "observation_start": "2025-01-01", "observation_end": "2026-10-30", "feature_fingerprint": fingerprint}
    return frame, artifact


@pytest.fixture
def exploration(tmp_path, monkeypatch, trained_fixture):
    monkeypatch.chdir(tmp_path)
    frame, artifact = trained_fixture
    filename = save_model_artifact(artifact, Path("ml/artifacts/fixture.joblib"))
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'explore.db'}"))
    def blocked(*args, **kwargs):
        pytest.fail("Exploration must not download prices or call providers")
    monkeypatch.setattr(requests, "get", blocked)
    settings = Settings(_env_file=None)
    with Session(engine) as session:
        timestamp = datetime(2026, 11, 1, tzinfo=timezone.utc)
        for symbol, row in frame.iterrows():
            session.add(InstrumentFeature(symbol=symbol, calculated_at=timestamp, **row.to_dict(),
                sector=INSTRUMENT_BY_SYMBOL[symbol].sector, volatility_bucket="fixture-unused"))
        session.add(MLClusterRun(run_id="fixture", created_at=timestamp + timedelta(minutes=1),
            artifact_path=str(filename), universe_size=len(frame), observation_start=date(2025, 1, 1),
            observation_end=date(2026, 10, 30), seed=42, n_clusters=artifact["model"].n_clusters,
            silhouette=artifact["silhouette"], stability_ari=artifact["stability_ari"], passed_thresholds=True))
        session.commit()
        yield session, settings, ConversationState()
    engine.dispose()


def ask(exploration, query, *, restore=False):
    session, settings, state = exploration
    response = answer_turn(session, "learner", query, settings, None if restore else state)
    assert response.answer.count(DISCLAIMER) == 1
    assert session.get(UserPreference, "learner") is None
    return response


@pytest.mark.parametrize("query", [
    "¿Qué acción o ETF me recomiendas para invertir hoy?",
    "Recomiéndame una acción para invertir", "quiero una recomendación de EFT",
    "Quiero explorar acciones y ETF", "¿Qué ETF me recomiendas?",
])
def test_investment_exploration_is_a_distinct_route(query):
    assert fallback_route(query).intent == "explore"


def test_guided_conversation_groups_missing_criteria_and_uses_real_model(exploration):
    first = ask(exploration, "Quiero una recomendación educativa para invertir")
    assert "acciones" in first.answer and "ETF" in first.answer
    assert "cuánto tiempo" in first.answer and "subidas y bajadas" in first.answer
    result = ask(exploration, "acciones, más de cinco años y variaciones bajas", restore=True)
    assert result.intent == "explore" and result.status == "ok"
    assert "Volatilidad anualizada" in result.answer and "2025-01-01 a 2026-10-30" in result.answer
    assert "Grupo ML" in result.answer and "11.20%" in result.answer
    assert "no una probabilidad" in result.answer and "perfiles personales" in result.answer
    assert any(s.source_id == "ml:fixture" for s in result.sources)
    assert "exploration_candidates" in result.tools_used
    assert load_memory(exploration[0], "learner").state.pending_field is None


def test_complete_request_uses_filters_and_reference_without_more_questions(exploration):
    result = ask(exploration, "Recomiéndame acciones a largo plazo con volatilidad baja en tecnología, referencia AAPL")
    assert result.status == "ok" and "cercanía a AAPL" in result.answer
    rows, run = exploration_candidates(exploration[0], load_memory(exploration[0], "learner").state.last_decision)
    assert rows and all(row["kind"] == "equity" and row["sector"] == "Technology" for row in rows)
    assert all(row["symbol"] != "AAPL" for row in rows)


def test_etf_request_cannot_return_equities(exploration):
    result = ask(exploration, "Recomiéndame ETF a largo plazo con volatilidad alta sin referencia")
    assert result.status == "ok"
    decision = load_memory(exploration[0], "learner").state.last_decision
    rows, _ = exploration_candidates(exploration[0], decision)
    assert rows and all(row["kind"] == "ETF" for row in rows)


def test_no_matching_etf_is_not_filled_with_incompatible_candidates(exploration):
    result = ask(exploration, "Recomiéndame ETF a largo plazo con volatilidad baja sin referencia")
    assert result.status == "degraded" and "No hay candidatos" in result.answer


def test_education_interrupts_and_the_exploration_can_resume(exploration):
    ask(exploration, "Recomiéndame ETF")
    lesson = ask(exploration, "¿Qué es la volatilidad?", restore=True)
    assert lesson.intent == "education" and lesson.sources
    assert load_memory(exploration[0], "learner").state.pending_field == "explore_horizon"
    ask(exploration, "más de cinco años", restore=True)
    result = ask(exploration, "alta", restore=True)
    assert result.intent == "explore" and result.status == "ok"


def test_short_horizon_does_not_require_ml_or_extra_questions(exploration, monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail("Short-horizon caution must not rank instruments")
    monkeypatch.setattr("investiq.handlers.exploration_candidates", blocked)
    result = ask(exploration, "Recomiéndame ETF a corto plazo")
    assert result.status == "degraded" and "menos de un año" in result.answer
    assert result.sources and "| Instrumento" not in result.answer
    assert load_memory(exploration[0], "learner").state.pending_field is None


def test_cancellation_and_explicit_topic_change_do_not_consume_criteria(exploration):
    ask(exploration, "Recomiéndame una acción")
    ask(exploration, "cancelar", restore=True)
    assert load_memory(exploration[0], "learner").state.pending_field is None
    response = ask(exploration, "¿Qué es Bitcoin?", restore=True)
    assert response.intent == "education"


def test_unknown_sector_is_clarified_instead_of_ignored(exploration):
    first = ask(exploration, "Recomiéndame acciones del sector inmobiliario")
    assert "no está en el catálogo" in first.answer
    assert load_memory(exploration[0], "learner").state.pending_field == "explore_sector"
    response = ask(exploration, "tecnología", restore=True)
    assert "cuánto tiempo" in response.answer.casefold()
    assert "subidas y bajadas" in response.answer.casefold()


def test_missing_model_is_honest_and_never_fabricates_percentages(exploration):
    session = exploration[0]
    session.delete(session.get(MLClusterRun, "fixture"))
    session.commit()
    result = ask(exploration, "Recomiéndame acciones a largo plazo con volatilidad baja sin referencia")
    assert result.status == "degraded" and "modelo aprobado" in result.answer
    assert not result.sources and "%" not in result.answer


def test_changed_features_are_not_combined_with_an_old_model(exploration):
    session = exploration[0]
    row = session.get(InstrumentFeature, "AAPL")
    row.calculated_at = datetime(2026, 11, 2, tzinfo=timezone.utc)
    session.add(row)
    session.commit()
    result = ask(exploration, "Recomiéndame acciones a largo plazo con volatilidad baja sin referencia")
    assert result.status == "degraded" and "características históricas coherentes" in result.answer


def test_changed_feature_values_fail_the_training_fingerprint(exploration):
    session = exploration[0]
    row = session.get(InstrumentFeature, "AAPL")
    row.volatility += .02
    session.add(row)
    session.commit()
    result = ask(exploration, "Recomiéndame acciones a largo plazo con volatilidad baja sin referencia")
    assert result.status == "degraded" and not result.sources


def test_negated_criterion_does_not_select_the_opposite_of_the_request(exploration):
    ask(exploration, "Recomiéndame ETF a largo plazo")
    result = ask(exploration, "no quiero volatilidad alta", restore=True)
    assert "¿Cómo te sientes" in result.answer
    assert load_memory(exploration[0], "learner").state.pending_decision.volatility_target is None


def test_cluster_distance_has_actual_effect_on_ranking(trained_fixture):
    frame, artifact = trained_fixture
    decision = RouterDecision(intent="explore", exploration_kind="any", exploration_horizon="long", volatility_target="baja", reference_skipped=True)
    rows = rank_candidates(frame, artifact, decision)
    assert rows == rank_candidates(frame.iloc[::-1], artifact, decision)
    expected = artifact["model"].transform(artifact["scaler"].transform(frame.sort_index()))
    by_symbol = dict(zip(frame.sort_index().index, expected.min(axis=1)))
    assert [row["distance"] for row in rows] == sorted(row["distance"] for row in rows)
    assert all(row["distance"] == pytest.approx(by_symbol[row["symbol"]]) for row in rows)


@pytest.mark.parametrize("failure", ["nan", "missing", "unapproved"])
def test_unusable_model_input_is_rejected(trained_fixture, failure):
    frame, artifact = trained_fixture
    frame, artifact = frame.copy(), dict(artifact)
    if failure == "nan": frame.iloc[0, 0] = float("nan")
    if failure == "missing": frame = frame.iloc[1:]
    if failure == "unapproved": artifact["passed_thresholds"] = False
    with pytest.raises(ValueError):
        rank_candidates(frame, artifact, RouterDecision(exploration_kind="any", volatility_target="baja"))
