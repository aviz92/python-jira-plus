from collections.abc import Iterable
from typing import Any

from python_jira_plus.consts import ISSUE_REF_PATTERN, ORDER_BY_PATTERN


def allowed_value_label(value: Any) -> str:
    """A readable label for one entry of a field's `allowedValues`."""
    if isinstance(value, dict):
        return str(value.get("name") or value.get("value") or value.get("key") or value.get("id"))
    return str(value)


def check_issue_ref(issue_ref: Any) -> None:
    """Reject an issue key/id that could change the request path (jira-python does not escape it)."""
    if isinstance(issue_ref, str) and not ISSUE_REF_PATTERN.fullmatch(issue_ref):
        raise ValueError(f"Invalid issue key '{issue_ref}'. Expected a key like PROJ-123 or a numeric id")


def scope_jql(jql: str, projects: Iterable[str]) -> str:
    """Restrict `jql` to `projects`, keeping any ORDER BY clause outside the filter."""
    parts = ORDER_BY_PATTERN.split(jql, maxsplit=1)
    where = parts[0].strip()
    scoped = f"project in ({', '.join(sorted(projects))})" + (f" AND ({where})" if where else "")
    return f"{scoped} ORDER BY {parts[1].strip()}" if len(parts) > 1 else scoped
