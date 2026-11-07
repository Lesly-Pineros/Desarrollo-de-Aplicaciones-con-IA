"""Opt-in NIM diagnostic: bounded educational turns, safe metadata only.

Run in the authorized environment with internet after rotating the exposed key:
    .venv/bin/python tools/verify_agent.py --live --key-rotated
No flags means no configuration read, no client construction and no network.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from time import perf_counter
from typing import Callable


_FAILURE_CATEGORIES = {
    "authentication", "forbidden", "model-unavailable", "rate-limited", "tls",
    "timeout", "structured-output", "provider-unavailable", "bad-request",
    "request-too-large", "invalid-request", "provider-error",
}
logger = logging.getLogger("investiq.verify_agent")


def _settings():
    from investiq.settings import Settings

    return Settings()


def _client(settings):
    from investiq.llm import ChatNVIDIAClient

    return ChatNVIDIAClient(settings)


def _failure_category(error: Exception) -> str:
    """Never stringify provider errors: they may include credentials or payloads."""
    category = getattr(error, "provider_failure_category", None)
    if isinstance(category, str) and category in _FAILURE_CATEGORIES:
        return category
    return "timeout" if isinstance(error, TimeoutError) else "provider-error"


def _validate_narration(narration, *, greeting_already_used: bool) -> tuple[str | None, bool]:
    answer = getattr(narration, "answer", None)
    citations = getattr(narration, "cited_source_ids", None)
    if not isinstance(answer, str) or not answer.strip():
        return "empty-answer", greeting_already_used
    if not isinstance(citations, list) or citations:
        return "unknown-citation", greeting_already_used
    if re.search(r"\d|https?://", answer):
        return "unsupported-fact", greeting_already_used
    affirmative_human_claim = re.search(
        r"(?:^|[.!?]\s+)(?:soy\s+(?:(?:un|una)\s+)?(?:humano|humana|persona(?: real)?)\b|como\s+(?:ser humano|persona real)\b)",
        answer.strip(), re.IGNORECASE,
    )
    if affirmative_human_claim:
        return "human-identity-claim", greeting_already_used
    greeting = bool(re.search(r"^\s*(?:hola|buenas(?: tardes| noches)?|buenos d[ií]as)\b", answer, re.IGNORECASE))
    if greeting and greeting_already_used:
        return "repeated-greeting", True
    return None, greeting_already_used or greeting


def verify_agent(*, live: bool = False, key_rotated: bool = False,
                 settings_factory: Callable | None = None,
                 client_factory: Callable | None = None,
                 clock: Callable = perf_counter) -> dict:
    """Return status and metrics without including prompts, responses or exceptions."""
    report = {"status": "not_run", "reason": "live-opt-in-required", "stages": [],
              "turns_completed": 0, "latency_ms": 0.0, "scope": "educational-dialogue"}
    if not live:
        return report
    if not key_rotated:
        report["reason"] = "key-rotation-confirmation-required"
        return report
    started = clock()

    def finish(status: str, reason: str) -> dict:
        report.update(status=status, reason=reason, latency_ms=round(max(0.0, clock() - started) * 1000, 3))
        return report

    try:
        settings = (settings_factory or _settings)()
    except Exception:
        return finish("failed", "configuration-error")
    if not settings.has_nvidia_key:
        return finish("not_run", "missing-key")
    try:
        client = (client_factory or _client)(settings)
    except Exception as error:
        return finish("failed", _failure_category(error))

    question = "¿Qué es beta?"
    stage_started = clock()
    try:
        decision = client.classify(question)
    except Exception as error:
        reason = _failure_category(error)
        report["stages"].append({"name": "routing", "status": "failed", "reason": reason,
                                 "latency_ms": round(max(0.0, clock() - stage_started) * 1000, 3)})
        return finish("failed", reason)
    correct_route = getattr(decision, "intent", None) == "education"
    report["stages"].append({"name": "routing", "status": "passed" if correct_route else "failed",
                             "reason": "ok" if correct_route else "routing-mismatch",
                             "latency_ms": round(max(0.0, clock() - stage_started) * 1000, 3)})
    if not correct_route:
        return finish("failed", "routing-mismatch")

    # Only public glossary grounding and this synthetic conversation enter NIM.
    from investiq.tools import GLOSSARY

    definition = GLOSSARY["beta"]
    history = []
    greeting_used = False
    for name, current_question in (("education", question), ("followup", "¿Puedes darme un ejemplo más sencillo?")):
        stage_started = clock()
        try:
            narration = client.narrate("education", current_question,
                                       {"definition": definition, "conversation_context": list(history)}, [])
            reason, greeting_used = _validate_narration(narration, greeting_already_used=greeting_used)
        except Exception as error:
            reason = _failure_category(error)
        report["stages"].append({"name": name, "status": "failed" if reason else "passed",
                                 "reason": reason or "ok",
                                 "latency_ms": round(max(0.0, clock() - stage_started) * 1000, 3)})
        if reason:
            return finish("failed", reason)
        report["turns_completed"] += 1
        history.extend([
            {"role": "user", "content": current_question},
            {"role": "assistant", "content": narration.answer[:1200]},
        ])
    return finish("passed", "ok")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Autoriza este diagnóstico contra NIM real.")
    parser.add_argument("--key-rotated", action="store_true", help="Confirma que se sustituyó la clave previamente expuesta.")
    args = parser.parse_args(argv)
    try:
        if args.live:
            from investiq.logging_config import configure_logging
            from investiq.settings import get_settings

            settings = get_settings()
            configure_logging(settings.log_level)
            logger.info("diagnostic.start live=true key_rotation_confirmed=%s", args.key_rotated)
        report = verify_agent(live=args.live, key_rotated=args.key_rotated)
    except Exception:
        # A broken local import or unexpected diagnostic bug still must not emit
        # a traceback carrying settings, provider payloads or credentials.
        report = {"status": "failed", "reason": "internal-error", "stages": [],
                  "turns_completed": 0, "latency_ms": 0.0, "scope": "educational-dialogue"}
    print(json.dumps(report, ensure_ascii=False))
    if args.live:
        logger.info("diagnostic.done status=%s reason=%s", report["status"], report["reason"])
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
