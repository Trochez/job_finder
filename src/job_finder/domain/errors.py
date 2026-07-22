"""Domain error types for job_finder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import override


class DomainError(Exception):
    """Base domain error for all job_finder exceptions."""


@dataclass(frozen=True, slots=True)
class InvalidTimezoneError(DomainError):
    """Raised when a timezone name is not a valid IANA timezone."""

    timezone_name: str

    @override
    def __str__(self) -> str:
        return f"unsupported IANA timezone: {self.timezone_name}"


@dataclass(frozen=True, slots=True)
class InvalidStateTagError(DomainError):
    """Raised when a state tag does not match any known state."""

    state_kind: str
    state_tag: str

    @override
    def __str__(self) -> str:
        return f"unsupported {self.state_kind} state tag: {self.state_tag}"


@dataclass(frozen=True, slots=True)
class CandidateValidationError(DomainError):
    """Raised when candidate data fails validation."""

    field_name: str
    detail: str

    @override
    def __str__(self) -> str:
        return f"{self.field_name}: {self.detail}"


@dataclass(frozen=True, slots=True)
class JobIdentityValidationError(DomainError):
    """Raised when job identity data fails validation."""

    field_name: str
    detail: str

    @override
    def __str__(self) -> str:
        return f"{self.field_name}: {self.detail}"


@dataclass(frozen=True, slots=True)
class ScoringValidationError(DomainError):
    """Raised when scoring data fails validation."""

    field_name: str
    detail: str

    @override
    def __str__(self) -> str:
        return f"{self.field_name}: {self.detail}"


@dataclass(frozen=True, slots=True)
class ScoringPolicyValidationError(DomainError):
    """Raised when scoring policy data fails validation."""

    field_name: str
    detail: str

    @override
    def __str__(self) -> str:
        return f"{self.field_name}: {self.detail}"
