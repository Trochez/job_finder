"""Identity types for job_finder domain entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NewType
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .errors import InvalidTimezoneError

CandidateId = NewType("CandidateId", str)
CandidateProfileId = NewType("CandidateProfileId", str)
CandidateProfileVersionId = NewType("CandidateProfileVersionId", str)
CandidateFactId = NewType("CandidateFactId", str)
CandidateSourceId = NewType("CandidateSourceId", str)
JobId = NewType("JobId", str)
RunId = NewType("RunId", str)


@dataclass(frozen=True, slots=True)
class UserTimezone:
    """A validated IANA timezone with its corresponding ZoneInfo object."""

    name: str
    zoneinfo: ZoneInfo

    @classmethod
    def from_name(cls, name: str) -> UserTimezone:
        """Build a UserTimezone from an IANA timezone string."""
        try:
            zoneinfo = ZoneInfo(name)
        except ZoneInfoNotFoundError as error:
            raise InvalidTimezoneError(timezone_name=name) from error

        return cls(name=name, zoneinfo=zoneinfo)
