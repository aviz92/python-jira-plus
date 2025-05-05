# get_jira_issue.py

import logging
from custom_python_logger.logger import get_logger

from python_jira_plus.jira_plus import JiraPlus

ISSUE_KEY = 'Test-123'


def main():
    _ = get_logger(
        project_name='Logger Project Test',
        log_level=logging.DEBUG,
        extra={'user': 'test_user'}
    )

    jira_plus = JiraPlus()
    _ = jira_plus.get_issue_by_key(key=ISSUE_KEY)
    print()


if __name__ == '__main__':
    main()
