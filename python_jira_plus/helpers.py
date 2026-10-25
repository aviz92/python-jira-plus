from typing import Any

from python_jira_plus.consts import ISSUE_REF_PATTERN


def allowed_value_label(value: Any) -> str:
    """A readable label for one entry of a field's `allowedValues`."""
    if isinstance(value, dict):
        return str(value.get("name") or value.get("value") or value.get("key") or value.get("id"))
    return str(value)


def check_issue_ref(issue_ref: Any) -> None:
    """Reject an issue key/id that could change the request path (jira-python does not escape it)."""
    if isinstance(issue_ref, str) and not ISSUE_REF_PATTERN.fullmatch(issue_ref):
        raise ValueError(f"Invalid issue key '{issue_ref}'. Expected a key like PROJ-123 or a numeric id")
