"""The daily refresh never publishes an empty catalog."""
import json

import festa_do_livro.__main__ as command_line
from festa_do_livro.fair_site import EventDetails, Publisher


class SiteWithoutPriceLists:
    def __init__(self, base_url):
        self.base_url = base_url

    def detect_current_edition(self):
        return "28-festa-do-livro-da-usp"

    def event_details(self, edition):
        return EventDetails(edition=edition, name=f"{edition[:2]} Festa do Livro da USP", period="")

    def list_publishers(self, edition):
        return [Publisher(name="Editora que ainda não mandou a lista", slug="", price_list_url="", site="")]


def publish_edition(data_directory, edition):
    edition_directory = data_directory / edition
    edition_directory.mkdir(parents=True)
    (edition_directory / "catalogo.json").write_text(json.dumps({"livros": [{"i": "9788535914849", "t": "1984", "f": 22.0, "x": 0}]}))
    (data_directory / "edicao-atual.json").write_text(json.dumps({
        "edicao": edition, "catalogo": f"{edition}/catalogo.json", "edicaoInfo": f"{edition}/edicao.json", "relatorio": f"{edition}/relatorio.md",
    }))


def run_build(tmp_path, monkeypatch):
    monkeypatch.setattr(command_line, "FairSite", SiteWithoutPriceLists)
    monkeypatch.delenv("FESTA_EDITION", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"edition": "auto", "site_base_url": "https://example.com"}))
    return command_line.main(["--settings", str(settings), "build", "--output", str(tmp_path / "data"), "--cache", str(tmp_path / "cache")])


def test_new_edition_without_price_lists_keeps_the_site_on_the_current_edition(tmp_path, monkeypatch):
    publish_edition(tmp_path / "data", "27-festa-do-livro-da-usp")
    pointer_before = (tmp_path / "data" / "edicao-atual.json").read_text()

    assert run_build(tmp_path, monkeypatch) == 0
    assert (tmp_path / "data" / "edicao-atual.json").read_text() == pointer_before
    assert not (tmp_path / "data" / "28-festa-do-livro-da-usp").exists()


def test_published_edition_that_suddenly_has_no_books_fails_without_erasing_its_catalog(tmp_path, monkeypatch):
    publish_edition(tmp_path / "data", "28-festa-do-livro-da-usp")
    catalog_before = (tmp_path / "data" / "28-festa-do-livro-da-usp" / "catalogo.json").read_text()

    assert run_build(tmp_path, monkeypatch) == 1
    assert (tmp_path / "data" / "28-festa-do-livro-da-usp" / "catalogo.json").read_text() == catalog_before
