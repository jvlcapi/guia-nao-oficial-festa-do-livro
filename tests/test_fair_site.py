import json
import re
from pathlib import Path

import pytest

from festa_do_livro.fair_site import EditionNotFoundError, FairSite, HttpResponse
from festa_do_livro.settings import Settings, load_settings

FIXTURES = Path(__file__).parent / "fixtures" / "site"
BASE_URL = "https://festadolivro.edusp.com.br"


def json_response(fixture_name):
    return HttpResponse(status=200, content_type="application/json", body=(FIXTURES / fixture_name).read_bytes())


def html_response(text):
    return HttpResponse(status=200, content_type="text/html; charset=utf-8", body=text.encode())


class FakeHttp:
    def __init__(self, routes):
        self.routes = routes
        self.requested_urls = []

    def __call__(self, url):
        self.requested_urls.append(url)
        for prefix, response in self.routes.items():
            if url.startswith(prefix):
                return response
        return html_response("<html>redirecionado para a página inicial</html>")


def test_detects_current_edition_from_homepage():
    homepage = (FIXTURES / "homepage_edition_27.html").read_text()
    site = FairSite(BASE_URL, FakeHttp({f"{BASE_URL}/": html_response(homepage)}))

    assert site.detect_current_edition() == "27-festa-do-livro-da-usp"


def test_detection_fails_with_clear_message_when_homepage_has_no_edition():
    site = FairSite(BASE_URL, FakeHttp({f"{BASE_URL}/": html_response("<html>manutenção</html>")}))

    with pytest.raises(EditionNotFoundError, match="página inicial"):
        site.detect_current_edition()


def test_reads_event_name_and_period():
    site = FairSite(BASE_URL, FakeHttp({f"{BASE_URL}/api/v1/event?flag=27-festa-do-livro-da-usp": json_response("event_27.json")}))

    event = site.event_details("27-festa-do-livro-da-usp")

    assert event.name == "27 Festa do Livro da USP"
    assert event.period == "26 e 30 de novembro"


def test_unknown_edition_raises_instead_of_parsing_the_redirect_page():
    site = FairSite(BASE_URL, FakeHttp({}))

    with pytest.raises(EditionNotFoundError, match="28-festa-do-livro-da-usp"):
        site.event_details("28-festa-do-livro-da-usp")


def test_lists_publishers_across_all_api_pages():
    http = FakeHttp({
        f"{BASE_URL}/api/v1/event-publishers?page=1&": json_response("publishers_page_1.json"),
        f"{BASE_URL}/api/v1/event-publishers?page=2&": json_response("publishers_page_2.json"),
    })
    site = FairSite(BASE_URL, http)

    publishers = site.list_publishers("27-festa-do-livro-da-usp")

    assert [publisher.name for publisher in publishers] == ["NewPOP Editora", "Pontes Editores", "L&PM Editores"]


def test_publisher_without_price_list_keeps_empty_url():
    http = FakeHttp({
        f"{BASE_URL}/api/v1/event-publishers?page=1&": json_response("publishers_page_1.json"),
        f"{BASE_URL}/api/v1/event-publishers?page=2&": json_response("publishers_page_2.json"),
    })

    publishers = FairSite(BASE_URL, http).list_publishers("27-festa-do-livro-da-usp")

    assert publishers[1].price_list_url == ""


def test_publisher_records_do_not_carry_contact_emails():
    http = FakeHttp({
        f"{BASE_URL}/api/v1/event-publishers?page=1&": json_response("publishers_page_1.json"),
        f"{BASE_URL}/api/v1/event-publishers?page=2&": json_response("publishers_page_2.json"),
    })

    publishers = FairSite(BASE_URL, http).list_publishers("27-festa-do-livro-da-usp")

    assert "email" not in json.dumps([publisher.__dict__ for publisher in publishers])


def publishers_page(names: list[str], page: int, total: int) -> HttpResponse:
    items = [{"name": name, "url": name.lower(), "price_list": f"https://example.com/{name}.pdf", "site": ""} for name in names]
    meta = {"current_page": page, "last_page": 2, "per_page": 2, "total": total}
    return HttpResponse(status=200, content_type="application/json", body=json.dumps({"data": items, "meta": meta}).encode())


class SiteThatChangesBetweenReadings:
    """Answers each page with the next answer prepared for it, the way the official site answers while publishers sign up."""

    def __init__(self, answers_by_page: dict[int, list[HttpResponse]]):
        self.answers_by_page = {page: list(answers) for page, answers in answers_by_page.items()}
        self.requested_pages = []

    def __call__(self, url):
        page = int(re.search(r"[?&]page=(\d+)", url).group(1))
        self.requested_pages.append(page)
        answers = self.answers_by_page[page]
        return answers.pop(0) if len(answers) > 1 else answers[0]


def test_reads_the_pages_again_when_a_publisher_signs_up_while_they_are_read():
    site = SiteThatChangesBetweenReadings({
        1: [publishers_page(["Aletria", "Balão"], page=1, total=3), publishers_page(["Novata", "Aletria"], page=1, total=4)],
        2: [publishers_page(["Balão", "Ciranda"], page=2, total=4)],
    })

    publishers = FairSite(BASE_URL, site).list_publishers("28-festa-do-livro-da-usp")

    assert [publisher.name for publisher in publishers] == ["Novata", "Aletria", "Balão", "Ciranda"]


def test_reads_each_page_once_when_the_list_does_not_change():
    site = SiteThatChangesBetweenReadings({
        1: [publishers_page(["Aletria", "Balão"], page=1, total=3)],
        2: [publishers_page(["Ciranda"], page=2, total=3)],
    })

    FairSite(BASE_URL, site).list_publishers("28-festa-do-livro-da-usp")

    assert site.requested_pages == [1, 2]


def test_never_repeats_a_publisher_when_the_list_keeps_changing():
    site = SiteThatChangesBetweenReadings({
        1: [publishers_page(["Aletria", "Balão"], page=1, total=3)],
        2: [publishers_page(["Balão", "Ciranda"], page=2, total=4)],
    })

    publishers = FairSite(BASE_URL, site).list_publishers("28-festa-do-livro-da-usp")

    assert [publisher.name for publisher in publishers] == ["Aletria", "Balão", "Ciranda"]


def test_settings_auto_edition(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"edition": "auto", "site_base_url": BASE_URL}))

    assert load_settings(settings_file, environment={}) == Settings(edition="auto", site_base_url=BASE_URL)


def test_environment_variable_overrides_edition(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"edition": "auto", "site_base_url": BASE_URL}))

    settings = load_settings(settings_file, environment={"FESTA_EDITION": "28-festa-do-livro-da-usp"})

    assert settings.edition == "28-festa-do-livro-da-usp"


def test_settings_reject_malformed_edition(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"edition": "festa 28", "site_base_url": BASE_URL}))

    with pytest.raises(ValueError, match="edition"):
        load_settings(settings_file, environment={})
