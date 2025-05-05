# create_jira_issue.py

import logging
from custom_python_logger.logger import get_logger

from python_jira_plus import JiraPlus


def main():
    _ = get_logger(
        project_name='Logger Project Test',
        log_level=logging.DEBUG,
        extra={'user': 'test_user'}
    )

    jira_plus = JiraPlus()
    _ = jira_plus.create_issue(
        project_key="JIRA TEST",
        issue_type='Story',
        summary='Test issue',
        description='This is a test issue.',
    )


if __name__ == '__main__':
    main()
