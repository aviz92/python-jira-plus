![PyPI version](https://img.shields.io/pypi/v/python-jira-plus)
![Python](https://img.shields.io/badge/python->=3.12-blue)
![Development Status](https://img.shields.io/badge/status-stable-green)
![Maintenance](https://img.shields.io/maintenance/yes/2026)
![PyPI](https://img.shields.io/pypi/dm/python-jira-plus)
![License](https://img.shields.io/pypi/l/python-jira-plus)

---

# Python JIRA Plus
An enhanced Python client for JIRA that extends the functionality of the official `jira` package, providing better error handling, pagination, metadata validation, and more.

---

## Features
- ✅ Simplified connection to JIRA Cloud and On-Premise instances
- ✅ Clear error handling: failures raise (`raise_on_error=True`) or are logged and returned as `None`/`False`. Rate limits (429) and 503 are retried by `jira-python` itself
- ✅ Built-in pagination for large result sets
- ✅ Field validation against JIRA metadata
- ✅ Enhanced issue creation, retrieval, and updating
- ✅ Support for allowed values validation

---

## Installation
```bash
pip install python-jira-plus
```

---

## Requirements
- Python 3.12+
- `jira` package
- `custom-python-logger` package

---

## Configuration
The package uses environment variables for authentication and configuration:

```bash
# Required environment variables
JIRA_USER_NAME=your_jira_username
JIRA_TOKEN=your_jira_api_token
JIRA_BASE_URL=your-instance.atlassian.net  # Only used if base_url is not provided to constructor
```

## Error handling
By default, write helpers (`delete_issue`, `create_link`, `transition_issue`, `upload_attachment`,
`update_issue`) and `get_issue_by_key` log the error and return `False`/`None`. Pass
`raise_on_error=True` to the constructor to get the original exception instead:

```python
jira_client = JiraCloud(raise_on_error=True)
jira_client.get_issue_by_key("PROJ-404")  # raises JIRAError instead of returning None
```

Validation problems (`ValueError`) and failed searches (`JIRAError`) are always raised.
Rate limits (429) and 503 are retried by `jira-python`'s own session, not by this package.

## Restricting access to projects

```python
from python_jira_plus import JiraCloud, ProjectNotAllowedError

jira = JiraCloud(allowed_projects=["PROJ", "OPS"])

issues = jira.get_objects_by_query("status = Open", limit=20)  # scoped to PROJ and OPS
print([issue["key"] for issue in issues])

try:
    jira.add_comment("SECRET-1", "hi")
except ProjectNotAllowedError as err:
    print(err)
```

Every method checks the project first. Issue operations also check the issue's *current* project,
which costs one extra request per call while `allowed_projects` is set.

## Examples

### Creating an Issue with Custom Fields
```python
from python_jira_plus import JiraCloud  # or JiraOnPremise

jira_client = JiraCloud()
issue = jira_client.create_issue(
    project_key="PROJ",
    summary="Implement new feature",
    description="This feature will improve performance",
    issue_type="Task",
    custom_fields={
        "priority": "Critical",  # Priority
        "customfield_10003": {"name": "Sprint 1"}  # Sprint
    }
)
```

### Searching for Issues
```python
from python_jira_plus import JiraCloud

jira_client = JiraCloud()
issues = jira_client.get_objects_by_query(
    query="project = PROJ AND status = 'In Progress' ORDER BY created DESC",
    max_results=50,  # page size
    limit=200,  # optional cap on the total number of issues returned
    specific_fields=["summary", "status", "assignee"],
    json_result=False
)

for issue in issues:
    print(f"{issue.key}: {issue.fields.summary} - {issue.fields.status.name}")
```

### Updating an Issue
```python
from python_jira_plus import JiraCloud

jira_client = JiraCloud()
issue = jira_client.get_issue_by_key(key="PROJ-123", json_result=False)

fields_to_update = {
    "summary": "Updated summary",
    "description": "Updated description",
    "customfield_10003": {"name": "Sprint 2"},  # Update Sprint
}
_ = jira_client.update_issue(
    issue_key=issue.key,
    fields_to_update=fields_to_update
)
```

---

## 🤝 Contributing
If you have a helpful tool, pattern, or improvement to suggest:
Fork the repo <br>
Create a new branch <br>
Submit a pull request <br>
I welcome additions that promote clean, productive, and maintainable development. <br>

---

## 🙏 Thanks
Thanks for exploring this repository! <br>
Happy coding! <br>
