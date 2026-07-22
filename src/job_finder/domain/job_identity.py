"""Job identity models for job_finder."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, unique
from hashlib import sha256
from typing import Final, NewType

from .errors import JobIdentityValidationError

JobSource = NewType("JobSource", str)
ExternalJobId = NewType("ExternalJobId", str)
CanonicalCompanyKey = NewType("CanonicalCompanyKey", str)
JobIdentityHash = NewType("JobIdentityHash", str)

IDENTITY_UNVERIFIED_AUDIT_STATUS: Final = "identity_unverified"
_IDENTITY_SEPARATOR: Final = "\x1f"


def _require_text(value: str, field_name: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise JobIdentityValidationError(
            field_name=field_name, detail="must not be blank"
        )

    return normalized_value


def _normalize_source(value: str) -> JobSource:
    return JobSource(_require_text(value, "source").lower())


def _normalize_company_key(value: str) -> CanonicalCompanyKey:
    return CanonicalCompanyKey(_require_text(value, "canonical_company_key").lower())


def _normalize_external_job_id(value: str) -> ExternalJobId:
    return ExternalJobId(_require_text(value, "external_job_id"))


def _make_identity_hash(
    *,
    source: JobSource,
    external_job_id: ExternalJobId,
    canonical_company_key: CanonicalCompanyKey,
) -> JobIdentityHash:
    identity_input = _IDENTITY_SEPARATOR.join(
        (source, external_job_id, canonical_company_key)
    )
    digest = sha256(identity_input.encode("utf-8")).hexdigest()
    return JobIdentityHash(digest)


@unique
class IdentityUnverifiedReason(StrEnum):
    """Reason why a job identity could not be verified."""

    MISSING_EXTERNAL_JOB_ID = "missing_external_job_id"

    @property
    def tag(self) -> str:
        """Return the enum value as a tag string."""
        return str(self)


@dataclass(frozen=True, slots=True)
class CanonicalJobIdentity:
    """A verified, hashable identity for a job posting."""

    source: JobSource
    external_job_id: ExternalJobId
    canonical_company_key: CanonicalCompanyKey
    identity_hash: JobIdentityHash

    @classmethod
    def from_parts(
        cls,
        *,
        source: str,
        external_job_id: str,
        canonical_company_key: str,
    ) -> CanonicalJobIdentity:
        """Build a CanonicalJobIdentity from raw strings, normalizing and hashing."""
        normalized_source = _normalize_source(source)
        normalized_external_job_id = _normalize_external_job_id(external_job_id)
        normalized_company_key = _normalize_company_key(canonical_company_key)
        identity_hash = _make_identity_hash(
            source=normalized_source,
            external_job_id=normalized_external_job_id,
            canonical_company_key=normalized_company_key,
        )
        return cls(
            source=normalized_source,
            external_job_id=normalized_external_job_id,
            canonical_company_key=normalized_company_key,
            identity_hash=identity_hash,
        )


@dataclass(frozen=True, slots=True)
class IdentityUnverified:
    """A job posting whose identity could not be fully verified."""

    source: JobSource
    canonical_company_key: CanonicalCompanyKey
    reason: IdentityUnverifiedReason

    @property
    def audit_status(self) -> str:
        """Return the unverified audit status tag."""
        return IDENTITY_UNVERIFIED_AUDIT_STATUS

    @property
    def eligible_for_submission(self) -> bool:
        """Indicate whether this identity is eligible for submission."""
        return False


type JobIdentityResult = CanonicalJobIdentity | IdentityUnverified


def build_job_identity(
    *, source: str, external_job_id: str | None, canonical_company_key: str
) -> JobIdentityResult:
    """Build a verified identity or an unverified result from the given parts."""
    normalized_source = _normalize_source(source)
    normalized_company_key = _normalize_company_key(canonical_company_key)

    if external_job_id is None or not external_job_id.strip():
        return IdentityUnverified(
            source=normalized_source,
            canonical_company_key=normalized_company_key,
            reason=IdentityUnverifiedReason.MISSING_EXTERNAL_JOB_ID,
        )

    normalized_external_job_id = _normalize_external_job_id(external_job_id)
    identity_hash = _make_identity_hash(
        source=normalized_source,
        external_job_id=normalized_external_job_id,
        canonical_company_key=normalized_company_key,
    )
    return CanonicalJobIdentity(
        source=normalized_source,
        external_job_id=normalized_external_job_id,
        canonical_company_key=normalized_company_key,
        identity_hash=identity_hash,
    )
