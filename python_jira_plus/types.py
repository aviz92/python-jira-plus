from typing import TypedDict


class IssueSummary(TypedDict):
    key: str
    summary: str | None
    status: str | None
    issue_type: str | None
    priority: str | None
    assignee: str | None
    updated: str | None


class IssueDetail(IssueSummary):
    project: str | None
    reporter: str | None
    created: str | None
    labels: list[str]
    resolution: str | None
    parent: str | None
    description: str | None


class CreateField(TypedDict):
    id: str
    name: str
    required: bool
    type: str | None
    allowed_values: list[str] | None
