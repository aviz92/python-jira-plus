# jira_on_premise.py

import logging
from functools import partial

from jira import JIRA, Issue, JIRAError
from jira.client import ResultList
from packaging.version import Version

from python_jira_plus.jira_base import JiraBase, UrlScheme


class JiraOnPremise(JiraBase):
    def __init__(
        self,
        base_url: str | None = None,
        urllib3_log_level: int = logging.WARNING,
        jira_username: str | None = None,
        jira_token: str | None = None,
        verify_ssl: bool = True,
        sso: bool = False,
        url_scheme: UrlScheme = UrlScheme.HTTPS,
        raise_on_error: bool = False,
    ) -> None:
        self.sso = sso  # must be set before super().__init__ — create_connection reads it
        super().__init__(
            base_url=base_url,
            urllib3_log_level=urllib3_log_level,
            jira_username=jira_username,
            jira_token=jira_token,
            verify_ssl=verify_ssl,
            url_scheme=url_scheme,
            raise_on_error=raise_on_error,
        )
        use_legacy = Version(".".join(str(x) for x in self.server_version)) < Version("9.0.0")
        self.logger.debug(
            f"Using {'legacy createmeta' if use_legacy else 'project_issue_types'} API "
            f"(ON_PREMISE {self.server_version})"
        )
        self.use_createmeta = use_legacy

    def _requires_username(self) -> bool:
        return self.sso  # token auth needs no username

    def create_connection(self, timeout: int = 580) -> JIRA:
        auth = (
            {"token_auth": self.jira_token} if not self.sso else {"basic_auth": (self.jira_username, self.jira_token)}
        )
        jira_client = JIRA(**auth, options={"server": self.server, "verify": self.verify_ssl}, timeout=timeout)
        if jira_client.projects():
            self.logger.info("Jira Connection Successful")
            return jira_client
        self.logger.error("Jira Connection Failed")
        raise JIRAError("Jira Connection Failed")

    def _format_assignee(self, assignee: str) -> dict:
        return {"name": assignee}

    def _paginate(
        self,
        query: str,
        max_results: int,
        specific_fields: str | list[str],
        json_result: bool,
        limit: int | None = None,
    ) -> ResultList[Issue] | list:
        cap = max_results if limit is None else limit  # without `limit`, max_results is also the total cap
        start_at = 0
        all_issues: list = []
        while start_at < cap:  # pylint: disable=while-used
            self.logger.debug(f"Fetching issues from startAt={start_at}")
            fetch = partial(
                self.jira_client.search_issues,
                jql_str=query,
                startAt=start_at,
                maxResults=min(max_results, cap - start_at),
                fields=specific_fields,
                json_result=json_result,
            )
            page = fetch()
            if not (issues := (page.get("issues") if json_result else list(page)) if page else None):
                break
            all_issues += issues
            start_at += len(issues)
            if start_at >= (page["total"] if json_result else page.total):
                break
        return all_issues[:cap]
