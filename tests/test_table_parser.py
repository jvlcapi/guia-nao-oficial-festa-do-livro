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


def test_isbn_printed_without_its_check_digit_keeps_title_author_and_imprint_in_place():
    rows = [
        HEADER,
        ["978-65-99145-69-8", "FOLHINHAS", "André Calixto", "Miolo Mole", "45,00", "22,50", "cooperação", "https://www.editoramiolomole.com/livros/folhinhas"],
        ["978-65-81555-00-", "GAROTO AVATAR", "Caeto, Luana Vignon", "Miolo Mole", "49,90", "24,95", "comportamento", "https://www.editoramiolomole.com/livros/garoto-avatar"],
    ]
    book = parse_table_rows(rows)[1]
    assert (book["isbn"], book["title"], book["author"], book["imprint"]) == ("9786581555009", "GAROTO AVATAR", "Caeto, Luana Vignon", "Miolo Mole")


def test_fair_price_without_its_zero_cents_after_a_cover_price_with_cents():
    rows = [
        ["ISBN", "Título", "Autor", "Editora", "Preço capa", "Preco 50% Desc.", "Assunto"],
        ["9786555801651", "A Cidade e os Cachorros", "Carlos Aguirre", "Ateliê", "120.00", "60", "Editoração"],
        ["9786555800609", "A Vida Notável e Instrutiva do Mestre Tinius", "Johann Georg Tinius", "Ateliê", "83.00", "41,5", "Bibliofilia"],
        ["9786555800760", "A Lua do Oriente e Outras Luas", "Christina Stephano de Queiroz", "Ateliê", "98.00", "49", "Biografia"],
        ["9786555801811", "Acento de Conteúdo, O", "Luiz Tatit", "Ateliê", "76.00", "38", "Comunicação"],
        ["9786555800715", "A Elite nos Bastidores do Modernismo Paulista", "Couto de Barros", "Ateliê", "200.00", "100", "História"],
    ]
    book = parse_table_rows(rows)[0]
    assert (book["cover_price"], book["fair_price"]) == (120.0, 60.0)


def test_whole_numbers_after_the_price_are_not_a_fair_price():
    rows = [
        ["ISBN", "Título", "Preço", "Estoque"],
        ["9786555801651", "A Cidade e os Cachorros", "50,00", "20"],
        ["9786555800609", "A Vida Notável e Instrutiva do Mestre Tinius", "60,00", "30"],
        ["9786555800760", "A Lua do Oriente e Outras Luas", "45,00", "15"],
        ["9786555801811", "Acento de Conteúdo, O", "40,00", "12"],
    ]
    book = parse_table_rows(rows)[0]
    assert (book["cover_price"], book["fair_price"]) == (None, 50.0)


def test_quantity_column_beside_whole_number_prices_is_not_a_price():
    rows = [
        ["Barras", "Titulo", "Qtd. Vend", "Vlr. Unit.", "50%"],
        ["9786557112120", "1923", "10", "98", "49"],
        ["9788539301843", "ABOLICAO", "3", "156", "78"],
        ["9788539300716", "ABOLICAO - 9ª EDICAO, A", "40", "58", "29"],
        ["9788539307814", "ACELERACAO", "6", "110", "55"],
    ]
    book = parse_table_rows(rows)[1]
    assert (book["title"], book["cover_price"], book["fair_price"]) == ("ABOLICAO", 156.0, 78.0)


def test_quantity_with_a_letter_spilled_from_the_title_is_not_the_author():
    rows = [
        ["Barras", "Titulo", "Qtd. Vend", "Vlr. Unit.", "50%"],
        ["9786557112120", "1923", "10", "98", "49"],
        ["9788539307630", "BUSCA DA LINGUA PERFEITA NA CULTURA EUROPEIA,", "A 6", "79", "40"],
        ["9788539300716", "ABOLICAO - 9ª EDICAO, A", "40", "58", "29"],
        ["9788539307814", "ACELERACAO", "6", "110", "55"],
        ["9786557112403", "ACONTECIMENTO DA LITERATURA, O", "50", "76", "38"],
    ]
    book = parse_table_rows(rows)[1]
    assert (book["author"], book["cover_price"], book["fair_price"]) == ("", 79.0, 40.0)


