import re
from pathlib import Path

import pytest

from festa_do_livro.catalog_builder import (
    NAMES_IN_OLD_IDS_FILE,
    ONLY_COVER_PRICE_NOTICE,
    ParsedPriceList,
    books_only_the_other_reader_found,
    build_catalog,
    has_only_cover_prices,
    imprint_repeats_exhibitor,
    load_names_in_old_ids,
    parse_price_list,
    safe_public_url,
    same_content,
    table_reader_wins,
    tidy_subject,
    without_garbled_copies,
)
from festa_do_livro.fair_site import EventDetails, Publisher
from festa_do_livro.isbn import isbn13_check_digit, isbn_of_book_id
from festa_do_livro.price_verification import verify_prices

PRICE_LISTS = Path(__file__).parent / "fixtures" / "price_lists"
EVENT = EventDetails(edition="27-festa-do-livro-da-usp", name="27 Festa do Livro da USP", period="26 e 30 de novembro")


def catalog_for(fixture_name: str, exhibitor_name: str) -> tuple[dict, ParsedPriceList]:
    parsed = parse_price_list(PRICE_LISTS / fixture_name)
    publishers = [Publisher(name=exhibitor_name, slug="", price_list_url="https://example.com/x.pdf", site="")]
    return build_catalog(EVENT, publishers, {0: parsed}, "2026-10-02T00:00:00+00:00"), parsed


def book_titled(catalog: dict, title_start: str) -> dict:
    matches = [book for book in catalog["livros"] if book["t"].startswith(title_start)]
    assert matches, f"livro começando com {title_start!r} não encontrado"
    return matches[0]


def parsed_book(isbn: str, title: str, cover=72.0, fair=36.0, subject="", url="") -> dict:
    return {"isbn": isbn, "title": title, "author": "", "imprint": "", "subject": subject, "url": url, "cover_price": cover, "fair_price": fair}


def catalog_from(books_by_exhibitor: dict[str, list[dict]], plain_text: str = "") -> dict:
    publishers = [Publisher(name=name, slug="", price_list_url="x", site="") for name in books_by_exhibitor]
    parsed = {index: ParsedPriceList(books=books, method="tabela", plain_text=plain_text) for index, books in enumerate(books_by_exhibitor.values())}
    return build_catalog(EVENT, publishers, parsed, "2026-10-02T00:00:00+00:00")


@pytest.fixture(scope="module")
def newpop():
    return catalog_for("newpop.pdf", "NewPOP Editora")


@pytest.fixture(scope="module")
def harpercollins():
    return catalog_for("harpercollins.pdf", "HarperCollins Brasil")


@pytest.fixture(scope="module")
def atma():
    return catalog_for("atma.pdf", "Atma Editora")


@pytest.fixture(scope="module")
def mundareu():
    return catalog_for("mundareu_manjuba.pdf", "Mundaréu / Manjuba")


@pytest.fixture(scope="module")
def bei():
    return catalog_for("bei.pdf", "BEĨ")


@pytest.fixture(scope="module")
def olhares():
    return catalog_for("olhares.pdf", "Olhares")


@pytest.fixture(scope="module")
def duna_dueto():
    return catalog_for("duna_dueto.pdf", "Duna Dueto Editora")


def test_reads_every_book_of_a_standard_list(newpop):
    catalog, _ = newpop
    assert len(catalog["livros"]) == 338


def test_standard_list_prices(newpop):
    book = book_titled(newpop[0], "Street Fighter: Alpha - Volume 01")
    assert (book["i"], book["c"], book["f"]) == ("9788583620143", 19.9, 9.95)


def test_table_number_column_is_not_read_as_price(harpercollins):
    book = book_titled(harpercollins[0], "A esperança da Primavera")
    assert (book["c"], book["f"]) == (89.9, 44.95)


def test_stray_number_in_imprint_column_is_not_read_as_price(atma):
    book = book_titled(atma[0], "Baya, Kamu e Yaí")
    assert (book["c"], book["f"]) == (96.0, 48.0)


def test_author_cut_by_the_table_cell_is_completed_from_the_text(atma):
    book = book_titled(atma[0], "O corvo")
    assert book["a"] == "Edgar Allan Poe"


def test_distributor_keeps_the_real_imprint(atma):
    book = book_titled(atma[0], "O corvo")
    assert book["s"] == "VALER EDITORA"


def test_row_numbers_are_not_read_as_prices():
    catalog, _ = catalog_for("autentica.pdf", "Autêntica Editora")
    book = book_titled(catalog, "1461 dias na trincheira")
    assert (book["c"], book["f"]) == (79.8, 39.9)


def test_list_with_only_cover_price_and_percentage():
    catalog, _ = catalog_for("contraponto.pdf", "Contraponto")
    book = book_titled(catalog, "Alexandre o Grande")
    assert (book["c"], book["f"]) == (116.0, 58.0)


def test_whole_number_cover_price_next_to_decimal_fair_price():
    catalog, _ = catalog_for("ars_et_vita.pdf", "Ars et Vita")
    book = book_titled(catalog, "A bússola adúltera")
    assert (book["c"], book["f"]) == (58.0, 23.2)


def test_every_newpop_price_matches_the_pdf_text(newpop):
    catalog, parsed = newpop
    report = verify_prices(catalog, {0: parsed.plain_text})
    assert report.mismatch_count == 0


def test_verification_flags_a_wrong_price(newpop):
    catalog, parsed = newpop
    tampered = {**catalog, "livros": [dict(book_titled(catalog, "Street Fighter: Alpha - Volume 01"), f=1.23)]}
    report = verify_prices(tampered, {0: parsed.plain_text})
    assert report.mismatch_count == 1


def test_catalog_carries_event_name_period_and_dates(newpop):
    assert newpop[0]["evento"] == {
        "edicao": "27-festa-do-livro-da-usp", "nome": "27 Festa do Livro da USP", "periodo": "26 e 30 de novembro",
        "ano": 2025, "inicio": "2025-11-26", "fim": "2025-11-30",
    }


def test_url_with_access_token_is_never_published():
    assert safe_public_url("https://api.metabooks.com/api/v1/cover/9788562564932/m?access_token=abc") == ""


