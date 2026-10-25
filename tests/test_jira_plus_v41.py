# pylint: disable=no-self-use
from collections.abc import Callable
from unittest.mock import MagicMock

import pytest

from python_jira_plus.helpers import check_issue_ref
from python_jira_plus.jira_base import JiraBase
from python_jira_plus.jira_cloud import JiraCloud

BAD_KEY = "PROJ-1/../myself"
ISSUE_METHODS: list[tuple[str, Callable[[JiraBase], object]]] = [
    ("get_issue_by_key", lambda jp: jp.get_issue_by_key(BAD_KEY)),
    ("update_issue", lambda jp: jp.update_issue(BAD_KEY, {"summary": "x"})),
    ("delete_issue", lambda jp: jp.delete_issue(BAD_KEY)),
    ("add_comment", lambda jp: jp.add_comment(BAD_KEY, "hi")),
    ("upload_attachment", lambda jp: jp.upload_attachment(BAD_KEY, "f.txt")),
    ("get_transitions", lambda jp: jp.get_transitions(BAD_KEY)),
    ("transition_issue", lambda jp: jp.transition_issue(BAD_KEY, "Done")),
    ("create_link (inward)", lambda jp: jp.create_link(BAD_KEY, "Blocks", "PROJ-2")),
    ("create_link (outward)", lambda jp: jp.create_link("PROJ-2", "Blocks", BAD_KEY)),
]


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

    @pytest.mark.parametrize("ref", [BAD_KEY, "PROJ-1?x=1", "", "a b", "PROJ-1#x"])
    def test_invalid(self, ref: str) -> None:
        with pytest.raises(ValueError, match="Invalid issue key"):
            check_issue_ref(ref)

    @pytest.mark.parametrize("call", [c for _, c in ISSUE_METHODS], ids=[n for n, _ in ISSUE_METHODS])
    def test_every_issue_method_rejects_before_any_request(
        self, jira_plus_cloud: JiraCloud, call: Callable[[JiraBase], object]
    ) -> None:
        jira = jira_plus_cloud.jira_client
        jira.reset_mock()
        with pytest.raises(ValueError, match="Invalid issue key"):
            call(jira_plus_cloud)  # raised even with raise_on_error=False
        assert not jira.method_calls, jira.method_calls

    def test_valid_key_still_reaches_jira(self, jira_plus_cloud: JiraCloud) -> None:
        jira_plus_cloud.add_comment("PROJ-1", "hi")
        jira_plus_cloud.jira_client.add_comment.assert_called_once_with(issue="PROJ-1", body="hi")