def test_quantity_before_a_cover_and_a_fair_price_with_cents_is_not_a_price():
    rows = [
        ["ISBN Título Autor Qtde. Valor 50% Venda", "", "", "", "", ""],
        ["9788571661820", "A Casa & Outros Poemas", "BOSI, Ecléa", "10", "36,00", "18,00"],
        ["9788571661608", "Algo a Declarar?", "ESCALEIRA, Bruna", "5", "30,00", "15,00"],
        ["9786589321057", "Árvore do Desconhecimento, A", "RENOVATO, Jurandir", "3", "71,00", "35,50"],
        ["9788571660502", "Duas Casas", "DRAGONETTI, Cláudia", "30", "16,00", "8,00"],
    ]
    book = parse_table_rows(rows)[0]
    assert (book["cover_price"], book["fair_price"]) == (36.0, 18.0)


def test_authors_that_name_a_site_are_still_the_authors():
    rows = [
        ["9786526116760", "Carreiras Extraordinárias", "Danila Sorrentino, Simona Bursi, Shutterstock.com, Freepik.com", "Ciranda Cultural - Coedição", "R$ 59,90", "R$ 50,00", "Profissões", "https://www.cirandacultural.com.br/produto/carreiras"],
        ["9786526118610", "Manual De Detetive", "Danila Sorrentino, Illary Casasanta", "Ciranda Cultural - Coedição", "R$ 59,90", "R$ 50,00", "Profissões", "https://www.cirandacultural.com.br/produto/detetive"],
    ]
    book = parse_table_rows(rows)[0]
    assert (book["author"], book["imprint"]) == ("Danila Sorrentino, Simona Bursi, Shutterstock.com, Freepik.com", "Ciranda Cultural - Coedição")


def test_author_column_whose_header_starts_with_nome_is_the_author():
    rows = [
        ["Título do livro", "Assunto", "Preço de capa", "Nome dos autor(es) /organizador(es)", "Código de barras (apenas números)"],
        ["Quem tem Mandioca tem tudo: A planta do século XXI", "História", "R$ 40,00", "Eduardo Guimarães e Francisco Guimarães", "9788585813574"],
        ["Filosofia Pé-no-Chão: uma filosofia enraizada em nosso contexto", "Filosofia", "R$ 40,00", "Hamilton Barreto Queiroz", "9788585813529"],
        ["Plataformas Digitais e o Futuro do Trabalho", "Administração", "R$ 40,00", "Vamberto Ferreira Miranda Filho", "9788585813680"],
    ]
    assert [book["author"] for book in parse_table_rows(rows)] == ["Eduardo Guimarães e Francisco Guimarães", "Hamilton Barreto Queiroz", "Vamberto Ferreira Miranda Filho"]


def test_magazine_barcode_in_the_isbn_column_is_not_the_title():
    rows = [
        ["977217974800703", "Monolito edição 3 - Biselli e Katchboria", "Fernando Serapião", "Monolito", "-R$ 99,00-", "-R$ 45,00-"],
        ["9788566275049", "Monolito edição 27 - Vilanova Artigas e a FAU/USP", "Fernando Serapião", "Monolito", "-R$ 112,00-", "-R$ 56,00-"],
        ["9788566275056", "Monolito edição 28 - Triptyque", "Fernando Serapião", "Monolito", "-R$ 112,00-", "-R$ 45,00-"],
        ["9788566275070", "Monolito edição 29 - Gui Mattos", "Fernando Serapião", "Monolito", "-R$ 121,00-", "-R$ 45,00-"],
    ]
    book = parse_table_rows(rows)[0]
    assert (book["isbn"], book["title"], book["author"]) == ("", "Monolito edição 3 - Biselli e Katchboria", "Fernando Serapião")


def test_isbn_followed_by_the_issue_number_of_a_magazine_is_the_isbn():
    rows = [
        ["978856627513110", "Monolito edição 34 - Humberto Serpa", "Fernando Serapião", "Monolito", "-R$ 121,00-", "-R$ 55,00-"],
        ["9788566275049", "Monolito edição 27 - Vilanova Artigas e a FAU/USP", "Fernando Serapião", "Monolito", "-R$ 112,00-", "-R$ 56,00-"],
        ["9788566275056", "Monolito edição 28 - Triptyque", "Fernando Serapião", "Monolito", "-R$ 112,00-", "-R$ 45,00-"],
    ]
    book = parse_table_rows(rows)[0]
    assert (book["isbn"], book["title"]) == ("9788566275131", "Monolito edição 34 - Humberto Serpa")
