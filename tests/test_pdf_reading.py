from festa_do_livro.pdf_reading import DrawnText, table_cell_texts

LETTER_WIDTH = 4.0
THREE_ROWS_OF_TITLE_AND_AUTHOR = [[(0, top, 20, top + 10), (20, top, 60, top + 10)] for top in (0, 10, 20)]


def letters(text: str, left: float, top: float) -> list[dict]:
    """Characters the way PyMuPDF's table reader keeps them, one after the other on the same line."""
    return [
        {
            "text": letter, "x0": left + index * LETTER_WIDTH, "x1": left + (index + 1) * LETTER_WIDTH, "top": top, "bottom": top + 6,
            "doctop": top, "upright": True, "matrix": (1, 0, 0, 1, left + index * LETTER_WIDTH, top + 6),
        }
        for index, letter in enumerate(text)
    ]


def rows_below(author_starts: tuple[float, float]) -> list[dict]:
    """Two more rows, each with a short title and an author that starts where the given spot says."""
    return [character for top, start in zip((12, 22), author_starts) for character in letters("AB", 4.5, top) + letters("Livro", start, top)]


def test_letter_cut_in_half_by_the_border_stays_with_the_text_it_ends():
    # "D" starts at 18.5, before the border at 20, and its middle (20.5) falls in the next cell.
    characters = letters("ABCD", 6.5, 2) + letters("Sonia", 22.5, 2) + rows_below((22.5, 22.5))
    assert table_cell_texts(THREE_ROWS_OF_TITLE_AND_AUTHOR, characters)[0] == ["ABCD", "Sonia"]


def test_first_letter_of_a_cell_that_starts_just_before_the_border_stays_in_its_cell():
    characters = letters("ABC", 4.5, 2) + letters("Sonia", 19.6, 2) + rows_below((19.6, 19.6))
    assert table_cell_texts(THREE_ROWS_OF_TITLE_AND_AUTHOR, characters)[0] == ["ABC", "Sonia"]


def test_first_letter_of_a_long_text_that_spills_out_of_its_cell_to_the_left_stays_in_it():
    characters = letters("ABC", 6.5, 2) + letters("QUADRI", 18.5, 2) + rows_below((25.0, 25.0))
    assert table_cell_texts(THREE_ROWS_OF_TITLE_AND_AUTHOR, characters)[0] == ["ABC", "QUADRI"]


def test_digit_cut_in_half_by_the_border_stays_where_its_middle_is():
    characters = letters("AB49", 6.5, 2) + letters("Sonia", 22.5, 2) + rows_below((22.5, 22.5))
    assert table_cell_texts(THREE_ROWS_OF_TITLE_AND_AUTHOR, characters)[0] == ["AB4", "9Sonia"]


def test_each_line_of_a_cell_taller_than_its_row_goes_to_the_row_it_is_printed_on():
    rows = [[(0, 0, 30, 10), (30, 0, 60, 30)], [(0, 10, 30, 20), None], [(0, 20, 30, 30), None]]
    characters = letters("A", 2, 2) + letters("B", 2, 12) + letters("C", 2, 22) + letters("70,00", 32, 2) + letters("77,00", 32, 12) + letters("68,00", 32, 22)
    assert table_cell_texts(rows, characters) == [["A", "70,00"], ["B", "77,00"], ["C", "68,00"]]


def test_book_whose_cells_span_the_two_lines_of_its_link_stays_whole_on_its_row():
    rows = [[(0, 0, 20, 20), (20, 0, 50, 20), (50, 0, 70, 20), (70, 0, 110, 10)], [None, None, None, (70, 10, 110, 20)]]
    characters = letters("978", 2, 6) + letters("NOITE", 22, 2) + letters("POCKET", 22, 12) + letters("44", 52, 6) + letters("https", 72, 2) + letters("b", 72, 12)
    assert table_cell_texts(rows, characters) == [["978", "NOITE\nPOCKET", "44", "https"], [None, None, None, "b"]]


def test_cell_spanning_several_columns_keeps_its_whole_text():
    rows = [[(0, 0, 60, 10), None], [(0, 10, 20, 20), (20, 10, 60, 20)]]
    characters = letters("ISBN", 2, 2) + letters("TITULO", 30, 2) + letters("978", 2, 12) + letters("Livro", 22, 12)
    assert table_cell_texts(rows, characters) == [["ISBN TITULO", None], ["978", "Livro"]]


def test_text_its_cell_cuts_at_the_border_is_read_whole():
    # The page shows "ABCDE" up to the border at 20, with "E" cut in half, and hides "FGH" under the author.
    shown = letters("ABCDE", 2, 2)
    hidden = letters("FGH", 22, 2)
    characters = shown + letters("Sonia", 22.5, 2) + rows_below((22.5, 22.5))
    assert table_cell_texts(THREE_ROWS_OF_TITLE_AND_AUTHOR, characters, [DrawnText([], shown, hidden)])[0] == ["ABCDEFGH", "Sonia"]


