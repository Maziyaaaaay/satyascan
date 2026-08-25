import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConfidenceLabel, IntentType, Language, ProviderName, Stance, Verdict
from app.providers.base import FactCheckResult, ReverseImageMatch


class ProviderCallRecord(BaseModel):
    """One external provider call made during this pipeline run, recorded by
    the calling agent so verification_service can persist it as an APILog
    row afterward - agents themselves stay DB-free and unit-testable."""

    provider: ProviderName
    endpoint: str


class IntentResult(BaseModel):
    intent_type: IntentType
    confidence: float = 0.5
    has_text_claim: bool = False
    has_image: bool = False


class ExtractedClaim(BaseModel):
    text: str
    normalized_text: str


class SearchResult(BaseModel):
    fact_checks: List[FactCheckResult] = Field(default_factory=list)


class ImageAnalysisResult(BaseModel):
    ocr_text: Optional[str] = None
    reverse_matches: List[ReverseImageMatch] = Field(default_factory=list)
    ai_generated_probability: Optional[float] = None
    ai_generated_reasoning: Optional[str] = None


class RankedEvidence(BaseModel):
    claim_snippet: str
    source_url: Optional[str] = None
    source_domain: Optional[str] = None
    stance: Stance = Stance.neutral
    relevance_score: float = 0.0
    rank: int = 0
    is_live_search: bool = False


class ReasoningResult(BaseModel):
    verdict: Verdict
    rationale: str
    certainty: float = 0.5


class ConfidenceResult(BaseModel):
    score: float
    label: ConfidenceLabel


class ExplanationResult(BaseModel):
    text: str
    language: Language


class PipelineState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    verification_id: uuid.UUID
    input_text: Optional[str] = None
    input_image_bytes: Optional[bytes] = None
    language_hint: Language = Language.en

    intent: Optional[IntentResult] = None
    claims: List[ExtractedClaim] = Field(default_factory=list)
    search: Optional[SearchResult] = None
    image_analysis: Optional[ImageAnalysisResult] = None
    ranked_evidence: List[RankedEvidence] = Field(default_factory=list)
    reasoning: Optional[ReasoningResult] = None
    confidence: Optional[ConfidenceResult] = None
    explanation: Optional[ExplanationResult] = None
    provider_calls: List[ProviderCallRecord] = Field(default_factory=list)
