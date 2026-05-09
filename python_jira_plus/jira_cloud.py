# jira_cloud.py

import logging
import time

import requests
from jira import JIRA, Issue, JIRAError
from jira.client import ResultList
from retrying import retry

from python_jira_plus.jira_base import JiraBase, UrlScheme


class JiraCloud(JiraBase):
    use_createmeta = True

    def __init__(
        self,
        base_url: str | None = None,
        urllib3_log_level: int = logging.WARNING,
        jira_username: str | None = None,
        jira_token: str | None = None,
        verify_ssl: bool = True,
        url_scheme: UrlScheme = UrlScheme.HTTPS,
    ) -> None:
        super().__init__(
            base_url=base_url,
            urllib3_log_level=urllib3_log_level,
            jira_username=jira_username,
            jira_token=jira_token,
            verify_ssl=verify_ssl,
            url_scheme=url_scheme,
        )

    @retry(stop_max_attempt_number=3, wait_fixed=180000)
    def create_connection(self, timeout: int = 580) -> JIRA:
        jira_client = JIRA(
            basic_auth=(self.jira_username, self.jira_token),
            options={"server": self.server, "verify": self.verify_ssl},
            timeout=timeout,
        )
        if jira_client.projects():
            self.logger.info("Jira Connection Successful")
            return jira_client
        self.logger.error("Jira Connection Failed")
        raise JIRAError("Jira Connection Failed")

    def _format_assignee(self, assignee: str) -> dict:
        return {"accountId": assignee}

    def _paginate(
        self,
        query: str,
        max_results: int,
        specific_fields: str | list[str],
        jira_err_limit: int,
        json_result: bool,
    ) -> ResultList[Issue] | list:
        all_issues = []
        retries = 0
        page = None
        while True:  # pylint: disable=while-used
            try:
                next_token = None
                if page is not None:
                    next_token = page.get("nextPageToken") if json_result else page.nextPageToken

                self.logger.debug(f"Fetching issues from startAt={len(all_issues)}")
                page = self.jira_client.enhanced_search_issues(
                    jql_str=query,
                    nextPageToken=next_token,
                    maxResults=max_results,
                    fields=specific_fields,
                    json_result=json_result,
                )
                if not page:
                    break

                all_issues += page["issues"] if json_result else page
                if page["isLast"] if json_result else page.isLast:
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

    def get_account_data(self, user_mail: str) -> list[dict]:
        response = requests.get(
            f"{self.server}/rest/api/3/user/search",
            params={"query": user_mail},
            auth=(self.jira_username, self.jira_token),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get_account_id(self, user_mail: str) -> str:
        data = self.get_account_data(user_mail=user_mail)
        return data[0]["accountId"]

    def get_account_display_name(self, user_display_name: str) -> str:
        data = self.get_account_data(user_mail=user_display_name)
        return data[0]["displayName"]