def test_credential_query_parameters_are_removed_from_shop_links():
    assert safe_public_url("https://loja.example.com/livro?id=7&token=segredo") == "https://loja.example.com/livro?id=7"


def test_cover_image_links_are_dropped():
    assert safe_public_url("https://fl-storage.bookinfometadados.com.br/uploads/book/first_cover/9788525431561.jpg") == ""


@pytest.mark.parametrize("imprint, repeats", [
    ("COMPANHIA DAS LETRA", True),
    ("Atma Editora L", True),
    ("NOVA FRONTEIRA / TRAMA", False),
    ("VALER EDITORA", False),
    ("EDITORA AUTORES ASSOCIADOS LTDA", True),
])
def test_imprint_redundancy(imprint, repeats):
    exhibitor = {"COMPANHIA DAS LETRA": "Companhia das Letras", "Atma Editora L": "Atma Editora", "NOVA FRONTEIRA / TRAMA": "Nova Fronteira",
                 "VALER EDITORA": "Atma Editora", "EDITORA AUTORES ASSOCIADOS LTDA": "Editora Autores Associados"}[imprint]
    assert imprint_repeats_exhibitor(imprint, exhibitor) is repeats


def test_prices_below_one_real_are_discarded():
    parsed = ParsedPriceList(
        books=[
            {"isbn": "9788539102211", "title": "Livro de verdade", "author": "", "imprint": "", "subject": "", "url": "", "cover_price": 72.0, "fair_price": 36.0},
            {"isbn": "9788539100001", "title": "Erro da planilha", "author": "", "imprint": "", "subject": "", "url": "", "cover_price": 0.1, "fair_price": 0.05},
        ],
        method="tabela",
        plain_text="",
    )
    publishers = [Publisher(name="Annablume", slug="", price_list_url="x", site="")]
    catalog = build_catalog(EVENT, publishers, {0: parsed}, "2026-10-02T00:00:00+00:00")
    assert [book["t"] for book in catalog["livros"]] == ["Livro de verdade"]


def test_same_content_ignores_generation_time(newpop):
    catalog, _ = newpop
    assert same_content(catalog, {**catalog, "geradoEm": "outro horário"})


def test_isbn_split_across_two_lines_is_joined(mundareu):
    book = book_titled(mundareu[0], "A melhor época da nossa vida")
    assert (book["i"], book["c"], book["f"]) == ("9786587955230", 88.0, 44.0)


def test_every_book_of_a_list_with_split_isbns_is_kept(mundareu):
    assert len(mundareu[0]["livros"]) == 40


def test_spreadsheet_isbns_do_not_merge_different_books(bei):
    assert len(bei[0]["livros"]) == 56


def test_book_with_spreadsheet_isbn_shows_no_isbn(bei):
    book = book_titled(bei[0], "ALEX VALLAURI")
    assert isbn_of_book_id(book["i"]) == ""


def test_cover_price_is_not_published_as_fair_price_when_the_table_loses_a_column(olhares):
    book = book_titled(olhares[0], "101 dicas de Sketching")
    assert (book["c"], book["f"]) == (95.0, 47.5)


def test_row_that_only_repeats_the_publisher_name_is_not_a_book(olhares):
    assert "Olhares" not in [book["t"] for book in olhares[0]["livros"]]


def test_fair_price_printed_above_the_isbn_line(duna_dueto):
    book = book_titled(duna_dueto[0], "Advogado e o imperador, O")
    assert (book["c"], book["f"]) == (52.0, 26.0)


def test_genre_never_carries_a_price(duna_dueto):
    assert [book["g"] for book in duna_dueto[0]["livros"] if re.search(r"\d,\d\d", book.get("g", ""))] == []


def test_price_completed_from_the_isbn_line():
    line = "9786556020679 Assata Assata Shakur Pallas R$ 98,00 R$ 49,00 Biografia https://pallaseditora.com.br/assata"
    catalog = catalog_from({"Pallas": [parsed_book("9786556020679", "Assata", cover=None, fair=98.0)]}, plain_text=line)
    assert (catalog["livros"][0]["c"], catalog["livros"][0]["f"]) == (98.0, 49.0)


def test_percentage_on_the_isbn_line_is_not_a_price():
    line = "9786558470427 A COR PURPURA WALKER, ALICE LIT.EST.-ROMANCE 292 JOSE OLYMPIO 129,90 64,95 50,00%"
    catalog = catalog_from({"Grupo Editorial Record": [parsed_book("9786558470427", "A COR PURPURA", cover=None, fair=64.95)]}, plain_text=line)
    assert (catalog["livros"][0]["c"], catalog["livros"][0]["f"]) == (129.9, 64.95)


def test_list_with_a_single_price_keeps_it_as_the_fair_price():
    line = "9786556020013 Da vida nas ruas Clarice Fortunato R$ 21,00 Biografia"
    catalog = catalog_from({"Carochinha Editora": [parsed_book("9786556020013", "Da vida nas ruas", cover=None, fair=21.0)]}, plain_text=line)
    assert ("c" not in catalog["livros"][0], catalog["livros"][0]["f"]) == (True, 21.0)


def test_same_isbn_at_two_exhibitors_gets_one_id_each():
    catalog = catalog_from({
        "Boitempo": [parsed_book("9788575593646", "MULHER, ESTADO E REVOLUCAO", 69.0, 34.5)],
        "Iskra / Casa Marx": [parsed_book("9788575593646", "Mulher, estado e revolução", 50.0, 25.0)],
    })
    ids = [book["i"] for book in catalog["livros"]]
    assert len(set(ids)) == 2
    assert {isbn_of_book_id(book_id) for book_id in ids} == {"9788575593646"}


def test_id_of_a_shared_isbn_does_not_depend_on_the_order_of_exhibitors():
    boitempo = [parsed_book("9788575593646", "MULHER, ESTADO E REVOLUCAO", 69.0, 34.5)]
    iskra = [parsed_book("9788575593646", "Mulher, estado e revolução", 50.0, 25.0)]
    first = catalog_from({"Boitempo": boitempo, "Iskra / Casa Marx": iskra})
    second = catalog_from({"Iskra / Casa Marx": iskra, "Boitempo": boitempo})
    boitempo_id = lambda catalog: next(book["i"] for book in catalog["livros"] if catalog["expositores"][book["x"]]["nome"] == "Boitempo")
    assert boitempo_id(first) == boitempo_id(second)


