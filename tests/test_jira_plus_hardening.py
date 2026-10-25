# pylint: disable=no-self-use,protected-access
from unittest.mock import MagicMock, patch

import pytest
from jira import JIRAError

from python_jira_plus.jira_base import JiraBase
from python_jira_plus.jira_cloud import JiraCloud
from python_jira_plus.jira_on_premise import JiraOnPremise
from tests.conftest import _build_jira_cloud


def _named(name: str, **attrs: str) -> MagicMock:
    mock = MagicMock(**attrs)
    mock.name = name
    return mock


class TestIsValueAllowed:
    @pytest.mark.parametrize(
        "value, allowed",
        [
            ({"value": "High"}, [{"id": "1", "value": "High"}]),
            ({"id": "1"}, [{"id": "1", "name": "Highest"}]),
            ({"name": "Bug"}, [{"name": "Bug"}]),
            ("PROJ", [{"key": "PROJ"}]),
        ],
    )
    def test_matches_name_key_value_or_id(self, value: object, allowed: list) -> None:
        assert JiraBase._is_value_allowed(value, allowed) is True

    def test_missing_keys_are_not_treated_as_allowed_none(self) -> None:
        assert JiraBase._is_value_allowed({"id": None}, [{"name": "Bug"}]) is False


class TestUpdateIssue:
    def test_validates_against_edit_metadata(self, jira_plus_cloud: JiraCloud) -> None:
        client = jira_plus_cloud.jira_client
        client.editmeta.return_value = {"fields": {"labels": {"schema": {"type": "array"}, "name": "Labels"}}}

        result = jira_plus_cloud.update_issue("PROJ-1", {"labels": ["a"]})

        client.editmeta.assert_called_once_with("PROJ-1")
        client.createmeta.assert_not_called()
        client.issue.return_value.update.assert_called_once_with(fields={"labels": ["a"]})
        assert result is client.issue.return_value

    def test_validation_error_propagates(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.editmeta.return_value = {"fields": {}}

        with pytest.raises(ValueError, match="Invalid field"):
            jira_plus_cloud.update_issue("PROJ-1", {"nope": 1})

    def test_jira_error_returns_none_by_default(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.issue.side_effect = JIRAError("boom", status_code=500)

        assert jira_plus_cloud.update_issue("PROJ-1", {"summary": "x"}) is None


class TestCreateIssueCustomFields:
    def test_conflicting_project_is_rejected(self, jira_plus_cloud: JiraCloud) -> None:
        with pytest.raises(ValueError, match="conflicts"):
            jira_plus_cloud.create_issue("PROJ", "s", "d", "Bug", custom_fields={"project": {"key": "OTHER"}})
        jira_plus_cloud.jira_client.create_issue.assert_not_called()


class TestTransitionIssue:
    def test_case_insensitive_match(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.transitions.return_value = [{"id": "31", "name": "Done"}]

        assert jira_plus_cloud.transition_issue("PROJ-1", "done") is True
        assert jira_plus_cloud.jira_client.transition_issue.call_args.kwargs["transition"] == "31"

    def test_unknown_transition_returns_false_or_raises(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.transitions.return_value = [{"id": "31", "name": "Done"}]
        assert jira_plus_cloud.transition_issue("PROJ-1", "nope") is False

        jira_plus_cloud.raise_on_error = True
        with pytest.raises(ValueError, match="Available transitions"):
            jira_plus_cloud.transition_issue("PROJ-1", "nope")


class TestTransitionComment:
    def test_comment_sent_inline_when_screen_has_comment_field(self, jira_plus_cloud: JiraCloud) -> None:
        client = jira_plus_cloud.jira_client
        client.transitions.return_value = [{"id": "31", "name": "Done", "fields": {"comment": {}}}]

        assert jira_plus_cloud.transition_issue("PROJ-1", "Done", comment="hi") is True

        assert client.transition_issue.call_args.kwargs["comment"] == "hi"
        client.add_comment.assert_not_called()

    def test_comment_added_separately_when_screen_lacks_comment_field(self, jira_plus_cloud: JiraCloud) -> None:
        client = jira_plus_cloud.jira_client
        client.transitions.return_value = [{"id": "31", "name": "Done", "fields": {}}]

        assert jira_plus_cloud.transition_issue("PROJ-1", "Done", comment="hi") is True

        assert client.transition_issue.call_args.kwargs["comment"] is None
        client.add_comment.assert_called_once_with(issue="PROJ-1", body="hi")


class TestCreateIssueCanonicalType:
    def test_wrong_cased_issue_type_is_sent_with_real_casing(self, jira_plus_cloud: JiraCloud) -> None:
        client = jira_plus_cloud.jira_client
        client.createmeta.return_value = {
            "projects": [
                {
                    "key": "PROJ",
                    "issuetypes": [
                        {
                            "name": "Task",
                            "fields": {
                                "project": {"schema": {"type": "project"}, "name": "Project"},
                                "issuetype": {
                                    "schema": {"type": "issuetype"},
                                    "name": "Issue Type",
                                    "allowedValues": [{"name": "Task"}],
                                },
                                "summary": {"schema": {"type": "string"}, "name": "Summary"},
                                "description": {"schema": {"type": "string"}, "name": "Description"},
                            },
                        }
                    ],
                }
            ]
        }

        jira_plus_cloud.create_issue("PROJ", "s", "d", "task")

        assert client.create_issue.call_args.kwargs["fields"]["issuetype"] == {"name": "Task"}

    def test_createmeta_retries_unfiltered_when_name_casing_differs(self, jira_plus_cloud: JiraCloud) -> None:
        client = jira_plus_cloud.jira_client
        full = {"projects": [{"key": "PROJ", "issuetypes": [{"name": "Task", "fields": {"summary": {}}}]}]}
        client.createmeta.side_effect = [{"projects": [{"key": "PROJ", "issuetypes": []}]}, full]

        assert jira_plus_cloud.get_project_fields_metadata("PROJ", "task") == {"summary": {}}
        assert "issuetypeNames" not in client.createmeta.call_args_list[1].kwargs


class TestRaiseOnError:
    def test_get_issue_raises_original_error(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.raise_on_error = True
        jira_plus_cloud.jira_client.issue.side_effect = JIRAError("nf", status_code=404)

        with pytest.raises(JIRAError):
            jira_plus_cloud.get_issue_by_key("PROJ-1")

    def test_upload_attachment_returns_bool(self, jira_plus_cloud: JiraCloud) -> None:
        assert jira_plus_cloud.upload_attachment("PROJ-1", "f.txt") is True
        jira_plus_cloud.jira_client.add_attachment.side_effect = JIRAError("x", status_code=500)
        assert jira_plus_cloud.upload_attachment("PROJ-1", "f.txt") is False


class TestCreateLink:
    def test_case_insensitive_and_uses_canonical_name(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.issue_link_types.return_value = [_named("Blocks")]

        assert jira_plus_cloud.create_link("A-1", "blocks", "B-2") is True
        assert jira_plus_cloud.jira_client.create_issue_link.call_args.kwargs["type"] == "Blocks"

    def test_lookup_failure_is_not_reported_as_empty_set(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.issue_link_types.side_effect = JIRAError("x", status_code=500)

        assert jira_plus_cloud.create_link("A-1", "Blocks", "B-2") is False


class TestConstructor:
    @pytest.fixture(autouse=True)
    def _no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in ("JIRA_USER_NAME", "JIRA_TOKEN", "JIRA_BASE_URL"):
            monkeypatch.delenv(name, raising=False)

    def test_missing_base_url_raises(self) -> None:
        with patch("python_jira_plus.jira_base.load_dotenv"), pytest.raises(ValueError, match="base URL"):
            JiraCloud(jira_username="u", jira_token="t")

    def test_missing_token_raises(self) -> None:
        with patch("python_jira_plus.jira_base.load_dotenv"), pytest.raises(ValueError, match="token"):
            JiraCloud(base_url="x.atlassian.net", jira_username="u")

    def test_on_premise_token_auth_needs_no_username(self) -> None:
        client = MagicMock()
        client.server_info.return_value = {"versionNumbers": [9, 0, 0]}
        with patch("python_jira_plus.jira_on_premise.JIRA", return_value=client):
            jira = JiraOnPremise(base_url="jira.internal", jira_token="t")
        assert jira.server == "https://jira.internal"

    def test_scheme_in_base_url_is_not_doubled(self) -> None:
        client = MagicMock()
        client.server_info.return_value = {"versionNumbers": [9, 0, 0]}
        with patch("python_jira_plus.jira_cloud.JIRA", return_value=client):
            jira = JiraCloud(base_url="http://x.atlassian.net/", jira_username="u", jira_token="t")
        assert jira.server == "http://x.atlassian.net"

    def test_projects_called_once_on_construction(self) -> None:
        jira = _build_jira_cloud()
        assert jira.jira_client.projects.call_count == 1


class TestCloudLimit:
    def test_limit_caps_total_and_page_size(self, jira_plus_cloud: JiraCloud) -> None:
        page1 = {"issues": [{"key": "1"}, {"key": "2"}], "isLast": False, "nextPageToken": "t"}
        page2 = {"issues": [{"key": "3"}], "isLast": False, "nextPageToken": "t2"}
        jira_plus_cloud.jira_client.enhanced_search_issues.side_effect = [page1, page2]

        result = jira_plus_cloud.get_objects_by_query("q", max_results=2, limit=3)

        assert [i["key"] for i in result] == ["1", "2", "3"]
        sizes = [c.kwargs["maxResults"] for c in jira_plus_cloud.jira_client.enhanced_search_issues.call_args_list]
        assert sizes == [2, 1]


class TestOnPremisePagination:
    def test_stops_when_total_reached(self, jira_plus_on_premise_legacy: JiraOnPremise) -> None:
        client = jira_plus_on_premise_legacy.jira_client
        client.search_issues.return_value = {"issues": [{"key": str(i)} for i in range(10)], "total": 10}

        result = jira_plus_on_premise_legacy.get_objects_by_query("q")

        assert len(result) == 10
        assert client.search_issues.call_count == 1

    def test_stops_on_empty_issues(self, jira_plus_on_premise_legacy: JiraOnPremise) -> None:
        client = jira_plus_on_premise_legacy.jira_client
        client.search_issues.return_value = {"issues": [], "total": 99}

        assert jira_plus_on_premise_legacy.get_objects_by_query("q") == []
        assert client.search_issues.call_count == 1

    def test_pages_until_total(self, jira_plus_on_premise_legacy: JiraOnPremise) -> None:
        client = jira_plus_on_premise_legacy.jira_client
        client.search_issues.side_effect = [
            {"issues": [{"key": "1"}, {"key": "2"}], "total": 3},
            {"issues": [{"key": "3"}], "total": 3},
        ]

        result = jira_plus_on_premise_legacy.get_objects_by_query("q", max_results=2, limit=10)

        assert [i["key"] for i in result] == ["1", "2", "3"]


class TestIssueTypeLookup:
    def test_on_premise_new_api_is_case_insensitive(self, jira_plus_on_premise_new: JiraOnPremise) -> None:
        client = jira_plus_on_premise_new.jira_client
        bug = _named("Bug", id="10")
        client.project_issue_types.return_value = [bug]
        field = MagicMock(fieldId="summary", raw={"name": "Summary"})
        client.project_issue_fields.return_value = [field]

        assert jira_plus_on_premise_new.get_project_fields_metadata("P", "bug") == {"summary": {"name": "Summary"}}

    def test_unknown_issue_type_lists_available(self, jira_plus_on_premise_new: JiraOnPremise) -> None:
        jira_plus_on_premise_new.jira_client.project_issue_types.return_value = [_named("Bug", id="10")]

        with pytest.raises(ValueError, match=r"Available issue types: \['Bug'\]"):
            jira_plus_on_premise_new.get_project_fields_metadata("P", "Epic")


class TestAccountLookup:
    def test_no_match_raises_value_error(self, jira_plus_cloud: JiraCloud) -> None:
        with patch.object(JiraCloud, "get_account_data", return_value=[]):
            with pytest.raises(ValueError, match="No Jira user"):
                jira_plus_cloud.get_account_id("nobody@x.com")

    def test_verify_ssl_is_forwarded(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.verify_ssl = False
        with patch("python_jira_plus.jira_cloud.requests.get") as get:
            jira_plus_cloud.get_account_data("a@b.com")
        assert get.call_args.kwargs["verify"] is False


class TestTransitionCommentFailure:
    def test_comment_failure_after_successful_transition_still_returns_true(self, jira_plus_cloud: JiraCloud) -> None:
        client = jira_plus_cloud.jira_client
        client.transitions.return_value = [{"id": "31", "name": "Done", "fields": {}}]
        client.add_comment.side_effect = JIRAError("nope", status_code=403)

        assert jira_plus_cloud.transition_issue("PROJ-1", "Done", comment="hi") is True

    def test_comment_failure_with_raise_on_error_raises(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.raise_on_error = True
        client = jira_plus_cloud.jira_client
        client.transitions.return_value = [{"id": "31", "name": "Done", "fields": {}}]
        client.add_comment.side_effect = JIRAError("nope", status_code=403)

        with pytest.raises(JIRAError):
            jira_plus_cloud.transition_issue("PROJ-1", "Done", comment="hi")


class TestValidateFieldsMetadataReuse:
    def test_validate_fields_uses_passed_metadata_without_fetching(self, jira_plus_cloud: JiraCloud) -> None:
        metadata = {"summary": {"schema": {"type": "string"}, "name": "Summary"}}

        jira_plus_cloud.validate_fields("PROJ", "Task", {"summary": "ok"}, fields_metadata=metadata)

        jira_plus_cloud.jira_client.createmeta.assert_not_called()


class TestPublicLookups:
    def test_get_transitions_returns_id_and_name_only(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.transitions.return_value = [
            {"id": "11", "name": "To Do", "fields": {"comment": {}}},
            {"id": "31", "name": "Done", "fields": {}},
        ]

        assert jira_plus_cloud.get_transitions("PROJ-1") == [
            {"id": "11", "name": "To Do"},
            {"id": "31", "name": "Done"},
        ]
        jira_plus_cloud.jira_client.transitions.assert_called_once_with("PROJ-1", expand="transitions.fields")

    def test_get_transitions_no_transitions_returns_empty_list(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.transitions.return_value = []

        assert jira_plus_cloud.get_transitions("PROJ-1") == []

    def test_get_link_types_returns_name_inward_outward(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.issue_link_types.return_value = [
            _named("Blocks", inward="is blocked by", outward="blocks"),
        ]

        assert jira_plus_cloud.get_link_types() == [
            {"name": "Blocks", "inward": "is blocked by", "outward": "blocks"},
        ]

    def test_create_link_uses_get_link_types_for_lookup(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.jira_client.issue_link_types.return_value = [
            _named("Relates", inward="relates to", outward="relates to"),
        ]

        assert jira_plus_cloud.create_link("A-1", "RELATES", "B-2") is True
        assert jira_plus_cloud.jira_client.create_issue_link.call_args.kwargs["type"] == "Relates"
