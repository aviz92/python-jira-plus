"""
Integration tests against a real Jira Cloud instance.

Required env vars:
    JIRA_USER_NAME      your Jira email
    JIRA_TOKEN          your Jira API token
    JIRA_BASE_URL       e.g. your-instance.atlassian.net

Optional env vars (fall back to defaults if not set):
    JIRA_TEST_PROJECT       project key to query  (default: SUP)
    JIRA_TEST_ISSUE_TYPE    issue type to query   (default: [System] Service request)
    JIRA_TEST_ISSUE_KEY     a known issue key     (default: SUP-1)
    JIRA_TEST_FIELD         field for allowed values check (default: Priority)

Run only integration tests:
    uv run pytest -m integration -v
"""

import os

import pytest

from python_jira_plus import BASIC_FIELDS
from python_jira_plus.jira_plus import JiraPlus

pytestmark = pytest.mark.integration

_REQUIRED_ENV = ("JIRA_USER_NAME", "JIRA_TOKEN", "JIRA_BASE_URL")


def _missing_env() -> list[str]:
    return [var for var in _REQUIRED_ENV if not os.getenv(var)]


@pytest.fixture(scope="module")
def jira() -> JiraPlus:
    missing = _missing_env()
    if missing:
        pytest.skip(f"Missing required env vars: {', '.join(missing)}")
    return JiraPlus()


@pytest.fixture(scope="module")
def project_key() -> str:
    return os.getenv("JIRA_TEST_PROJECT", "SUP")


@pytest.fixture(scope="module")
def issue_type() -> str:
    return os.getenv("JIRA_TEST_ISSUE_TYPE", "[System] Service request")


@pytest.fixture(scope="module")
def issue_key() -> str:
    return os.getenv("JIRA_TEST_ISSUE_KEY", "SUP-1")


@pytest.fixture(scope="module")
def test_field() -> str:
    return os.getenv("JIRA_TEST_FIELD", "Priority")


class TestConnection:
    def test_client_is_connected(self, jira: JiraPlus) -> None:
        result = jira.check_client_connection()
        assert result is True, "Expected active connection to Jira Cloud"

    def test_server_version_is_tuple(self, jira: JiraPlus) -> None:
        assert isinstance(jira.server_version, tuple), \
            f"Expected tuple, got {type(jira.server_version)}"
        assert len(jira.server_version) > 0, "Expected non-empty version tuple"

    def test_cloud_uses_legacy_api(self, jira: JiraPlus) -> None:
        assert jira.use_legacy_api is True, \
            "Cloud uses legacy createmeta API — project_issue_types is not supported for Cloud by the jira library"


class TestGetObjectsByQuery:
    def test_returns_list_of_issues(self, jira: JiraPlus, project_key: str, issue_type: str) -> None:
        query = f'project = "{project_key}" AND issuetype = "{issue_type}"'
        result = jira.get_objects_by_query(
            query=query,
            specific_fields=BASIC_FIELDS,
            max_results=10,
            json_result=True,
        )
        assert isinstance(result, list), f"Expected list, got {type(result)}"

    def test_returned_issues_have_basic_fields(self, jira: JiraPlus, project_key: str, issue_type: str) -> None:
        query = f'project = "{project_key}" AND issuetype = "{issue_type}"'
        result = jira.get_objects_by_query(
            query=query,
            specific_fields=BASIC_FIELDS,
            max_results=5,
            json_result=True,
        )
        if not result:
            pytest.skip(f"No issues found in project '{project_key}' with issue type '{issue_type}'")

        issue = result[0]
        assert "key" in issue, f"Expected 'key' in issue, got keys: {list(issue.keys())}"
        assert "fields" in issue, f"Expected 'fields' in issue, got keys: {list(issue.keys())}"

    def test_invalid_jql_raises(self, jira: JiraPlus) -> None:
        from jira import JIRAError
        with pytest.raises(JIRAError):
            jira.get_objects_by_query(query="INVALID JQL !!!", max_results=1)


class TestGetIssueByKey:
    def test_json_result_true_returns_dict(self, jira: JiraPlus, issue_key: str) -> None:
        result = jira.get_issue_by_key(key=issue_key, json_result=True)
        if result is None:
            pytest.skip(f"Issue '{issue_key}' not found — set JIRA_TEST_ISSUE_KEY to a valid key")
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "key" in result, f"Expected 'key' in result"

    def test_json_result_false_returns_issue_object(self, jira: JiraPlus, issue_key: str) -> None:
        from jira import Issue
        result = jira.get_issue_by_key(key=issue_key, json_result=False)
        if result is None:
            pytest.skip(f"Issue '{issue_key}' not found — set JIRA_TEST_ISSUE_KEY to a valid key")
        assert isinstance(result, Issue), f"Expected Issue object, got {type(result)}"

    def test_nonexistent_issue_returns_none(self, jira: JiraPlus) -> None:
        result = jira.get_issue_by_key(key="NONEXISTENT-99999999")
        assert result is None, "Expected None for a nonexistent issue key"


class TestGetAllowedValues:
    def test_returns_list_for_valid_field(
        self, jira: JiraPlus, project_key: str, issue_type: str, test_field: str
    ) -> None:
        result = jira.get_allowed_values(
            project_key=project_key,
            issue_type=issue_type,
            field_id_or_name=test_field,
        )
        assert result is None or isinstance(result, list), \
            f"Expected list or None, got {type(result)}"

    def test_invalid_field_raises_value_error(
        self, jira: JiraPlus, project_key: str, issue_type: str
    ) -> None:
        with pytest.raises(ValueError, match="not found"):
            jira.get_allowed_values(
                project_key=project_key,
                issue_type=issue_type,
                field_id_or_name="nonexistent_field_xyz_999",
            )
