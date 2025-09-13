# featch_jira_issue.py

import logging
from custom_python_logger.logger import build_logger

from python_jira_plus import BASIC_FIELDS
from python_jira_plus.jira_plus import JiraPlus

QUERY = 'project = "JIRA TEST" AND issuetype = Story'


def main():
    _ = build_logger(
        project_name='Logger Project Test',
        log_level=logging.DEBUG,
        extra={'user': 'test_user'}
    )

    jira_plus = JiraPlus()
    _ = jira_plus.get_objects_by_query(
        query=QUERY,
        specific_fields=BASIC_FIELDS,
        max_results=300,
    )


if __name__ == '__main__':
    main()
