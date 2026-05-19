# create_jira_issue.py

import logging

from custom_python_logger.logger import build_logger

from python_jira_plus import JiraCloud
from python_jira_plus.consts import LOGGER_NAME


def main() -> None:
    _ = build_logger(project_name=LOGGER_NAME, log_level=logging.DEBUG, extra={"user": "test_user"})

    jira_plus = JiraCloud()
    _ = jira_plus.create_issue(
        project_key="SCRUM",
        issue_type="Story",
        summary="Test issue",
        description="This is a test issue.",
    )


if __name__ == "__main__":
    main()
