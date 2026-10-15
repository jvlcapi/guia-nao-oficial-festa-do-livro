import json
import re
import struct
from pathlib import Path

from festa_do_livro.site_assembly import assemble_site

ROOT = Path(__file__).resolve().parents[1]
SITE_ADDRESS = "https://jvlcapi.github.io/guia-nao-oficial-festa-do-livro/"
WHATSAPP_PREVIEW_LIMIT_BYTES = 300 * 1024


def write_edition(data_directory: Path, edition: str):
    edition_directory = data_directory / edition
    edition_directory.mkdir(parents=True)
    (edition_directory / "catalogo.json").write_text(json.dumps({"livros": [], "expositores": []}))
    (edition_directory / "edicao.json").write_text(json.dumps({"edicao": edition, "nome": "28 Festa do Livro da USP", "periodo": ""}))
    (data_directory / "edicao-atual.json").write_text(json.dumps({
        "edicao": edition, "catalogo": f"{edition}/catalogo.json", "edicaoInfo": f"{edition}/edicao.json", "relatorio": f"{edition}/relatorio.md",
    }))


def test_site_gets_the_current_edition_files(tmp_path):
    write_edition(tmp_path / "data", "28-festa-do-livro-da-usp")

    assemble_site(ROOT / "site", tmp_path / "data", tmp_path / "_site")

    published = json.loads((tmp_path / "_site" / "edicao.json").read_text())
    assert published["edicao"] == "28-festa-do-livro-da-usp"


def test_site_contains_page_offline_worker_and_catalog(tmp_path):
    write_edition(tmp_path / "data", "28-festa-do-livro-da-usp")

    assemble_site(ROOT / "site", tmp_path / "data", tmp_path / "_site")

    names = sorted(path.name for path in (tmp_path / "_site").iterdir())
    assert names == [".nojekyll", "apple-touch-icon.png", "catalogo.json", "edicao.json", "icon.svg", "index.html", "link-preview.png", "manifest.webmanifest", "sw.js"]


def test_site_page_has_no_claude_artifact_dependency():
    page = (ROOT / "site" / "index.html").read_text()
    assert "claude.use" not in page and "claude?.use" not in page


def meta_content(page: str, property_name: str) -> str:
    match = re.search(rf'<meta (?:property|name)="{re.escape(property_name)}" content="([^"]*)"', page)
    assert match, f"site/index.html não tem a tag {property_name}"
    return match.group(1)


def link_preview_image_name() -> str:
    page = (ROOT / "site" / "index.html").read_text()
    return meta_content(page, "og:image").removeprefix(SITE_ADDRESS)


def test_link_preview_image_uses_the_full_site_address():
    page = (ROOT / "site" / "index.html").read_text()
    assert meta_content(page, "og:image").startswith(SITE_ADDRESS)


def test_link_preview_image_is_published_with_the_site(tmp_path):
    write_edition(tmp_path / "data", "28-festa-do-livro-da-usp")

    assemble_site(ROOT / "site", tmp_path / "data", tmp_path / "_site")

    assert (tmp_path / "_site" / link_preview_image_name()).is_file()


def test_link_preview_declares_the_real_image_size():
    page = (ROOT / "site" / "index.html").read_text()
    width, height = struct.unpack(">II", (ROOT / "site" / link_preview_image_name()).read_bytes()[16:24])
    assert (meta_content(page, "og:image:width"), meta_content(page, "og:image:height")) == (str(width), str(height))


def test_link_preview_image_is_small_enough_for_whatsapp():
    assert (ROOT / "site" / link_preview_image_name()).stat().st_size < WHATSAPP_PREVIEW_LIMIT_BYTES
