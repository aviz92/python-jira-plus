"""
Read/write integration tests against a real Jira Cloud instance.

These tests CREATE, UPDATE, TRANSITION, LINK and DELETE issues in the test project.
Every issue they create is deleted on teardown. Use a sandbox project.

Required env vars (loaded from .env):
    JIRA_USER_NAME, JIRA_TOKEN, JIRA_BASE_URL
    JIRA_TEST_PROJECT       sandbox project key the tests may write to (tests skip if unset)

Optional env vars:
    JIRA_TEST_ISSUE_TYPE    issue type to create (default: Task)

Run:
    uv run pytest tests/test_jira_cloud_write_integration.py -v
"""

# pylint: disable=no-self-use,redefined-outer-name,protected-access
import os
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from custom_python_logger import get_logger
from dotenv import load_dotenv
from jira import Issue, JIRAError

from python_jira_plus.consts import LOGGER_NAME
from python_jira_plus.jira_cloud import JiraCloud

load_dotenv()

pytestmark = pytest.mark.integration

logger = get_logger(LOGGER_NAME)

_REQUIRED_ENV = ("JIRA_USER_NAME", "JIRA_TOKEN", "JIRA_BASE_URL", "JIRA_TEST_PROJECT")
SUMMARY_PREFIX = "[python-jira-plus test]"
RUN_ID = str(int(time.time()))


class _NotYetVisibleError(AssertionError):
    """Raised while Jira's search index has not caught up with a write."""


def _eventually(check: Callable[[], Any], timeout: float = 30.0) -> Any:
    """Poll `check` until it stops raising `_NotYetVisibleError` (Jira search is eventually consistent)."""
    deadline = time.monotonic() + timeout
    while True:  # pylint: disable=while-used
        try:
            return check()
        except _NotYetVisibleError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)


@pytest.fixture(scope="module")
def jira() -> JiraCloud:
    if missing := [var for var in _REQUIRED_ENV if not os.getenv(var)]:
        pytest.skip(f"Missing required env vars: {', '.join(missing)}")
    return JiraCloud()


@pytest.fixture(scope="module")
def project_key() -> str:
    return os.environ["JIRA_TEST_PROJECT"]


@pytest.fixture(scope="module")
def issue_type() -> str:
    return os.getenv("JIRA_TEST_ISSUE_TYPE", "Task")


@pytest.fixture(scope="module")
def created_keys(jira: JiraCloud) -> Iterator[list[str]]:
    """Registry of every issue key created by this module; all are deleted on teardown."""
    keys: list[str] = []
    yield keys
    for key in keys:
        try:
            jira.jira_client.issue(key).delete()
            logger.info(f"Cleaned up {key}")
        except JIRAError as err:
            if err.status_code != 404:
                logger.error(f"Could not delete {key}: {err.text}")


@pytest.fixture(scope="module")
def make_issue(jira: JiraCloud, project_key: str, issue_type: str, created_keys: list[str]) -> Callable[..., Issue]:
    def _make(name: str, **kwargs: Any) -> Issue:
        issue = jira.create_issue(
            **{
                "project_key": project_key,
                "summary": f"{SUMMARY_PREFIX} {name} {RUN_ID}",
                "description": f"Created by automated test {name}",
                "issue_type": issue_type,
                **kwargs,
            }
        )
        assert issue is not None, f"create_issue returned None for {name}"
        created_keys.append(issue.key)
        return issue

    return _make


@pytest.fixture(scope="module")
def issue(make_issue: Callable[..., Issue]) -> Issue:
    """Shared issue for tests that mutate but do not delete."""
    return make_issue("shared")


