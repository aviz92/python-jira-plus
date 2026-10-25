"""
Python JIRA Plus

An enhanced Python client for JIRA with better error handling,
pagination, metadata validation, and more.
"""

from python_jira_plus.describe_allowed_value import describe_allowed_value
from python_jira_plus.jira_base import JiraBase, UrlScheme
from python_jira_plus.jira_cloud import JiraCloud
from python_jira_plus.jira_on_premise import JiraOnPremise

BASIC_FIELDS = [
    "created",
    "updated",
    "issuetype",
    "project",
    "status",
    "summary",
    "description",
    "reporter",
    "assignee",
    "priority",
    "labels",
    "resolution",
    "parent",
]
__all__ = ["JiraBase", "JiraCloud", "JiraOnPremise", "UrlScheme", "BASIC_FIELDS"]
