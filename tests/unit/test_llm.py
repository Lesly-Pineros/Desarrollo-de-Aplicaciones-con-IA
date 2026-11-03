import pytest
from langchain_core.messages import AIMessage

from investiq.domain import RouterDecision
from investiq.llm import ChatNVIDIAClient, LLMUnavailable
from investiq.settings import Settings


class FakeModel:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        value = self.outputs.pop(0)
        if isinstance(value, Exception):
            raise value
        return AIMessage(content=value)


def test_structured_output_uses_regular_chat_json_and_validates_pydantic():
    model = FakeModel(['```json\n{"intent":"education","education_topic":"beta"}\n```'])
    client = ChatNVIDIAClient(Settings(), model=model)

    result = client.classify("¿Qué es beta?")

    assert result == RouterDecision(intent="education", education_topic="beta")
    assert "JSON Schema" in model.calls[0][0].content


def test_structured_output_retries_invalid_json_then_recovers():
    model = FakeModel(["No puedo", '{"intent":"education"}'])
    client = ChatNVIDIAClient(Settings(), model=model)

    result = client.classify("¿Qué es beta?")

    assert result.intent == "education"
    assert len(model.calls) == 2
    assert "solo JSON válido" in model.calls[1][1].content


def test_structured_output_exhaustion_hides_provider_exception_text():
    model = FakeModel([RuntimeError("Authorization: Bearer must-never-appear")] * 3)
    client = ChatNVIDIAClient(Settings(), model=model)

    with pytest.raises(LLMUnavailable) as raised:
        client.classify("test")

    assert "must-never-appear" not in str(raised.value)
    assert raised.value.provider_error_type == "RuntimeError"