def test_isbn_reused_for_another_title_keeps_both_books():
    catalog = catalog_from({"Editora Patuá": [parsed_book("9786528102556", "Primeiro livro"), parsed_book("9786528102556", "Segundo livro")]})
    assert [book["t"] for book in catalog["livros"]] == ["Primeiro livro", "Segundo livro"]


def test_row_listed_twice_appears_once():
    catalog = catalog_from({"Editora Vozes": [parsed_book("9788532616463", "Livro repetido"), parsed_book("9788532616463", "Livro repetido")]})
    assert len(catalog["livros"]) == 1


@pytest.mark.parametrize("url, published", [
    ("https://loja.editoraunica", ""),
    ("https://www.companhiadasletras.com.br/", ""),
    ("https://www.lojanewpop.com.br/record-of-ragnarok-16577175", "https://www.lojanewpop.com.br/record-of-ragnarok-16577175"),
    ("https://www.livraria.com.br/?produto=123", "https://www.livraria.com.br/?produto=123"),
])
def test_link_to_a_front_page_is_dropped(url, published):
    assert safe_public_url(url) == published


@pytest.mark.parametrize("subject, cleaned", [
    ("<p>Poesia&#160;brasileira</p>", "Poesia brasileira"),
    ("/shop/68-como-incendiar-um-pais-230", ""),
    ("Luiz Gama, abolição, preconceito, 26,00 justiça", "Luiz Gama, abolição, preconceito, justiça"),
    ("R$ 49,00 Biografia", "Biografia"),
    ("POESIA", "Poesia"),
    ("Alfabetização, Inglês, Primeiros conceitos, Adição, Contagem, Matemática, Apoio escolar", "Alfabetização, Inglês, Primeiros conceitos, Adição, Contagem"),
])
def test_genre_cleanup(subject, cleaned):
    assert tidy_subject(subject) == cleaned


def test_synopsis_column_is_not_used_as_genre():
    isbns = ["9788526810563", "9788526807969", "9788526806498", "9788526815223", "9786528102556"]
    books = [parsed_book(isbn, f"Livro {number}", subject=f"Uma história comovente sobre o livro {number} e as pessoas que o leram.")
             for number, isbn in enumerate(isbns)]
    catalog = catalog_from({"Editora Biruta / Gaivota": books})
    assert [book.get("g") for book in catalog["livros"]] == [None] * 5


def test_long_lists_of_tags_are_kept_as_genres():
    isbns = ["9788526810563", "9788526807969", "9788526806498", "9788526815223", "9786528102556"]
    books = [parsed_book(isbn, f"Livro {number}", subject=f"Alfabetização, Inglês, Primeiros conceitos, Flash Cards {number}")
             for number, isbn in enumerate(isbns)]
    catalog = catalog_from({"Grupo Ciranda Cultural": books})
    assert [book.get("g") for book in catalog["livros"]] == [f"Alfabetização, Inglês, Primeiros conceitos, Flash Cards {number}" for number in range(5)]


def test_short_genres_are_kept():
    isbns = ["9788526810563", "9788526807969", "9788526806498"]
    catalog = catalog_from({"Editora Unesp": [parsed_book(isbn, f"Livro {number}", subject="Filosofia") for number, isbn in enumerate(isbns)]})
    assert [book.get("g") for book in catalog["livros"]] == ["Filosofia"] * 3


def test_edition_prefix_is_removed_from_title():
    catalog = catalog_from({"Editora UFMG": [parsed_book("9788526810563", "1a ed. ACO EM FLOR: A POESIA DE PAULO LEMINSKI")]})
    assert catalog["livros"][0]["t"] == "ACO EM FLOR: A POESIA DE PAULO LEMINSKI"


def test_several_titles_glued_into_one_row_are_not_a_book():
    glued = "PAIXÃO DA JUVENTUDE: UMA BIOGRAFIA PRÁTICAS SEXUAIS, HOLLYWOOD E IMAGENS DA AMÉRICA NO EDUCAÇÃO IMIGRANTE EM SANTOS " * 3
    catalog = catalog_from({"Annablume": [parsed_book("9788526810563", glued), parsed_book("9788526807969", "A invenção do impossível")]})
    assert [book["t"] for book in catalog["livros"]] == ["A invenção do impossível"]


def test_cover_price_between_dashes_is_read():
    catalog, _ = catalog_for("ubu.pdf", "Ubu Editora")
    book = book_titled(catalog, "A planta do mundo")
    assert (book["c"], book["f"]) == (79.9, 39.95)


@pytest.mark.parametrize("header, only_cover", [
    ("PONTES EDITORES LTDA. - FONE: (019) 3252-6011 RANKING ISBN DESCRIÇÃO AUTOR $ CAPA\n9788521702108", True),
    ("ISBN TITULO AUTOR EDITORA PREÇO de CAPA PREÇO com DESCONTO ASSUNTO URL_LIVRO\n9788535914849", False),
    ("ISBN TITULO AUTOR EDITORA PREÇO de CAPA PREÇO com DESCONT O ASSUNTO URL_LIVRO\n9788535914849", False),
    ("ISBN TITULO AUTOR(ES) EDITORA PREÇO CAPA PREÇO PRES. ASSUNTO LINKS\n9788535914849", False),
    ("ISBN TITULO AUTOR EDITORA PREÇO FEIRA\n9788535914849", False),
    # Uneb 2026: the ISBN comes after the price, so the first book's price sits before the first ISBN.
    ("Título do livro Assunto Preço de capa Nome dos autor(es) Código de barras\n1 Quem tem Mandioca tem tudo História R$ 40,00 Eduardo Guimarães\n9788585813574", True),
])
def test_list_with_only_cover_prices_is_recognized(header, only_cover):
    assert has_only_cover_prices(header) is only_cover


