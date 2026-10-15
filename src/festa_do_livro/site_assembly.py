"""Puts together the folder GitHub Pages publishes: the static site plus the current edition's data."""
import json
import shutil
from pathlib import Path

SITE_FILES = ("index.html", "sw.js", "manifest.webmanifest", "icon.svg", "apple-touch-icon.png", "link-preview.png")


def assemble_site(site_source: Path, data_directory: Path, output: Path) -> dict:
    pointer = json.loads((Path(data_directory) / "edicao-atual.json").read_text())
    output = Path(output)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name in SITE_FILES:
        shutil.copy(Path(site_source) / name, output / name)
    shutil.copy(Path(data_directory) / pointer["catalogo"], output / "catalogo.json")
    shutil.copy(Path(data_directory) / pointer["edicaoInfo"], output / "edicao.json")
    (output / ".nojekyll").write_text("")
    return pointer
