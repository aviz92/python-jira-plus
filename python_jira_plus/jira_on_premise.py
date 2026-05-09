# jira_on_premise.py

import logging
import time

from jira import JIRA, Issue, JIRAError
from jira.client import ResultList
from packaging.version import Version
from retrying import retry

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
    ) -> None:
        self.sso = sso  # must be set before super().__init__ — create_connection reads it
        super().__init__(
            base_url=base_url,
            urllib3_log_level=urllib3_log_level,
            jira_username=jira_username,
            jira_token=jira_token,
            verify_ssl=verify_ssl,
            url_scheme=url_scheme,
        )
        use_legacy = Version(".".join(str(x) for x in self.server_version)) < Version("9.0.0")
        self.logger.debug(
            f"Using {'legacy createmeta' if use_legacy else 'project_issue_types'} API "
            f"(ON_PREMISE {self.server_version})"
        )
        self.use_createmeta = use_legacy

    @retry(stop_max_attempt_number=3, wait_fixed=180000)
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
        jira_err_limit: int,
        json_result: bool,
    ) -> ResultList[Issue] | list:
        start_at = 0
        all_issues = []
        retries = 0
        while True:  # pylint: disable=while-used
            try:
                self.logger.debug(f"Fetching issues from startAt={start_at}")
                page = self.jira_client.search_issues(
                    jql_str=query,
                    startAt=start_at,
                    maxResults=max_results,
                    fields=specific_fields,
                    json_result=json_result,
                )
                if not page:
                    break

                all_issues += page["issues"] if json_result else page
                if json_result:
                    start_at += page["maxResults"]
                else:
                    start_at += page.maxResults
                if start_at >= max_results:
                    break
                retries = 0
            except JIRAError as err:
                if err.status_code == 400:
                    self.logger.error(f"Bad Request: {err.text}")
                    raise JIRAError(f"Bad Request: {err.text}") from err
                retries += 1
                self.logger.warning(f"Retry {retries}/{jira_err_limit} after JIRAError: {err}")
                if retries >= jira_err_limit:
                    self.logger.exception("Max retries exceeded.")
                    return []
                time.sleep(300 if retries == jira_err_limit - 1 else 90)
        return all_issues
