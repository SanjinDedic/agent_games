from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class APIKeysResponse(BaseModel):
    """Response with masked API keys"""

    openai_api_key: str = ""


class UpdateAPIKeysRequest(BaseModel):
    """Request to update API keys. None means 'do not change'."""

    openai_api_key: Optional[str] = None


class ValidateAPIKeyRequest(BaseModel):
    """Request to validate a specific provider's key"""

    provider: str
    api_key: Optional[str] = None  # If None, validate the stored key


# --- Plagiarism assessment ---


class PlagiarismRequest(BaseModel):
    """Request to assess a team's submissions for plagiarism / AI-generation."""

    league_id: int = Field(..., gt=0)
    team_name: str = Field(..., min_length=1, max_length=200)


class SubmissionMetrics(BaseModel):
    """Per-submission deterministic stats."""

    index: int  # 0-based position in the (possibly sampled) sequence
    submission_id: int
    timestamp: str  # ISO-8601
    total_chars: int
    normalized_chars: int
    line_count: int
    truncated: bool = False


class PairwiseMetrics(BaseModel):
    """Deterministic deltas between two consecutive submissions."""

    from_index: int
    to_index: int
    elapsed_seconds: float
    chars_added: int
    chars_removed: int
    chars_added_per_minute: Optional[float] = None  # None when elapsed_seconds == 0
    chars_added_per_second: Optional[float] = None  # None when elapsed_seconds == 0
    raw_similarity: float = Field(..., ge=0.0, le=1.0)
    normalized_similarity: float = Field(..., ge=0.0, le=1.0)
    # Hard deterministic heuristic, independent of the LLM verdict.
    # "normal" | "probable_plagiarism" | "likely_plagiarism".
    deterministic_flag: Literal[
        "normal", "probable_plagiarism", "likely_plagiarism"
    ] = "normal"


class PlagiarismVerdict(BaseModel):
    """LLM-produced verdict. extra='forbid' rejects hallucinated extra keys."""

    model_config = ConfigDict(extra="forbid")

    progression_verdict: Literal[
        "organic", "suspicious", "clearly_copied", "not_applicable"
    ]
    progression_reasoning: str = Field(..., min_length=1, max_length=2000)
    ai_generation_verdict: Literal["unlikely", "possible", "likely", "highly_likely"]
    ai_generation_reasoning: str = Field(..., min_length=1, max_length=2000)
    overall_concern_level: Literal["low", "medium", "high"]
    specific_flags: List[str] = Field(default_factory=list, max_length=20)


class PlagiarismReport(BaseModel):
    """Full response returned by POST /ai/assess-plagiarism."""

    team_name: str
    league_id: int
    submission_count_total: int
    submission_count_analyzed: int
    sampled: bool
    submission_metrics: List[SubmissionMetrics]
    pairwise_metrics: List[PairwiseMetrics]
    # Report-level deterministic summary, derived from pairwise_metrics. The
    # concern level is the worst of any pairwise flag; the list contains one
    # human-readable line per over-threshold pair.
    deterministic_concern_level: Literal[
        "none", "probable_plagiarism", "likely_plagiarism"
    ] = "none"
    deterministic_flag_summary: List[str] = Field(default_factory=list)
    verdict: PlagiarismVerdict
    model_used: str
    generated_at: str  # ISO-8601
