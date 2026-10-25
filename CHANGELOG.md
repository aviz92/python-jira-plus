# Changelog

## 4.1.0

### Added
- `get_create_fields(project_key, issue_type)`: the fields for creating an issue, required first,
  with allowed values as readable labels.
- `CreateField` typed dict.

### Changed
- Issue keys and ids are validated before use: anything other than a key (`PROJ-123`) or a numeric id
  raises `ValueError`, even with `raise_on_error=False`. jira-python puts the key into the request path
  unescaped, so a value like `PROJ-1/../myself` would otherwise reach a different endpoint.

## 4.0.0

### Breaking changes
- `get_objects_by_query`: `jira_err_count` removed. Retries for 429/503 are handled by jira-python's ResilientSession.
- `get_objects_by_query`: raises `JIRAError` on failure instead of returning `[]`.
- `update_issue`: raises `ValueError` on invalid fields or values instead of returning `None`, and validates against edit metadata.
- `create_issue`: raises `ValueError` when `custom_fields` conflicts with `project`/`issuetype`.
- `.env` is no longer loaded on import, only when constructor arguments are missing.
- `dev` extra moved to `[dependency-groups]`, so `pip install python-jira-plus[dev]` no longer works.

### Added
- `raise_on_error` constructor option.
- `limit` parameter on `get_objects_by_query` (a true total cap on Cloud and on-prem).
- `get_transitions()`, `get_link_types()`.
- Full URLs with a scheme are accepted in `base_url`, and missing credentials fail fast with a clear message.

### Fixed
- Allowed-value validation accepts `value` and `id` (custom select fields, values given by id).
- Case-insensitive transition, link type and issue type names.
- On-prem pagination stops at `total` or an empty page.
- Cloud pagination respects `limit`.
- Transition comments are no longer dropped when the transition screen has no comment field.
- `get_account_data` honors `verify_ssl`; `get_account_id`/`get_account_display_name` raise `ValueError` when no user matches.
- `upload_attachment` returns `bool`.
- `projects()` is called once on construction.
