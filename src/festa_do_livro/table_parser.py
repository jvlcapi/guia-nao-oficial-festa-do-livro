"""Reads price lists whose PDF has real table cells (most publishers)."""
import collections
import itertools
import re

from .text_helpers import without_accents_lowercase

STRICT_MONEY = re.compile(
    r"^\s*(?:R\$\s*)?\d{1,3}(?:\.\d{3})*,\d{1,2}\s*(?:R\$)?\s*$"
    r"|^\s*R\$\s*\d+(?:[.,]\d{1,2})?\s*$"
    r"|^\s*\d{1,4}\.\d{2}\s*$",
    re.I,
)
INTERNAL_CODE = re.compile(r"^\s*\d{1,9}\s*$")
PERCENT_CELL = re.compile(r"\s*-?(\d{1,2}(?:[.,]\d+)?)\s*%\s*")
HEADER_KEYWORDS = [
    ("url", ["url", "link", "endereco", "capa/url"]),
    ("isbn", ["isbn", "ean", "codigo"]),
    ("title", ["titulo", "livro", "produto nome", "nome"]),
    ("author", ["autor"]),
    ("imprint", ["editora", "selo"]),
    ("subject", ["assunto", "area", "genero", "tema"]),
]


def join_split_digits(cell: str) -> str:
    """Normalizes a price cell: "R$ 1 09,00" -> "R$ 109,00", "S 44,90" (letter spilled from the next cell) -> "44,90"
    and "-R$ 79,90-" (dashes drawn around the cover price) -> "R$ 79,90"."""
    cell = re.sub(r"^[\s\-–]+|[\s\-–]+$", "", cell or "")
    cell = re.sub(r"^\s*[A-Za-z]\s+(?=(?:R\$\s*)?\d)", "", cell)
    return re.sub(r"(?<=\d)\s+(?=[\d,])", "", cell)


def isbn_in_cell(cell: str) -> str:
    digits = re.sub(r"[^\dXx]", "", cell)
    if cell.lower().startswith("ean") or re.fullmatch(r"[\d\-\s\.xX]+", cell.strip()):
        if len(digits) in (10, 13):
            return digits
    return ""


def looks_like_url(cell: str) -> bool:
    return "http" in cell or "www." in cell or ".com" in cell


def header_role(cell: str):
    normalized = without_accents_lowercase(cell)
    if "preco" in normalized or "valor" in normalized or "%" in normalized or "desc" in normalized:
        return None
    for role, keywords in HEADER_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return role
    return None


def money_values_in_cell(cell: str) -> list[float]:
    values = []
    for match in re.findall(r"\d{1,3}(?:\.\d{3})*,\d{1,2}|(?<![\d,])\d+(?:\.\d{1,2})?(?![\d,])", join_split_digits(cell)):
        value = float(match.replace(".", "").replace(",", ".")) if "," in match else float(match)
        if 0.01 <= value <= 5000:
            values.append(value)
    return values


