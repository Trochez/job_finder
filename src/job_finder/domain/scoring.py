"""Scoring models and logic for job_finder."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from .errors import ScoringValidationError
from .scoring_policy import (
    CURRENT_SCORING_POLICY,
    ScoringFactor,
    ScoringPolicy,
    ScoringPolicyVersion,
)

if TYPE_CHECKING:
    from .candidate import CandidateFact


class CriterionEvidenceStatus(StrEnum):
    """Evidence support level for a scoring criterion."""

    SUPPORTED = "supported"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    CONFLICTING = "conflicting"


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ScoringValidationError(field_name, "must not be blank")


def _candidate_evidence_reference(fact: CandidateFact) -> str:
    return f"{fact.provenance.source.source_id}#{fact.provenance.source.locator}"


def _dedupe_in_order(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()

    for value in values:
        if value in seen:
            continue

        deduped.append(value)
        seen.add(value)

    return tuple(deduped)


def _sorted_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


@dataclass(frozen=True, slots=True)
class CriterionEvaluation:
    """Evaluation of a single scoring criterion against candidate facts."""

    factor: ScoringFactor
    criterion_id: str
    description: str
    source_fields: tuple[str, ...]
    job_evidence_references: tuple[str, ...]
    evidence_status: CriterionEvidenceStatus
    matched_facts: tuple[CandidateFact, ...]

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        _require_text(self.criterion_id, "criterion_id")
        _require_text(self.description, "description")

        if not self.source_fields:
            msg = "source_fields"
            raise ScoringValidationError(
                msg,
                "must include at least one source field",
            )

        if not self.job_evidence_references:
            msg = "job_evidence_references"
            raise ScoringValidationError(
                msg,
                "must include at least one evidence reference",
            )

        for source_field in self.source_fields:
            _require_text(source_field, "source_fields")

        for evidence_reference in self.job_evidence_references:
            _require_text(evidence_reference, "job_evidence_references")

        match self.evidence_status:
            case CriterionEvidenceStatus.SUPPORTED:
                if not self.matched_facts:
                    msg = "matched_facts"
                    raise ScoringValidationError(
                        msg,
                        "must not be empty when evidence is supported",
                    )
            case CriterionEvidenceStatus.MISSING:
                pass
            case CriterionEvidenceStatus.AMBIGUOUS:
                pass
            case CriterionEvidenceStatus.CONFLICTING:
                pass


@dataclass(frozen=True, slots=True)
class CriterionScoreExplanation:
    """Explanation of the score awarded for a single criterion."""

    criterion_id: str
    description: str
    criterion_score: int
    evidence_status: CriterionEvidenceStatus
    source_fields: tuple[str, ...]
    evidence_references: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FactorScoreExplanation:
    """Explanation of the weighted score for a scoring factor."""

    factor: ScoringFactor
    weight: int
    is_applicable: bool
    applicable_criteria_count: int
    supported_criteria_count: int
    factor_score: Decimal
    weighted_points: Decimal
    source_fields: tuple[str, ...]
    evidence_references: tuple[str, ...]
    criteria: tuple[CriterionScoreExplanation, ...]


@dataclass(frozen=True, slots=True)
class ScoreResult:
    """Final aggregated score result with per-factor explanations."""

    score: int
    policy_version: ScoringPolicyVersion
    factor_explanations: tuple[FactorScoreExplanation, ...]


def score_criteria(
    *,
    criteria: tuple[CriterionEvaluation, ...],
    policy: ScoringPolicy = CURRENT_SCORING_POLICY,
) -> ScoreResult:
    """Score all criteria against the given scoring policy."""
    factor_explanations: list[FactorScoreExplanation] = []
    weighted_total = Decimal(0)

    for factor, weight in policy.factor_weights:
        factor_criteria = tuple(
            criterion for criterion in criteria if criterion.factor is factor
        )
        supported_criteria_count = sum(
            1
            for criterion in factor_criteria
            if criterion.evidence_status is CriterionEvidenceStatus.SUPPORTED
        )
        applicable_criteria_count = len(factor_criteria)
        factor_score = _factor_score(
            supported_criteria_count=supported_criteria_count,
            applicable_criteria_count=applicable_criteria_count,
        )
        weighted_points = (factor_score * Decimal(weight)) / Decimal(100)
        criterion_explanations = tuple(
            _build_criterion_explanation(criterion) for criterion in factor_criteria
        )
        factor_explanations.append(
            FactorScoreExplanation(
                factor=factor,
                weight=weight,
                is_applicable=applicable_criteria_count > 0,
                applicable_criteria_count=applicable_criteria_count,
                supported_criteria_count=supported_criteria_count,
                factor_score=factor_score,
                weighted_points=weighted_points,
                source_fields=_sorted_unique(
                    tuple(
                        source_field
                        for explanation in criterion_explanations
                        for source_field in explanation.source_fields
                    )
                ),
                evidence_references=_dedupe_in_order(
                    tuple(
                        evidence_reference
                        for explanation in criterion_explanations
                        for evidence_reference in explanation.evidence_references
                    )
                ),
                criteria=criterion_explanations,
            )
        )
        weighted_total += weighted_points

    return ScoreResult(
        score=int(weighted_total.quantize(Decimal(1), rounding=ROUND_HALF_UP)),
        policy_version=policy.version,
        factor_explanations=tuple(factor_explanations),
    )


def _factor_score(
    *,
    supported_criteria_count: int,
    applicable_criteria_count: int,
) -> Decimal:
    if applicable_criteria_count == 0:
        return Decimal(0)

    ratio = Decimal(supported_criteria_count) / Decimal(applicable_criteria_count)
    return ratio * Decimal(100)


def _build_criterion_explanation(
    criterion: CriterionEvaluation,
) -> CriterionScoreExplanation:
    candidate_evidence_references = tuple(
        _candidate_evidence_reference(fact) for fact in criterion.matched_facts
    )

    return CriterionScoreExplanation(
        criterion_id=criterion.criterion_id,
        description=criterion.description,
        criterion_score=_criterion_score(criterion.evidence_status),
        evidence_status=criterion.evidence_status,
        source_fields=tuple(sorted(criterion.source_fields)),
        evidence_references=_dedupe_in_order(
            criterion.job_evidence_references + candidate_evidence_references,
        ),
    )


def _criterion_score(evidence_status: CriterionEvidenceStatus) -> int:
    match evidence_status:
        case CriterionEvidenceStatus.SUPPORTED:
            return 100
        case CriterionEvidenceStatus.MISSING:
            return 0
        case CriterionEvidenceStatus.AMBIGUOUS:
            return 0
        case CriterionEvidenceStatus.CONFLICTING:
            return 0