def test_list_with_only_cover_prices_keeps_the_cover_price_and_a_notice(monkeypatch):
    import festa_do_livro.catalog_builder as catalog_builder
    pontes_text = "PONTES EDITORES LTDA. RANKING ISBN DESCRIÇÃO AUTOR $ CAPA\n9788521702108#FICA ESPANHOL NO RS FAGUNDES 48,00\n"
    monkeypatch.setattr(catalog_builder, "extract_plain_text", lambda path: pontes_text)
    monkeypatch.setattr(catalog_builder, "extract_table_rows", lambda path: [["ISBN", "DESCRIÇÃO", "AUTOR", "$ CAPA"], ["9788521702108", "#FICA ESPANHOL NO RS", "FAGUNDES", "48,00"]])
    monkeypatch.setattr(catalog_builder, "extract_text_spans", lambda path: [])
    parsed = catalog_builder.parse_price_list(Path("pontes.pdf"))
    book = parsed.books[0]
    assert (book["cover_price"], book["fair_price"], parsed.notice) == (48.0, None, "só tem preço de capa; o preço de feira não foi informado")


def test_book_from_a_list_with_only_cover_prices_has_no_fair_price():
    publishers = [Publisher(name="Pontes Editores", slug="", price_list_url="https://festadolivro.edusp.com.br/storage/pontes.pdf", site="")]
    parsed = {0: ParsedPriceList(
        books=[parsed_book("9788521702108", "#FICA ESPANHOL NO RS", cover=48.0, fair=None), parsed_book("9786556372495", "Esgotado", cover=0.0, fair=None)],
        method="tabela", plain_text="", notice="só tem preço de capa; o preço de feira não foi informado",
    )}
    catalog = build_catalog(EVENT, publishers, parsed, "2026-11-09T00:00:00+00:00")
    assert [(book["t"], book.get("c"), book.get("f")) for book in catalog["livros"]] == [("#FICA ESPANHOL NO RS", 48.0, None)]


def test_catalog_carries_each_publisher_price_list_and_notice():
    publishers = [Publisher(name="Pontes Editores", slug="", price_list_url="https://festadolivro.edusp.com.br/storage/pontes.pdf", site="")]
    parsed = {0: ParsedPriceList(books=[], method="tabela", plain_text="", notice="só tem preço de capa; o preço de feira não foi informado")}
    catalog = build_catalog(EVENT, publishers, parsed, "2026-11-09T00:00:00+00:00")
    assert catalog["expositores"] == [{
        "nome": "Pontes Editores", "site": "", "lista": "https://festadolivro.edusp.com.br/storage/pontes.pdf",
        "aviso": "só tem preço de capa; o preço de feira não foi informado",
    }]
def test_list_printed_in_strips_keeps_title_author_and_prices_together():
    catalog, _ = catalog_for("phorte.pdf", "Phorte Editora")
    book = book_titled(catalog, "A estética no pensamento e na obra")
    assert (book["i"], book["a"], book["c"], book["f"]) == ("9786599017476", "Alfredo Hoyuelos", 69.0, 34.5)


def test_report_names_the_reading_of_a_list_printed_in_strips():
    _, parsed = catalog_for("phorte.pdf", "Phorte Editora")
    assert parsed.method == "tabela em faixas"


@pytest.fixture(scope="module")
def nos():
    return catalog_for("nos.pdf", "Nós")


def test_prices_written_without_cents_are_read(nos):
    book = book_titled(nos[0], "Dezembros")
    assert (book["c"], book["f"]) == (78.0, 39.0)


def test_reads_every_book_of_a_list_with_prices_without_cents(nos):
    assert len(nos[0]["livros"]) == 143


def test_three_digit_cover_price_stays_out_of_the_title(nos):
    book = book_titled(nos[0], "A trilogia do genocídio de Ruanda")
    assert (book["t"], book["c"], book["f"]) == ("A trilogia do genocídio de Ruanda", 257.0, 128.5)


def test_price_column_is_not_read_as_author(nos):
    assert [book["a"] for book in nos[0]["livros"] if re.search(r"\d", book.get("a", ""))] == []


def test_list_printed_in_two_strips_of_the_same_width_is_read():
    catalog, _ = catalog_for("universo_dos_livros.pdf", "Universo dos livros")
    book = book_titled(catalog, "ACEITA-ME - EDIÇÃO DE LUXO LIMITADA")
    assert (book["i"], book["c"], book["f"]) == ("9788550306643", 89.9, 44.95)


def test_fair_price_computed_from_a_discount_percentage_is_not_a_divergence():
    catalog = catalog_from({"Instituto Tomie Ohtake": [parsed_book("9788553190133", "AI-5 - AINDA NÃO TERMINOU DE ACABAR", cover=120.0, fair=60.0)]})
    plain_text = "978-8553190133 AI-5 - AINDA NÃO TERMINOU DE ACABAR Paulo Miyada Instituto Tomie Ohtake R$ 120,00 50,00% POLÍTICA"
    assert verify_prices(catalog, {0: plain_text}).mismatch_count == 0


def test_fair_price_that_does_not_follow_the_discount_percentage_is_a_divergence():
    catalog = catalog_from({"Instituto Tomie Ohtake": [parsed_book("9788553190133", "AI-5 - AINDA NÃO TERMINOU DE ACABAR", cover=120.0, fair=70.0)]})
    plain_text = "978-8553190133 AI-5 - AINDA NÃO TERMINOU DE ACABAR Paulo Miyada Instituto Tomie Ohtake R$ 120,00 50,00% POLÍTICA"
    assert verify_prices(catalog, {0: plain_text}).mismatch_count == 1


def test_price_of_an_isbn_printed_without_its_check_digit_is_found_in_the_pdf():
    catalog = catalog_from({"Editora Miolo Mole": [parsed_book("9786581555009", "GAROTO AVATAR", cover=49.9, fair=24.95)]})
    plain_text = "978-65-81555-00-\nGAROTO AVATAR\nCaeto, Luana Vignon\nMiolo Mole\n49,90\n24,95 comportamento, videogame, cotidiano"
    assert verify_prices(catalog, {0: plain_text}).mismatch_count == 0


