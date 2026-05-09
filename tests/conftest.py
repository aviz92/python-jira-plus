from unittest.mock import MagicMock, patch

import pytest

from python_jira_plus.jira_cloud import JiraCloud
from python_jira_plus.jira_on_premise import JiraOnPremise


def _build_jira_cloud(version: tuple[int, ...] = (9, 12, 0)) -> JiraCloud:
    mock_client = MagicMock()
    mock_client.projects.return_value = [MagicMock()]
    mock_client.server_info.return_value = {"versionNumbers": list(version)}

    with patch("python_jira_plus.jira_cloud.JIRA", return_value=mock_client):
        jp = JiraCloud(
            base_url="test.atlassian.net",
            jira_username="test@test.com",
            jira_token="test-token",
        )
    return jp


def _build_jira_on_premise(version: tuple[int, ...]) -> JiraOnPremise:
    mock_client = MagicMock()
    mock_client.projects.return_value = [MagicMock()]
    mock_client.server_info.return_value = {"versionNumbers": list(version)}

    with patch("python_jira_plus.jira_on_premise.JIRA", return_value=mock_client):
        jp = JiraOnPremise(
            base_url="jira.internal.com",
            jira_username="test@test.com",
            jira_token="test-token",
        )
    return jp


@pytest.fixture
def jira_plus_cloud() -> JiraCloud:
    return _build_jira_cloud()


@pytest.fixture
def jira_plus_on_premise_legacy() -> JiraOnPremise:
    return _build_jira_on_premise(version=(8, 5, 0))


@pytest.fixture
def jira_plus_on_premise_new() -> JiraOnPremise:
    return _build_jira_on_premise(version=(9, 0, 0))
