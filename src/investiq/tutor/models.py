"""Structured teaching output and the HTTP-independent tutor result."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from investiq.domain import ResponseDiagnostics, SourceReference


class TutorEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passage_id: str = Field(min_length=1, max_length=160)
    quote: str = Field(min_length=18, max_length=1800)


class TutorParagraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=1400)
    evidence: list[TutorEvidence] = Field(min_length=1, max_length=4)


class TutorNarration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraphs: list[TutorParagraph] = Field(min_length=1, max_length=4)


@dataclass
class TutorResult:
    answer: str
    sources: list[SourceReference] = field(default_factory=list)
    facts: dict = field(default_factory=dict)
    status: Literal["ok", "degraded", "error"] = "ok"
    tools_used: list[str] = field(default_factory=lambda: ["knowledge_search"])
    diagnostics: ResponseDiagnostics = field(default_factory=ResponseDiagnostics)