def test_price_check_of_an_isbn_without_its_check_digit_stops_at_the_next_one():
    catalog = catalog_from({"Editora Miolo Mole": [parsed_book("9786581555009", "GAROTO AVATAR", cover=35.0, fair=17.5)]})
    plain_text = "978-65-81555-00-\nGAROTO AVATAR\n49,90\n24,95\n978-65-88749-03-\nGIRAFA?\nFelipe Tognoli\n35,00\n17,50"
    assert verify_prices(catalog, {0: plain_text}).mismatch_count == 1


@pytest.fixture(scope="module")
def miolo_mole():
    return catalog_for("miolo_mole.pdf", "Editora Miolo Mole")


def test_book_whose_isbn_was_printed_without_its_check_digit_is_read(miolo_mole):
    book = book_titled(miolo_mole[0], "GAROTO AVATAR")
    assert (book["i"], book["a"], book["c"], book["f"]) == ("9786581555009", "Caeto, Luana Vignon", 49.9, 24.95)


def test_reads_every_book_of_a_list_whose_isbns_lost_their_check_digit(miolo_mole):
    assert len(miolo_mole[0]["livros"]) == 36


def test_every_price_of_a_list_whose_isbns_lost_their_check_digit_matches_the_pdf(miolo_mole):
    catalog, parsed = miolo_mole
    assert verify_prices(catalog, {0: parsed.plain_text}).mismatch_count == 0


def isbn_with_serial(serial: int) -> str:
    first_twelve_digits = f"978853260{serial:03d}"
    return first_twelve_digits + isbn13_check_digit(first_twelve_digits)


def books_read(count: int, with_isbn: bool) -> list[dict]:
    return [parsed_book(isbn_with_serial(serial) if with_isbn else "", f"Livro número {serial}") for serial in range(count)]


def test_table_reader_that_lost_the_isbns_loses_even_reading_more_rows():
    assert not table_reader_wins(books_read(12, with_isbn=False), books_read(11, with_isbn=True), plain_text="")


def test_position_reader_that_lost_the_isbns_loses_even_reading_more_rows():
    assert table_reader_wins(books_read(11, with_isbn=True), books_read(20, with_isbn=False), plain_text="")


def test_with_isbns_on_both_sides_a_tie_goes_to_the_table_reader():
    assert table_reader_wins(books_read(12, with_isbn=True), books_read(12, with_isbn=True), plain_text="")


def test_with_isbns_on_both_sides_the_reader_with_clearly_more_books_wins():
    assert not table_reader_wins(books_read(10, with_isbn=True), books_read(12, with_isbn=True), plain_text="")


def test_a_handful_of_isbns_does_not_decide_the_reader():
    assert table_reader_wins(books_read(6, with_isbn=False), books_read(5, with_isbn=True), plain_text="")


def test_isbns_printed_before_the_titles_count_for_the_table_reader():
    """The chosen reader's books get the ISBN printed right before their title, so those ISBNs count in the choice."""
    tables = books_read(12, with_isbn=False)
    plain_text = "\n".join(f"{isbn_with_serial(serial)} {book['title']}" for serial, book in enumerate(tables))
    assert table_reader_wins(tables, books_read(11, with_isbn=True), plain_text=plain_text)


@pytest.fixture(scope="module")
def vozes():
    """The first three pages of the Vozes list of 2026. Its table borders split only some columns, so the table reader glued each
    page's ISBNs, titles and cover prices into one cell and read the rows without them."""
    return catalog_for("vozes.pdf", "EDITORA VOZES")


def test_book_of_a_list_whose_table_reader_lost_the_isbns_is_read_whole(vozes):
    book = book_titled(vozes[0], "A AGUIA E A GALINHA")
    assert (book["i"], book["a"], book["c"], book["f"]) == ("9788532655011", "Leonardo Boff", 49.9, 24.95)


def test_every_row_of_a_list_whose_table_reader_lost_the_isbns_is_a_book_with_its_isbn(vozes):
    isbns = [isbn_of_book_id(book["i"]) for book in vozes[0]["livros"]]
    assert (len(isbns), all(isbns)) == (115, True)


def test_every_price_of_a_list_whose_table_reader_lost_the_isbns_matches_the_pdf(vozes):
    catalog, parsed = vozes
    assert verify_prices(catalog, {0: parsed.plain_text}).mismatch_count == 0


def test_author_glued_to_a_long_title_is_read_apart(vozes):
    book = book_titled(vozes[0], "A AMOROSIDADE DO DEUS-ABBA")
    assert (book["t"], book["a"]) == ("A AMOROSIDADE DO DEUS-ABBA E JESUS DE NAZARE", "Leonardo Boff")


def test_author_glued_to_a_title_the_cell_cut_in_the_middle_of_a_word_is_read_apart(vozes):
    book = book_titled(vozes[0], "A AUTOTRANSCENDENCIA")
    assert (book["t"], book["a"]) == ("A AUTOTRANSCENDENCIA NA LOGOTERAPIA DE VIKTO", "Ana Clara de Andrade Patricio;Clara M")


def test_only_books_printed_without_an_author_have_none(vozes):
    without_author = [book["t"] for book in vozes[0]["livros"] if "a" not in book]
    assert without_author == ["150 EXERCICIOS PARA TURBINAR O SEU CEREBRO", "A CONQUISTA ESPIRITUAL DA AMERICA ESPANHOLA", "A EPOCA MODERNA"]


@pytest.fixture(scope="module")
def ercolano():
    return catalog_for("ercolano.pdf", "Ercolano")


def test_isbn_and_author_the_table_reader_glued_to_the_title_are_read_apart(ercolano):
    book = book_titled(ercolano[0], "A Condessa Ensanguentada")
    assert (book["i"], book["t"], book["a"], book["c"], book["f"]) == ("9786585960489", "A Condessa Ensanguentada", "Valentine Penrose", 116.0, 58.0)


def test_book_whose_isbn_lost_its_first_nine_is_read_on_its_own_without_isbn(ercolano):
    book = book_titled(ercolano[0], "A guerra das bichas")
    assert (isbn_of_book_id(book["i"]), book["t"], book["a"], book["c"], book["f"]) == ("", "A guerra das bichas", "Copi", 89.9, 44.95)


