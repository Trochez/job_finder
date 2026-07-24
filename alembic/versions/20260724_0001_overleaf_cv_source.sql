-- Overleaf CV source settings table.
-- 
-- Stores the renderer type and Overleaf project ID per candidate profile.
-- Token is NEVER stored in the database — it lives in a 0o600 file on the
-- filesystem.
--
-- FK references candidate_profiles(profile_id) to enforce referential integrity.
-- UNIQUE(candidate_profile_id) enforces 1:1 relationship — each profile has at
-- most one CV source configuration.
--
-- Downgrade: DROP TABLE IF EXISTS cv_source_settings;

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cv_source_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    renderer_type TEXT NOT NULL CHECK (renderer_type IN ('local', 'overleaf')),
    overleaf_project_id TEXT,
    active_version TEXT,
    candidate_profile_id TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (candidate_profile_id) REFERENCES candidate_profiles(profile_id) ON DELETE RESTRICT,
    UNIQUE(candidate_profile_id)
);
