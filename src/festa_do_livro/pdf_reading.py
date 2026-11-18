import collections
import logging
import statistics
from pathlib import Path
from typing import NamedTuple

import pymupdf
import pymupdf.table
from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)

# A letter starts this far into the cell before it, and the text of that cell ends this close to where the letter starts.
CUT_LETTER_START_BEFORE_BORDER = 0.3
CUT_LETTER_DISTANCE_FROM_TEXT = 0.6
SAME_LINE_DISTANCE = 1.0
USUAL_START_DISTANCE = 0.3
TALLER_THAN_ROW = 1.0
SAME_CHARACTER_DISTANCE = 0.05  # the page shows a character where the PDF draws it, to rounding


MOST_LETTERS_SPILLED_PAST_A_BORDER = 2


class DrawnText(NamedTuple):
    """A text as the page draws it, in one piece: the characters it hides before the shown ones, the shown ones, and the ones it hides
    after. A text the page shows whole hides nothing."""
    hidden_before: list[dict]
    shown: list[dict]
    hidden_after: list[dict]


def extract_table_rows(pdf_path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    with pymupdf.open(pdf_path) as document:
        for page in document:
            tables = page.find_tables().tables
            characters = list(pymupdf.table.CHARS)  # the characters find_tables read from this page, the ones Table.extract uses
            texts = drawn_texts(page, characters)
            for table in tables:
                for row in table_cell_texts([row.cells for row in table.rows], characters, texts):
                    rows.append([(cell or "").replace("\n", " ").strip() for cell in row])
    return rows


def drawn_texts(page: pymupdf.Page, shown_characters: list[dict]) -> list[DrawnText]:
    """Every text the page draws, with what it shows and what it hides. A spreadsheet clips a text longer than its cell at the border,
    so the PDF holds the whole text and the table reader only sees the part inside the cell: "A Cidade e os Ca" of "A Cidade e os
    Cachorros: Biografia de um Romance", and "978-85-7480-442" of the ISBN 978-85-7480-442-2 (Ateliê 2026). A centered text wider
    than its cell is clipped on both sides: "DADE DE SAO PAULO GEOGRAFIA E HIST" of "A CIDADE DE SAO PAULO GEOGRAFIA E HISTORIA"
    (Brasiliense 2026). So the shown part is the first unbroken run of shown characters, and what the page draws before and after
    it is hidden: a hidden letter can sit right over the same letter of the next cell ("i" of "Mestre Tinius" over the "i" of "Ateliê")."""
    shown_by_letter_and_column = collections.defaultdict(list)
    for character in shown_characters:
        shown_by_letter_and_column[(character["text"], round(character["x0"]))].append(character)
    doctop_base = page.rect.height * page.number
    texts = []
    for drawn in page.get_texttrace():
        first_shown, shown = 0, []
        for position, (code, _, _, (x0, top, x1, _)) in enumerate(drawn["chars"]):
            same = shown_character_at(shown_by_letter_and_column, chr(code), x0, x1, top)
            if same is None:
                if shown:
                    break
                continue
            if not shown:
                first_shown = position
            shown.append(same)
            shown_by_letter_and_column[(same["text"], round(same["x0"]))].remove(same)
        if shown:
            def hidden_characters(drawn_characters):
                return [
                    {**shown[0], "text": chr(code), "x0": x0, "x1": x1, "top": top, "bottom": bottom, "doctop": top + doctop_base, "width": x1 - x0}
                    for code, _, _, (x0, top, x1, bottom) in drawn_characters
                ]
            texts.append(DrawnText(
                hidden_characters(drawn["chars"][:first_shown]), shown, hidden_characters(drawn["chars"][first_shown + len(shown):]),
            ))
    return texts


def shown_character_at(shown_by_letter_and_column: dict, letter: str, x0: float, x1: float, top: float) -> dict | None:
    for column in (round(x0) - 1, round(x0), round(x0) + 1):
        for character in shown_by_letter_and_column.get((letter, column), []):
            if all(abs(character[edge] - value) < SAME_CHARACTER_DISTANCE for edge, value in (("x0", x0), ("x1", x1), ("top", top))):
                return character
    return None


def table_cell_texts(rows: list[list[tuple | None]], characters: list[dict], texts: list[DrawnText] = ()) -> list[list[str | None]]:
    """The text of each cell as PyMuPDF's Table.extract reads it (every character in the cell that holds its middle), with three
    repairs. A column that lost the borders between its rows comes out as one tall cell over the rows below it (Hucitec 2026: 31
    cover prices in one cell and none in the 30 rows below), so each line goes back to the row it is printed on. A narrow cell
    cuts the last letter of its text in half, so the middle of that letter falls in the next cell ("6 PERGUNTAS" and "SSonia
    Salzstein" in IMS 2026), and the letter goes back to the text it ends. And each text the page draws in one piece goes whole
    to its cell, with what the cell hides."""
    cells = cells_by_row_and_column(rows)
    characters_by_cell = {position: [character for character in characters if middle_inside(character, bbox)] for position, bbox in cells.items()}
    give_cut_letters_back(cells, characters_by_cell)
    keep_each_drawn_text_in_its_cell(cells, characters_by_cell, texts)
    return [
        [cell_text(characters_by_cell[(row_index, column)]) if (row_index, column) in cells else None for column in range(len(row))]
        for row_index, row in enumerate(rows)
    ]


def keep_each_drawn_text_in_its_cell(
    cells: dict[tuple[int, int], tuple], characters_by_cell: dict[tuple[int, int], list[dict]], texts: list[DrawnText],
) -> None:
    """A spreadsheet draws the text of each cell in one piece. A text that its cell cuts at the borders goes whole to that cell, with
    the letters each border cuts in half and the letters hidden past the borders, and a text the page shows whole that spills a letter
    or two into the cells beside it goes whole to the cell that holds the rest. Any other text stays as the table reader read it,
    like a text drawn over several cells."""
    cell_of_character = {id(character): position for position, characters in characters_by_cell.items() for character in characters}
    for text in texts:
        if text.hidden_before or text.hidden_after:
            cell = cell_that_cuts(text, cells, cell_of_character)
        else:
            cell = cell_a_shown_text_spills_out_of(text, cells, cell_of_character)
        if cell is None:
            continue
        for character in text.shown:
            position = cell_of_character.get(id(character))
            if position is not None and position != cell:
                characters_by_cell[position].remove(character)
                characters_by_cell[cell].append(character)
                cell_of_character[id(character)] = cell
        characters_by_cell[cell].extend(character for character in text.hidden_before + text.hidden_after if not middle_inside(character, cells[cell]))


def cell_a_shown_text_spills_out_of(
    text: DrawnText, cells: dict[tuple[int, int], tuple], cell_of_character: dict[int, tuple[int, int]],
) -> tuple[int, int] | None:
    """The cell of a text the page shows whole but a little wider than its cell, centered, so that the middle of its first or last
    letter falls in the cell beside it: "A REFORMA AGRARIA NA ROMA ANTIGA" puts its first "A" in the cell of the ISBN and its last
    "A" in the cell of the author (Brasiliense 2026). Only up to two letters on each side spill, into the cells right beside it,
    unbroken from the rest of the text and with the letter next to the border lying across it. Some PDFs draw the texts of
    neighbouring cells in one piece, with a gap between them ("Cabe ...Fê", title and author, Paulinas 2026): those stay apart."""
    positions = [cell_of_character.get(id(character)) for character in text.shown]
    if None in positions or len(set(positions)) == 1:
        return None
    cell = collections.Counter(positions).most_common(1)[0][0]
    row, column = cell
    inside = [position == cell for position in positions]
    first_inside, last_inside = inside.index(True), len(inside) - 1 - inside[::-1].index(True)
    before, after = positions[:first_inside], positions[last_inside + 1:]
    if not all(inside[first_inside:last_inside + 1]) or len(before) > MOST_LETTERS_SPILLED_PAST_A_BORDER or len(after) > MOST_LETTERS_SPILLED_PAST_A_BORDER:
        return None
    if any(position != (row, column - 1) for position in before) or any(position != (row, column + 1) for position in after):
        return None
    left_border, right_border = cells[cell][0], cells[cell][2]
    if before and not (text.shown[first_inside - 1]["x0"] < left_border < text.shown[first_inside - 1]["x1"] and unbroken(text.shown[:first_inside + 1])):
        return None
    if after and not (text.shown[last_inside + 1]["x0"] < right_border < text.shown[last_inside + 1]["x1"] and unbroken(text.shown[last_inside:])):
        return None
    return cell


def unbroken(characters: list[dict]) -> bool:
    return all(abs(following["x0"] - previous["x1"]) <= CUT_LETTER_DISTANCE_FROM_TEXT for previous, following in zip(characters, characters[1:]))


def cell_that_cuts(text: DrawnText, cells: dict[tuple[int, int], tuple], cell_of_character: dict[int, tuple[int, int]]) -> tuple[int, int] | None:
    """The cell whose borders hide the rest of a text: the text shows only inside it, and what it hides lies past its borders. A
    centered text wider than its cell spills out of both sides, so the first letter it shows can be cut in half by the left
    border, with its middle in the cell before: "D" of "A CIDADE", whose "A CI" the page hides (Brasiliense 2026). Every other
    letter it shows starts inside the cell."""
    cells_of_shown = collections.Counter(cell_of_character[id(character)] for character in text.shown if id(character) in cell_of_character)
    if not cells_of_shown:
        return None
    cell = cells_of_shown.most_common(1)[0][0]
    left_border, right_border = cells[cell][0], cells[cell][2]
    first, rest = text.shown[0], text.shown[1:]
    first_cut_by_the_left_border = first["x0"] < left_border < first["x1"] < right_border
    if not (starts_inside(first, cells[cell]) or first_cut_by_the_left_border) or not all(starts_inside(character, cells[cell]) for character in rest):
        return None
    if not all((character["x0"] + character["x1"]) / 2 < left_border for character in text.hidden_before):
        return None
    if text.hidden_after and middle_inside(text.hidden_after[0], cells[cell]):
        return None
    return cell


def starts_inside(character: dict, bbox: tuple) -> bool:
    vertical_middle = (character["top"] + character["bottom"]) / 2
    return bbox[0] - SAME_LINE_DISTANCE <= character["x0"] < bbox[2] and bbox[1] <= vertical_middle < bbox[3]


def cells_by_row_and_column(rows: list[list[tuple | None]]) -> dict[tuple[int, int], tuple]:
    """Every cell, and a cell taller than the other cells of its row split into one piece per row it covers, each from the top of
    its row to the top of the next. Only rows with cells of their own in most columns count as rows: in some lists every cell of a
    book spans the two lines of its link, and each of those lines is a row with a single cell (L&PM 2025)."""
    tops = [min(cell[1] for cell in row if cell) for row in rows]
    usual_bottoms = [statistics.median(cell[3] for cell in row if cell) for row in rows]
    has_own_cells = [sum(1 for cell in row if cell) >= len(row) / 2 for row in rows]
    cells = {}
    for row_index, row in enumerate(rows):
        for column, cell in enumerate(row):
            if cell is None:
                continue
            covered = [row_index]
            if cell[3] > usual_bottoms[row_index] + TALLER_THAN_ROW:
                for next_index in range(row_index + 1, len(rows)):
                    if tops[next_index] >= cell[3] - TALLER_THAN_ROW or rows[next_index][column] is not None or not has_own_cells[next_index]:
                        break
                    covered.append(next_index)
            for position, covered_index in enumerate(covered):
                top = cell[1] if position == 0 else tops[covered_index]
                bottom = tops[covered[position + 1]] if position + 1 < len(covered) else cell[3]
                cells[(covered_index, column)] = (cell[0], top, cell[2], bottom)
    return cells


def give_cut_letters_back(cells: dict[tuple[int, int], tuple], characters_by_cell: dict[tuple[int, int], list[dict]]) -> None:
    """A letter that starts before the border of its cell belongs to the cell before when it is a letter (a moved digit would
    change a price: "23,00" read as "3,00", Unesp 2026), when it ends the line of the cell before (one unbroken run from the start
    of the line up to it; text that spills out of the next cell sits after a gap: "O r" of "O ruído de uma época", Instante 2026),
    and when the text of its own cell does not go on from it. A long text that spills to the left out of its cell goes on from its
    first letter ("Q" and "UADRINHOS NA CIA", Companhia das Letras e JBC 2025); next to a cut letter, the text of the cell starts
    over the letter, after a gap, or where the column usually starts its text ("tra" and "n", then "Luiz" where every author
    starts, Hucitec 2026)."""
    usual_starts = usual_text_starts(cells, characters_by_cell)
    for (row_index, column), cell in cells.items():
        cell_before = cells.get((row_index, column - 1))
        if cell_before is None or abs(cell_before[2] - cell[0]) > SAME_LINE_DISTANCE:
            continue
        characters_before = characters_by_cell[(row_index, column - 1)]
        for character in list(characters_by_cell[(row_index, column)]):
            starts_before_border = character["x0"] < cell[0] - CUT_LETTER_START_BEFORE_BORDER
            if not (starts_before_border and character["text"].isalpha() and ends_unbroken_line(character, characters_before)):
                continue
            following = next_on_the_same_line(character, characters_by_cell[(row_index, column)])
            text_goes_on = following is not None and following["text"].isalnum() and abs(following["x0"] - character["x1"]) <= CUT_LETTER_DISTANCE_FROM_TEXT
            if text_goes_on and abs(following["x0"] - usual_starts[column]) > USUAL_START_DISTANCE:
                continue
            characters_by_cell[(row_index, column)].remove(character)
            characters_before.append(character)


def next_on_the_same_line(character: dict, characters: list[dict]) -> dict | None:
    later = [other for other in characters if other["x0"] > character["x0"] and abs(other["top"] - character["top"]) < SAME_LINE_DISTANCE]
    return min(later, key=lambda other: other["x0"]) if later else None


def usual_text_starts(cells: dict[tuple[int, int], tuple], characters_by_cell: dict[tuple[int, int], list[dict]]) -> dict[int, float]:
    """Where each column most often starts its text after the border, to half a point."""
    starts_by_column = collections.defaultdict(collections.Counter)
    for position, cell in cells.items():
        after_border = [character["x0"] for character in characters_by_cell[position] if character["x0"] >= cell[0]]
        if after_border:
            starts_by_column[position[1]][round(min(after_border) * 2) / 2] += 1
    return collections.defaultdict(lambda: float("inf"), {column: starts.most_common(1)[0][0] for column, starts in starts_by_column.items()})


def ends_unbroken_line(character: dict, characters_before: list[dict]) -> bool:
    line = sorted((other for other in characters_before if abs(other["top"] - character["top"]) < SAME_LINE_DISTANCE), key=lambda other: other["x0"])
    letters = line + [character]
    return bool(line) and all(abs(following["x0"] - previous["x1"]) <= CUT_LETTER_DISTANCE_FROM_TEXT for previous, following in zip(letters, letters[1:]))


def middle_inside(character: dict, bbox: tuple) -> bool:
    horizontal_middle = (character["x0"] + character["x1"]) / 2
    vertical_middle = (character["top"] + character["bottom"]) / 2
    return bbox[0] <= horizontal_middle < bbox[2] and bbox[1] <= vertical_middle < bbox[3]


def cell_text(characters: list[dict]) -> str:
    return pymupdf.table.extract_text(characters) if characters else ""


def extract_plain_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def extract_text_spans(pdf_path: Path) -> list[list[dict]]:
    """Every text span of every page, with horizontal bounds, vertical center and where each of its characters starts."""
    pages: list[list[dict]] = []
    with pymupdf.open(pdf_path) as document:
        for page in document:
            spans = []
            for block in page.get_text("rawdict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        characters = [(letter, character["bbox"][0]) for character in span["chars"] for letter in character["c"]]
                        raw_text = "".join(letter for letter, _ in characters)
                        text = raw_text.strip()
                        if not text:
                            continue
                        first = len(raw_text) - len(raw_text.lstrip())
                        left, top, right, bottom = span["bbox"]
                        spans.append({
                            "left": left, "right": right, "middle": (top + bottom) / 2, "text": text,
                            "character_lefts": [character_left for _, character_left in characters[first:first + len(text)]],
                        })
            pages.append(merge_adjacent_spans(spans))
    return pages


def merge_adjacent_spans(spans: list[dict]) -> list[dict]:
    spans = sorted(spans, key=lambda span: (round(span["middle"]), span["left"]))
    merged: list[dict] = []
    for span in spans:
        previous = merged[-1] if merged else None
        gap = span["left"] - previous["right"] if previous else None
        if previous and abs(previous["middle"] - span["middle"]) < 1.5 and 0 <= gap < 2.5:
            separator = "" if gap < 0.8 else " "
            previous["text"] += separator + span["text"]
            previous["character_lefts"] = previous["character_lefts"] + [previous["right"]] * len(separator) + span["character_lefts"]
            previous["right"] = span["right"]
        else:
            merged.append(dict(span))
    return merged
