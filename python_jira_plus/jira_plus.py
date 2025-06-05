# jira_plus.py

import json
import logging
import os
import time
from enum import Enum
from typing import Any, Union, Optional
import requests
from jira import JIRA, JIRAError, Issue
from jira.client import ResultList
from retrying import retry

from python_jira_plus.describe_allowed_value import describe_allowed_value


class ServerType(Enum):
    CLOUD = 'cloud'
    ON_PREMISE = 'on_premise'


class JiraPlus:
    def __init__(
            self, base_url: Optional[str] = None,
            server_type: ServerType = ServerType.CLOUD,
            urllib3_log_level: int = logging.WARNING,
            jira_username: Optional[str] = None,
            jira_token: Optional[str] = None,  # Use API token (not PAT)
            verify_ssl: bool = True,
            sso: bool = False
    ) -> None:
        self.logger = logging.getLogger()
        logging.getLogger("urllib3").setLevel(urllib3_log_level)

        self.jira_username = jira_username or os.getenv('JIRA_USER_NAME')
        self.jira_token = jira_token or os.getenv('JIRA_TOKEN')
        self.base_url = base_url or os.getenv('JIRA_BASE_URL')

        self.server_type = server_type
        self.server = f'https://{self.base_url}'
        self.verify_ssl = verify_ssl
        self.sso = sso

        self.jira_client = self.create_connection()
        self.check_client_connection()

    @retry(stop_max_attempt_number=3, wait_fixed=180000)  # Retry 3 times with a 3-min (180000) delay between each attempt
    def create_connection(self, timeout=580) -> Optional[JIRA]:
        if self.server_type == ServerType.ON_PREMISE and not self.sso:
            jira_client = JIRA(
                token_auth=self.jira_token,
                options={'server': self.server},
                timeout=timeout
            )
        else:
            jira_client = JIRA(
                basic_auth=(self.jira_username, self.jira_token),
                options={'server': self.server},
                timeout=timeout
            )

        if jira_client.projects():
            self.logger.info(f"Jira Connection Successful")
            return jira_client
        else:
            self.logger.error(f"Jira Connection Failed")
            raise JIRAError("Jira Connection Failed")

    def close_connection(self) -> None:
        try:
            self.jira_client.close()
        except JIRAError as err:
            self.logger.exception(f"JIRAError \n{err}")
        except Exception as err:
            self.logger.exception(f"Exception \n{err}")

        self.check_client_connection()

    def check_client_connection(self) -> bool:
        try:
            if self.jira_client.projects():
                return True
            else:
                self.logger.info("Jira client is closed")
                return False
        except JIRAError as err:
            self.logger.exception(f"JIRAError \n{err}")
            return False
        except Exception as err:
            self.logger.exception(f"Exception \n{err}")
            return False

    def get_issue_by_key(
            self,
            key: str,
            specific_fields: str | list[str] = '*all',
            json_result: bool = True
    ) -> None | Issue | dict[str, Any]:
        try:
            jira_issue = self.jira_client.issue(id=key, fields=specific_fields)
            if json_result:
                return jira_issue.raw
            return jira_issue
        except JIRAError as err:
            self.logger.exception(f"JIRAError \n{err}")
            return None
        except Exception as err:
            self.logger.exception(f"Exception \n{err}")
            return None

    def get_objects_by_query(
            self,
            query: str,
            max_results: int = 5000,
            specific_fields: Union[str, list[str]] = "*all",
            jira_err_count: int = 3,
            json_result: bool = True,
    ) -> Optional[Union[ResultList[Issue], dict]]:
        return self._paginate_query(
            query=query,
            max_results=max_results,
            specific_fields=specific_fields,
            jira_err_limit=jira_err_count,
            json_result=json_result,
        )

    def _paginate_query(
            self,
            query: str,
            max_results: int,
            specific_fields: Union[str, list[str]],
            jira_err_limit: int,
            json_result: bool
    ) -> Union[ResultList[Issue] | list]:
        start_at = 0
        all_issues = []
        retries = 0
        while True:
            try:
                self.logger.debug(f"Fetching issues from startAt={start_at}")
                page = self.jira_client.search_issues(
                    jql_str=query,
                    startAt=start_at,
                    maxResults=max_results,
                    fields=specific_fields,
                    json_result=json_result
                )
                all_issues += page['issues'] if json_result else page
                if json_result:
                    start_at += page['maxResults']
                else:
                    start_at += page.maxResults
                if start_at >= max_results:
                    break
                retries = 0  # reset on success
            except JIRAError as err:
                retries += 1
                self.logger.warning(f"Retry {retries}/{jira_err_limit} after JIRAError: {err}")
                if retries >= jira_err_limit:
                    self.logger.exception("Max retries exceeded.")
                    return []
                time.sleep(300 if retries == jira_err_limit - 1 else 90)
        return all_issues

    def _fetch_metadata(self, project_key: str, issue_type: str) -> tuple[dict, dict]:
        meta = self.jira_client.createmeta(
            projectKeys=project_key,
            issuetypeNames=issue_type,
            expand="projects.issuetypes.fields"
        )

        project_meta = next((p for p in meta['projects'] if p['key'] == project_key), None)
        if not project_meta:
            raise ValueError(f"Project {project_key} not found in metadata")

        issue_meta = next(
            (it for it in project_meta['issuetypes'] if it['name'].lower() == issue_type.lower()),
            None
        )
        if not issue_meta:
            raise ValueError(f"Issue type '{issue_type}' not found in project '{project_key}'")
        return meta, issue_meta

    def get_allowed_values(
            self,
            project_key: str,
            issue_type: str,
            field_id_or_name: str,
    ) -> Optional[list]:
        """
        Returns the allowed values for a specific field in a project + issue type context.
        """
        _, issue_meta = self._fetch_metadata(project_key=project_key, issue_type=issue_type)

        # Try to find by ID or fallback to case-insensitive name
        field = issue_meta['fields'].get(field_id_or_name)
        if not field:
            # Try matching by name (case-insensitive)
            for fid, fmeta in issue_meta['fields'].items():
                if fmeta['name'].lower() == field_id_or_name.lower():
                    field = fmeta
                    break

        if not field:
            raise ValueError(
                f"Field '{field_id_or_name}' not found in project '{project_key}' with issue type '{issue_type}'")

        allowed = field.get('allowedValues')
        if not allowed:
            self.logger.info(f"No allowed values found for field '{field_id_or_name}'")
            return None

        return allowed

    def _is_value_allowed(self, value: Any, allowed_values: list[Any]) -> bool:
        allowed_names = {av.get('name') for av in allowed_values}
        allowed_keys = {av.get('key') for av in allowed_values}
        allowed_values = allowed_names | allowed_keys
        return describe_allowed_value(value, allowed_values=allowed_values)

    def validate_fields(
            self,
            project_key: str,
            issue_type: str,
            fields: Optional[dict] = None
    ) -> None:
        meta, issue_meta = self._fetch_metadata(project_key=project_key, issue_type=issue_type)
        field_types = meta['projects'][0]['issuetypes'][0]['fields']
        for custom_field, value in fields.items():
            if custom_field not in issue_meta['fields']:
                raise ValueError(
                    f'Invalid field(s) for project "{project_key}", issue type "{issue_type}": "{custom_field}"'
                )

            if allowed_value := issue_meta['fields'][custom_field].get('allowedValues'):
                if not self._is_value_allowed(value=value, allowed_values=allowed_value):
                    raise ValueError(
                        f"Invalid value '{value}' for field '{custom_field}' in project '{project_key}' with issue type '{issue_type}'."
                        f"The allowed values are: {json.dumps(allowed_value, indent=4, sort_keys=True)}"
                    )

            field_type = field_types[custom_field]['schema']['type']
            if field_type == 'string' and not isinstance(value, str):
                raise ValueError(f"Field '{custom_field}' must be a string")
            elif field_type == 'number' and not isinstance(value, (int, float)):
                raise ValueError(f"Field '{custom_field}' must be a number")
            elif field_type == 'boolean' and not isinstance(value, bool):
                raise ValueError(f"Field '{custom_field}' must be a boolean")
            elif field_type == 'array' and not isinstance(value, list):
                raise ValueError(f"Field '{custom_field}' must be an array")
            elif field_type == 'object' and not isinstance(value, dict):
                raise ValueError(f"Field '{custom_field}' must be an object")
            elif field_type == 'issuetype' and not isinstance(value, dict):
                raise ValueError(f"Field '{custom_field}' must be an issue type")
            # Add more field type checks as needed
        return issue_meta['fields'].keys()

    def create_issue(
            self,
            project_key: str,
            summary: str,
            description: str,
            issue_type: str,
            assignee: Optional[str] = None,
            custom_fields: Optional[dict] = None,
    ) -> Optional[Issue]:
        issue_fields = {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type},
            "summary": summary,
            "description": description,
        }
        if assignee:
            issue_fields["assignee"] = {"accountId": assignee} if self.server_type == ServerType.CLOUD else {
                "name": assignee}

        if custom_fields:
            issue_fields = issue_fields | custom_fields
        self.validate_fields(project_key=project_key, issue_type=issue_type, fields=issue_fields)

        try:
            issue = self.jira_client.create_issue(fields=issue_fields)
            self.logger.info(f"Issue {issue.key} created successfully.")
            return issue
        except JIRAError as err:
            self.logger.error(f"JIRAError while creating issue: {err.text}")
            return None
        except Exception as err:
            self.logger.exception(f"Unexpected error: {err}")
            return None

    def update_issue(
            self,
            issue_key: str,
            fields_to_update: dict
    ) -> Optional[Issue]:
        try:
            issue = self.jira_client.issue(issue_key)
            self.validate_fields(
                project_key=issue.fields.project.key,
                issue_type=issue.fields.issuetype.name,
                fields=fields_to_update
            )

            issue.update(fields=fields_to_update)
            self.logger.info(f"Issue {issue.key} updated successfully.")
            return issue
        except JIRAError as err:
            self.logger.error(f"JIRAError while updating issue: {err.text}")
            return None
        except Exception as err:
            self.logger.exception(f"Unexpected error: {err}")
            return None

    def delete_issue(self, issue_key: str) -> bool:
        try:
            issue = self.get_issue_by_key(key=issue_key)
            issue.delete()
            self.logger.info(f"Issue {issue_key} deleted successfully.")
            return True
        except JIRAError as err:
            self.logger.error(f"JIRAError while deleting issue: {err.text}")
            return False
        except Exception as err:
            self.logger.exception(f"Unexpected error: {err}")
            return False

    def _get_available_link_types(self) -> set[str]:
        try:
            return {link_type.name for link_type in self.jira_client.issue_link_types()}
        except Exception as err:
            self.logger.exception(f"Failed to retrieve link types from JIRA. \n{err}")
            return set()

    def create_link(self, issue_key: str, link_type: str, in_issue_key: str) -> bool:
        available_link_types = self._get_available_link_types()
        if link_type not in available_link_types:
            raise ValueError(f"Invalid link type '{link_type}'. Available link types: {available_link_types}")

        try:
            self.jira_client.create_issue_link(
                type=link_type,
                inwardIssue=issue_key,
                outwardIssue=in_issue_key,
            )
            self.logger.info(f"Link between {issue_key} and {in_issue_key} was created")
            return True
        except JIRAError as err:
            self.logger.exception(f"JIRAError - Link between {issue_key} and {in_issue_key} was not created\n{err}")
            return False
        except Exception as err:
            self.logger.exception(f"Exception - Link between {issue_key} and {in_issue_key} was not created\n{err}")
            return False

    def upload_attachment(self, issue_key: str, file_path: str) -> None:
        try:
            self.jira_client.add_attachment(issue=issue_key, attachment=file_path)
        except JIRAError as err:
            self.logger.exception(f"JIRAError - Attachment {file_path} was not uploaded to issue {issue_key}\n{err}")
        except Exception as err:
            self.logger.exception(f"Exception - Attachment {file_path} was not uploaded to issue {issue_key}\n{err}")

    def transition_issue(
            self,
            issue_key: str,
            transition_name: str,
            fields: Optional[dict] = None,
            comment: Optional[str] = None,
    ) -> bool:
        try:
            transitions = self.jira_client.transitions(issue_key)
            transition_names = {t['name'] for t in transitions}
            if transition_name not in transition_names:
                self.logger.error(
                    f"Transition '{transition_name}' not found for issue {issue_key}. "
                    f"\nAvailable transitions: {transition_names}"
                )
                return False

            transition_id = next(
                (t['id'] for t in transitions if t['name'].lower() == transition_name.lower()),
                None
            )
            if not transition_id:
                self.logger.error(f"Transition '{transition_name}' not found for issue {issue_key}")
                return False

            self.jira_client.transition_issue(
                issue=issue_key,
                transition=transition_id,
                fields=fields or {},
                comment=comment or None
            )
            self.logger.info(f"Issue {issue_key} transitioned to '{transition_name}'")
            return True
        except JIRAError as err:
            self.logger.exception(f"JIRAError during transition of {issue_key}: {err}")
            return False
        except Exception as err:
            self.logger.exception(f"Unexpected error during transition of {issue_key}: {err}")
            return False

    def get_account_data(self, user_mail: str) -> list[dict]:
        jira_rst_url = \
            f'https://{self.jira_username}:{self.jira_token}@{self.base_url}/rest/api/{3}/user/search?query={user_mail}'
        response = requests.get(jira_rst_url)
        return response.json()

    def get_account_id(self, user_mail: str) -> str:
        data = self.get_account_data(user_mail=user_mail)
        return data[0]['accountId']

    def get_account_display_name(self, user_display_name: str) -> str:
        data = self.get_account_data(user_mail=user_display_name)
        return data[0]['displayName']
