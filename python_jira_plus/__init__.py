# python-jira-plus

"""
Python JIRA Plus

An enhanced Python client for JIRA with better error handling,
pagination, metadata validation, and more.
"""

__version__ = '0.1.0'

from dotenv import load_dotenv
load_dotenv()

from python_jira_plus.jira_plus import JiraPlus, ServerType
from python_jira_plus.describe_allowed_value import describe_allowed_value

load_dotenv()

BASIC_FIELDS = [
    'created',
    'updated',
    'issuetype',
    'project',
    'status',
    'summary',
    'description',
    'reporter',
    'assignee',
    'priority',
    'labels',
    'resolution',
    'parent'
]
__all__ = ['JiraPlus', 'ServerType', 'BASIC_FIELDS']
