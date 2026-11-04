"""Build the public response envelope independently of tools and storage."""

from investiq.domain import AssistantResponse, Intent, ResponseDiagnostics, SourceReference

DISCLAIMER = "No es asesoría financiera."


def make_response(intent: Intent, answer: str, *, sources: list[SourceReference] | None = None,
                  status: str = "ok", tools: list[str] | None = None, client=None,
                  diagnostics: ResponseDiagnostics | None = None) -> AssistantResponse:
    answer = answer.replace(DISCLAIMER, "").strip()
    return AssistantResponse(
        answer=f"{answer}\n\n{DISCLAIMER}", intent=intent,
        sources=sources or [], status=status, tools_used=tools or [],
        input_tokens=getattr(client, "total_input_tokens", None) or getattr(client, "last_input_tokens", None),
        output_tokens=getattr(client, "total_output_tokens", None) or getattr(client, "last_output_tokens", None),
        diagnostics=diagnostics if diagnostics is not None else ResponseDiagnostics(),
    )