class TestCreateIssue:
    def test_create_issue_basic_fields_returns_issue_with_values(
        self, jira: JiraCloud, issue: Issue, project_key: str, issue_type: str
    ) -> None:
        fetched = jira.get_issue_by_key(issue.key, json_result=False)

        assert fetched.key.startswith(f"{project_key}-"), f"Unexpected key {fetched.key}"
        assert fetched.fields.issuetype.name == issue_type
        assert fetched.fields.summary.startswith(SUMMARY_PREFIX)

    def test_create_issue_with_assignee_sets_assignee(self, jira: JiraCloud, make_issue: Callable[..., Issue]) -> None:
        account_id = jira.get_account_id(os.environ["JIRA_USER_NAME"])

        created = make_issue("assignee", assignee=account_id)

        assert jira.get_issue_by_key(created.key, json_result=False).fields.assignee.accountId == account_id

    def test_create_issue_priority_by_name_in_custom_fields_is_accepted(
        self, jira: JiraCloud, make_issue: Callable[..., Issue]
    ) -> None:
        created = make_issue("priority-name", custom_fields={"priority": {"name": "High"}})

        assert jira.get_issue_by_key(created.key, json_result=False).fields.priority.name == "High"

    def test_create_issue_priority_by_id_in_custom_fields_is_accepted(
        self, jira: JiraCloud, make_issue: Callable[..., Issue]
    ) -> None:
        priorities = jira.get_allowed_values(os.environ["JIRA_TEST_PROJECT"], "Task", "Priority")
        low = next(p for p in priorities if p["name"] == "Low")

        created = make_issue("priority-id", custom_fields={"priority": {"id": low["id"]}})

        assert jira.get_issue_by_key(created.key, json_result=False).fields.priority.name == "Low"

    def test_create_issue_labels_custom_field_is_accepted(
        self, jira: JiraCloud, make_issue: Callable[..., Issue]
    ) -> None:
        created = make_issue("labels", custom_fields={"labels": ["pjp-test"]})

        assert jira.get_issue_by_key(created.key, json_result=False).fields.labels == ["pjp-test"]

    def test_create_issue_conflicting_project_in_custom_fields_raises_before_creating(
        self, jira: JiraCloud, project_key: str, issue_type: str
    ) -> None:
        with pytest.raises(ValueError, match="conflicts with the dedicated argument"):
            jira.create_issue(project_key, "s", "d", issue_type, custom_fields={"project": {"key": "OTHER"}})

    def test_create_issue_invalid_priority_raises_with_allowed_values(
        self, jira: JiraCloud, project_key: str, issue_type: str
    ) -> None:
        with pytest.raises(ValueError, match="The allowed values are"):
            jira.create_issue(project_key, "s", "d", issue_type, custom_fields={"priority": {"name": "Nope"}})

    def test_create_issue_unknown_field_raises(self, jira: JiraCloud, project_key: str, issue_type: str) -> None:
        with pytest.raises(ValueError, match="Invalid field"):
            jira.create_issue(project_key, "s", "d", issue_type, custom_fields={"not_a_field": "x"})

    def test_create_issue_unknown_issue_type_raises(self, jira: JiraCloud, project_key: str) -> None:
        with pytest.raises(ValueError, match="not found"):
            jira.create_issue(project_key, "s", "d", "No Such Type")

    def test_create_issue_issue_type_is_case_insensitive(
        self, jira: JiraCloud, make_issue: Callable[..., Issue], issue_type: str
    ) -> None:
        created = make_issue("case", issue_type=issue_type.lower())

        assert jira.get_issue_by_key(created.key, json_result=False).fields.issuetype.name == issue_type

    def test_get_project_fields_metadata_issue_type_is_case_insensitive(
        self, jira: JiraCloud, project_key: str, issue_type: str
    ) -> None:
        exact = jira.get_project_fields_metadata(project_key, issue_type)

        assert jira.get_project_fields_metadata(project_key, issue_type.lower()).keys() == exact.keys()


