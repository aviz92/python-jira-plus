from unittest.mock import MagicMock, patch

import pytest

from python_jira_plus.jira_plus import JiraPlus, ServerType


def _build_jira_plus(server_type: ServerType, version: tuple[int, ...]) -> JiraPlus:
    mock_client = MagicMock()
    mock_client.projects.return_value = [MagicMock()]
    mock_client.server_info.return_value = {"versionNumbers": list(version)}

    with patch("python_jira_plus.jira_plus.JIRA", return_value=mock_client):
        jp = JiraPlus(
            base_url="test.atlassian.net",
            jira_username="test@test.com",
            jira_token="test-token",
            server_type=server_type,
        )
    return jp


@pytest.fixture
def jira_plus_cloud() -> JiraPlus:
    return _build_jira_plus(ServerType.CLOUD, (9, 12, 0))


@pytest.fixture
def jira_plus_on_premise_legacy() -> JiraPlus:
    return _build_jira_plus(ServerType.ON_PREMISE, (8, 5, 0))


@pytest.fixture
def jira_plus_on_premise_new() -> JiraPlus:
    return _build_jira_plus(ServerType.ON_PREMISE, (9, 0, 0))
