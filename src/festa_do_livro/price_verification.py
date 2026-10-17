"""Checks every catalog price against the line of the same ISBN in the publisher's PDF text."""
import collections
import re
from dataclasses import dataclass, field

from .isbn import isbn_of_book_id


@dataclass
class VerificationReport:
    total_books: int = 0
    books_without_isbn: int = 0
    mismatches_by_exhibitor: dict = field(default_factory=lambda: collections.defaultdict(list))

    @property
    def mismatch_count(self) -> int:
        return sum(len(items) for items in self.mismatches_by_exhibitor.values())


def written_forms(value: float, allow_whole_number: bool) -> set[str]:
    two_decimals = f"{value:.2f}"
    forms = {two_decimals.replace(".", ","), two_decimals}
    if two_decimals.endswith("0"):
        forms.add(f"{value:.1f}".replace(".", ","))
    if allow_whole_number and value == int(value):
        forms.add(str(int(value)))
    if value >= 1000:
        forms.add(f"{int(value) // 1000}.{two_decimals.replace('.', ',')[-6:]}")
    return forms


def compact_text(plain_text: str) -> str:
    """Joins the parts of an ISBN written with dashes, broken across two lines ("978-65-87955-" above "23-0") or ending in X."""
    joined = re.sub(r"(?<=\d)-\s+(?=\d)", "", plain_text)
    joined = re.sub(r"(?<=\d)[\-\s](?=\d)|(?<=\d)-(?=[Xx]\b)", "", joined)
    return re.sub(r"\s+", " ", joined)


def verify_prices(catalog: dict, plain_text_by_exhibitor: dict[int, str]) -> VerificationReport:
    report = VerificationReport()
    compacted: dict[int, str] = {}
    for book in catalog["livros"]:
        report.total_books += 1
        exhibitor_index = book["x"]
        isbn = isbn_of_book_id(book["i"])
        if not isbn:
            report.books_without_isbn += 1
            continue
        if exhibitor_index not in compacted:
            compacted[exhibitor_index] = compact_text(plain_text_by_exhibitor.get(exhibitor_index, ""))
        text = compacted[exhibitor_index]
        position = text.find(isbn)
        if position < 0:
            report.mismatches_by_exhibitor[exhibitor_index].append((book["t"], "ISBN não aparece no PDF"))
            continue
        next_isbn = re.search(r"97[89]\d{10}", text[position + 13:position + 1500])
        window = text[max(0, position - 200):position + 13 + (next_isbn.start() if next_isbn else 900)]
        window_without_spaces = window.replace(" ", "")
        found = lambda value: any(form in window or form in window_without_spaces for form in written_forms(value, True))
        if not found(book["f"]) or ("c" in book and not found(book["c"])):
            report.mismatches_by_exhibitor[exhibitor_index].append((book["t"], f"capa {book.get('c')} · feira {book['f']}"))
    return report


def report_markdown(
    catalog: dict, report: VerificationReport, download_problems: list[tuple[str, str]], methods: dict[int, str], rows_read: dict[int, int],
) -> str:
    """Per exhibitor, "Lidos" far above "Livros" means rows were lost, and many books "Sem capa" usually mean a price column was misread."""
    exhibitors = catalog["expositores"]
    event = catalog["evento"]
    lines = [
        f"# Relatório do catálogo: {event['nome']}",
        "",
        f"- Edição: `{event['edicao']}`" + (f" · {event['periodo']}" if event.get("periodo") else ""),
        f"- Editoras no site: {len(exhibitors)}",
        f"- Livros no catálogo: {report.total_books}",
        f"- Livros sem ISBN (preço não conferível automaticamente): {report.books_without_isbn}",
        f"- Preços que não bateram com o PDF: {report.mismatch_count}",
        f"- Livros sem preço de capa: {sum(1 for book in catalog['livros'] if 'c' not in book)}",
        "",
    ]
    if download_problems:
        lines += ["## Listas que não foram lidas", ""] + [f"- {name}: {problem}" for name, problem in download_problems] + [""]
    counts = collections.Counter(book["x"] for book in catalog["livros"])
    without_cover = collections.Counter(book["x"] for book in catalog["livros"] if "c" not in book)
    lines += ["## Livros por editora", "", "| Editora | Livros | Lidos | Sem capa | Leitura | Divergências |", "|---|---:|---:|---:|---|---:|"]
    for index, exhibitor in enumerate(exhibitors):
        if index in methods:
            lines.append(
                f"| {exhibitor['nome']} | {counts.get(index, 0)} | {rows_read.get(index, 0)} | {without_cover.get(index, 0)} | {methods[index]} "
                f"| {len(report.mismatches_by_exhibitor.get(index, []))} |"
            )
    if report.mismatch_count:
        lines += ["", "## Divergências (amostra de até 5 por editora)", ""]
        for index, items in sorted(report.mismatches_by_exhibitor.items(), key=lambda pair: -len(pair[1])):
            lines.append(f"- **{exhibitors[index]['nome']}** ({len(items)}): " + "; ".join(f"{title} ({detail})" for title, detail in items[:5]))
    return "\n".join(lines) + "\n"
