"""Validated, portable educational documents and bounded retrieval passages."""

from datetime import date
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from investiq.domain import SourceReference


class KnowledgeSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=300)
    url: str = Field(min_length=1, max_length=2048)
    provider: str = Field(min_length=1, max_length=200)
    reviewed_on: date

    @field_validator("source_id", "title", "provider")
    @classmethod
    def meaningful_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source metadata cannot be blank")
        return value.strip()

    @field_validator("url")
    @classmethod
    def public_https_reference(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ValueError("sources require an HTTPS URL without credentials")
        return value

    def to_reference(self) -> SourceReference:
        # A review date is not the publisher's publication date.
        return SourceReference(source_id=self.source_id, title=self.title,
                               url=self.url, provider=self.provider)


class KnowledgeDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    aliases: tuple[str, ...] = ()
    questions: tuple[str, ...] = ()
    summary: str = Field(min_length=1, max_length=5000)
    explanation: str = Field(min_length=1, max_length=12000)
    example: str = Field(min_length=1, max_length=5000)
    cautions: str = Field(min_length=1, max_length=5000)
    related_ids: tuple[str, ...] = ()
    sources: tuple[KnowledgeSource, ...] = Field(min_length=1, max_length=8)

    @field_validator("title", "category", "summary", "explanation", "example", "cautions")
    @classmethod
    def nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("document text cannot be blank")
        return value.strip()

    @field_validator("aliases", "questions", "related_ids")
    @classmethod
    def nonblank_items(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("document lists cannot contain blank values")
        return tuple(dict.fromkeys(value.strip() for value in values))


class KnowledgePassage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    passage_id: str
    document_id: str
    title: str
    section: Literal["summary", "explanation", "example", "cautions"]
    text: str = Field(min_length=1, max_length=1000)
    score: float = Field(ge=0)
    sources: tuple[KnowledgeSource, ...] = Field(min_length=1)


class KnowledgeFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    documents: list[KnowledgeDocument] = Field(min_length=1)
