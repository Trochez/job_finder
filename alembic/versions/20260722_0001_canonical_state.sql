PRAGMA foreign_keys = ON;

CREATE TABLE candidate_profiles (
    profile_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL UNIQUE,
    active_version_id TEXT NOT NULL,
    timezone_name TEXT NOT NULL,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE canonical_jobs (
    job_id TEXT PRIMARY KEY,
    candidate_profile_id TEXT NOT NULL,
    source TEXT NOT NULL,
    external_job_id TEXT,
    canonical_company_key TEXT NOT NULL,
    identity_hash TEXT UNIQUE,
    identity_status TEXT NOT NULL CHECK (identity_status IN ('canonical', 'identity_unverified')),
    identity_unverified_reason TEXT,
    application_route TEXT,
    execution_access_state TEXT,
    current_workflow_state TEXT,
    discovered_at_utc TEXT NOT NULL,
    FOREIGN KEY(candidate_profile_id) REFERENCES candidate_profiles(profile_id) ON DELETE RESTRICT,
    UNIQUE(source, external_job_id, canonical_company_key)
);

CREATE TABLE run_watermarks (
    candidate_profile_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    previous_successful_watermark_utc TEXT NOT NULL,
    successful_through_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY(candidate_profile_id) REFERENCES candidate_profiles(profile_id) ON DELETE RESTRICT
);

CREATE TABLE workflow_transitions (
    transition_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL CHECK (sequence_number > 0),
    from_state TEXT,
    to_state TEXT NOT NULL,
    occurred_at_utc TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES canonical_jobs(job_id) ON DELETE RESTRICT,
    UNIQUE(job_id, sequence_number)
);

CREATE INDEX ix_canonical_jobs_candidate_profile_id
    ON canonical_jobs(candidate_profile_id);

CREATE INDEX ix_workflow_transitions_job_sequence
    ON workflow_transitions(job_id, sequence_number);

CREATE TABLE evaluation_audit (
    entry_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    applied_threshold INT,
    score_value INT,
    scoring_policy_version TEXT NOT NULL,
    factor_breakdown_json TEXT NOT NULL,
    evidence_references TEXT NOT NULL,
    cv_artifact_reference TEXT,
    evaluated_at_utc TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES canonical_jobs(job_id) ON DELETE RESTRICT
);

CREATE TABLE submission_tombstones (
    identity_hash TEXT PRIMARY KEY,
    purged_at_utc TEXT NOT NULL,
    reason TEXT NOT NULL
);

CREATE INDEX ix_evaluation_audit_job_id
    ON evaluation_audit(job_id);

CREATE INDEX ix_evaluation_audit_evaluated_at_utc
    ON evaluation_audit(evaluated_at_utc);
