import pytest

from investiq.preferences import PreferenceChange
from investiq.understanding import (
    PreferenceEvidence,
    PreferenceProposal,
    semantic_preference_change,
)


class Interpreter:
    def __init__(self, proposal):
        self.proposal = proposal
        self.calls = []

    def interpret_preferences(self, query, context):
        self.calls.append((query, context))
        if isinstance(self.proposal, Exception):
            raise self.proposal
        return self.proposal


def proposal(field, value, evidence, **kwargs):
    return {"kind": "preference", "changes": [
        {"field": field, "value": value, "evidence": evidence, **kwargs},
    ]}


def test_price_movement_paraphrase_is_grounded_in_the_current_message():
    query = "Prefiero pocos sobresaltos en el precio"
    client = Interpreter(proposal("volatility_target", "baja", "pocos sobresaltos en el precio"))

    change = semantic_preference_change(query, client)

    assert isinstance(change, PreferenceChange)
    assert change.error is None
    assert change.updates == {"volatility_target": "baja"}
    assert client.calls[0][0] == query


def test_partial_patch_carries_only_expressed_criteria_and_beta_zero_is_valid():
    query = "Me gustaría tecnología y mi beta ideal es 0"
    client = Interpreter({"kind": "preference", "changes": [
        {"field": "sector", "value": "Technology", "evidence": "tecnología"},
        {"field": "beta_target", "value": 0, "evidence": "beta ideal es 0"},
    ]})

    change = semantic_preference_change(query, client, current={"volatility_target": "alta"})

    assert change.error is None
    assert change.updates == {"sector": "Technology", "beta_target": 0.0}
    assert "volatility_target" not in change.updates


def test_covered_company_name_can_support_a_reference():
    query = "Me gustaría Apple como referencia"
    client = Interpreter(proposal("reference_symbol", "AAPL", "Apple como referencia"))
    change = semantic_preference_change(query, client)
    assert change.error is None
    assert change.updates == {"reference_symbol": "AAPL"}


def test_clear_operation_requires_an_explicit_field_removal():
    query = "Quita mi beta"
    client = Interpreter(proposal("beta_target", None, query, operation="clear"))
    change = semantic_preference_change(query, client)
    assert change.error is None
    assert change.updates == {"beta_target": None}


@pytest.mark.parametrize("query,model_output", [
    ("Prefiero pocos sobresaltos en el precio", proposal("volatility_target", "alta", "pocos sobresaltos en el precio")),
    ("Prefiero volatilidad baja", proposal("volatility_target", "alta", "volatilidad alta")),
    ("Prefiero riesgo bajo", proposal("volatility_target", "baja", "riesgo bajo")),
    ("Prefiero volatilidad baja o alta", proposal("volatility_target", "baja", "volatilidad baja")),
    ("Prefiero tecnología o salud", proposal("sector", "Technology", "tecnología")),
    ("Prefiero tecnología", proposal("sector", "Mining", "tecnología")),
    ("Prefiero NVDA como referencia", proposal("reference_symbol", "FAKE", "NVDA como referencia")),
    ("Prefiero NVDA o AAPL como referencia", proposal("reference_symbol", "NVDA", "NVDA")),
    ("Prefiero beta 99", proposal("beta_target", 99, "beta 99")),
    ("Prefiero beta 1,2", proposal("beta_target", 0.8, "beta 1,2")),
    ("Prefiero beta 0 o beta 1", proposal("beta_target", 0, "beta 0")),
    ("Quita mi sector y conserva mi beta", proposal("beta_target", None, "Quita mi sector y conserva mi beta", operation="clear")),
    ("Quita mi sector", proposal("sector", "Technology", "Quita mi sector")),
])
def test_unsupported_or_ambiguous_proposal_has_no_partial_updates(query, model_output):
    result = semantic_preference_change(query, Interpreter(model_output))
    assert result.requested
    assert result.error
    assert result.updates == {}


