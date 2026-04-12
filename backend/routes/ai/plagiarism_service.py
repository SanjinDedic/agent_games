"""Orchestration layer for the plagiarism assessment feature.

This module holds all the imperative logic that the router calls:
- fetch submissions from the DB
- sample / truncate them
- compute deterministic metrics
- build an anonymized payload
- call OpenAI
- validate the LLM JSON response with Pydantic
- assemble the final PlagiarismReport

The router handler remains thin and only deals with auth + error mapping.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List

import httpx
from pydantic import ValidationError
from sqlmodel import Session

from backend.database.db_models import Team
from backend.routes.ai.ai_db import (
    get_stored_key,
    get_team_submissions_ordered,
)
from backend.routes.ai.ai_models import (
    PairwiseMetrics,
    PlagiarismReport,
    PlagiarismVerdict,
    SubmissionMetrics,
)
from backend.games.game_factory import GameFactory
from backend.routes.ai.plagiarism_metrics import (
    compute_complexity_jump,
    compute_pairwise_metrics,
    compute_submission_metrics,
    compute_template_similarity,
    count_ast_constructs,
    select_submissions_for_analysis,
    truncate_code,
)
from backend.routes.ai.plagiarism_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MODEL_NAME = "gpt-4o-mini"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MAX_TOTAL_PAYLOAD_CHARS = 200_000
REQUEST_TIMEOUT = 60.0
MAX_ANALYZED_SUBMISSIONS = 10


def _summarize_deterministic_flags(
    pair_metrics: List[PairwiseMetrics],
    sub_metrics: "List[SubmissionMetrics] | None" = None,
) -> tuple[str, List[str]]:
    """Collapse per-pair deterministic flags into a report-level concern level.

    Returns (concern_level, human_readable_summary_lines).
    """
    concern_level = "none"
    summary: List[str] = []

    for pm in pair_metrics:
        # Typing speed flags.
        if pm.deterministic_flag == "likely_plagiarism":
            concern_level = "likely_plagiarism"
            summary.append(
                f"submission_{pm.from_index + 1} → submission_{pm.to_index + 1}: "
                f"{pm.chars_added_per_second} chars/sec (>"
                f"6) — most likely plagiarising"
            )
        elif pm.deterministic_flag == "probable_plagiarism":
            if concern_level != "likely_plagiarism":
                concern_level = "probable_plagiarism"
            summary.append(
                f"submission_{pm.from_index + 1} → submission_{pm.to_index + 1}: "
                f"{pm.chars_added_per_second} chars/sec (>"
                f"4) — probably plagiarising"
            )

        # Complexity jump flags.
        if pm.complexity_jump_flag == "highly_suspicious":
            if concern_level == "none":
                concern_level = "probable_plagiarism"
            summary.append(
                f"submission_{pm.from_index + 1} → submission_{pm.to_index + 1}: "
                f"AST constructs jumped {pm.constructs_added} "
                f"(new types: {', '.join(pm.new_construct_types) or 'none'}) "
                f"— highly suspicious complexity jump"
            )
        elif pm.complexity_jump_flag == "suspicious":
            if concern_level == "none":
                concern_level = "probable_plagiarism"
            summary.append(
                f"submission_{pm.from_index + 1} → submission_{pm.to_index + 1}: "
                f"AST constructs added: {pm.constructs_added} "
                f"— suspicious complexity jump"
            )

    # Template similarity: flag if first submission is already very different.
    if sub_metrics and sub_metrics[0].template_similarity is not None:
        first_sim = sub_metrics[0].template_similarity
        if first_sim < 0.3:
            summary.append(
                f"First submission is only {first_sim:.0%} similar to the "
                f"starter template — started with non-template code"
            )

    return concern_level, summary


# --- Error taxonomy ---


class PlagiarismServiceError(Exception):
    """Base error for plagiarism service failures."""


class NoApiKeyError(PlagiarismServiceError):
    """OpenAI API key is not configured in the database."""


class NoSubmissionsError(PlagiarismServiceError):
    """The team has no submissions to analyze."""


class PayloadTooLargeError(PlagiarismServiceError):
    """Combined submission code exceeds the size limit."""


class LLMResponseError(PlagiarismServiceError):
    """The LLM returned an unusable response (HTTP error, bad JSON, schema mismatch)."""


# --- Public API ---


def _get_template_code(game_name: str) -> Optional[str]:
    """Safely retrieve the starter template for a game. Returns None on failure."""
    try:
        game_class = GameFactory.get_game_class(game_name)
        template = getattr(game_class, "starter_code", None)
        return template.strip() if template else None
    except (ValueError, Exception):
        return None


async def assess_team_for_plagiarism(
    session: Session, team: Team, league_id: int, game_name: str = ""
) -> PlagiarismReport:
    """Run the full assessment pipeline for a team.

    Raises the exceptions above on failure. The router is responsible for
    translating them into ErrorResponseModel.
    """
    all_subs = get_team_submissions_ordered(session, team.id)
    if not all_subs:
        raise NoSubmissionsError(f"Team '{team.name}' has no submissions")

    sampled_subs, was_sampled = select_submissions_for_analysis(
        all_subs, max_count=MAX_ANALYZED_SUBMISSIONS
    )

    # Retrieve the game template for similarity comparison.
    template_code = _get_template_code(game_name) if game_name else None

    # Build anonymized LLM payload + per-submission metrics + total size check.
    anon_payload = []
    sub_metrics: List[SubmissionMetrics] = []
    ast_counts_per_sub: list[dict] = []
    total_payload_chars = 0
    for idx, sub in enumerate(sampled_subs):
        truncated_code_str, was_truncated = truncate_code(sub.code)
        per = compute_submission_metrics(sub.code)
        tpl_sim = (
            compute_template_similarity(sub.code, template_code)
            if template_code
            else None
        )
        ast_counts = count_ast_constructs(sub.code)
        ast_counts_per_sub.append(ast_counts)

        sub_metrics.append(
            SubmissionMetrics(
                index=idx,
                submission_id=sub.id,
                timestamp=sub.timestamp.isoformat(),
                total_chars=per["total_chars"],
                normalized_chars=per["normalized_chars"],
                line_count=per["line_count"],
                truncated=was_truncated,
                template_similarity=tpl_sim,
                ast_construct_count=ast_counts.get("total", 0),
            )
        )
        total_payload_chars += len(truncated_code_str)
        anon_payload.append(
            {
                "label": f"submission_{idx + 1}",
                "timestamp": sub.timestamp.isoformat(),
                "code": truncated_code_str,
            }
        )

    if total_payload_chars > MAX_TOTAL_PAYLOAD_CHARS:
        raise PayloadTooLargeError(
            f"Combined code size {total_payload_chars} chars exceeds limit "
            f"{MAX_TOTAL_PAYLOAD_CHARS}"
        )

    # Pairwise deltas (consecutive in the sampled sequence).
    pair_metrics: List[PairwiseMetrics] = []
    for i in range(1, len(sampled_subs)):
        pm = compute_pairwise_metrics(
            sampled_subs[i - 1].code,
            sampled_subs[i - 1].timestamp,
            sampled_subs[i].code,
            sampled_subs[i].timestamp,
        )
        cj = compute_complexity_jump(ast_counts_per_sub[i - 1], ast_counts_per_sub[i])
        pair_metrics.append(
            PairwiseMetrics(
                from_index=i - 1,
                to_index=i,
                **pm,
                complexity_jump_flag=cj["complexity_jump_flag"],
                constructs_added=cj["constructs_added"],
                new_construct_types=cj["new_construct_types"],
            )
        )

    # Deterministic summary — computed locally, independent of the LLM.
    concern_level, flag_summary = _summarize_deterministic_flags(
        pair_metrics, sub_metrics
    )

    # LLM call — separate branches for single vs multi-submission.
    # Flag summary is passed as extra context so the LLM is aware of it.
    if len(sampled_subs) == 1:
        verdict = await _call_llm_single_submission(session, anon_payload, sub_metrics)
    else:
        verdict = await _call_llm_full_assessment(
            session, anon_payload, sub_metrics, pair_metrics, flag_summary
        )

    return PlagiarismReport(
        team_name=team.name,
        league_id=league_id,
        submission_count_total=len(all_subs),
        submission_count_analyzed=len(sampled_subs),
        sampled=was_sampled,
        submission_metrics=sub_metrics,
        pairwise_metrics=pair_metrics,
        deterministic_concern_level=concern_level,
        deterministic_flag_summary=flag_summary,
        verdict=verdict,
        model_used=MODEL_NAME,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


# --- Internal: OpenAI call + response parsing ---


async def _call_openai(api_key: str, user_content: str) -> dict:
    """Make the raw HTTP call to OpenAI chat completions.

    Returns the parsed JSON envelope. Raises LLMResponseError on non-200.
    """
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(
            OPENAI_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL_NAME,
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            },
        )
    if resp.status_code != 200:
        logger.error(
            "OpenAI returned HTTP %s: %s", resp.status_code, resp.text[:500]
        )
        raise LLMResponseError(f"OpenAI returned HTTP {resp.status_code}")
    return resp.json()


def _extract_and_validate_verdict(response_json: dict) -> PlagiarismVerdict:
    """Pull content out of the OpenAI envelope and validate against PlagiarismVerdict."""
    try:
        content = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMResponseError(f"Malformed OpenAI response envelope: {e}") from e

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise LLMResponseError(f"LLM returned non-JSON content: {e}") from e

    try:
        return PlagiarismVerdict.model_validate(parsed)
    except ValidationError as e:
        raise LLMResponseError(f"LLM JSON did not match schema: {e}") from e


async def _call_llm_full_assessment(
    session: Session,
    anon_payload: list,
    sub_metrics: List[SubmissionMetrics],
    pair_metrics: List[PairwiseMetrics],
    deterministic_flag_summary: List[str],
) -> PlagiarismVerdict:
    api_key = get_stored_key(session, "openai")
    if not api_key:
        raise NoApiKeyError("OpenAI API key is not configured")

    user_content = json.dumps(
        {
            "task": (
                "Assess these anonymized submissions for organic progression "
                "and AI-generated code. Note: the deterministic_flag_summary "
                "below is a hard heuristic already computed by the backend "
                "(based on chars-per-second typing speed) — incorporate it "
                "into your reasoning but do not echo it verbatim. Return JSON "
                "matching the schema in the system prompt."
            ),
            "submissions": anon_payload,
            "per_submission_metrics": [m.model_dump() for m in sub_metrics],
            "pairwise_metrics": [m.model_dump() for m in pair_metrics],
            "deterministic_flag_summary": deterministic_flag_summary,
        },
        indent=2,
    )

    response_json = await _call_openai(api_key, user_content)
    return _extract_and_validate_verdict(response_json)


async def _call_llm_single_submission(
    session: Session,
    anon_payload: list,
    sub_metrics: List[SubmissionMetrics],
) -> PlagiarismVerdict:
    api_key = get_stored_key(session, "openai")
    if not api_key:
        raise NoApiKeyError("OpenAI API key is not configured")

    user_content = json.dumps(
        {
            "task": (
                "Only one submission is available. Set progression_verdict to "
                "'not_applicable' and explain briefly in progression_reasoning. "
                "Assess ai_generation_verdict and overall_concern_level on the "
                "single submission. Return JSON matching the schema."
            ),
            "submissions": anon_payload,
            "per_submission_metrics": [m.model_dump() for m in sub_metrics],
            "pairwise_metrics": [],
        },
        indent=2,
    )

    response_json = await _call_openai(api_key, user_content)
    return _extract_and_validate_verdict(response_json)
