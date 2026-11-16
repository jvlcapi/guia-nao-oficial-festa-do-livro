"""The visitor counter: the published site adds one per browser, and the daily snapshot only reads it. The snapshot saves the total
in the repository, where the README badges read it, so they keep working when the counter service is down."""
import json
import re
from pathlib import Path
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[1]
COUNTER_ADDRESS = re.compile(r"https://abacus\.jasoncameron\.dev/(hit|get)/([\w.-]+)/([\w.-]+)")
SITE_PAGE = "site/index.html"
SNAPSHOT_WORKFLOW = ".github/workflows/guardar-contador-de-visitantes.yml"
READMES = ["README.md", "README.en.md"]
SAVED_BADGE = "data/selo-de-visitantes.json"
SAVED_BADGE_ADDRESS = f"https://raw.githubusercontent.com/jvlcapi/guia-nao-oficial-festa-do-livro/main/{SAVED_BADGE}"


def counter_references(relative_path: str) -> list[tuple[str, str]]:
    text = unquote((ROOT / relative_path).read_text())
    return [(operation, f"{namespace}/{key}") for operation, namespace, key in COUNTER_ADDRESS.findall(text)]


def test_site_adds_to_the_counter():
    assert [operation for operation, _ in counter_references(SITE_PAGE)] == ["hit"]


def test_snapshot_only_reads_the_counter():
    assert {operation for operation, _ in counter_references(SNAPSHOT_WORKFLOW)} == {"get"}


def test_site_and_snapshot_use_the_same_counter():
    counters = {counter for path in [SITE_PAGE, SNAPSHOT_WORKFLOW] for _, counter in counter_references(path)}
    assert len(counters) == 1


@pytest.mark.parametrize("path", READMES)
def test_readme_badge_shows_the_total_saved_in_the_repository(path):
    assert SAVED_BADGE_ADDRESS in unquote((ROOT / path).read_text())


@pytest.mark.parametrize("path", READMES)
def test_readme_never_calls_the_counter(path):
    assert counter_references(path) == []


def test_snapshot_saves_the_total_the_badges_show():
    assert f"ARQUIVO_DO_SELO: {SAVED_BADGE}" in (ROOT / SNAPSHOT_WORKFLOW).read_text()


def test_saved_total_is_a_badge_shields_can_read():
    badge = json.loads((ROOT / SAVED_BADGE).read_text())
    assert (badge["schemaVersion"], badge["message"].isdigit()) == (1, True)


def test_footer_tells_visitors_about_the_counter():
    page = (ROOT / SITE_PAGE).read_text()
    footer = page[page.index('<footer id="footer">'):page.index("</footer>")]
    assert "contador público de visitantes" in footer
