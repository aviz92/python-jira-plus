# pylint: disable=no-self-use,protected-access
from unittest.mock import MagicMock, patch

import pytest
from jira import JIRAError

from python_jira_plus.jira_cloud import JiraCloud
from python_jira_plus.jira_on_premise import JiraOnPremise


def _make_issue_type_mock(name: str, issue_id: str) -> MagicMock:
    mock = MagicMock()
    mock.name = name
    mock.id = issue_id
    return mock


def _make_field_mock(field_id: str, raw: dict) -> MagicMock:
    mock = MagicMock()
    mock.fieldId = field_id
    mock.raw = raw
    return mock


class TestResolveLegacyApi:
    def test_cloud_uses_legacy_api(self, jira_plus_cloud: JiraCloud) -> None:
        assert (
            jira_plus_cloud.use_createmeta is True
        ), "Cloud always uses createmeta — project_issue_types is not supported for Cloud by the jira library"

    def test_on_premise_below_9_uses_legacy_api(self, jira_plus_on_premise_legacy: JiraOnPremise) -> None:
        assert jira_plus_on_premise_legacy.use_createmeta is True, "ON_PREMISE < 9.0 should use createmeta API"

    def test_on_premise_9_and_above_uses_new_api(self, jira_plus_on_premise_new: JiraOnPremise) -> None:
        assert (
            jira_plus_on_premise_new.use_createmeta is False
        ), "ON_PREMISE >= 9.0 should use project_issue_types / project_issue_fields API"


