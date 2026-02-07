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
- ✅ Robust error handling with automatic retries
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
- Python 3.9+
- `jira` package
- `retrying` package
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

## Examples

### Creating an Issue with Custom Fields
```python
from python_jira_plus.jira_plus import JiraPlus

jira_client = JiraPlus()
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
from python_jira_plus.jira_plus import JiraPlus

jira_client = JiraPlus()
issues = jira_client.get_objects_by_query(
    query="project = PROJ AND status = 'In Progress' ORDER BY created DESC",
    max_results=50,
    specific_fields=["summary", "status", "assignee"],
    json_result=False
)

for issue in issues:
    print(f"{issue.key}: {issue.fields.summary} - {issue.fields.status.name}")
```

### Updating an Issue
```python
from python_jira_plus.jira_plus import JiraPlus

jira_client = JiraPlus()
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
