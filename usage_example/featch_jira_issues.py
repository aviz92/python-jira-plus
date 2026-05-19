# featch_jira_issue.py

import logging

from custom_python_logger.logger import build_logger

from python_jira_plus import BASIC_FIELDS, JiraCloud
from python_jira_plus.const import LOGGER_NAME

# QUERY = 'project = "JIRA TEST" AND issuetype = Story'
QUERY = 'project = "SUP" AND issuetype = "[System] Service request"'


def main() -> None:
    _ = build_logger(project_name=LOGGER_NAME, log_level=logging.DEBUG, extra={"user": "test_user"})

    jira_plus = JiraCloud()
    _ = jira_plus.get_objects_by_query(
        query=QUERY,
        specific_fields=BASIC_FIELDS,
        max_results=300,
    )
    print()
    _ = jira_plus.get_allowed_values(
        project_key="SUP", issue_type="[System] Service request", field_id_or_name="Priority"
    )
    print()


if __name__ == "__main__":
    main()
