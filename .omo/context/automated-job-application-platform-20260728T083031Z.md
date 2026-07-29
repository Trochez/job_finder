# Deep Interview Context Snapshot

## Task statement
Create a dark-themed platform that discovers recent LinkedIn jobs, ranks them against an Overleaf CV, tailors a versioned CV per selected job, applies automatically where possible, tracks pending answers and application status, and reconciles Gmail updates through Composio.

## Desired outcome
An execution-ready requirements specification for the platform; no implementation in this interview stage.

## Known facts
- Workspace currently contains operational/configuration folders only; application source has not yet been confirmed.
- User requires LinkedIn job discovery through borgius/jobspy-mcp-server.
- User requires SQLite persistence, configurable daily limits and match threshold, Gmail status tracking through Composio, `.keys/` credential storage, and a dark frontend.

## Constraints
- Search jobs from the last 24 hours.
- Rank by CV/job match percentage and act on the configured highest-ranked set.
- Generate a new, incremented, visually consistent CV version for every application.
- Support manual iteration execution and stopping daily automation.
- Application policy: browser automation submits every selected job, including external forms.
- Selected jobs submit immediately after ranking; no final approval step.
- Unknown or ambiguous application questions pause that job as pending. Users answer in the frontend; answers persist and may be reused for future applications.
- Original CV source is an Overleaf project accessed through credentials stored under `.keys/`.
- Tailored CV generation runs automatically and remains conservative: it must not invent education or certifications. Any application question requiring a fact not already established, including education or experience details, becomes pending for user confirmation; confirmed answers persist for reuse.
- Seniority must be inferred from the CV; employment types are configurable.
- Job title, location, and remote preference are configurable fields; defaults remain unspecified.

## Unknowns / open questions
- Exact approval boundary for automatic application submission, including non-Easy Apply flows.
- Default values for configurable search fields.
- Target user profile, geography, job titles, remote policy, and authorization model.
- Accepted CV source/export format and tailoring rules.
- Credential-security and deployment model.
- Exact definition and source of authoritative application status.
- Tailored CV output format and matching-scoring definition.

## Likely codebase touchpoints
- New frontend, backend, scheduler, SQLite schema, provider adapters, CV renderer, credential configuration, and test suites.
