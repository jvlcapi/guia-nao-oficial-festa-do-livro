"""Price lists the reader may have misread, so the daily refresh can ask a person to open their PDF.
Each rule matches a failure that already reached the site: a list with no book at all, a price column read as text,
rows dropped on the way to the catalog, and prices that cannot be found next to their ISBN in the PDF."""
import collections
import json
from dataclasses import dataclass
from pathlib import Path

from .catalog_builder import READ_IN_STRIPS
from .price_list_download import NO_PRICE_LIST_YET
from .price_verification import VerificationReport

LISTS_TO_CHECK_FILE = "listas-para-conferir.json"
SMALLEST_PROBLEM = 3
SHARE_OF_BOOKS_KEPT = 0.8
SHARE_WITHOUT_COVER_PRICE = 0.5
SHARE_OF_PRICES_NOT_IN_THE_PDF = 0.2


@dataclass(frozen=True)
class ListToCheck:
    publisher: str
    problem: str
    detail: str

    @property
    def key(self) -> str:
        """Stays the same while the numbers in the detail change, so the same problem is never announced twice."""
        return f"**{self.publisher}**: {self.problem}"

    def markdown_line(self) -> str:
        return f"- {self.key} ({self.detail})"


def lists_to_check(
    catalog: dict, report: VerificationReport, download_problems: list[tuple[str, str]], methods: dict[int, str], rows_read: dict[int, int],
) -> list[ListToCheck]:
    exhibitors = catalog["expositores"]
    books = collections.Counter(book["x"] for book in catalog["livros"])
    without_cover = collections.Counter(book["x"] for book in catalog["livros"] if "c" not in book)
    found = [ListToCheck(name, "lista não baixada", problem) for name, problem in download_problems if problem != NO_PRICE_LIST_YET]
    for index in sorted(methods):
        name, book_count, row_count = exhibitors[index]["nome"], books.get(index, 0), rows_read.get(index, 0)
        if book_count == 0:
            detail = f"o leitor achou {row_count} linhas e nenhuma virou livro" if row_count else "a lista foi baixada, mas o leitor não achou nenhum livro"
            found.append(ListToCheck(name, "nenhum livro lido", detail))
            continue
        if row_count - book_count >= SMALLEST_PROBLEM and book_count < SHARE_OF_BOOKS_KEPT * row_count:
            found.append(ListToCheck(name, "livros perdidos", f"{book_count} das {row_count} linhas lidas viraram livro"))
        if without_cover[index] >= SMALLEST_PROBLEM and without_cover[index] > SHARE_WITHOUT_COVER_PRICE * book_count:
            found.append(ListToCheck(name, "sem preço de capa", f"{without_cover[index]} de {book_count} livros"))
        # In a list printed in strips the ISBN and its prices sit on different pages, so the price check cannot find them together.
        mismatches = len(report.mismatches_by_exhibitor.get(index, []))
        if methods[index] != READ_IN_STRIPS and mismatches >= SMALLEST_PROBLEM and mismatches > SHARE_OF_PRICES_NOT_IN_THE_PDF * book_count:
            found.append(ListToCheck(name, "preços que não batem com o PDF", f"{mismatches} de {book_count} livros"))
    return found


def save_lists_to_check(path: Path, items: list[ListToCheck]) -> None:
    entries = [{"editora": item.publisher, "problema": item.problem, "detalhe": item.detail} for item in items]
    Path(path).write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n")


def load_lists_to_check(path: Path) -> list[ListToCheck]:
    return [ListToCheck(entry["editora"], entry["problema"], entry["detalhe"]) for entry in json.loads(Path(path).read_text())]