class TestGetIssue:
    def test_get_issue_by_key_json_returns_raw_dict(self, jira: JiraCloud, issue: Issue) -> None:
        raw = jira.get_issue_by_key(issue.key)

        assert raw["key"] == issue.key

    def test_get_issue_by_key_specific_fields_limits_fields(self, jira: JiraCloud, issue: Issue) -> None:
        raw = jira.get_issue_by_key(issue.key, specific_fields=["summary"])

        assert set(raw["fields"]) == {"summary"}

    def test_get_issue_by_key_missing_issue_returns_none(self, jira: JiraCloud, project_key: str) -> None:
        assert jira.get_issue_by_key(f"{project_key}-99999999") is None

    def test_get_issue_by_key_missing_issue_with_raise_on_error_raises(self, project_key: str) -> None:
        strict = JiraCloud(raise_on_error=True)

        with pytest.raises(JIRAError):
            strict.get_issue_by_key(f"{project_key}-99999999")


class TestUpdateIssue:
    def test_update_issue_summary_persists(self, jira: JiraCloud, issue: Issue) -> None:
        new_summary = f"{SUMMARY_PREFIX} updated {RUN_ID}"

        result = jira.update_issue(issue.key, {"summary": new_summary})

        assert result is not None
        assert jira.get_issue_by_key(issue.key, json_result=False).fields.summary == new_summary

    def test_update_issue_priority_by_name_persists(self, jira: JiraCloud, issue: Issue) -> None:
        jira.update_issue(issue.key, {"priority": {"name": "Highest"}})

        assert jira.get_issue_by_key(issue.key, json_result=False).fields.priority.name == "Highest"

    def test_update_issue_priority_by_id_persists(self, jira: JiraCloud, issue: Issue) -> None:
        medium = next(
            p
            for p in jira.get_allowed_values(os.environ["JIRA_TEST_PROJECT"], "Task", "Priority")
            if p["name"] == "Medium"
        )

        jira.update_issue(issue.key, {"priority": {"id": medium["id"]}})

        assert jira.get_issue_by_key(issue.key, json_result=False).fields.priority.name == "Medium"

    def test_update_issue_invalid_value_raises_value_error_not_none(self, jira: JiraCloud, issue: Issue) -> None:
        with pytest.raises(ValueError, match="The allowed values are"):
            jira.update_issue(issue.key, {"priority": {"name": "Nope"}})

    def test_update_issue_field_not_on_edit_screen_raises(self, jira: JiraCloud, issue: Issue) -> None:
        with pytest.raises(ValueError, match="Invalid field"):
            jira.update_issue(issue.key, {"not_a_field": "x"})

    def test_update_issue_wrong_type_raises(self, jira: JiraCloud, issue: Issue) -> None:
        with pytest.raises(ValueError, match="must be a string"):
            jira.update_issue(issue.key, {"summary": 123})

    def test_update_issue_missing_issue_returns_none(self, jira: JiraCloud, project_key: str) -> None:
        assert jira.update_issue(f"{project_key}-99999999", {"summary": "x"}) is None

    def test_update_issue_missing_issue_with_raise_on_error_raises(self, project_key: str) -> None:
        strict = JiraCloud(raise_on_error=True)

        with pytest.raises(JIRAError):
            strict.update_issue(f"{project_key}-99999999", {"summary": "x"})


class TestComments:
    def test_add_comment_is_stored_on_issue(self, jira: JiraCloud, issue: Issue) -> None:
        body = f"comment {RUN_ID}"

        jira.add_comment(issue.key, body)

        comments = jira.jira_client.comments(issue.key)
        assert any(body in str(c.body) for c in comments), "Added comment not found on issue"


