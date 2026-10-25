from collections.abc import Iterable
from typing import Any

from jira import Issue

from python_jira_plus.consts import ISSUE_REF_PATTERN, ORDER_BY_PATTERN
from python_jira_plus.types import IssueDetail, IssueSummary


def _get(obj: Any, key: str = "name") -> Any:
    return obj.get(key) if isinstance(obj, dict) else None


def simplify_issue(issue: dict[str, Any] | Issue, detail: bool = False) -> IssueSummary | IssueDetail:
    """Flatten a raw issue (or `Issue`) into plain values: names instead of nested objects."""
    raw = issue.raw if isinstance(issue, Issue) else issue
    fields = raw.get("fields") or {}
    summary = IssueSummary(
        key=raw["key"],
        summary=fields.get("summary"),
        status=_get(fields.get("status")),
        issue_type=_get(fields.get("issuetype")),
        priority=_get(fields.get("priority")),
        assignee=_get(fields.get("assignee"), "displayName"),
        updated=fields.get("updated"),
    )
    if not detail:
        return summary
    return IssueDetail(
        **summary,
        project=_get(fields.get("project"), "key"),
        reporter=_get(fields.get("reporter"), "displayName"),
        created=fields.get("created"),
        labels=fields.get("labels") or [],
        resolution=_get(fields.get("resolution")),
        parent=_get(fields.get("parent"), "key"),
        description=fields.get("description"),
    )


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
