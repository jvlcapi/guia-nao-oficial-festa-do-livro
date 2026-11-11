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


def test_sheet_printed_in_strips_is_glued_back_line_by_line():
    rows = [
        ["ISBN", "TITULO"],
        ["9786588868539", "A Aventura dialógica na infância"],
        ["9786588868478", "A dança na arte, no esporte e na educação"],
        ["9786588868768", "A escola do ser e do querer (ser)"],
        ["AUTOR", "EDITORA", "PREÇO de CAPA", "PREÇO com DESCONTO"],
        ["Myrtha Chockler", "Phorte Editora", "R$ 95,00", "R$ 47,50"],
        ["Carla Salvagni e Antonio Carlos de Quadros", "Phorte Editora", "R$ 63,00", "R$ 31,50"],
        ["Angeles Abelleira e Isabel Abelleira", "Phorte Editora", "R$ 120,00", "R$ 60,00"],
    ]
    books = {book["isbn"]: book for book in parse_table_rows(rows)}
    book = books["9786588868768"]
    assert (book["title"], book["author"], book["cover_price"], book["fair_price"]) == ("A escola do ser e do querer (ser)", "Angeles Abelleira e Isabel Abelleira", 120.0, 60.0)


def test_later_section_without_a_price_column_is_not_read_as_books():
    rows = [
        ["ISBN", "DESCRIÇÃO", "AUTOR", "$ CAPA"],
        ["9788521702108", "#FICA ESPANHOL NO RS", "FAGUNDES/LACERDA/SANTOS", "48,00"],
        ["9786556372495", "(ARTE)FATOS LITERARIOS - VOLUME I", "QUERIDO/MANTOVANI E BARBOSA", "59,00"],
        ["ASSUNTO", "COLEÇÃO", "COD. BARRA", "PAGINAS"],
        ["ENSINO DE ESPANHOL", "", "9788521702108", "298"],
        ["TECNOLOGIA", "", "9786556372495", "262"],
    ]
    assert [book["title"] for book in parse_table_rows(rows)] == ["#FICA ESPANHOL NO RS", "(ARTE)FATOS LITERARIOS - VOLUME I"]


def test_cover_price_followed_by_a_stray_parenthesis():
    rows = [
        HEADER,
        ["9786589741350", "A BIBLIOTECA NO FIM DO TÚNEL", "RODRIGO CASARIN", "ARQUIPÉLAGO", "69,90)", "34,95", "CRÔNICAS", "https://www.arquipelago.com.br/a-biblioteca-no-fim-do-tunel-rodrigo-casarin"],
        ["9786589741534", "A CRÔNICA NÃO MATA", "LUIS HENRIQUE PELLANDA", "ARQUIPÉLAGO", "59,90)", "29,95", "CRÔNICAS", "https://www.arquipelago.com.br/a-cronica-nao-mata-luis-henrique-pellanda"],
        ["9788560171392", "DIAS DE LUTA", "RICARDO ALEXANDRE", "ARQUIPÉLAGO", "129,90)", "64,95", "MÚSICA", "https://www.arquipelago.com.br/dias-de-luta-ricardo-alexandre"],
    ]
    books = {book["title"]: book for book in parse_table_rows(rows)}
    assert (books["DIAS DE LUTA"]["cover_price"], books["DIAS DE LUTA"]["fair_price"]) == (129.9, 64.95)


def test_sheet_printed_in_two_strips_of_the_same_width_is_glued_back_line_by_line():
    rows = [
        ["UNIVERSO DOS LIVROS - 28° FESTA DO LIVRO DA USP", ""],
        ["ISBN Title", ""],
        ["9786597941247", "A Casa Coruja: Bruxas contra Feiticeiros"],
        ["9786556091921", "Aceita-me"],
        ["9788550306643", "ACEITA-ME - EDIÇÃO DE LUXO LIMITADA"],
        ["", ""],
        ["Preço Capa preço USP", ""],
        ["-R$ 39,90-", "-R$ 19,95-"],
        ["-R$ 59,90-", "-R$ 29,95-"],
        ["-R$ 89,90-", "-R$ 44,95-"],
    ]
    books = {book["isbn"]: book for book in parse_table_rows(rows)}
    book = books["9788550306643"]
    assert (book["title"], book["cover_price"], book["fair_price"]) == ("ACEITA-ME - EDIÇÃO DE LUXO LIMITADA", 89.9, 44.95)


def test_rows_with_isbn_and_price_together_are_never_glued_as_strips():
    rows = [
        HEADER,
        row("9788535914849", "1984", "ORWELL, GEORGE", "R$ 44,90", "R$ 22,00"),
        ["9788571646858", "A METAMORFOSE", "", "", "", "", "", ""],
        ["9788535911626", "PERSÉPOLIS (COMPLETO)", "", "", "", "", "", ""],
        ["9788535906288", "MAUS", "", "", "", "", "", ""],
        ["", "", "", "", "R$ 49,90", "R$ 24,50", "", ""],
        ["", "", "", "", "R$ 104,90", "R$ 52,00", "", ""],
        ["", "", "", "", "R$ 94,90", "R$ 47,00", "", ""],
    ]
    assert [book["title"] for book in parse_table_rows(rows)] == ["1984"]