def price_columns_by_row_length(rows: list[list[str]]) -> dict[int, set[int]]:
    """Which columns hold prices, decided per table shape so codes and row numbers are never read as prices."""
    strict_hits = collections.defaultdict(collections.Counter)
    rows_with_money = collections.Counter()
    for row in rows:
        if not any(STRICT_MONEY.match(join_split_digits(cell)) for cell in row):
            continue
        rows_with_money[len(row)] += 1
        for column, cell in enumerate(row):
            if STRICT_MONEY.match(join_split_digits(cell)):
                strict_hits[len(row)][column] += 1

    columns = {
        length: {column for column, hits in strict_hits[length].items() if hits >= 0.5 * count}
        for length, count in rows_with_money.items()
    }

    rows_by_length = collections.defaultdict(list)
    for row in rows:
        rows_by_length[len(row)].append(row)

    def book_rows(length):
        return [row for row in rows_by_length[length] if any(isbn_in_cell(cell) for cell in row)]

    def mostly_integers(data_rows, column):
        values = [(row[column] or "").strip() for row in data_rows]
        integers = [int(value) for value in values if re.fullmatch(r"\d{1,4}", value)]
        return integers, len(integers) >= 0.8 * len(data_rows) and sorted(integers)[len(integers) // 2] >= 5

    # A cover price written as a whole number, right before a decimal fair price.
    for length, price_columns in list(columns.items()):
        data_rows = book_rows(length)
        if not data_rows:
            continue
        for column in sorted(price_columns):
            candidate = column - 1
            if candidate <= 0 or candidate in price_columns:
                continue
            integers, is_price_column = mostly_integers(data_rows, candidate)
            if integers and is_price_column:
                columns[length] = columns[length] | {candidate}

    # Lists that write every price as a whole number.
    for length in rows_by_length:
        if columns.get(length):
            continue
        data_rows = book_rows(length)
        if len(data_rows) < 3:
            continue
        found = set()
        for column in range(1, length):
            integers, is_price_column = mostly_integers(data_rows, column)
            if integers and is_price_column and len(set(integers)) > 1:
                found.add(column)
        if found:
            columns[length] = found
    return columns


def numeric_columns_by_row_length(rows: list[list[str]]) -> dict[int, set[int]]:
    """Columns that hold row numbers or internal codes, so a numeric title like "1984" is still read as a title."""
    numeric_hits = collections.defaultdict(collections.Counter)
    filled = collections.defaultdict(collections.Counter)
    for row in rows:
        for column, cell in enumerate(row):
            if cell and cell.strip():
                filled[len(row)][column] += 1
                if INTERNAL_CODE.match(cell) or isbn_in_cell(cell):
                    numeric_hits[len(row)][column] += 1
    return {
        length: {column for column, count in counts.items() if count >= 3 and numeric_hits[length][column] >= 0.8 * count}
        for length, counts in filled.items()
    }


def has_isbn(row: list[str]) -> bool:
    return any(isbn_in_cell(cell) for cell in row)


def has_price(row: list[str]) -> bool:
    return any(STRICT_MONEY.match(join_split_digits(cell)) for cell in row)


def join_sheet_printed_in_strips(rows: list[list[str]]) -> list[list[str]]:
    """Some spreadsheets are printed in vertical strips: first every ISBN and title, then every author and price, in the same order.
    A strip with ISBNs and no prices followed by a strip of the same length with prices and no ISBNs is glued back line by line."""
    strips = [list(strip) for _, strip in itertools.groupby(rows, key=len)]
    joined: list[list[str]] = []
    position = 0
    while position < len(strips):
        left = strips[position]
        right = strips[position + 1] if position + 1 < len(strips) else []
        isbns_without_prices = sum(map(has_isbn, left)) >= 0.8 * (len(left) - 1) and not any(map(has_price, left))
        prices_without_isbns = sum(map(has_price, right)) >= 0.8 * (len(right) - 1) and not any(map(has_isbn, right))
        if len(left) >= 3 and len(left) == len(right) and isbns_without_prices and prices_without_isbns:
            joined += [left_row + right_row for left_row, right_row in zip(left, right)]
            position += 2
        else:
            joined += left
            position += 1
    return joined


def parse_table_rows(rows: list[list[str]]) -> list[dict]:
    rows = join_sheet_printed_in_strips(rows)
    price_columns = price_columns_by_row_length(rows)
    numeric_columns = numeric_columns_by_row_length(rows)
    books = []
    header = None
    for row in rows:
        if not any(row):
            continue
        joined = without_accents_lowercase(" ".join(row))
        if ("isbn" in joined or "titulo" in joined or "ean" in joined.split()) and not any(isbn_in_cell(cell) for cell in row):
            roles = [header_role(cell) for cell in row]
            if sum(1 for role in roles if role) >= 2:
                header = roles
            continue

        row_price_columns = price_columns.get(len(row), set())
        filled_price_columns = [column for column in sorted(row_price_columns) if money_values_in_cell(row[column])]
        if not filled_price_columns:
            continue
        prices = [value for column in filled_price_columns for value in money_values_in_cell(row[column])]
        isbn_columns = [column for column, cell in enumerate(row) if column not in row_price_columns and isbn_in_cell(cell)]
        row_numeric_columns = numeric_columns.get(len(row), set())
        code_columns = [
            column for column, cell in enumerate(row)
            if column not in row_price_columns and column not in isbn_columns and column in row_numeric_columns and INTERNAL_CODE.match(cell or "")
        ]
        text_columns = [
            column for column, cell in enumerate(row)
            if cell and column not in row_price_columns and column not in isbn_columns and column not in code_columns
            and not re.fullmatch(r"-?\d+([.,]\d+)?\s*%", cell.strip())
        ]

        book = {"isbn": isbn_in_cell(row[isbn_columns[0]]) if isbn_columns else "", "title": "", "author": "", "imprint": "", "subject": "", "url": ""}
        used = set()
        if header and len(header) == len(row):
            for column in text_columns:
                role = header[column]
                if role and role != "isbn" and not book.get(role):
                    book[role] = row[column]
                    used.add(column)
        for column in text_columns:
            if column not in used and looks_like_url(row[column]) and not book["url"]:
                book["url"] = row[column]
                used.add(column)
        remaining = [column for column in text_columns if column not in used]
        before_prices = [column for column in remaining if column < filled_price_columns[0]]
        after_prices = [column for column in remaining if column > filled_price_columns[-1]]
        for role in ("title", "author", "imprint"):
            if not book[role] and before_prices:
                book[role] = row[before_prices.pop(0)]
        if not book["subject"] and after_prices:
            book["subject"] = row[after_prices.pop(0)]
        if not book["title"]:
            continue

        percentages = [float(match.group(1).replace(",", ".")) for cell in row for match in [PERCENT_CELL.fullmatch(cell or "")] if match]
        if len(prices) >= 2:
            cover_price, fair_price = max(prices), min(prices)
        elif percentages and 0 < percentages[0] < 95:
            cover_price, fair_price = prices[0], round(prices[0] * (1 - percentages[0] / 100), 2)
        else:
            cover_price, fair_price = None, prices[0]
        book.update(cover_price=cover_price, fair_price=fair_price)
        books.append(book)
    return books
