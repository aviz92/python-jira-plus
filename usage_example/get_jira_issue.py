# get_jira_issue.py

import logging

from custom_python_logger.logger import build_logger

from python_jira_plus import JiraCloud

ISSUE_KEY = "Test-123"


def main() -> None:
    _ = build_logger(project_name="Logger Project Test", log_level=logging.DEBUG, extra={"user": "test_user"})

    jira_plus = JiraCloud()
    _ = jira_plus.get_issue_by_key(key=ISSUE_KEY)
    print()


if __name__ == "__main__":
    main()
