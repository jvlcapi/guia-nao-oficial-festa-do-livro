from festa_do_livro.price_verification import VerificationReport, report_markdown, verify_prices

CATALOG = {
    "evento": {"edicao": "27-festa-do-livro-da-usp", "nome": "27 Festa do Livro da USP", "periodo": "26 e 30 de novembro"},
    "expositores": [{"nome": "Olhares", "site": ""}, {"nome": "Boitempo", "site": ""}],
    "livros": [
        {"i": "9786588280713", "t": "101 dicas de Sketching", "c": 95.0, "f": 47.5, "x": 0},
        {"i": "9786588280386", "t": "Croche moderno", "f": 75.0, "x": 0},
        {"i": "9788575593646-1a2b3c", "t": "Mulher, estado e revolução", "c": 69.0, "f": 34.5, "x": 1},
    ],
}


def test_report_shows_books_read_and_books_without_cover_per_exhibitor():
    text = report_markdown(CATALOG, VerificationReport(total_books=3), [], {0: "tabela", 1: "tabela"}, {0: 70, 1: 1})
    assert "| Olhares | 2 | 70 | 1 | tabela | 0 |" in text


def test_book_whose_id_carries_an_exhibitor_suffix_is_still_checked_by_isbn():
    report = verify_prices(CATALOG, {0: "", 1: "9788575593646 MULHER, ESTADO E REVOLUCAO 69,00 34,50"})
    assert (report.books_without_isbn, report.mismatches_by_exhibitor.get(1, [])) == (0, [])


def test_isbn_broken_across_two_lines_is_found():
    catalog = {**CATALOG, "livros": [{"i": "9786587955230", "t": "A melhor época da nossa vida", "c": 88.0, "f": 44.0, "x": 0}]}
    report = verify_prices(catalog, {0: "978-65-87955-\n23-0\nA melhor época da nossa vida\nAntonio Scurati\nR$ 88,00 R$ 44,00"})
    assert report.mismatch_count == 0


def test_isbn_10_ending_in_x_is_found():
    catalog = {**CATALOG, "livros": [{"i": "857480195X", "t": "Ancora Medicinal", "c": 68.0, "f": 34.0, "x": 0}]}
    report = verify_prices(catalog, {0: "85-7480-195-X Ancora Medicinal para Conservar a Vida 68,00 34,00"})
    assert report.mismatch_count == 0
