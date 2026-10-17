import re
from pathlib import Path

import pytest

from festa_do_livro.catalog_builder import (
    ParsedPriceList,
    build_catalog,
    imprint_repeats_exhibitor,
    parse_price_list,
    safe_public_url,
    same_content,
    tidy_subject,
)
from festa_do_livro.fair_site import EventDetails, Publisher
from festa_do_livro.isbn import isbn_of_book_id
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
])
def test_genre_cleanup(subject, cleaned):
    assert tidy_subject(subject) == cleaned


def test_synopsis_column_is_not_used_as_genre():
    isbns = ["9788526810563", "9788526807969", "9788526806498", "9788526815223", "9786528102556"]
    books = [parsed_book(isbn, f"Livro {number}", subject=f"Uma história comovente sobre o livro {number} e as pessoas que o leram.")
             for number, isbn in enumerate(isbns)]
    catalog = catalog_from({"Editora Biruta / Gaivota": books})
    assert [book.get("g") for book in catalog["livros"]] == [None] * 5


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
