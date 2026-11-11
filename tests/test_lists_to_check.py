"""Which price lists the daily refresh asks a person to look at."""
from festa_do_livro.lists_to_check import ListToCheck, lists_to_check, load_lists_to_check, save_lists_to_check
from festa_do_livro.price_verification import VerificationReport


def book(number: int, cover=59.9, fair=29.95) -> dict:
    entry = {"i": f"97865000000{number:02d}", "t": f"Livro {number}", "f": fair, "x": 0}
    if cover is not None:
        entry["c"] = cover
    return entry


def catalog_of(publisher: str, books: list[dict]) -> dict:
    return {"evento": {"edicao": "28-festa-do-livro-da-usp", "nome": "28 Festa do Livro da USP"}, "expositores": [{"nome": publisher, "site": ""}], "livros": books}


TEN_BOOKS = [book(number) for number in range(10)]


def test_list_read_well_is_not_flagged():
    assert lists_to_check(catalog_of("Arquipélago", TEN_BOOKS), VerificationReport(), [], {0: "tabela"}, {0: 10}) == []


def test_list_read_without_any_book_is_flagged():
    found = lists_to_check(catalog_of("Universo dos Livros", []), VerificationReport(), [], {0: "posição do texto"}, {0: 0})
    assert [(item.publisher, item.problem) for item in found] == [("Universo dos Livros", "nenhum livro lido")]


def test_list_where_most_books_have_no_cover_price_is_flagged():
    books = [book(number, cover=None) for number in range(10)]
    found = lists_to_check(catalog_of("Arquipélago", books), VerificationReport(), [], {0: "tabela"}, {0: 10})
    assert [(item.problem, item.detail) for item in found] == [("sem preço de capa", "10 de 10 livros")]


def test_list_with_many_prices_missing_from_the_pdf_is_flagged():
    report = VerificationReport(mismatches_by_exhibitor={0: [("Livro 1", "capa 59.9 · feira 29.95")] * 4})
    found = lists_to_check(catalog_of("Instituto Tomie Ohtake", TEN_BOOKS), report, [], {0: "tabela"}, {0: 10})
    assert [item.problem for item in found] == ["preços que não batem com o PDF"]


def test_list_printed_in_strips_is_not_flagged_for_prices_on_other_pages():
    report = VerificationReport(mismatches_by_exhibitor={0: [("Livro 1", "capa 59.9 · feira 29.95")] * 10})
    assert lists_to_check(catalog_of("Phorte Editora", TEN_BOOKS), report, [], {0: "tabela em faixas"}, {0: 10}) == []


def test_list_that_lost_most_of_its_rows_is_flagged():
    found = lists_to_check(catalog_of("Mundaréu / Manjuba", TEN_BOOKS[:2]), VerificationReport(), [], {0: "tabela"}, {0: 10})
    assert [(item.problem, item.detail) for item in found] == [("livros perdidos", "2 das 10 linhas lidas viraram livro")]


def test_list_that_failed_to_download_is_flagged():
    found = lists_to_check(catalog_of("Edusp", []), VerificationReport(), [("Edusp", "falha de rede: timed out")], {}, {})
    assert [(item.problem, item.detail) for item in found] == [("lista não baixada", "falha de rede: timed out")]


def test_publisher_without_a_price_list_yet_is_not_flagged():
    assert lists_to_check(catalog_of("Editora nova", []), VerificationReport(), [("Editora nova", "sem lista de preços")], {}, {}) == []


def test_lists_to_check_come_back_the_same_from_their_file(tmp_path):
    items = [ListToCheck("Nós", "sem preço de capa", "68 de 68 livros")]
    save_lists_to_check(tmp_path / "listas-para-conferir.json", items)
    assert load_lists_to_check(tmp_path / "listas-para-conferir.json") == items
