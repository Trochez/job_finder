# Overleaf CV Pull Setup

## Overview
This guide explains how to configure the job_finder application to pull CV source from an Overleaf project for rendering.

## Prerequisites
- An Overleaf project with Git access enabled.
- A personal access token (PAT) or Git token from Overleaf with `repo` scope.
- The project ID (24-character hex string) from the Overleaf project URL.
- Git installed and available in the system `PATH`.

## Configuration Steps

### 1. Set Up Token File
Store your Overleaf Git token in a file with restricted permissions (0o600).  
**Do not store this file in the project directory or version control.**

Example:
```bash
mkdir -p $HOME/.local/share/job-finder/secrets
echo "your_overleaf_git_token_here" > $HOME/.local/share/job-finder/secrets/overleaf_token
chmod 600 $HOME/.local/share/job-finder/secrets/overleaf_token
```

### 2. Set Overleaf Configuration Path
Tell the application where to find the token file by setting the `overleaf_config_path` in `PrivateSettings`.  
This is typically done via environment variables or by modifying the `PrivateSettings.from_paths` call in `src/job_finder/web/app.py`.

Example environment variable (if using a custom setup):
```bash
export JOB_FINDER_OVERLEAF_CONFIG_PATH=$HOME/.local/share/job-finder/secrets/overleaf_config.toml
```

Alternatively, modify the `PrivateSettings.from_paths` call in `src/job_finder/web/app.py`:
```python
settings = PrivateSettings.from_paths(
    app_data_dir=Path.home() / ".local/share/job-finder",
    overleaf_config_path=Path.home() / ".local/share/job-finder/secrets/overleaf_config.toml",
)
```

Note: The `overleaf_config.toml` file is not currently used; the token path is derived from `secrets_reference_path`.  
See `src/job_finder/adapters/settings.py` for details.

### 3. Configure via Web UI
1. Start the application: `uv run job_finder` (or however you run it).
2. Navigate to the CV Source settings page (usually `/cv-source`).
3. Select **Renderer Type: Overleaf Integration**.
4. Enter your 24-character hex Overleaf Project ID.
5. Save the settings.  
   The application will write the token to the file specified by `secrets_reference_path` / `overleaf_token` (if configured) or use the default location.

### 4. Verify Connection
After saving, the application will attempt to verify the token and project access.  
If successful, you will see a success message.  
If there is an error, check the token, project ID, and Git availability.

## Environment Variables
The application does not currently use dedicated environment variables for Overleaf configuration.  
Configuration is primarily done via the `PrivateSettings` object in `src/job_finder/web/app.py`.

However, you can influence the base directories via:
- `JOB_FINDER_APP_DATA_DIR`: Overrides the default `app_data_dir` (default: `$HOME/.local/share/job-finder`).
- `JOB_FINDER_SECRETS_REFERENCE_PATH`: Overrides the `secrets_reference_path` (default: `None`; if set, token is expected at `<secrets_reference_path>/overleaf_token`).

## Token Path
The token file is expected at:
```
<secrets_reference_path>/overleaf_token
```
If `secrets_reference_path` is not set, the token is read from `/dev/null` (which will cause authentication to fail).  
Ensure `secrets_reference_path` is set to a directory containing the token file.

File permissions must be 0o600 (readable only by the owner).

## Operational Notes
### Token Security
- The token is never stored in the database.
- It is stored only in a file with 0o600 permissions.
- The file path should be outside the project root and not backed up to cloud services inadvertently.

### Git Requirements
- Git version 2.0+ is required for `GIT_ASKPASS` support.
- The Git executable must be found in the system `PATH`.

### Cache Directory
The application caches the cloned Overleaf repository in:
```
<app_data_dir>/overleaf_cache
```
This directory is reused across renders to avoid re-cloning on every request.  
It is updated via `git pull` when the cache already exists.

### Troubleshooting
- **GitBinaryMissing**: Ensure Git is installed and in `PATH`.
- **OverleafTokenExpired**: Regenerate your Overleaf Git token and update the token file.
- **OverleafProjectNotFound**: Verify the project ID is correct and that the token has access to the project.
- **OverleafRateLimited**: Wait before retrying; consider reducing the frequency of requests.
- **OverleafUnreachable**: Check network connectivity and Overleaf service status.

### Logs
Application logs (if enabled) will show debug information about Git operations and errors.

## Updating Configuration
To change the Overleaf project or token:
1. Update the token file if rotating tokens.
2. Update the Project ID via the CV Source settings page.
3. The next CV render will use the new settings.

## Backup and Recovery
- Back up the token file securely (encrypted backup recommended).
- The cache directory can be safely deleted; it will be re-cloned as needed.