def test_text_drawn_over_several_cells_stays_as_the_table_reader_reads_it():
    shown = letters("AB", 2, 2) + letters("CD", 22, 2)
    hidden = letters("EF", 62, 2)
    characters = shown + rows_below((22.5, 22.5))
    assert table_cell_texts(THREE_ROWS_OF_TITLE_AND_AUTHOR, characters, [DrawnText([], shown, hidden)])[0] == ["AB", "CD"]


def test_text_that_stops_showing_inside_its_cell_is_not_a_text_cut_at_the_border():
    characters = letters("ABC", 2, 2) + letters("Sonia", 22.5, 2) + rows_below((22.5, 22.5))
    hidden = letters("C", 10, 2) + letters("XYZ", 62, 2)
    assert table_cell_texts(THREE_ROWS_OF_TITLE_AND_AUTHOR, characters, [DrawnText([], characters[:2], hidden)])[0] == ["ABC", "Sonia"]


def test_text_its_cell_hides_on_both_sides_is_read_whole():
    # A centered title wider than its cell (20 to 60): the page hides "XY" over the ISBN, shows "Z" cut in half by the border
    # (its middle, 19, falls in the ISBN cell) and "ABCDEFGHIJ", and hides "KLM" past the right border.
    hidden_before = letters("XY", 9, 2)
    shown = letters("ZABCDEFGHIJ", 17, 2)
    hidden_after = letters("KLM", 61, 2)
    characters = letters("978", 1, 2) + shown + rows_below((22.5, 22.5))
    rows = table_cell_texts(THREE_ROWS_OF_TITLE_AND_AUTHOR, characters, [DrawnText(hidden_before, shown, hidden_after)])
    assert rows[0] == ["978", "XYZABCDEFGHIJKLM"]


def test_text_hidden_on_the_left_that_shows_in_two_cells_stays_as_the_table_reader_reads_it():
    hidden_before = letters("XY", -7, 2)
    shown = letters("AB", 2, 2) + letters("CD", 22, 2)
    characters = shown + rows_below((22.5, 22.5))
    assert table_cell_texts(THREE_ROWS_OF_TITLE_AND_AUTHOR, characters, [DrawnText(hidden_before, shown, [])])[0] == ["AB", "CD"]


def test_text_that_starts_with_a_letter_cut_by_the_left_border_goes_whole_to_its_cell():
    # "O QUE E..." centered in a cell (20 to 60) it barely outgrows: the page shows "O" cut in half by the border (its middle,
    # 19, falls in the ISBN cell) and hides "KLM" past the right border.
    shown = letters("OABCDEFGHIJ", 17, 2)
    hidden_after = letters("KLM", 61, 2)
    characters = letters("978", 1, 2) + shown + rows_below((22.5, 22.5))
    rows = table_cell_texts(THREE_ROWS_OF_TITLE_AND_AUTHOR, characters, [DrawnText([], shown, hidden_after)])
    assert rows[0] == ["978", "OABCDEFGHIJKLM"]


def test_text_the_page_shows_whole_but_a_little_wider_than_its_cell_goes_whole_to_it():
    # "A REFORMA..." centered in a cell (20 to 60) it barely outgrows, all of it shown: the middle of its first letter (19)
    # falls in the ISBN cell.
    shown = letters("AREFORMAXYZ", 17, 2)
    characters = letters("978", 1, 2) + shown + rows_below((22.5, 22.5))
    assert table_cell_texts(THREE_ROWS_OF_TITLE_AND_AUTHOR, characters, [DrawnText([], shown, [])])[0] == ["978", "AREFORMAXYZ"]


def test_text_the_page_shows_whole_over_two_cells_stays_as_the_table_reader_reads_it():
    shown = letters("ABCD", 2, 2) + letters("EFGHI", 22, 2)
    characters = shown + rows_below((22.5, 22.5))
    assert table_cell_texts(THREE_ROWS_OF_TITLE_AND_AUTHOR, characters, [DrawnText([], shown, [])])[0] == ["ABCD", "EFGHI"]


def test_texts_of_two_cells_drawn_in_one_piece_with_a_gap_stay_in_their_cells():
    # Paulinas 2026 draws the title and a short author as one piece ("Cabe ...Fê"), with a gap between the two cells' texts.
    shown = letters("ABCD", 2, 2) + letters("EF", 22.5, 2)
    characters = shown + rows_below((22.5, 22.5))
    assert table_cell_texts(THREE_ROWS_OF_TITLE_AND_AUTHOR, characters, [DrawnText([], shown, [])])[0] == ["ABCD", "EF"]
