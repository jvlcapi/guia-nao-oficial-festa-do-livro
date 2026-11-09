from festa_do_livro.table_parser import parse_table_rows

HEADER = ["ISBN", "TITULO", "AUTOR", "EDITORA", "PREÇO de CAPA", "PREÇO com DESCONTO", "ASSUNTO", "URL_LIVRO"]


def row(isbn, title, author, cover, fair):
    return [isbn, title, author, "COMPANHIA DAS LETRA", cover, fair, "Ficção", "https://www.companhiadasletras.com.br/"]


ROWS = [
    HEADER,
    row("9788535914849", "1984", "ORWELL, GEORGE", "S 44,90", "R$ 22,00"),
    row("9788571646858", "A METAMORFOSE", "KAFKA, FRANZ", "S 49,90", "R$ 24,50"),
    row("9788535911626", "PERSÉPOLIS (COMPLETO)", "SATRAPI, MARJANE", "S 104,90", "R$ 52,00"),
    row("9788535906288", "MAUS", "SPIEGELMAN, ART", "R$ 9 4,90", "R$ 47,00"),
]


def test_cover_price_with_a_letter_spilled_from_the_neighbouring_cell():
    books = {book["title"]: book for book in parse_table_rows(ROWS)}
    assert (books["A METAMORFOSE"]["cover_price"], books["A METAMORFOSE"]["fair_price"]) == (49.9, 24.5)


def test_price_split_by_a_stray_space():
    books = {book["title"]: book for book in parse_table_rows(ROWS)}
    assert books["MAUS"]["cover_price"] == 94.9


def test_numeric_title_is_kept_as_title():
    books = {book["isbn"]: book for book in parse_table_rows(ROWS)}
    assert (books["9788535914849"]["title"], books["9788535914849"]["author"]) == ("1984", "ORWELL, GEORGE")


def test_numeric_code_column_is_not_read_as_title():
    rows = [
        ["ISBN", "TITULO", "AUTOR", "EDITORA", "PREÇO de CAPA", "PREÇO com DESCONTO", "ASSUNTO"],
        ["9788583460459", "#RIOUTÓPICO [EM CONSTRUÇÃO]", "Rosângela Rennó", "IMS", "R$ 94,90", "R$ 30,00", "FOTOGRAFIA"],
        ["26005547", "6 PERGUNTAS SOBRE VOLPI", "Sonia Salzstein", "IMS", "R$ 35,00", "R$ 10,00", "ARTES"],
        ["26004235", "A CRÍTICA CÚMPLICE", "Ana Bernstein", "IMS", "R$ 65,00", "R$ 2,00", "CRÍTICA"],
        ["9788583460114", "A FORMA DA LUZ", "Sergio Burgi", "IMS", "R$ 89,90", "R$ 20,00", "FOTOGRAFIA"],
    ]
    titles = [book["title"] for book in parse_table_rows(rows)]
    assert titles == ["#RIOUTÓPICO [EM CONSTRUÇÃO]", "6 PERGUNTAS SOBRE VOLPI", "A CRÍTICA CÚMPLICE", "A FORMA DA LUZ"]


def test_price_written_between_dashes():
    rows = [
        HEADER,
        ["9788592886059", "24/07 – Capitalismo tardio", "Jonathan Crary", "UBU", "-R$ 79,90-", "R$ 39,95", "filosofia", "https://www.ubueditora.com.br/"],
        ["9786586497298", "A planta do mundo", "Stefano Mancuso", "UBU", "-R$ 79,90-", "R$ 39,95", "ecologia", "https://www.ubueditora.com.br/"],
        ["9788571260092", "Ai Weiwei Raiz", "Marcello Dantas", "UBU", "-R$ 169,00", "- R$ 50,00", "arte", "https://www.ubueditora.com.br/"],
    ]
    books = {book["title"]: book for book in parse_table_rows(rows)}
    assert (books["Ai Weiwei Raiz"]["cover_price"], books["Ai Weiwei Raiz"]["fair_price"]) == (169.0, 50.0)