def test_book_below_an_isbn_without_its_first_nine_keeps_its_own_title_and_prices(ercolano):
    book = book_titled(ercolano[0], "A revolta dos bichos")
    assert (book["i"], book["t"], book["a"], book["c"], book["f"]) == ("9786585960052", "A revolta dos bichos", "Mykola Kostomárov", 57.5, 28.75)


def test_author_glued_to_a_title_the_cell_cut_short_is_read_apart(ercolano):
    book = book_titled(ercolano[0], "Complementos à teoria sexual")
    assert (book["t"], book["a"]) == ("Complementos à teoria sexual sobre o", "Pascal Quignard")


def test_link_that_lost_its_start_to_the_subject_cell_is_dropped_from_the_subject(ercolano):
    assert book_titled(ercolano[0], "Complementos à teoria sexual")["g"] == "Ensaio"


@pytest.fixture(scope="module")
def ims():
    """The first page of the IMS list of 2026, whose narrow cells cut titles and authors in the middle of a letter."""
    return catalog_for("ims.pdf", "IMS")


def test_title_a_narrow_cell_cuts_in_the_middle_of_a_letter_is_read_whole(ims):
    book = book_titled(ims[0], "A CRÍTICA CÚM")
    assert (book["t"], book["a"]) == ("A CRÍTICA CÚMPLICE", "Ana Bernstein")


def test_no_author_of_a_list_with_narrow_cells_starts_with_the_last_letter_of_the_title(ims):
    letter_glued_to_a_name = re.compile(r"^[^\W\d_][A-ZÀ-Ý][a-zà-ÿ]")
    assert [book["a"] for book in ims[0]["livros"] if letter_glued_to_a_name.match(book.get("a", ""))] == []


def test_lowercase_title_a_narrow_cell_cuts_in_the_middle_of_a_letter_is_read_whole():
    catalog, _ = catalog_for("lavrapalavra.pdf", "LavraPalavra")
    book = book_titled(catalog, "centralismo democr")
    assert (book["t"], book["a"]) == ("centralismo democrático de Lênin", "Vladímir Ilitch Lênin")


@pytest.fixture(scope="module")
def hucitec():
    """Page 8 of the Hucitec list of 2026: below its tenth book, the cover price column lost the borders between its rows."""
    return catalog_for("hucitec.pdf", "Hucitec Editora")


def test_cover_price_in_a_column_that_lost_its_row_borders_is_read(hucitec):
    book = book_titled(hucitec[0], "Estrela e o sensitivo")
    assert (book["c"], book["f"]) == (77.0, 38.5)


def test_book_where_the_column_lost_its_row_borders_keeps_only_its_own_cover_price(hucitec):
    book = book_titled(hucitec[0], "Nos arredores da prisão")
    assert (book["c"], book["f"]) == (70.0, 35.0)


def test_every_book_of_a_page_whose_price_column_lost_its_row_borders_has_a_cover_price(hucitec):
    assert [book["t"] for book in hucitec[0]["livros"] if "c" not in book] == []


def test_every_price_of_a_page_whose_price_column_lost_its_row_borders_matches_the_pdf(hucitec):
    catalog, parsed = hucitec
    assert verify_prices(catalog, {0: parsed.plain_text}).mismatch_count == 0


@pytest.fixture(scope="module")
def letra_selvagem():
    return catalog_for("letra_selvagem.pdf", "Letra Selvagem")


def test_rows_below_the_table_borders_are_read(letra_selvagem):
    book = book_titled(letra_selvagem[0], "Meu Dostoiévski")
    assert (book["i"], book["c"], book["f"]) == ("9786589841234", 80.0, 40.0)


def test_reads_every_book_of_a_list_whose_table_loses_its_borders(letra_selvagem):
    assert len(letra_selvagem[0]["livros"]) == 72


def test_cover_price_written_at_the_left_of_its_cell_is_read(letra_selvagem):
    book = book_titled(letra_selvagem[0], "Bandoleiros de Taubaté")
    assert (book["c"], book["f"]) == (60.0, 30.0)


@pytest.fixture(scope="module")
def unifesp():
    return catalog_for("unifesp.pdf", "Unifesp")


def test_last_row_with_broken_cell_borders_is_read(unifesp):
    book = book_titled(unifesp[0], "PRISMA DA RAÇA")
    assert (book["i"], book["c"], book["f"]) == ("9786556322001", 98.0, 49.0)


def test_last_row_with_broken_cell_borders_is_shown_once(unifesp):
    assert len([book for book in unifesp[0]["livros"] if "PRISMA DA RAÇA" in book["t"]]) == 1


@pytest.fixture(scope="module")
def atelie():
    return catalog_for("atelie.pdf", "Ateliê Editorial")


def test_title_its_cell_cuts_at_the_border_is_read_whole(atelie):
    assert book_titled(atelie[0], "A Cidade e os Ca")["t"] == "A Cidade e os Cachorros: Biografia de um Romance"


def test_isbn_its_cell_cuts_at_the_border_is_read_whole(atelie):
    assert book_titled(atelie[0], "Do Formalismo Estético")["i"] == "9788574804422"


def test_letter_hidden_over_the_same_letter_of_the_next_cell_stays_in_the_title(atelie):
    assert book_titled(atelie[0], "A Vida Notável")["t"] == "A Vida Notável e Instrutiva do Mestre Tinius"


def test_fair_price_written_without_its_zero_cents_is_not_mistaken_for_the_cover_price(atelie):
    book = book_titled(atelie[0], "A Cidade e os Ca")
    assert (book["c"], book["f"]) == (120.0, 60.0)


def test_every_book_of_a_list_whose_cells_cut_their_texts_is_read(atelie):
    # The two pages have 85 rows with an ISBN: 78 with thirteen digits and 7 with ten.
    assert len(atelie[0]["livros"]) == 85


def isbn_with_check_digit(first_twelve_digits: str) -> str:
    weighted_sum = sum(int(digit) * (3 if position % 2 else 1) for position, digit in enumerate(first_twelve_digits))
    return first_twelve_digits + str((10 - weighted_sum % 10) % 10)


