import argparse
import json
import logging
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .catalog_builder import build_catalog, event_summary, parse_price_list, same_content
from .fair_site import FairSite
from .price_list_download import download_price_lists
from .price_verification import report_markdown, verify_prices
from .settings import load_settings
from .site_assembly import assemble_site

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_edition(settings, site: FairSite, edition_argument: str) -> str:
    edition = edition_argument or settings.edition
    return site.detect_current_edition() if edition == "auto" else edition


def published_edition(output_directory: Path) -> str:
    pointer = output_directory / "edicao-atual.json"
    return json.loads(pointer.read_text())["edicao"] if pointer.exists() else ""


def refuse_empty_catalog(edition: str, output_directory: Path) -> int:
    """An empty catalog never replaces the published one: a new edition waits for its lists, and the published edition losing every book means reading broke."""
    published = published_edition(output_directory)
    if edition != published:
        message, exit_code = f"Nenhuma lista de preço da edição {edition} foi lida ainda; o site continua com {published or 'a edição atual'}.", 0
    else:
        message, exit_code = f"Nenhum livro lido para {edition}, a edição publicada: o catálogo atual foi mantido. Veja as listas com problema acima.", 1
    print(message, file=sys.stderr)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as summary:
            summary.write(message + "\n")
    return exit_code


def command_detect_edition(arguments) -> int:
    settings = load_settings(arguments.settings)
    site = FairSite(settings.site_base_url)
    edition = resolve_edition(settings, site, arguments.edition)
    print(json.dumps(event_summary(site.event_details(edition)), ensure_ascii=False))
    return 0


def command_build(arguments) -> int:
    settings = load_settings(arguments.settings)
    site = FairSite(settings.site_base_url)
    edition = resolve_edition(settings, site, arguments.edition)
    event = site.event_details(edition)
    publishers = site.list_publishers(edition)
    print(f"{event.name}: {len(publishers)} editoras", file=sys.stderr)

    downloads = download_price_lists(publishers, Path(arguments.cache) / edition)
    download_problems = [(result.publisher.name, result.problem) for result in downloads if result.problem]
    readable = [result for result in downloads if result.path is not None]
    parsed_lists = []
    if readable:
        with ProcessPoolExecutor() as executor:
            parsed_lists = list(executor.map(parse_price_list, [result.path for result in readable]))
    parsed_by_index = {result.publisher_index: parsed for result, parsed in zip(readable, parsed_lists)}
    print(f"{len(parsed_by_index)} listas lidas, {len(download_problems)} com problema", file=sys.stderr)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    catalog = build_catalog(event, publishers, parsed_by_index, generated_at)
    if not catalog["livros"]:
        return refuse_empty_catalog(edition, Path(arguments.output))

    output_directory = Path(arguments.output) / edition
    output_directory.mkdir(parents=True, exist_ok=True)
    catalog_path = output_directory / "catalogo.json"
    if catalog_path.exists():
        previous = json.loads(catalog_path.read_text())
        if same_content(previous, catalog):
            catalog["geradoEm"] = previous.get("geradoEm", generated_at)

    report = verify_prices(catalog, {index: parsed.plain_text for index, parsed in parsed_by_index.items()})
    methods = {index: parsed.method for index, parsed in parsed_by_index.items()}
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")))
    rows_read = {index: len(parsed.books) for index, parsed in parsed_by_index.items()}
    (output_directory / "relatorio.md").write_text(report_markdown(catalog, report, download_problems, methods, rows_read))
    (output_directory / "edicao.json").write_text(json.dumps(catalog["evento"], ensure_ascii=False, indent=2) + "\n")
    (Path(arguments.output) / "edicao-atual.json").write_text(
        json.dumps({"edicao": edition, "catalogo": f"{edition}/catalogo.json", "edicaoInfo": f"{edition}/edicao.json", "relatorio": f"{edition}/relatorio.md"}, ensure_ascii=False, indent=2) + "\n"
    )
    print(f"{report.total_books} livros · {report.mismatch_count} preços a conferir · {catalog_path}", file=sys.stderr)
    return 0


def command_assemble_site(arguments) -> int:
    pointer = assemble_site(PROJECT_ROOT / "site", Path(arguments.data), Path(arguments.output))
    print(f"Site montado em {arguments.output} com a edição {pointer['edicao']}", file=sys.stderr)
    return 0


def main(argv=None) -> int:
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    parser = argparse.ArgumentParser(prog="festa_do_livro", description="Catálogo de preços da Festa do Livro da USP")
    parser.add_argument("--settings", default=str(PROJECT_ROOT / "settings.json"), help="arquivo de configuração")
    parser.add_argument("--edition", default="", help='sobrepõe a edição (ex.: "28-festa-do-livro-da-usp")')
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("detect-edition", help="mostra a edição que seria usada")
    build = subcommands.add_parser("build", help="baixa as listas e gera catálogo + relatório")
    build.add_argument("--cache", default=str(PROJECT_ROOT / "cache"), help="pasta para os PDFs baixados")
    build.add_argument("--output", default=str(PROJECT_ROOT / "data"), help="pasta de saída")
    assemble = subcommands.add_parser("assemble-site", help="monta a pasta publicada no GitHub Pages")
    assemble.add_argument("--data", default=str(PROJECT_ROOT / "data"), help="pasta com os catálogos gerados")
    assemble.add_argument("--output", default=str(PROJECT_ROOT / "_site"), help="pasta de saída do site")
    arguments = parser.parse_args(argv)
    commands = {"detect-edition": command_detect_edition, "build": command_build, "assemble-site": command_assemble_site}
    return commands[arguments.command](arguments)


if __name__ == "__main__":
    sys.exit(main())
