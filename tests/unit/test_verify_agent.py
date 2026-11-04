import json
from types import SimpleNamespace

import pytest

from investiq.domain import Narration, RouterDecision
from tools.verify_agent import main, verify_agent


class FakeClient:
    def __init__(self, answers=None, *, route="education", error=None):
        self.answers = list(answers or [
            Narration(answer="Beta compara movimientos históricos con un mercado de referencia."),
            Narration(answer="Imagina dos recorridos y cómo se relacionaron sus movimientos."),
        ])
        self.route = route
        self.error = error
        self.calls = []

    def classify(self, question):
        self.calls.append(("classify", question))
        if self.error:
            raise self.error
        return RouterDecision(intent=self.route)

    def narrate(self, intent, query, facts, sources):
        self.calls.append(("narrate", query, facts, sources))
        return self.answers.pop(0)


def run_fake(client, **kwargs):
    return verify_agent(live=True, key_rotated=True,
                        settings_factory=lambda: SimpleNamespace(has_nvidia_key=True),
                        client_factory=lambda settings: client, **kwargs)


@pytest.mark.parametrize("flags,reason", [
    ({}, "live-opt-in-required"),
    ({"key_rotated": True}, "live-opt-in-required"),
    ({"live": True}, "key-rotation-confirmation-required"),
])
def test_diagnostic_does_not_construct_settings_or_client_without_both_opt_ins(flags, reason):
    def unexpected(*args):
        raise AssertionError("Configuration and network clients must remain untouched")

    report = verify_agent(settings_factory=unexpected, client_factory=unexpected, **flags)

    assert report["status"] == "not_run"
    assert report["reason"] == reason
    assert report["stages"] == []
    assert report["turns_completed"] == 0


def test_missing_key_is_not_reported_as_a_success_and_never_constructs_a_client():
    def unexpected(*args):
        raise AssertionError("No credential was configured")

    report = verify_agent(live=True, key_rotated=True,
                          settings_factory=lambda: SimpleNamespace(has_nvidia_key=False),
                          client_factory=unexpected)

    assert report["status"] == "not_run"
    assert report["reason"] == "missing-key"


def test_success_checks_a_followup_in_context_without_reporting_conversation_text():
    client = FakeClient()

    report = run_fake(client)

    assert report["status"] == "passed"
    assert report["turns_completed"] == 2
    assert [stage["name"] for stage in report["stages"]] == ["routing", "education", "followup"]
    assert all(stage["status"] == "passed" for stage in report["stages"])
    assert len(client.calls[-1][2]["conversation_context"]) == 2
    assert report["latency_ms"] >= 0
    serialized = json.dumps(report)
    assert "Beta compara" not in serialized
    assert "mercado de referencia" not in serialized
    assert "question" not in report


@pytest.mark.parametrize("category", ["authentication", "timeout", "Bearer secret-key-sentinel"])
def test_provider_failure_only_reports_allowlisted_categories(category):
    error = RuntimeError("Authorization: Bearer secret-key-sentinel")
    error.provider_failure_category = category

    report = run_fake(FakeClient(error=error))

    assert report["status"] == "failed"
    assert report["reason"] == (category if category in {"authentication", "timeout"} else "provider-error")
    assert "secret-key-sentinel" not in json.dumps(report)
    assert report["turns_completed"] == 0


def test_configuration_errors_do_not_expose_settings_validation_payloads():
    def broken_settings():
        raise ValueError("NVIDIA_API_KEY=secret-key-sentinel")

    report = verify_agent(live=True, key_rotated=True, settings_factory=broken_settings)

    assert report["status"] == "failed"
    assert report["reason"] == "configuration-error"
    assert "secret-key-sentinel" not in json.dumps(report)


@pytest.mark.parametrize("answer,citations,reason", [
    ("Beta garantiza un retorno de 20%.", [], "unsupported-fact"),
    ("Consulta https://invented.example/data", [], "unsupported-fact"),
    ("Beta relaciona movimientos históricos.", ["invented-source"], "unknown-citation"),
    ("Soy una persona real. Te acompaño.", [], "human-identity-claim"),
])
def test_invalid_narrations_fail_without_printing_model_output(answer, citations, reason):
    report = run_fake(FakeClient(answers=[Narration(answer=answer, cited_source_ids=citations)]))

    assert report["status"] == "failed"
    assert report["reason"] == reason
    assert answer not in json.dumps(report)


def test_a_greeting_on_each_turn_is_detected_as_a_repeated_greeting():
    client = FakeClient(answers=[Narration(answer="Hola. Beta resume una relación histórica."),
                                 Narration(answer="Hola. Imagina dos recorridos.")])

    report = run_fake(client)

    assert report["status"] == "failed"
    assert report["reason"] == "repeated-greeting"
    assert report["turns_completed"] == 1


def test_wrong_intent_fails_before_narration_is_requested():
    client = FakeClient(route="unknown")

    report = run_fake(client)

    assert report["reason"] == "routing-mismatch"
    assert report["status"] == "failed"
    assert len(client.calls) == 1


def test_cli_status_is_machine_readable_and_failure_returns_nonzero(monkeypatch, capsys):
    monkeypatch.setattr("tools.verify_agent.verify_agent", lambda **kwargs: {"status": "failed", "reason": "timeout"})

    assert main(["--live", "--key-rotated"]) == 1
    assert json.loads(capsys.readouterr().out) == {"status": "failed", "reason": "timeout"}


def test_cli_without_flags_returns_not_run_and_zero(capsys):
    assert main([]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "not_run"


def test_cli_hides_unexpected_local_diagnostic_exceptions(monkeypatch, capsys):
    def broken_diagnostic(**kwargs):
        raise RuntimeError("unexpected local failure with secret-key-sentinel")

    monkeypatch.setattr("tools.verify_agent.verify_agent", broken_diagnostic)
    assert main(["--live", "--key-rotated"]) == 1
    output = capsys.readouterr()
    assert json.loads(output.out)["reason"] == "internal-error"
    assert "secret-key-sentinel" not in output.out + output.err