def numbered_books(count: int, title_prefix: str = "Livro") -> list[dict]:
    return [parsed_book(isbn_with_check_digit(f"978850000{number:03d}"), f"{title_prefix} {number}") for number in range(count)]


def test_book_the_chosen_reader_lost_is_taken_from_the_other_reader():
    lost_book = parsed_book(isbn_with_check_digit("978850000999"), "Livro da última linha")
    assert books_only_the_other_reader_found(numbered_books(10), numbered_books(10) + [lost_book]) == [lost_book]


def test_other_reader_that_sees_the_titles_cut_short_by_their_cells_is_still_trusted():
    lost_book = parsed_book(isbn_with_check_digit("978850000999"), "Livro da última linha")
    whole_titles =[{**book, "title": book["title"].replace("Livro", "Livro com um título longo demais para a célula")} for book in numbered_books(10)]
    cut_short = [{**book, "title": book["title"][:20]} for book in whole_titles]
    assert books_only_the_other_reader_found(whole_titles, cut_short + [lost_book]) == [lost_book]


def test_other_reader_that_glues_the_author_to_every_title_is_not_trusted():
    lost_book = parsed_book(isbn_with_check_digit("978850000999"), "Livro da última linha")
    titles_with_author = [{**book, "title": book["title"] + " Neves, Juliano C. S."} for book in numbered_books(10)]
    assert books_only_the_other_reader_found(numbered_books(10), titles_with_author + [lost_book]) == []


def test_other_reader_is_not_trusted_when_it_reads_the_shared_books_another_way():
    lost_book = parsed_book(isbn_with_check_digit("978850000999"), "Livro da última linha")
    codes_read_as_titles = numbered_books(10, title_prefix="21144")
    assert books_only_the_other_reader_found(numbered_books(10), codes_read_as_titles + [lost_book]) == []


def test_row_read_with_its_isbn_inside_the_title_goes_away_when_the_other_reader_brings_the_book():
    garbled_row = parsed_book("", "9786556322001 PRISMA DA RAÇA, O Lehmann, David", cover=98.0, fair=49.0)
    same_book_with_isbn = parsed_book("9786556322001", "PRISMA DA RAÇA, O", cover=98.0, fair=49.0)
    assert without_garbled_copies(numbered_books(3) + [garbled_row], [same_book_with_isbn]) == numbered_books(3)


def test_row_read_without_its_isbn_goes_away_when_the_other_reader_brings_the_same_title():
    row_without_isbn = parsed_book("", "ANTROPOLOGIA", fair=67.5)
    same_book_with_isbn = parsed_book(isbn_with_check_digit("978853265015"), "Antropologia", fair=67.5)
    assert without_garbled_copies([row_without_isbn], [same_book_with_isbn]) == []


def test_another_volume_without_isbn_stays_when_the_other_reader_brings_a_volume_with_the_same_price():
    third_volume = parsed_book("", "EXERCICIOS PRATICOS PARA ESTIMULAR A MEMORIA VOL. 3", fair=26.25)
    second_volume = parsed_book(isbn_with_check_digit("978853264000"), "EXERCICIOS PRATICOS PARA ESTIMULAR A MEMORIA VOL. 2", fair=26.25)
    assert without_garbled_copies([third_volume], [second_volume]) == [third_volume]


def test_book_without_isbn_with_another_price_stays_when_the_other_reader_brings_the_same_title():
    book_without_isbn = parsed_book("", "ANTROPOLOGIA", fair=40.0)
    book_with_isbn = parsed_book(isbn_with_check_digit("978853265015"), "ANTROPOLOGIA", fair=67.5)
    assert without_garbled_copies([book_without_isbn], [book_with_isbn]) == [book_without_isbn]


@pytest.fixture(scope="module")
def ufv():
    return catalog_for("ufv.pdf", "Ed. UFV")


def test_list_whose_fair_price_column_is_empty_shows_the_cover_price_with_the_notice(ufv):
    book = book_titled(ufv[0], "A PRONUNCIA DO LATIM")
    assert (book["c"], book.get("f"), ufv[1].notice) == (75.0, None, ONLY_COVER_PRICE_NOTICE)


def test_every_book_of_a_list_with_an_empty_fair_price_column_keeps_its_cover_price(ufv):
    assert [(book.get("c") is not None, book.get("f")) for book in ufv[0]["livros"]] == [(True, None)] * 19


@pytest.fixture(scope="module")
def uneb():
    return catalog_for("uneb.pdf", "Uneb")


def test_list_with_only_cover_prices_whose_isbn_comes_after_the_price_shows_the_cover_price_with_the_notice(uneb):
    book = book_titled(uneb[0], "Quem tem Mandioca")
    assert (book["c"], book.get("f"), uneb[1].notice) == (40.0, None, ONLY_COVER_PRICE_NOTICE)


def test_author_column_whose_header_starts_with_nome_is_read_as_the_author(uneb):
    assert book_titled(uneb[0], "Quem tem Mandioca")["a"] == "Eduardo Guimarães e Francisco Guimarães"


@pytest.fixture(scope="module")
def monolito():
    return catalog_for("monolito.pdf", "Monolito")


def test_magazine_issue_sold_with_its_issn_barcode_keeps_its_title_and_prices(monolito):
    book = book_titled(monolito[0], "Monolito edição 3 - ")
    assert (book["t"], book["c"], book["f"]) == ("Monolito edição 3 - Biselli e Katchborian", 99.0, 45.0)


def test_magazine_issue_whose_barcode_is_its_isbn_and_the_issue_number_keeps_its_isbn_and_its_own_title(monolito):
    book = book_titled(monolito[0], "Monolito edição 34 - ")
    assert (book["i"], book["t"]) == ("9788566275131", "Monolito edição 34 - Humberto Serpa")


def test_every_issue_of_a_magazine_list_is_read(monolito):
    # 37 rows have an ISBN, 6 of them followed by the issue number, and 15 have the barcode of the magazine's ISSN.
    assert len(monolito[0]["livros"]) == 52