def test_one_invalid_field_rejects_the_entire_patch():
    query = "Prefiero tecnología y beta 99"
    client = Interpreter({"kind": "preference", "changes": [
        {"field": "sector", "value": "Technology", "evidence": "tecnología"},
        {"field": "beta_target", "value": 99, "evidence": "beta 99"},
    ]})
    change = semantic_preference_change(query, client)
    assert change.error
    assert change.updates == {}


@pytest.mark.parametrize("query", [
    "Busca instrumentos de volatilidad baja",
    "Busco instrumentos de volatilidad baja",
    "Compara AAPL y MSFT",
    "¿Qué es volatilidad baja?",
    "¿Qué sector me conviene?",
    "Explícame mi beta",
    "Mi amigo dice que prefiero volatilidad baja",
    "Hola",
])
def test_questions_filters_and_reported_words_are_never_preference_evidence(query):
    client = Interpreter(proposal("volatility_target", "baja", query))
    assert semantic_preference_change(query, client, expected=True) is None
    assert client.calls == []


def test_a_bare_volatility_answer_can_complete_a_preference_question():
    client = Interpreter(proposal("volatility_target", "baja", "Baja"))
    result = semantic_preference_change("Baja", client, expected=True)
    assert result.error is None
    assert result.updates == {"volatility_target": "baja"}


@pytest.mark.parametrize("query", [
    "No quiero volatilidad alta",
    "Prefiero evitar volatilidad alta",
    "Prefiero no alta sino baja volatilidad",
    "Prefiero sin volatilidad alta",
])
def test_negated_or_ambiguous_wishes_get_a_clarification_instead_of_opposite_value(query):
    client = Interpreter(proposal("volatility_target", "alta", "alta"))
    result = semantic_preference_change(query, client, expected=True)
    assert result.error
    assert result.updates == {}
    assert client.calls == []


def test_context_is_restricted_to_validated_existing_preferences():
    client = Interpreter(proposal("sector", "Technology", "tecnología"))
    semantic_preference_change("Prefiero tecnología", client, current={
        "secret": "must-never-be-forwarded", "history": ["private text"],
        "volatility_target": ["invalid"], "sector": "Technology",
        "reference_symbol": "FAKE", "beta_target": 0,
    })
    assert client.calls[0][1] == {
        "expecting_preference": False,
        "current_preferences": {"sector": "Technology", "beta_target": 0.0},
    }


def test_provider_errors_or_missing_capability_leave_local_fallback_available():
    assert semantic_preference_change("Prefiero tecnología", object()) is None
    failed = Interpreter(RuntimeError("Authorization: Bearer must-never-appear"))
    assert semantic_preference_change("Prefiero tecnología", failed) is None


@pytest.mark.parametrize("kind", ["question", "one_off", "none"])
def test_non_preference_model_classification_cannot_mutate_preferences(kind):
    client = Interpreter({"kind": kind, "changes": [
        {"field": "sector", "value": "Technology", "evidence": "tecnología"},
    ]})
    assert semantic_preference_change("Prefiero tecnología", client) is None


def test_duplicate_fields_or_clarification_request_do_not_create_an_update():
    change = {"field": "sector", "value": "Technology", "evidence": "tecnología"}
    duplicate = Interpreter({"kind": "preference", "changes": [change, change]})
    assert semantic_preference_change("Prefiero tecnología", duplicate).error
    clarification = Interpreter({"kind": "preference", "needs_clarification": True, "changes": [change]})
    assert semantic_preference_change("Prefiero tecnología", clarification).updates == {}


def test_proposal_schema_rejects_bool_beta_or_unrecognized_fields():
    for change in (
        {"field": "beta_target", "value": True, "evidence": "beta 1"},
        {"field": "password", "value": "private", "evidence": "private"},
    ):
        client = Interpreter({"kind": "preference", "changes": [change]})
        result = semantic_preference_change("Prefiero beta 1", client)
        assert result.error
        assert result.updates == {}


def test_client_may_return_the_validated_proposal_directly():
    client = Interpreter(PreferenceProposal(kind="preference", changes=[
        PreferenceEvidence(field="beta_target", value=1.2, evidence="beta 1,2"),
    ]))
    result = semantic_preference_change("Prefiero beta 1,2", client)
    assert result.updates == {"beta_target": 1.2}
