"""Grounded educational generation over the local financial library."""

from investiq.tutor.generation import answer_from_knowledge
from investiq.tutor.models import TutorEvidence, TutorNarration, TutorParagraph, TutorResult

__all__ = ["answer_from_knowledge", "TutorEvidence", "TutorNarration", "TutorParagraph", "TutorResult"]
