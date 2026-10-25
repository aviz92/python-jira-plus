# pylint: disable=no-self-use,redefined-outer-name
from unittest.mock import MagicMock, patch

import pytest

from python_jira_plus import ProjectNotAllowedError, simplify_issue
from python_jira_plus.helpers import check_issue_ref, scope_jql
from python_jira_plus.jira_cloud import JiraCloud
from python_jira_plus.jira_on_premise import JiraOnPremise

RAW_ISSUE = {
    "key": "OK-1",
    "fields": {
        "summary": "Fix it",
        "status": {"name": "Open"},
        "issuetype": {"name": "Bug"},
        "priority": {"name": "P1"},
        "assignee": {"displayName": "Avi"},
        "updated": "2026-10-25",
        "project": {"key": "OK"},
        "reporter": {"displayName": "Dana"},
        "created": "2026-10-01",
        "labels": ["a"],
        "resolution": None,
        "parent": {"key": "OK-0"},
        "description": "text",
    },
}


def _issue_in(project: str) -> MagicMock:
    issue = MagicMock()
    issue.fields.project.key = project
    issue.raw = {"key": f"{project}-1", "fields": {"project": {"key": project}}}
    return issue


@pytest.fixture
def scoped(jira_plus_cloud: JiraCloud) -> JiraCloud:
    jira_plus_cloud.allowed_projects = frozenset({"OK"})
    return jira_plus_cloud


class TestSimplifyIssue:
    def test_summary(self) -> None:
        assert simplify_issue(RAW_ISSUE) == {
            "key": "OK-1",
            "summary": "Fix it",
            "status": "Open",
            "issue_type": "Bug",
            "priority": "P1",
            "assignee": "Avi",
            "updated": "2026-10-25",
        }

    def test_detail(self) -> None:
        detail = simplify_issue(RAW_ISSUE, detail=True)
        assert (detail["project"], detail["reporter"], detail["parent"], detail["labels"]) == (
            "OK",
            "Dana",
            "OK-0",
            ["a"],
        )
        assert detail["resolution"] is None

    def test_missing_fields(self) -> None:
        detail = simplify_issue({"key": "OK-2"}, detail=True)
        assert detail["status"] is None and detail["labels"] == []

    def test_accepts_issue_object(self) -> None:
        issue = MagicMock()
        issue.raw = RAW_ISSUE
        with patch("python_jira_plus.helpers.Issue", MagicMock):
            assert simplify_issue(issue)["key"] == "OK-1"