def publisher_filed_under(name: str, number: int) -> Publisher:
    address = f"https://festadolivro.edusp.com.br/storage/event/publishers/publisher-{number}/publisher-price-list/lista.pdf"
    return Publisher(name=name, slug="", price_list_url=address, site="")


def catalog_of(publishers: list[Publisher], books_by_publisher: list[list[dict]], names_in_old_ids=None) -> dict:
    parsed = {index: ParsedPriceList(books=books, method="tabela", plain_text="") for index, books in enumerate(books_by_publisher)}
    return build_catalog(EVENT, publishers, parsed, "2026-11-18T00:00:00+00:00", names_in_old_ids)


def test_book_without_isbn_keeps_its_id_when_the_festa_renames_its_publisher():
    book = [parsed_book("", "Livro sem ISBN")]
    before = catalog_of([publisher_filed_under("Editora Brasiliense", 512)], [book])
    after = catalog_of([publisher_filed_under("Brasiliense", 512)], [book])
    assert after["livros"][0]["i"] == before["livros"][0]["i"]


def test_isbn_sold_at_two_stands_keeps_its_suffix_when_the_festa_renames_a_publisher():
    book = [parsed_book("9788575593646", "Mulher, estado e revolução")]
    before = catalog_of([publisher_filed_under("Boitempo", 1), publisher_filed_under("Iskra / Casa Marx", 2)], [book, book])
    after = catalog_of([publisher_filed_under("Boitempo", 1), publisher_filed_under("Casa Marx | Iskra", 2)], [book, book])
    assert [entry["i"] for entry in after["livros"]] == [entry["i"] for entry in before["livros"]]


def test_book_without_isbn_carries_the_ids_it_had_under_each_name_of_its_publisher():
    # Without the number of the publisher in the address of its list, the id still comes from the name, as it did until v1.9.0.
    book = [parsed_book("", "Livro sem ISBN")]
    ids_under_each_name = {catalog_from({name: book})["livros"][0]["i"] for name in ("Editora Brasiliense", "Brasiliense")}
    catalog = catalog_of([publisher_filed_under("Brasiliense", 512)], [book], {"publisher-512": ["Editora Brasiliense", "Brasiliense"]})
    assert set(catalog["livros"][0]["o"]) == ids_under_each_name


def test_isbn_sold_at_two_stands_carries_the_ids_it_had_under_each_name_of_its_publisher():
    book = [parsed_book("9788575593646", "Mulher, estado e revolução")]
    id_under_the_old_name = catalog_from({"Boitempo": book, "Iskra / Casa Marx": book})["livros"][1]["i"]
    catalog = catalog_of(
        [publisher_filed_under("Boitempo", 1), publisher_filed_under("Casa Marx | Iskra", 2)], [book, book],
        {"publisher-2": ["Iskra / Casa Marx", "Casa Marx | Iskra"]},
    )
    assert id_under_the_old_name in catalog["livros"][1]["o"]


def test_book_whose_id_is_its_isbn_carries_no_old_id():
    book = [parsed_book(isbn_with_check_digit("978851100000"), "Livro com ISBN")]
    catalog = catalog_of([publisher_filed_under("Brasiliense", 512)], [book], {"publisher-512": ["Editora Brasiliense", "Brasiliense"]})
    assert "o" not in catalog["livros"][0]


def test_names_in_old_ids_are_read_from_the_edition_folder(tmp_path):
    (tmp_path / NAMES_IN_OLD_IDS_FILE).write_text('{"publisher-512": ["Editora Brasiliense", "Brasiliense"]}')
    assert load_names_in_old_ids(tmp_path) == {"publisher-512": ["Editora Brasiliense", "Brasiliense"]}


def test_edition_without_names_in_old_ids_has_none(tmp_path):
    assert load_names_in_old_ids(tmp_path) == {}


@pytest.fixture(scope="module")
def brasiliense():
    return catalog_for("brasiliense.pdf", "Brasiliense")


def test_title_its_cell_hides_on_both_sides_is_read_whole_with_its_isbn_and_author(brasiliense):
    book = book_titled(brasiliense[0], "A CIDADE DE SAO PAULO")
    assert (book["i"], book["t"], book["a"]) == ("9788511020786", "A CIDADE DE SAO PAULO GEOGRAFIA E HISTORIA", "CAIO DA SILVA PRADO JUNIOR")


def test_no_title_of_a_list_whose_cells_hide_centered_text_is_an_isbn_with_a_letter(brasiliense):
    assert [book["t"] for book in brasiliense[0]["livros"] if re.match(r"97[89]\d{10}", book["t"])] == []


@pytest.fixture(scope="module")
def com_arte():
    return catalog_for("com_arte.pdf", "Com-Arte")


def test_quantity_in_a_list_whose_header_is_one_cell_is_not_the_fair_price(com_arte):
    book = book_titled(com_arte[0], "A Casa & Outros Poemas")
    assert (book["c"], book["f"]) == (36.0, 18.0)


@pytest.fixture(scope="module")
def edusp():
    return catalog_for("edusp.pdf", "Edusp")


def test_quantity_written_with_a_parenthesis_is_not_glued_to_the_author(edusp):
    book = book_titled(edusp[0], "(Re)Produção do Espaço Urbano")
    assert book["a"] == "CARLOS, Ana Fani Alessandri"


def test_no_author_of_a_list_with_quantities_in_parentheses_ends_with_a_number(edusp):
    assert [book["a"] for book in edusp[0]["livros"] if re.search(r"\d\)?$", book.get("a", ""))] == []


@pytest.fixture(scope="module")
def boitata():
    return catalog_for("boitata.pdf", "Boitatá")


def test_link_wider_than_the_last_column_keeps_the_letter_that_crosses_the_border(boitata):
    book = book_titled(boitata[0], "BICHO BOLOTA")
    assert book["u"] == "https://www.boitempoeditorial.com.br/produto/bicho-bolota-153014"


def test_every_link_of_a_list_whose_links_cross_the_border_is_printed_in_the_pdf(boitata):
    printed = re.sub(r"\s+", "", boitata[1].plain_text)
    assert [book["u"] for book in boitata[0]["livros"] if book["u"] not in printed] == []
