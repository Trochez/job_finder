# Session Learnings: Overleaf CV Pull Integration

## Architecture Decisions

### Port Split (Architect fix #1)
- Separated concerns into two synchronous ports:
  - `CvSourcePort`: Responsible for fetching CV source from remote (Overleaf Git) into a local cache.
  - `CvRendererPort`: Responsible for rendering CV artifacts from a local working tree (already existed).
- This separation allows the renderer to remain agnostic of the source, enabling multiple CV sources (local, Overleaf, etc.) without changing rendering logic.

### Concurrency Guard (Architect fix #2)
- Used `threading.Lock` (not asyncio) in `OverleafGitSource.fetch_source()` to serialize concurrent fetch operations.
- The lock is per-instance, and the instance is a singleton in `AppDependencies` to ensure lock effectiveness across all requests.
- Prevents working-tree corruption when multiple requests attempt to clone/pull the same Overleaf repository simultaneously.

### Error Hierarchy (Architect fix #3)
- Defined a base exception `OverleafSourceError` with six specific subclasses:
  - `OverleafTokenExpired`: Token invalid or expired.
  - `OverleafProjectNotFound`: Project does not exist or inaccessible.
  - `OverleafRateLimited`: Rate limit exceeded by Overleaf.
  - `OverleafUnreachable`: Service unreachable or unknown error.
  - `GitBinaryMissing`: Git executable not found in PATH.
  - `OverleafSourceError`: Catch-all for other Overleaf-specific issues.
- Preserved existing `EvidenceInsufficient` for render-time failures (e.g., missing .tex files).
- This hierarchy allows callers to handle specific failure modes appropriately (e.g., prompt user to refresh token).

### Migration (Architect fix #4)
- Added `cv_source_settings` table with:
  - `renderer_type`: Enum ('local', 'overleaf').
  - `overleaf_project_id`: Text, nullable.
  - `active_version`: Text, nullable (for future use).
  - `candidate_profile_id`: Foreign key to `candidate_profiles(profile_id)`, with `ON DELETE RESTRICT`.
  - `UNIQUE(candidate_profile_id)` to enforce one CV source configuration per profile.
- Downgrade strategy: `DROP TABLE IF EXISTS cv_source_settings;`.
- Token is never stored in database; kept in a 0o600 file on filesystem referenced by `overleaf_config_path`.

### TOCTOU Fix (Critic iteration 3)
- Each fetch request uses a unique temporary `snapshot_dir` via `tempfile.mkdtemp()`.
- Inside the lock, fetched files are copied from the cache directory to the snapshot directory using `shutil.copytree(dirs_exist_ok=True)`.
- The renderer reads from the snapshot directory after the lock is released, ensuring a stable view.
- Temporary snapshot directory is cleaned up in a `finally` block.

### GIT_ASKPASS (Critic iteration 3)
- Instead of embedding token in URL or environment, we use Git's `GIT_ASKPASS` mechanism:
  - Create a temporary, executable script that outputs the token content.
  - Set `GIT_ASKPASS` to the script path and `GIT_TERMINAL_PROMPT=0` to disable interactive prompts.
  - Script is chmod 0o700 and read from a 0o600 token file.
  - Script is deleted after use.
- This avoids exposing the token in process lists (via `ps`) or in shell history.

## Consensus Planning Rounds
- The planner drafted an initial plan for Overleaf CV pull integration.
- Architect reviewed and iterated twice (×2) to address port splitting, concurrency, error handling, and migration design.
- Critic reviewed and iterated three times, focusing on TOCTOU safety, credential handling, and test coverage.
- Both Architect and Critic eventually gave APPROVAL, allowing the plan to proceed to execution.

## Omo-Team Dispatch
- All 24 atomic tasks (foundation, adapter, web, tests) were dispatched via `omo-team --plan ...` in the `omo-jobfinder` tmux session.
- Tasks included:
  - Creating new adapter modules (`overleaf_config.py`, `overleaf_errors.py`, etc.).
  - Modifying existing files (`settings.py`, `web/app.py`, `web/routes/cv_source.py`, etc.).
  - Writing unit, integration, contract, and security tests.
  - Adding Alembic migration for `cv_source_settings` table.
- The team executed in parallel, with the main thread waiting for all tasks to complete.

## What Worked
- **Test-Driven Development**: Writing tests first (especially for error cases) helped drive the design and catch edge cases early.
- **Modular Ports**: Separating source and renderer ports made the system easier to extend and test.
- **Threading Lock**: Simple and effective for serializing Git operations in a synchronous context.
- **Typed Exceptions**: Enabled precise error handling in the web layer (e.g., mapping token expiry to 401).
- **Atomic Commits**: Frequent, small commits during development made it easy to track changes and revert if needed.
- **Pre-commit Hooks**: Ruff and basedpyright caught formatting and type issues early.

## What to Reuse Next Time
- **Port Pattern**: For any new external service integration, define a clear port interface (e.g., `JobSourcePort`, `NotificationPort`).
- **Singleton with Lock**: For resources that require serialized access (e.g., external API rate limits, file-based locks), use a singleton with a threading lock in the dependency container.
- **Error Hierarchy**: Define a base exception and specific subclasses for each integration to enable fine-grained error handling.
- **TOCTOU-Safe Patterns**: When copying files from a shared cache to a per-request workspace, do the copy inside a lock and use a temporary directory.
- **GIT_ASKPASS Pattern**: For any Git credential handling that requires a token or password, use the `GIT_ASKPASS` mechanism with a temporary script.
- **Consensus Planning**: Use the Planner/Architect/Critic loop for complex features to ensure robustness before implementation.
- **Omo-Team Dispatch**: For well-defined, parallelizable tasks, use the omo-team skill to distribute work and accelerate development.

## Open Issues and Future Work
- **Token Refresh UI**: Currently, if the token expires, the user must manually update the file. Consider adding a UI to update the token securely.
- **Cache Invalidation**: The cache directory (`overleaf_cache`) is never automatically cleared. Implement a TTL or size-based eviction policy.
- **Branch Support**: Currently assumes `main` then `master` branch. Allow configuring the branch name in `OverleafConfig`.
- **Submodule Support**: Overleaf projects may use Git submodules; consider recursive clone/pull.
- **Performance**: For large repositories, consider shallow clones or single-branch clones to speed up fetching.
- **Testing**: Add more integration tests with a real Overleaf test project (if available) or a mock Git server.