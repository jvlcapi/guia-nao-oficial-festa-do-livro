import collections
import logging
import statistics
from pathlib import Path

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


def extract_table_rows(pdf_path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    with pymupdf.open(pdf_path) as document:
        for page in document:
            tables = page.find_tables().tables
            characters = list(pymupdf.table.CHARS)  # the characters find_tables read from this page, the ones Table.extract uses
            partly_hidden = partly_hidden_texts(page, characters)
            for table in tables:
                for row in table_cell_texts([row.cells for row in table.rows], characters, partly_hidden):
                    rows.append([(cell or "").replace("\n", " ").strip() for cell in row])
    return rows


def partly_hidden_texts(page: pymupdf.Page, shown_characters: list[dict]) -> list[tuple[list[dict], list[dict]]]:
    """Every text the page draws only in part, as the characters the page shows and the ones it hides. A spreadsheet clips a text
    longer than its cell at the border, so the PDF holds the whole text and the table reader only sees the part inside the cell:
    "A Cidade e os Ca" of "A Cidade e os Cachorros: Biografia de um Romance", and "978-85-7480-442" of the ISBN 978-85-7480-442-2
    (Ateliê 2026). The page shows the text from its start up to the border, so the shown part is the run of shown characters from
    the first one, and the hidden part is everything after it: a hidden letter can sit right over the same letter of the next cell
    ("i" of "Mestre Tinius" over the "i" of "Ateliê")."""
    shown_by_letter_and_column = collections.defaultdict(list)
    for character in shown_characters:
        shown_by_letter_and_column[(character["text"], round(character["x0"]))].append(character)
    doctop_base = page.rect.height * page.number
    texts = []
    for drawn in page.get_texttrace():
        shown = []
        for code, _, _, (x0, top, x1, _) in drawn["chars"]:
            same = shown_character_at(shown_by_letter_and_column, chr(code), x0, x1, top)
            if same is None:
                break
            shown.append(same)
            shown_by_letter_and_column[(same["text"], round(same["x0"]))].remove(same)
        if shown and len(shown) < len(drawn["chars"]):
            hidden = [
                {**shown[0], "text": chr(code), "x0": x0, "x1": x1, "top": top, "bottom": bottom, "doctop": top + doctop_base, "width": x1 - x0}
                for code, _, _, (x0, top, x1, bottom) in drawn["chars"][len(shown):]
            ]
            texts.append((shown, hidden))
    return texts


def shown_character_at(shown_by_letter_and_column: dict, letter: str, x0: float, x1: float, top: float) -> dict | None:
    for column in (round(x0) - 1, round(x0), round(x0) + 1):
        for character in shown_by_letter_and_column.get((letter, column), []):
            if all(abs(character[edge] - value) < SAME_CHARACTER_DISTANCE for edge, value in (("x0", x0), ("x1", x1), ("top", top))):
                return character
    return None


def table_cell_texts(rows: list[list[tuple | None]], characters: list[dict], partly_hidden: list[tuple[list[dict], list[dict]]] = ()) -> list[list[str | None]]:
    """The text of each cell as PyMuPDF's Table.extract reads it (every character in the cell that holds its middle), with three
    repairs. A column that lost the borders between its rows comes out as one tall cell over the rows below it (Hucitec 2026: 31
    cover prices in one cell and none in the 30 rows below), so each line goes back to the row it is printed on. A narrow cell
    cuts the last letter of its text in half, so the middle of that letter falls in the next cell ("6 PERGUNTAS" and "SSonia
    Salzstein" in IMS 2026), and the letter goes back to the text it ends. And a text that its cell hides in part is read whole."""
    cells = cells_by_row_and_column(rows)
    characters_by_cell = {position: [character for character in characters if middle_inside(character, bbox)] for position, bbox in cells.items()}
    give_cut_letters_back(cells, characters_by_cell)
    give_hidden_text_back(cells, characters_by_cell, partly_hidden)
    return [
        [cell_text(characters_by_cell[(row_index, column)]) if (row_index, column) in cells else None for column in range(len(row))]
        for row_index, row in enumerate(rows)
    ]


def give_hidden_text_back(
    cells: dict[tuple[int, int], tuple], characters_by_cell: dict[tuple[int, int], list[dict]], partly_hidden: list[tuple[list[dict], list[dict]]],
) -> None:
    """A text that its cell cuts at the border goes whole to the cell where it starts, with the letter the border cuts in half and
    the letters hidden past the border. A cut text shows only inside its cell and hides from the border on; any other text stays
    as the table reader read it, like a text drawn over several cells."""
    cell_of_character = {id(character): position for position, characters in characters_by_cell.items() for character in characters}
    for shown, hidden in partly_hidden:
        start = cell_of_character.get(id(shown[0]))
        if start is None or not all(starts_inside(character, cells[start]) for character in shown) or middle_inside(hidden[0], cells[start]):
            continue
        for character in shown:
            position = cell_of_character.get(id(character))
            if position is not None and position != start:
                characters_by_cell[position].remove(character)
                characters_by_cell[start].append(character)
                cell_of_character[id(character)] = start
        characters_by_cell[start].extend(character for character in hidden if not middle_inside(character, cells[start]))


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
