"""The GitHub issue that tells the owner which price lists to check, without repeating itself."""
from festa_do_livro.alert_issue import ISSUE_TITLE, GitHubIssues, Issue, issue_body, sync_issue
from festa_do_livro.lists_to_check import ListToCheck

OWNER = "dona-do-guia"
REPORT_URL = "https://github.com/exemplo/guia/blob/main/data/28-festa-do-livro-da-usp/relatorio.md"
UNIVERSO = ListToCheck("Universo dos Livros", "nenhum livro lido", "a lista foi baixada, mas o leitor não achou nenhum livro")
NOS = ListToCheck("Nós", "sem preço de capa", "68 de 68 livros")


class RecordedIssues:
    """Keeps the issue in memory and records each call instead of sending it to GitHub."""

    def __init__(self, issue: Issue | None = None):
        self.issue = issue
        self.calls: list[tuple[str, object]] = []

    def latest(self, title):
        return self.issue if title == ISSUE_TITLE else None

    def create(self, title, body):
        self.calls.append(("create", body))
        self.issue = Issue(1, "open", body)

    def update(self, number, body):
        self.calls.append(("update", body))
        self.issue = Issue(number, self.issue.state, body)

    def comment(self, number, text):
        self.calls.append(("comment", text))

    def close(self, number):
        self.calls.append(("close", number))
        self.issue = Issue(number, "closed", self.issue.body)

    def reopen(self, number):
        self.calls.append(("reopen", number))
        self.issue = Issue(number, "open", self.issue.body)


def call_kinds(issues: RecordedIssues) -> list[str]:
    return [kind for kind, _ in issues.calls]


def test_first_list_to_check_opens_an_issue_that_mentions_the_owner():
    issues = RecordedIssues()
    sync_issue([UNIVERSO], issues, OWNER, REPORT_URL)
    assert (call_kinds(issues), f"@{OWNER}" in issues.issue.body, UNIVERSO.key in issues.issue.body) == (["create"], True, True)


def test_same_lists_on_the_next_day_send_nothing():
    issues = RecordedIssues()
    sync_issue([UNIVERSO], issues, OWNER, REPORT_URL)
    issues.calls.clear()
    sync_issue([UNIVERSO], issues, OWNER, REPORT_URL)
    assert issues.calls == []


def test_new_list_to_check_is_announced_in_a_comment_that_mentions_the_owner():
    issues = RecordedIssues()
    sync_issue([UNIVERSO], issues, OWNER, REPORT_URL)
    issues.calls.clear()
    sync_issue([UNIVERSO, NOS], issues, OWNER, REPORT_URL)
    comments = [text for kind, text in issues.calls if kind == "comment"]
    assert [(NOS.key in text, UNIVERSO.key in text, f"@{OWNER}" in text) for text in comments] == [(True, False, True)]


def test_issue_closes_when_every_list_reads_well():
    issues = RecordedIssues()
    sync_issue([UNIVERSO], issues, OWNER, REPORT_URL)
    sync_issue([], issues, OWNER, REPORT_URL)
    assert issues.issue.state == "closed"


def test_issue_closed_by_the_owner_stays_closed_while_the_same_lists_remain():
    issues = RecordedIssues(Issue(7, "closed", issue_body([UNIVERSO], OWNER, REPORT_URL)))
    sync_issue([UNIVERSO], issues, OWNER, REPORT_URL)
    assert issues.calls == []


def test_new_list_to_check_reopens_a_closed_issue():
    issues = RecordedIssues(Issue(7, "closed", issue_body([UNIVERSO], OWNER, REPORT_URL)))
    sync_issue([UNIVERSO, NOS], issues, OWNER, REPORT_URL)
    assert issues.issue.state == "open"


def test_list_that_breaks_again_after_everything_read_well_is_announced_again():
    issues = RecordedIssues()
    sync_issue([UNIVERSO], issues, OWNER, REPORT_URL)
    sync_issue([], issues, OWNER, REPORT_URL)
    issues.calls.clear()
    sync_issue([UNIVERSO], issues, OWNER, REPORT_URL)
    assert call_kinds(issues) == ["reopen", "update", "comment"]


def test_nothing_to_check_and_no_issue_does_nothing():
    issues = RecordedIssues()
    sync_issue([], issues, OWNER, REPORT_URL)
    assert issues.calls == []


def test_latest_issue_is_found_by_its_exact_title_and_never_a_pull_request():
    listed = [
        {"number": 9, "title": ISSUE_TITLE, "state": "open", "body": "pedido de mudança", "pull_request": {}},
        {"number": 8, "title": f"{ISSUE_TITLE} (rascunho)", "state": "open", "body": "outra"},
        {"number": 5, "title": ISSUE_TITLE, "state": "closed", "body": "corpo"},
    ]
    issues = GitHubIssues("exemplo/guia", "token-de-teste", send=lambda method, url, payload, headers: listed)
    assert issues.latest(ISSUE_TITLE) == Issue(5, "closed", "corpo")
