# jira_cloud.py

from functools import partial
from typing import Any

import requests
from jira import JIRA, Issue, JIRAError
from jira.client import ResultList

from python_jira_plus.jira_base import JiraBase


class JiraCloud(JiraBase):
    use_createmeta = True

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

    @staticmethod
    def _split_page(page: Any, json_result: bool) -> tuple[list, bool, str | None]:
        """Return (issues, is_last, next_page_token) from a search page; an empty page counts as the last."""
        if not page:
            return [], True, None
        if json_result:
            return page.get("issues", []), page["isLast"], page.get("nextPageToken")
        return list(page), page.isLast, page.nextPageToken

    def _paginate(
        self,
        query: str,
        max_results: int,
        specific_fields: str | list[str],
        json_result: bool,
        limit: int | None = None,
    ) -> ResultList[Issue] | list:
        all_issues: list = []
        next_token = None
        while limit is None or len(all_issues) < limit:  # pylint: disable=while-used
            self.logger.debug(f"Fetching issues from startAt={len(all_issues)}")
            page_size = max_results if limit is None else min(max_results, limit - len(all_issues))
            fetch = partial(
                self.jira_client.enhanced_search_issues,
                jql_str=query,
                nextPageToken=next_token,
                maxResults=page_size,
                fields=specific_fields,
                json_result=json_result,
            )
            issues, is_last, next_token = self._split_page(fetch(), json_result)
            all_issues += issues
            if is_last or not issues:
                break
        return all_issues if limit is None else all_issues[:limit]

    def get_account_data(self, user_mail: str) -> list[dict]:
        response = requests.get(
            f"{self.server}/rest/api/3/user/search",
            params={"query": user_mail},
            auth=(self.jira_username, self.jira_token),
            verify=self.verify_ssl,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _first_account(self, query: str) -> dict:
        if not (data := self.get_account_data(user_mail=query)):
            raise ValueError(f"No Jira user found matching '{query}'")
        return data[0]

    def get_account_id(self, user_mail: str) -> str:
        return self._first_account(user_mail)["accountId"]

    def get_account_display_name(self, user_display_name: str) -> str:
        return self._first_account(user_display_name)["displayName"]
