# jira_base.py

import json
import logging
import os
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from custom_python_logger import get_logger
from dotenv import load_dotenv
from jira import JIRA, Issue, JIRAError
from jira.client import ResultList

from python_jira_plus.consts import (
    ALLOWED_VALUE_KEYS,
    FIELD_TYPE_CHECKS,
    LOGGER_NAME,
    SCHEME_PATTERN,
)
from python_jira_plus.describe_allowed_value import describe_allowed_value


class UrlScheme(Enum):
    HTTP = "http"
    HTTPS = "https"


class JiraBase(ABC):  # pylint: disable=too-many-instance-attributes
    use_createmeta: bool

    def __init__(
        self,
        base_url: str | None = None,
        urllib3_log_level: int = logging.WARNING,
        jira_username: str | None = None,
        jira_token: str | None = None,
        verify_ssl: bool = True,
        url_scheme: UrlScheme = UrlScheme.HTTPS,
        raise_on_error: bool = False,
    ) -> None:
        self.logger = get_logger(LOGGER_NAME)
        get_logger("urllib3").setLevel(urllib3_log_level)

        if not (jira_username and jira_token and base_url):
            load_dotenv()  # fallback for missing arguments only — no import-time side effect
        self.jira_username = jira_username or os.getenv("JIRA_USER_NAME")
        self.jira_token = jira_token or os.getenv("JIRA_TOKEN")
        self.base_url, self.url_scheme = self._parse_base_url(base_url or os.getenv("JIRA_BASE_URL"), url_scheme)
        self.server = f"{self.url_scheme}://{self.base_url}"
        self.verify_ssl = verify_ssl
        self.raise_on_error = raise_on_error
        self._validate_credentials()

        self.jira_client = self.create_connection()
        self.server_version = self.get_server_version()

    @staticmethod
    def _parse_base_url(base_url: str | None, url_scheme: UrlScheme) -> tuple[str, str]:
        """Split an optional scheme off `base_url`; a scheme embedded in the URL wins over `url_scheme`."""
        if not base_url or not base_url.strip():
            raise ValueError("Jira base URL is missing — pass `base_url` or set JIRA_BASE_URL")
        base_url = base_url.strip()
        scheme = url_scheme.value
        if match := SCHEME_PATTERN.match(base_url):
            scheme = match.group(1).lower()
            base_url = base_url[match.end() :]
        return base_url.rstrip("/"), scheme

    def _requires_username(self) -> bool:
        return True

    def _validate_credentials(self) -> None:
        if not self.jira_token:
            raise ValueError("Jira token is missing — pass `jira_token` or set JIRA_TOKEN")
        if self._requires_username() and not self.jira_username:
            raise ValueError("Jira username is missing — pass `jira_username` or set JIRA_USER_NAME")

    @abstractmethod
    def create_connection(self, timeout: int = 580) -> JIRA: ...

    @abstractmethod
    def _paginate(
        self,
        query: str,
        max_results: int,
        specific_fields: str | list[str],
        json_result: bool,
        limit: int | None = None,
    ) -> ResultList[Issue] | list: ...

    @abstractmethod
    def _format_assignee(self, assignee: str) -> dict: ...

    def _handle_error(self, message: str, err: Exception) -> None:
        """Log `err`; re-raise it when `raise_on_error` is set. Callers return their failure value after."""
        self.logger.exception(f"{message}\n{err}")
        if self.raise_on_error:
            raise err

    def close_connection(self) -> None:
        try:
            self.jira_client.close()
        except JIRAError as err:
            self.logger.exception(f"JIRAError \n{err}")
        except Exception as err:
            self.logger.exception(f"Exception \n{err}")

    def check_client_connection(self) -> bool:
        try:
            if self.jira_client.projects():
                return True
            self.logger.info("Jira client is closed")
            return False
        except JIRAError as err:
            self.logger.exception(f"JIRAError \n{err}")
            return False
        except Exception as err:
            self.logger.exception(f"Exception \n{err}")
            return False

    def get_server_version(self) -> tuple[int, ...]:
        return tuple(self.jira_client.server_info()["versionNumbers"])

    def get_issue_by_key(
        self, key: str, specific_fields: str | list[str] = "*all", json_result: bool = True
    ) -> None | Issue | dict[str, Any]:
        try:
            jira_issue = self.jira_client.issue(id=key, fields=specific_fields)
            if json_result:
                return jira_issue.raw
            return jira_issue
        except Exception as err:
            self._handle_error(f"Failed to get issue {key}", err)
            return None

    def get_objects_by_query(
        self,
        query: str,
        max_results: int = 5000,
        specific_fields: str | list[str] = "*all",
        json_result: bool = True,
        limit: int | None = None,
    ) -> ResultList[Issue] | list:
        """Run a JQL query and return all matches.

        Args:
            query: JQL string.
            max_results: Page size (on-premise: also the total cap unless `limit` is given).
            specific_fields: Fields to fetch.
            json_result: Return raw dicts instead of `Issue` objects.
            limit: Optional cap on the total number of issues returned.

        Raises:
            JIRAError: If Jira rejects the query or a request fails.
        """
        return self._paginate(
            query=query,
            max_results=max_results,
            specific_fields=specific_fields,
            json_result=json_result,
            limit=limit,
        )

    @staticmethod
    def _find_issue_meta(meta: dict, project_key: str, issue_type: str) -> tuple[dict | None, dict | None]:
        if (project_meta := next((p for p in meta["projects"] if p["key"] == project_key), None)) is None:
            return None, None
        issue_meta = next((it for it in project_meta["issuetypes"] if it["name"].lower() == issue_type.lower()), None)
        return project_meta, issue_meta

    def _fetch_via_createmeta(self, project_key: str, issue_type: str) -> dict:
        expand = "projects.issuetypes.fields"
        meta = self.jira_client.createmeta(projectKeys=project_key, issuetypeNames=issue_type, expand=expand)
        project_meta, issue_meta = self._find_issue_meta(meta, project_key, issue_type)
        if issue_meta is None:
            # `issuetypeNames` is matched case-sensitively server-side, so a wrong-cased name comes back empty.
            meta = self.jira_client.createmeta(projectKeys=project_key, expand=expand)
            project_meta, issue_meta = self._find_issue_meta(meta, project_key, issue_type)
        if project_meta is None:
            raise ValueError(f"Project {project_key} not found in metadata")
        if issue_meta is None:
            raise ValueError(f"Issue type '{issue_type}' not found in project '{project_key}'")
        return issue_meta["fields"]

    def _fetch_via_issue_types_api(self, project_key: str, issue_type: str) -> dict:
        issue_types = {t.name.lower(): t for t in self.jira_client.project_issue_types(project_key)}
        if (matched := issue_types.get(issue_type.lower())) is None:
            available = sorted(t.name for t in issue_types.values())
            raise ValueError(
                f"Issue type '{issue_type}' not found in project '{project_key}'. Available issue types: {available}"
            )
        field_list = self.jira_client.project_issue_fields(project_key, matched.id)
        return {f.fieldId: f.raw for f in field_list}

    def get_project_fields_metadata(self, project_key: str, issue_type: str) -> dict:
        if self.use_createmeta:
            return self._fetch_via_createmeta(project_key=project_key, issue_type=issue_type)
        return self._fetch_via_issue_types_api(project_key=project_key, issue_type=issue_type)

    def get_allowed_values(
        self,
        project_key: str,
        issue_type: str,
        field_id_or_name: str,
    ) -> list | None:
        """Returns the allowed values for a specific field in a project + issue type context."""
        fields_metadata = self.get_project_fields_metadata(project_key=project_key, issue_type=issue_type)
        if not (field := fields_metadata.get(field_id_or_name)):
            for _, fmeta in fields_metadata.items():
                if fmeta["name"].lower() == field_id_or_name.lower():
                    field = fmeta
                    break
        if not field:
            raise ValueError(
                f"Field '{field_id_or_name}' not found in project '{project_key}' with issue type '{issue_type}'"
            )
        if not (allowed := field.get("allowedValues")):
            self.logger.info(f"No allowed values found for field '{field_id_or_name}'")
            return None
        return allowed

    @staticmethod
    def _is_value_allowed(value: Any, allowed_values: list[Any]) -> bool:
        allowed = {av.get(key) for av in allowed_values for key in ALLOWED_VALUE_KEYS}
        allowed.discard(None)
        return describe_allowed_value(value, allowed_values=allowed)

    @staticmethod
    def _check_field_type(field_id: str, field_type: str | None, value: Any) -> None:
        if (check := FIELD_TYPE_CHECKS.get(field_type or "")) and not isinstance(value, check.python_types):
            raise ValueError(f"Field '{field_id}' must be {check.label}")

    def _validate_against_metadata(self, fields_metadata: dict, fields: dict, context: str) -> None:
        for field_id, value in fields.items():
            if field_id not in fields_metadata:
                raise ValueError(f'Invalid field(s) for {context}: "{field_id}"')
            field_meta = fields_metadata[field_id]
            if (allowed_value := field_meta.get("allowedValues")) and not self._is_value_allowed(
                value=value, allowed_values=allowed_value
            ):
                raise ValueError(
                    f"Invalid value '{value}' for field '{field_id}' in {context}. "
                    f"The allowed values are: {json.dumps(allowed_value, indent=4, sort_keys=True)}"
                )
            self._check_field_type(field_id, field_meta.get("schema", {}).get("type"), value)

    def validate_fields(
        self, project_key: str, issue_type: str, fields: dict, fields_metadata: dict | None = None
    ) -> None:
        """Validate `fields`; pass `fields_metadata` to reuse an already-fetched result."""
        if fields_metadata is None:
            fields_metadata = self.get_project_fields_metadata(project_key=project_key, issue_type=issue_type)
        self._validate_against_metadata(
            fields_metadata, fields, context=f'project "{project_key}", issue type "{issue_type}"'
        )

    @staticmethod
    def _canonical_issue_type(fields_metadata: dict, issue_type: str) -> str:
        """Return the issue type's real casing (e.g. 'task' -> 'Task'), or `issue_type` if metadata lacks it."""
        allowed = fields_metadata.get("issuetype", {}).get("allowedValues", [])
        return next((av["name"] for av in allowed if av.get("name", "").lower() == issue_type.lower()), issue_type)

    @staticmethod
    def _merge_custom_fields(issue_fields: dict[str, Any], custom_fields: dict | None) -> dict[str, Any]:
        """Merge `custom_fields` in, refusing to let them override the dedicated arguments."""
        for key, value in (custom_fields or {}).items():
            if key in issue_fields and issue_fields[key] != value:
                raise ValueError(f"custom_fields['{key}'] conflicts with the dedicated argument for '{key}'")
        return {**(custom_fields or {}), **issue_fields}

    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str,
        assignee: str | None = None,
        custom_fields: dict | None = None,
    ) -> Issue | None:
        issue_fields: dict[str, Any] = {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type},
            "summary": summary,
            "description": description,
        }
        if assignee:
            issue_fields["assignee"] = self._format_assignee(assignee)
        issue_fields = self._merge_custom_fields(issue_fields, custom_fields)
        fields_metadata = self.get_project_fields_metadata(project_key=project_key, issue_type=issue_type)
        issue_fields["issuetype"] = {"name": self._canonical_issue_type(fields_metadata, issue_type)}
        self.validate_fields(project_key, issue_type, issue_fields, fields_metadata=fields_metadata)
        issue = self.jira_client.create_issue(fields=issue_fields)
        self.logger.info(f"Issue {issue.key} created successfully.")
        return issue

    def update_issue(self, issue_key: str, fields_to_update: dict) -> Issue | None:
        """Update an issue after validating `fields_to_update` against its edit metadata.

        Raises:
            ValueError: If a field is not editable or a value is invalid (always raised).
        """
        try:
            issue = self.jira_client.issue(issue_key)
            edit_fields = self.jira_client.editmeta(issue_key)["fields"]
            self._validate_against_metadata(edit_fields, fields_to_update, context=f'issue "{issue_key}"')
            issue.update(fields=fields_to_update)
            self.logger.info(f"Issue {issue.key} updated successfully.")
            return issue
        except ValueError:
            raise
        except Exception as err:
            self._handle_error(f"Failed to update issue {issue_key}", err)
            return None

    def delete_issue(self, issue_key: str) -> bool:
        try:
            issue = self.jira_client.issue(issue_key)
            issue.delete()
            self.logger.info(f"Issue {issue_key} deleted successfully.")
            return True
        except Exception as err:
            self._handle_error(f"Failed to delete issue {issue_key}", err)
            return False

    def add_comment(self, issue: str, comment: str) -> None:
        self.jira_client.add_comment(issue=issue, body=comment)
        self.logger.debug(f"Comment added to issue {issue} successfully.")

    def _get_available_link_types(self) -> set[str]:
        return {link_type.name for link_type in self.jira_client.issue_link_types()}

    def create_link(self, issue_key: str, link_type: str, in_issue_key: str) -> bool:
        try:
            available_link_types = self._get_available_link_types()
        except Exception as err:
            self._handle_error("Failed to retrieve link types from JIRA", err)
            return False
        if (canonical := {name.lower(): name for name in available_link_types}.get(link_type.lower())) is None:
            raise ValueError(f"Invalid link type '{link_type}'. Available link types: {sorted(available_link_types)}")
        try:
            self.jira_client.create_issue_link(
                type=canonical,
                inwardIssue=issue_key,
                outwardIssue=in_issue_key,
            )
            self.logger.info(f"Link between {issue_key} and {in_issue_key} was created")
            return True
        except Exception as err:
            self._handle_error(f"Link between {issue_key} and {in_issue_key} was not created", err)
            return False

    def upload_attachment(self, issue_key: str, file_path: str) -> bool:
        try:
            self.jira_client.add_attachment(issue=issue_key, attachment=file_path)
            return True
        except Exception as err:
            self._handle_error(f"Attachment {file_path} was not uploaded to issue {issue_key}", err)
            return False

    def _resolve_transition(self, issue_key: str, transition_name: str) -> dict:
        transitions = self.jira_client.transitions(issue_key, expand="transitions.fields")
        if transition := next((t for t in transitions if t["name"].lower() == transition_name.lower()), None):
            return transition
        raise ValueError(
            f"Transition '{transition_name}' not found for issue {issue_key}. "
            f"Available transitions: {sorted(t['name'] for t in transitions)}"
        )

    def transition_issue(
        self,
        issue_key: str,
        transition_name: str,
        fields: dict | None = None,
        comment: str | None = None,
    ) -> bool:
        """Transition an issue by name (case-insensitive), optionally with a comment.

        Jira silently drops a transition comment when the transition screen has no comment field,
        so in that case the comment is added separately after the transition succeeds.
        """
        needs_separate_comment = False
        try:
            transition = self._resolve_transition(issue_key, transition_name)
            needs_separate_comment = bool(comment) and "comment" not in transition.get("fields", {})
            self.jira_client.transition_issue(
                issue=issue_key,
                transition=transition["id"],
                fields=fields or {},
                comment=None if needs_separate_comment else comment or None,
            )
        except Exception as err:
            self._handle_error(f"Failed to transition {issue_key} to '{transition_name}'", err)
            return False
        self.logger.info(f"Issue {issue_key} transitioned to '{transition_name}'")
        if needs_separate_comment:
            self._comment_after_transition(issue_key, comment)
        return True

    def _comment_after_transition(self, issue_key: str, comment: str | None) -> None:
        """The transition already happened, so a comment failure is reported but does not undo its success."""
        try:
            if comment:
                self.add_comment(issue=issue_key, comment=comment)
        except Exception as err:
            self._handle_error(f"Issue {issue_key} was transitioned but the comment was not added", err)
