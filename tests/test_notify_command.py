"""The daily refresh hands the lists to check of the published edition to the GitHub issue."""
import json

import pytest

import festa_do_livro.__main__ as command_line
from festa_do_livro.lists_to_check import ListToCheck, save_lists_to_check

EDITION = "28-festa-do-livro-da-usp"


def published_data(tmp_path, items):
    data_directory = tmp_path / "data"
    (data_directory / EDITION).mkdir(parents=True)
    (data_directory / "edicao-atual.json").write_text(json.dumps({"edicao": EDITION}))
    if items is not None:
        save_lists_to_check(data_directory / EDITION / "listas-para-conferir.json", items)
    return data_directory


def test_lists_to_check_reach_the_issue_with_a_link_to_the_report(tmp_path, monkeypatch):
    received = []
    monkeypatch.setattr(command_line, "GitHubIssues", lambda repository, token: f"issues de {repository}")
    monkeypatch.setattr(command_line, "sync_issue", lambda items, issues, owner, report_url: received.append((items, issues, owner, report_url)) or "aberta")
    for name, value in {"GITHUB_REPOSITORY": "exemplo/guia", "GITHUB_TOKEN": "token-de-teste", "GITHUB_REPOSITORY_OWNER": "exemplo", "GITHUB_SERVER_URL": "https://github.com"}.items():
        monkeypatch.setenv(name, value)
    items = [ListToCheck("Nós", "sem preço de capa", "68 de 68 livros")]

    exit_code = command_line.main(["notify-lists-to-check", "--data", str(published_data(tmp_path, items))])

    assert (exit_code, received) == (0, [(items, "issues de exemplo/guia", "exemplo", f"https://github.com/exemplo/guia/blob/main/data/{EDITION}/relatorio.md")])


def test_edition_without_a_lists_to_check_file_leaves_the_issue_alone(tmp_path, monkeypatch):
    monkeypatch.setattr(command_line, "GitHubIssues", lambda repository, token: pytest.fail("não deveria chamar o GitHub"))
    assert command_line.main(["notify-lists-to-check", "--data", str(published_data(tmp_path, None))]) == 0
