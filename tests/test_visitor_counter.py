"""The visitor counter: the published site adds one per browser; the README badges and the weekly snapshot only read it."""
import re
from pathlib import Path
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[1]
COUNTER_ADDRESS = re.compile(r"https://abacus\.jasoncameron\.dev/(hit|get)/([\w.-]+)/([\w.-]+)")
SITE_PAGE = "site/index.html"
COUNTER_READERS = ["README.md", "README.pt-BR.md", ".github/workflows/guardar-contador-de-visitantes.yml"]


def counter_references(relative_path: str) -> list[tuple[str, str]]:
    text = unquote((ROOT / relative_path).read_text())
    return [(operation, f"{namespace}/{key}") for operation, namespace, key in COUNTER_ADDRESS.findall(text)]


def test_site_adds_to_the_counter():
    assert [operation for operation, _ in counter_references(SITE_PAGE)] == ["hit"]


@pytest.mark.parametrize("path", COUNTER_READERS)
def test_badges_and_snapshot_only_read_the_counter(path):
    assert {operation for operation, _ in counter_references(path)} == {"get"}


def test_site_badges_and_snapshot_use_the_same_counter():
    counters = {counter for path in [SITE_PAGE, *COUNTER_READERS] for _, counter in counter_references(path)}
    assert len(counters) == 1


def test_footer_tells_visitors_about_the_counter():
    page = (ROOT / SITE_PAGE).read_text()
    footer = page[page.index('<footer id="footer">'):page.index("</footer>")]
    assert "contador público de visitantes" in footer