class TestGetCreateFields:
    def test_required_first_and_labels(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.get_project_fields_metadata = MagicMock(
            return_value={
                "customfield_1": {
                    "name": "Severity",
                    "required": False,
                    "schema": {"type": "option"},
                    "allowedValues": [{"value": "High", "id": "1"}, {"id": "2"}],
                },
                "summary": {"name": "Summary", "required": True, "schema": {"type": "string"}},
            }
        )
        fields = jira_plus_cloud.get_create_fields("OK", "Bug")
        assert [f["id"] for f in fields] == ["summary", "customfield_1"]
        assert fields[0]["allowed_values"] is None
        assert fields[1]["allowed_values"] == ["High", "2"]
        assert fields[1]["type"] == "option"


class TestIssueRefValidation:
    @pytest.mark.parametrize("ref", ["PROJ-1", "proj-12", "10001", "AB_C-3"])
    def test_valid(self, ref: str) -> None:
        check_issue_ref(ref)

    @pytest.mark.parametrize("ref", ["PROJ-1/../myself", "PROJ-1?x=1", "", "a b", "PROJ-1#x"])
    def test_invalid(self, ref: str) -> None:
        with pytest.raises(ValueError, match="Invalid issue key"):
            check_issue_ref(ref)

    def test_enforced_without_allowlist(self, jira_plus_cloud: JiraCloud) -> None:
        with pytest.raises(ValueError):
            jira_plus_cloud.get_issue_by_key("PROJ-1/../myself")
        jira_plus_cloud.jira_client.issue.assert_not_called()


class TestScopeJql:
    def test_wraps_where_and_keeps_order_by(self) -> None:
        assert scope_jql("status = Open ORDER BY created DESC", {"B", "A"}) == (
            "project in (A, B) AND (status = Open) ORDER BY created DESC"
        )

    def test_empty_where(self) -> None:
        assert scope_jql("order by created", {"A"}) == "project in (A) ORDER BY created"


class TestAllowlist:
    def test_no_allowlist_makes_no_extra_request(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.add_comment("ANY-1", "hi")
        jira_plus_cloud.jira_client.issue.assert_not_called()

    def test_normalized_from_constructor(self) -> None:
        client = MagicMock()
        client.server_info.return_value = {"versionNumbers": [9, 0, 0]}
        with patch("python_jira_plus.jira_on_premise.JIRA", return_value=client):
            jp = JiraOnPremise(base_url="j", jira_token="t", allowed_projects=[" ok ", "", "b"])
        assert jp.allowed_projects == frozenset({"OK", "B"})

    def test_disallowed_project_key(self, scoped: JiraCloud) -> None:
        with pytest.raises(ProjectNotAllowedError):
            scoped.create_issue("SECRET", "s", "d", "Bug")
        scoped.jira_client.create_issue.assert_not_called()

    def test_disallowed_prefix_rejected_without_request(self, scoped: JiraCloud) -> None:
        with pytest.raises(ProjectNotAllowedError):
            scoped.update_issue("SECRET-1", {"summary": "x"})
        scoped.jira_client.issue.assert_not_called()

    def test_moved_issue_checked_by_current_project(self, scoped: JiraCloud) -> None:
        scoped.jira_client.issue.return_value = _issue_in("SECRET")
        with pytest.raises(ProjectNotAllowedError):
            scoped.delete_issue("OK-5")

    def test_numeric_id(self, scoped: JiraCloud) -> None:
        scoped.jira_client.issue.return_value = _issue_in("SECRET")
        with pytest.raises(ProjectNotAllowedError):
            scoped.add_comment("10001", "hi")

    def test_raised_even_when_errors_are_swallowed(self, scoped: JiraCloud) -> None:
        assert scoped.raise_on_error is False
        scoped.jira_client.issue.return_value = _issue_in("SECRET")
        with pytest.raises(ProjectNotAllowedError):
            scoped.transition_issue("OK-5", "Done")

    def test_create_link_checks_both_sides(self, scoped: JiraCloud) -> None:
        scoped.jira_client.issue.return_value = _issue_in("OK")
        with pytest.raises(ProjectNotAllowedError):
            scoped.create_link("OK-1", "Blocks", "SECRET-2")
        scoped.jira_client.create_issue_link.assert_not_called()

    def test_get_issue_uses_one_request(self, scoped: JiraCloud) -> None:
        scoped.jira_client.issue.return_value = _issue_in("OK")
        scoped.get_issue_by_key("OK-1", specific_fields=["summary"])
        scoped.jira_client.issue.assert_called_once_with(id="OK-1", fields=["summary", "project"])

    def test_get_issue_in_disallowed_project(self, scoped: JiraCloud) -> None:
        scoped.jira_client.issue.return_value = _issue_in("SECRET")
        with pytest.raises(ProjectNotAllowedError):
            scoped.get_issue_by_key("OK-1")

    def test_search_is_scoped_and_filtered(self, scoped: JiraCloud) -> None:
        scoped.jira_client.enhanced_search_issues.return_value = {
            "issues": [
                {"key": "OK-1", "fields": {"project": {"key": "OK"}}},
                {"key": "S-1", "fields": {"project": {"key": "SECRET"}}},
            ],
            "isLast": True,
        }
        found = scoped.get_objects_by_query("x = 1) OR (project = SECRET", specific_fields=["summary"])
        kwargs = scoped.jira_client.enhanced_search_issues.call_args.kwargs
        assert kwargs["jql_str"].startswith("project in (OK) AND (")
        assert kwargs["fields"] == ["summary", "project"]
        assert [i["key"] for i in found] == ["OK-1"]

    def test_metadata_for_disallowed_project(self, scoped: JiraCloud) -> None:
        with pytest.raises(ProjectNotAllowedError):
            scoped.get_create_fields("SECRET", "Bug")
