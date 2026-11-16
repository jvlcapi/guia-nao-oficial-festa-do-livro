from festa_do_livro.position_parser import exact_column_starts, is_isbn_missing_a_digit, split_at_column_starts

COLUMN_STARTS = (112.0, 321.0, 453.0)
AUTHOR_COLUMN_START = 321.1


def column_of(left: float):
    found = None
    for column, start in enumerate(COLUMN_STARTS):
        if left >= start - 4:
            found = column
    return found


def span(text: str, character_lefts: list[float]) -> dict:
    return {"left": character_lefts[0], "right": character_lefts[-1] + 4, "middle": 100, "text": text, "character_lefts": character_lefts}


def evenly_spaced(first_left: float, count: int, width: float = 4.5) -> list[float]:
    return [first_left + index * width for index in range(count)]


def test_title_cut_short_and_glued_to_its_author_is_cut_where_the_author_column_starts():
    glued = span("VIKTOAna", evenly_spaced(298.6, 5) + [321.15, 325.5, 329.8])
    assert [piece["text"] for piece in split_at_column_starts(glued, {1: AUTHOR_COLUMN_START}, column_of)] == ["VIKTO", "Ana"]


def test_author_piece_starts_where_the_author_column_starts():
    glued = span("NAZARE Leonardo", evenly_spaced(290.1, 7) + evenly_spaced(321.15, 8, 4.3))
    assert split_at_column_starts(glued, {1: AUTHOR_COLUMN_START}, column_of)[1]["left"] == AUTHOR_COLUMN_START


def test_text_that_runs_past_a_column_start_without_a_letter_there_is_kept_whole():
    running = span("ESPIRITUALIDADE", evenly_spaced(300.0, 15))
    assert split_at_column_starts(running, {1: AUTHOR_COLUMN_START}, column_of) == [running]


def test_column_aligned_to_the_right_has_no_exact_start_even_when_one_word_repeats():
    lefts = (651.4, 651.4, 651.4, 651.4, 644.9, 599.8, 608.9, 630.2, 621.7, 640.3)
    rows = [[{"left": left, "text": "Filosofia" if left == 651.4 else "Outro assunto"}] for left in lefts]
    assert exact_column_starts(rows, lambda left: 0, row_count=len(lefts)) == {}


def test_column_aligned_to_the_left_starts_where_most_of_its_lines_start():
    authors = ("Leonardo Boff", "Katy Grissault", "Anselm Grun", "Slavoj Zizek")
    rows = [[{"left": 321.15, "text": author}] for author in authors] + [[{"left": 340.0, "text": "Boff"}]]
    assert exact_column_starts(rows, lambda left: 1, row_count=5) == {1: AUTHOR_COLUMN_START}


def test_isbn_printed_without_its_first_nine_still_starts_a_row():
    assert is_isbn_missing_a_digit("786585960589")



def test_spot_where_one_centered_text_repeats_is_not_a_column_start():
    rows = [[{"left": 1405.6, "text": "FICÇÃO ESTRANGEIRA"}]] * 79 + [[{"left": 1399.5, "text": "NÃO FICÇÃO BRASILEIRA"}]] * 44
    assert exact_column_starts(rows, lambda left: 7, row_count=len(rows)) == {}


def test_column_that_repeats_one_name_on_every_line_starts_where_the_name_starts():
    rows = [[{"left": 453.9, "text": "VOZES"}]] * 10
    assert exact_column_starts(rows, lambda left: 2, row_count=len(rows)) == {2: 453.9}

