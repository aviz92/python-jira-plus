# update_jira_issue.py

import logging
from custom_python_logger.logger import build_logger

from python_jira_plus.jira_plus import JiraPlus

ISSUE_KEY = 'Test-123'


def main():
    _ = build_logger(
        project_name='Logger Project Test',
        log_level=logging.DEBUG,
        extra={'user': 'test_user'}
    )

    jira_plus = JiraPlus()
    _ = jira_plus.update_issue(
        issue_key=ISSUE_KEY,
        fields_to_update={
            'priority': {'name': 'Critical'},
        }
    )


if __name__ == '__main__':
    main()
