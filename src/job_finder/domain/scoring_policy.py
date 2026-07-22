"""Scoring policy models for job_finder."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from .errors import ScoringPolicyValidationError

_TOTAL_WEIGHT = 100


class ScoringFactor(StrEnum):
    """Scoring dimension for evaluating candidate fit."""

    ROLE_ALIGNMENT = "role_alignment"
    SKILLS_TOOLS = "skills_tools"
    EXPERIENCE_SENIORITY = "experience_seniority"
    DOMAIN_RELEVANCE = "domain_relevance"
    PREFERRED_QUALIFICATIONS = "preferred_qualifications"


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ScoringPolicyValidationError(field_name, "must not be blank")


_FACTOR_ORDER: Final[tuple[ScoringFactor, ...]] = (
    ScoringFactor.ROLE_ALIGNMENT,
    ScoringFactor.SKILLS_TOOLS,
    ScoringFactor.EXPERIENCE_SENIORITY,
    ScoringFactor.DOMAIN_RELEVANCE,
    ScoringFactor.PREFERRED_QUALIFICATIONS,
)
_CURRENT_VERSION_VALUE: Final[str] = "2026-07-fixed-30-30-25-10-5"
_CURRENT_FACTOR_WEIGHTS: Final[tuple[tuple[ScoringFactor, int], ...]] = (
    (ScoringFactor.ROLE_ALIGNMENT, 30),
    (ScoringFactor.SKILLS_TOOLS, 30),
    (ScoringFactor.EXPERIENCE_SENIORITY, 25),
    (ScoringFactor.DOMAIN_RELEVANCE, 10),
    (ScoringFactor.PREFERRED_QUALIFICATIONS, 5),
)


@dataclass(frozen=True, slots=True)
class ScoringPolicyVersion:
    """Identifier for a specific scoring policy version."""

    value: str

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        _require_text(self.value, "value")


@dataclass(frozen=True, slots=True)
class ScoringPolicy:
    """A scoring policy defining factor weights and validation rules."""

    version: ScoringPolicyVersion
    factor_weights: tuple[tuple[ScoringFactor, int], ...]

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if len(self.factor_weights) != len(_FACTOR_ORDER):
            msg = "factor_weights"
            raise ScoringPolicyValidationError(
                msg,
                "must define every scoring factor exactly once",
            )

        factor_order = tuple(factor for factor, _weight in self.factor_weights)
        if factor_order != _FACTOR_ORDER:
            msg = "factor_weights"
            raise ScoringPolicyValidationError(
                msg,
                "must preserve the canonical scoring factor order",
            )

        total_weight = sum(weight for _factor, weight in self.factor_weights)
        if total_weight != _TOTAL_WEIGHT:
            msg = "factor_weights"
            raise ScoringPolicyValidationError(
                msg,
                "must total exactly 100",
            )

        if any(weight < 0 for _factor, weight in self.factor_weights):
            msg = "factor_weights"
            raise ScoringPolicyValidationError(
                msg,
                "must not contain negative weights",
            )

        if self.version.value == _CURRENT_VERSION_VALUE:
            if self.factor_weights != _CURRENT_FACTOR_WEIGHTS:
                msg = "version"
                raise ScoringPolicyValidationError(
                    msg,
                    "must change version before changing scoring semantics",
                )
            return

        msg = "version"
        raise ScoringPolicyValidationError(
            msg,
            "must be an explicitly registered scoring policy version",
        )

    def weight_for(self, factor: ScoringFactor) -> int:
        """Return the configured weight for a given scoring factor."""
        for registered_factor, weight in self.factor_weights:
            if registered_factor is factor:
                return weight

        msg = "factor_weights"
        raise ScoringPolicyValidationError(
            msg,
            f"missing weight for factor: {factor.value}",
        )


CURRENT_SCORING_POLICY_VERSION: Final[ScoringPolicyVersion] = ScoringPolicyVersion(
    _CURRENT_VERSION_VALUE,
)
CURRENT_SCORING_POLICY: Final[ScoringPolicy] = ScoringPolicy(
    version=CURRENT_SCORING_POLICY_VERSION,
    factor_weights=_CURRENT_FACTOR_WEIGHTS,
)
