"""Keeps one GitHub issue with the price lists to check, so a misread list is noticed the day it arrives.
GitHub emails the owner when the issue opens and when a comment mentions them; a list already announced is never announced again,
and an issue the owner closed only comes back for a problem it did not list."""
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

from .fair_site import USER_AGENT
from .lists_to_check import ListToCheck

ISSUE_TITLE = "Listas de preço para conferir"
NOTHING_TO_CHECK = "Nenhuma lista para conferir na última atualização."


@dataclass(frozen=True)
class Issue:
    number: int
    state: str
    body: str


def issue_body(items: list[ListToCheck], owner: str, report_url: str) -> str:
    return "\n".join([
        f"@{owner}, a atualização automática leu estas listas de um jeito que parece errado. Elas já estão no site como o leitor "
        "entendeu, então vale abrir o PDF de cada uma e, se for o caso, ajustar o leitor.",
        "",
        *(item.markdown_line() for item in items),
        "",
        f"Relatório completo: {report_url}",
        "",
        "Esta issue fecha sozinha quando a atualização ler todas as listas sem problema. Se você fechar antes, ela só volta "
        "quando aparecer um problema que ainda não está aqui.",
    ])


def sync_issue(items: list[ListToCheck], issues, owner: str, report_url: str) -> str:
    """Opens the issue for the first problem, comments only on problems it does not list yet and closes it when every list reads well."""
    issue = issues.latest(ISSUE_TITLE)
    if not items:
        if issue is None or issue.state != "open":
            return "nada a fazer"
        issues.update(issue.number, NOTHING_TO_CHECK)
        issues.comment(issue.number, "A atualização de hoje leu todas as listas sem problema.")
        issues.close(issue.number)
        return "fechada"
    body = issue_body(items, owner, report_url)
    if issue is None:
        issues.create(ISSUE_TITLE, body)
        return "aberta"
    new_items = [item for item in items if item.key not in issue.body]
    if issue.state != "open":
        if not new_items:
            return "nada a fazer"
        issues.reopen(issue.number)
    if body != issue.body:
        issues.update(issue.number, body)
    if not new_items:
        return "atualizada"
    issues.comment(issue.number, f"@{owner}, listas novas para conferir:\n\n" + "\n".join(item.markdown_line() for item in new_items))
    return "avisada"


def send_to_github(method: str, url: str, payload: Optional[dict], headers: dict):
    request = urllib.request.Request(url, data=json.dumps(payload).encode() if payload is not None else None, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"GitHub respondeu {error.code} a {method} {url}: {error.read()[:300]!r}") from error


class GitHubIssues:
    """The issue calls the daily refresh needs, made with the workflow token through the GitHub REST API."""

    def __init__(self, repository: str, token: str, send: Callable = send_to_github, api_url: str = "https://api.github.com"):
        self.repository_url = f"{api_url.rstrip('/')}/repos/{repository}"
        self.headers = {
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": USER_AGENT,
        }
        self.send = send

    def call(self, method: str, path: str, payload: Optional[dict] = None):
        return self.send(method, self.repository_url + path, payload, self.headers)

    def latest(self, title: str) -> Optional[Issue]:
        query = urllib.parse.urlencode({"state": "all", "creator": "github-actions[bot]", "sort": "created", "direction": "desc", "per_page": 100})
        for item in self.call("GET", f"/issues?{query}"):
            if item["title"] == title and "pull_request" not in item:
                return Issue(item["number"], item["state"], item.get("body") or "")
        return None

    def create(self, title: str, body: str) -> None:
        self.call("POST", "/issues", {"title": title, "body": body})

    def update(self, number: int, body: str) -> None:
        self.call("PATCH", f"/issues/{number}", {"body": body})

    def comment(self, number: int, text: str) -> None:
        self.call("POST", f"/issues/{number}/comments", {"body": text})

    def close(self, number: int) -> None:
        self.call("PATCH", f"/issues/{number}", {"state": "closed", "state_reason": "completed"})

    def reopen(self, number: int) -> None:
        self.call("PATCH", f"/issues/{number}", {"state": "open"})