class TestTransitions:
    def test_transition_issue_lowercase_name_matches_and_changes_status(self, jira: JiraCloud, issue: Issue) -> None:
        assert jira.transition_issue(issue.key, "in progress") is True
        assert jira.get_issue_by_key(issue.key, json_result=False).fields.status.name.lower() == "in progress"

    def test_transition_issue_with_comment_adds_comment(self, jira: JiraCloud, issue: Issue) -> None:
        body = f"transition comment {RUN_ID}"

        assert jira.transition_issue(issue.key, "TO DO", comment=body) is True

        assert any(body in str(c.body) for c in jira.jira_client.comments(issue.key))
        assert jira.get_issue_by_key(issue.key, json_result=False).fields.status.name.lower() == "to do"

    def test_transition_issue_unknown_name_returns_false(self, jira: JiraCloud, issue: Issue) -> None:
        assert jira.transition_issue(issue.key, "no such transition") is False

    def test_transition_issue_unknown_name_with_raise_on_error_lists_available(self, issue: Issue) -> None:
        strict = JiraCloud(raise_on_error=True)

        with pytest.raises(ValueError, match="Available transitions"):
            strict.transition_issue(issue.key, "no such transition")


class TestLinks:
    def test_create_link_case_insensitive_type_creates_link(
        self, jira: JiraCloud, make_issue: Callable[..., Issue]
    ) -> None:
        first, second = make_issue("link-a"), make_issue("link-b")

        assert jira.create_link(first.key, "relates", second.key) is True

        links = jira.get_issue_by_key(first.key, json_result=False).fields.issuelinks
        linked = {(link.inwardIssue.key if hasattr(link, "inwardIssue") else link.outwardIssue.key) for link in links}
        assert second.key in linked

    def test_create_link_invalid_type_raises_with_available_types(self, jira: JiraCloud, issue: Issue) -> None:
        with pytest.raises(ValueError, match="Available link types"):
            jira.create_link(issue.key, "not-a-link-type", issue.key)

    def test_create_link_missing_issue_returns_false(self, jira: JiraCloud, issue: Issue, project_key: str) -> None:
        assert jira.create_link(issue.key, "Relates", f"{project_key}-99999999") is False


class TestAttachments:
    def test_upload_attachment_returns_true_and_attaches_file(
        self, jira: JiraCloud, issue: Issue, tmp_path: Path
    ) -> None:
        file = tmp_path / f"pjp-{RUN_ID}.txt"
        file.write_text("attachment body")

        assert jira.upload_attachment(issue.key, str(file)) is True

        names = [a.filename for a in jira.get_issue_by_key(issue.key, json_result=False).fields.attachment]
        assert file.name in names

    def test_upload_attachment_missing_file_returns_false(self, jira: JiraCloud, issue: Issue) -> None:
        assert jira.upload_attachment(issue.key, "/no/such/file.txt") is False

    def test_upload_attachment_missing_file_with_raise_on_error_raises(self, issue: Issue) -> None:
        strict = JiraCloud(raise_on_error=True)

        with pytest.raises(OSError):
            strict.upload_attachment(issue.key, "/no/such/file.txt")


class TestQueries:
    def test_get_objects_by_query_finds_created_issue(self, jira: JiraCloud, issue: Issue) -> None:
        def check() -> list:
            if not (found := jira.get_objects_by_query(f"key = {issue.key}")):
                raise _NotYetVisibleError(f"{issue.key} not indexed yet")
            return found

        assert _eventually(check)[0]["key"] == issue.key

    @pytest.mark.usefixtures("issue")
    def test_get_objects_by_query_limit_caps_total(self, jira: JiraCloud, project_key: str) -> None:
        def check() -> list:
            found = jira.get_objects_by_query(f"project = {project_key} ORDER BY key", max_results=1, limit=2)
            if len(found) < 2:
                raise _NotYetVisibleError("fewer than 2 issues indexed")
            return found

        assert len(_eventually(check)) == 2

    @pytest.mark.usefixtures("issue")
    def test_get_objects_by_query_pages_through_all_results_without_limit(
        self, jira: JiraCloud, project_key: str
    ) -> None:
        everything = jira.get_objects_by_query(f"project = {project_key} ORDER BY key", max_results=1)
        capped = jira.get_objects_by_query(f"project = {project_key} ORDER BY key", max_results=1, limit=1)

        assert len(capped) == 1
        assert capped[0]["key"] in {i["key"] for i in everything}
        assert len(everything) > len(capped), "Expected unlimited query to page past the first result"

    def test_get_objects_by_query_invalid_jql_raises_jira_error(self, jira: JiraCloud) -> None:
        with pytest.raises(JIRAError, match="400"):
            jira.get_objects_by_query("this is !!! not jql")

    def test_get_objects_by_query_invalid_jql_fails_fast(self, jira: JiraCloud) -> None:
        started = time.monotonic()
        with pytest.raises(JIRAError):
            jira.get_objects_by_query("this is !!! not jql")

        assert time.monotonic() - started < 30, "A rejected query must fail fast"