class TestGetIssueByKey:
    def test_json_result_true_returns_raw_dict(self, jira_plus_cloud: JiraCloud) -> None:
        mock_issue = MagicMock()
        mock_issue.raw = {"key": "PROJ-1", "fields": {}}
        jira_plus_cloud.jira_client.issue.return_value = mock_issue

        result = jira_plus_cloud.get_issue_by_key(key="PROJ-1", json_result=True)

        assert result == {"key": "PROJ-1", "fields": {}}, f"Expected raw dict, got {result}"

    def test_json_result_false_returns_issue_object(self, jira_plus_cloud: JiraCloud) -> None:
        mock_issue = MagicMock()
        jira_plus_cloud.jira_client.issue.return_value = mock_issue

        result = jira_plus_cloud.get_issue_by_key(key="PROJ-1", json_result=False)

        assert result is mock_issue, "Expected Issue object, not raw dict"

    def test_jira_error_returns_none(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.issue.side_effect = JIRAError("Not found", status_code=404)

        result = jira_plus_cloud.get_issue_by_key(key="PROJ-999")

        assert result is None, "Expected None on JIRAError"

    def test_unexpected_error_returns_none(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.issue.side_effect = RuntimeError("network failure")

        result = jira_plus_cloud.get_issue_by_key(key="PROJ-1")

        assert result is None, "Expected None on unexpected error"


class TestDeleteIssue:
    def test_success_returns_true_and_calls_delete(self, jira_plus_cloud: JiraCloud) -> None:
        mock_issue = MagicMock()
        jira_plus_cloud.jira_client.issue.return_value = mock_issue

        result = jira_plus_cloud.delete_issue("PROJ-1")

        assert result is True, "Expected True on successful delete"
        mock_issue.delete.assert_called_once()

    def test_jira_error_returns_false(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.issue.side_effect = JIRAError("Forbidden", status_code=403)

        result = jira_plus_cloud.delete_issue("PROJ-1")

        assert result is False, "Expected False on JIRAError"

    def test_unexpected_error_returns_false(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.issue.side_effect = RuntimeError("network failure")

        result = jira_plus_cloud.delete_issue("PROJ-1")

        assert result is False, "Expected False on unexpected error"


class TestValidateFields:
    def _setup_createmeta(self, jira_plus: JiraCloud, fields: dict) -> None:
        jira_plus.jira_client.createmeta.return_value = {
            "projects": [
                {
                    "key": "PROJ",
                    "issuetypes": [{"name": "Story", "fields": fields}],
                }
            ]
        }

    def test_valid_string_field_raises_no_error(self, jira_plus_cloud: JiraCloud) -> None:
        self._setup_createmeta(
            jira_plus_cloud,
            {
                "summary": {"schema": {"type": "string"}, "name": "Summary"},
            },
        )

        jira_plus_cloud.validate_fields("PROJ", "Story", {"summary": "Hello"})

    def test_field_not_in_metadata_raises_value_error(self, jira_plus_cloud: JiraCloud) -> None:
        self._setup_createmeta(
            jira_plus_cloud,
            {
                "summary": {"schema": {"type": "string"}, "name": "Summary"},
            },
        )

        with pytest.raises(ValueError, match="Invalid field"):
            jira_plus_cloud.validate_fields("PROJ", "Story", {"nonexistent_field": "value"})

    def test_wrong_type_for_string_field_raises_value_error(self, jira_plus_cloud: JiraCloud) -> None:
        self._setup_createmeta(
            jira_plus_cloud,
            {
                "summary": {"schema": {"type": "string"}, "name": "Summary"},
            },
        )

        with pytest.raises(ValueError, match="must be a string"):
            jira_plus_cloud.validate_fields("PROJ", "Story", {"summary": 123})

    def test_wrong_type_for_number_field_raises_value_error(self, jira_plus_cloud: JiraCloud) -> None:
        self._setup_createmeta(
            jira_plus_cloud,
            {
                "story_points": {"schema": {"type": "number"}, "name": "Story Points"},
            },
        )

        with pytest.raises(ValueError, match="must be a number"):
            jira_plus_cloud.validate_fields("PROJ", "Story", {"story_points": "five"})

    def test_invalid_allowed_value_raises_value_error(self, jira_plus_cloud: JiraCloud) -> None:
        self._setup_createmeta(
            jira_plus_cloud,
            {
                "priority": {
                    "schema": {"type": "string"},
                    "name": "Priority",
                    "allowedValues": [{"name": "High"}, {"name": "Low"}],
                },
            },
        )

        with pytest.raises(ValueError, match="Invalid value"):
            jira_plus_cloud.validate_fields("PROJ", "Story", {"priority": "Critical"})


class TestPaginateQueryNew:
    def test_single_page_returns_issues(self, jira_plus_cloud: JiraCloud) -> None:
        issues = [{"key": "PROJ-1"}, {"key": "PROJ-2"}]
        jira_plus_cloud.jira_client.enhanced_search_issues.return_value = {
            "issues": issues,
            "isLast": True,
        }

        result = jira_plus_cloud._paginate(
            query="project = PROJ",
            max_results=50,
            specific_fields="*all",
            jira_err_limit=3,
            json_result=True,
        )

        assert result == issues, f"Expected {issues}, got {result}"

    def test_multiple_pages_accumulates_all_issues(self, jira_plus_cloud: JiraCloud) -> None:
        page1 = {"issues": [{"key": "PROJ-1"}], "isLast": False, "nextPageToken": "token-2"}
        page2 = {"issues": [{"key": "PROJ-2"}], "isLast": True}
        jira_plus_cloud.jira_client.enhanced_search_issues.side_effect = [page1, page2]

        result = jira_plus_cloud._paginate(
            query="project = PROJ",
            max_results=50,
            specific_fields="*all",
            jira_err_limit=3,
            json_result=True,
        )

        assert result == [{"key": "PROJ-1"}, {"key": "PROJ-2"}], f"Expected both pages merged, got {result}"

    def test_empty_page_returns_empty_list(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.enhanced_search_issues.return_value = {}

        result = jira_plus_cloud._paginate(
            query="project = PROJ",
            max_results=50,
            specific_fields="*all",
            jira_err_limit=3,
            json_result=True,
        )

        assert result == [], f"Expected empty list, got {result}"

    def test_bad_request_raises_jira_error(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.enhanced_search_issues.side_effect = JIRAError("Bad JQL", status_code=400)

        with pytest.raises(JIRAError):
            jira_plus_cloud._paginate(
                query="invalid JQL !!!",
                max_results=50,
                specific_fields="*all",
                jira_err_limit=3,
                json_result=True,
            )


class TestGetAccountData:
    def test_success_returns_user_list(self, jira_plus_cloud: JiraCloud) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = [{"accountId": "abc123", "displayName": "Test User"}]

        with patch("python_jira_plus.jira_cloud.requests.get", return_value=mock_response):
            result = jira_plus_cloud.get_account_data("test@test.com")

        assert result[0]["accountId"] == "abc123", f"Expected 'abc123', got {result[0]['accountId']}"
        mock_response.raise_for_status.assert_called_once()

    def test_http_error_raises(self, jira_plus_cloud: JiraCloud) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")

        with patch("python_jira_plus.jira_cloud.requests.get", return_value=mock_response):
            with pytest.raises(Exception, match="401"):
                jira_plus_cloud.get_account_data("bad@test.com")
