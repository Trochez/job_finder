# Task 30A Evidence — Compliance Gate Implementation

## Scope

Implement written-access-basis validation in a compliance gate module with
contract tests.

## Files

- `src/job_finder/application/compliance_gate.py` — compliance gate with:
  - `AccessBasisRecord` — frozen dataclass with 10 fields
  - `ComplianceViolationError` — structured error type
  - `ComplianceGateResult` — pass/fail result with violations tuple
  - `validate_basis_record()` — read-only validator
  - Validation: access_basis_id (non-blank), mcp_server (non-blank),
    pinned_commit (40-char hex SHA), pinned_tag (vX.Y.Z semver),
    review_date (ISO-8601, timezone-aware, not future), reviewer (non-blank),
    written_permitted_access_basis (≥100 chars), permitted_operations
    (non-empty, known ops), retention_days (positive), data_classification
    (known label)
- `tests/contract/test_compliance_enablement.py` — 28 contract tests covering
  valid records, each validation field, multiple violations, structured error
  fields, and expiry logic.

## Red

- No compliance gate existed.
- No `AccessBasisRecord` type existed.

## Green

- Compliance gate module written with all 10 validation rules.
- 28 contract tests pass.
- Gate is read-only: validates but never enables, never modifies state.

## Final verification snapshot

- `uv run pytest -q tests/contract/test_compliance_enablement.py` → `28 passed`
- `basedpyright` on compliance gate → `0 errors, 0 warnings, 0 notes`
- `ruff` → `All checks passed`

## Notes

- Gate deliberately does not raise exceptions — returns `ComplianceGateResult`.
- `AccessBasisRecord.is_expired()` compares review date to retention window.
- No imports from adapters/ — gate is pure application logic.