class TestMetadata:
    def test_get_allowed_values_priority_contains_names_and_ids(
        self, jira: JiraCloud, project_key: str, issue_type: str
    ) -> None:
        allowed = jira.get_allowed_values(project_key, issue_type, "Priority")

        assert {"name", "id"} <= set(allowed[0])

    def test_validate_fields_accepts_name_and_id_forms(
        self, jira: JiraCloud, project_key: str, issue_type: str
    ) -> None:
        first = jira.get_allowed_values(project_key, issue_type, "Priority")[0]

        jira.validate_fields(project_key, issue_type, {"priority": {"name": first["name"]}})
        jira.validate_fields(project_key, issue_type, {"priority": {"id": first["id"]}})

    def test_validate_fields_rejects_unknown_value(self, jira: JiraCloud, project_key: str, issue_type: str) -> None:
        with pytest.raises(ValueError, match="Invalid value"):
            jira.validate_fields(project_key, issue_type, {"priority": {"name": "Nope"}})


class TestAccounts:
    def test_get_account_id_own_username_returns_id(self, jira: JiraCloud) -> None:
        assert jira.get_account_id(os.environ["JIRA_USER_NAME"])

    def test_get_account_display_name_own_username_returns_name(self, jira: JiraCloud) -> None:
        assert jira.get_account_display_name(os.environ["JIRA_USER_NAME"])

    def test_get_account_id_unknown_user_raises_value_error(self, jira: JiraCloud) -> None:
        with pytest.raises(ValueError, match="No Jira user found"):
            jira.get_account_id("zz-no-such-user-9f3k@example.invalid")


class TestDeleteIssue:
    def test_delete_issue_removes_issue(self, jira: JiraCloud, make_issue: Callable[..., Issue]) -> None:
        doomed = make_issue("delete-me")

        assert jira.delete_issue(doomed.key) is True
        assert jira.get_issue_by_key(doomed.key) is None

    def test_delete_issue_missing_issue_returns_false(self, jira: JiraCloud, project_key: str) -> None:
        assert jira.delete_issue(f"{project_key}-99999999") is False

    def test_delete_issue_missing_issue_with_raise_on_error_raises(self, project_key: str) -> None:
        strict = JiraCloud(raise_on_error=True)

        with pytest.raises(JIRAError):
            strict.delete_issue(f"{project_key}-99999999")


class TestConnection:
    def test_check_client_connection_open_client_returns_true(self, jira: JiraCloud) -> None:
        assert jira.check_client_connection() is True

    def test_constructor_base_url_with_scheme_and_slash_connects(self) -> None:
        host = os.environ["JIRA_BASE_URL"].removeprefix("https://").rstrip("/")

        client = JiraCloud(base_url=f"https://{host}/")

        assert client.server == f"https://{host}"
        assert client.check_client_connection() is True

    def test_constructor_bad_token_raises_jira_error(self) -> None:
        with pytest.raises(JIRAError):
            JiraCloud(jira_token="definitely-not-a-valid-token")

    def test_close_connection_does_not_raise(self) -> None:
        client = JiraCloud()

        client.close_connection()
