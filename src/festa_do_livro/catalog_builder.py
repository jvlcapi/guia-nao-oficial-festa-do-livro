"""Turns the parsed price lists into the catalog file the web page reads."""
import collections
import hashlib
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .fair_dates import edition_year, period_dates
from .fair_site import EventDetails, Publisher
from .isbn import is_valid_isbn, isbn_of_book_id
from .pdf_reading import extract_plain_text, extract_table_rows, extract_text_spans
from .position_parser import parse_by_position
from .table_parser import (
    LOWEST_FAIR_SHARE_OF_COVER,
    PERCENT_CELL,
    SHARE_OF_ROWS_IN_A_COLUMN,
    isbn_in_cell,
    join_sheet_printed_in_strips,
    money_values_in_cell,
    parse_table_rows,
)
from .text_helpers import without_accents_lowercase

URL_IN_TEXT = re.compile(r"https?://\S+")
LINK_CUT_AT_THE_START = re.compile(r"\S*://\S*")
CREDENTIAL_QUERY_KEYS = {"token", "access_token", "accesstoken", "key", "apikey", "api_key", "signature", "sig", "auth", "password", "secret"}
IMAGE_HOSTS_AND_PATHS = ("bookinfometadados", "metabooks.com/api", "/cover/")
COMPANY_SUFFIX_WORDS = {"e", "livraria", "ltda", "me", "eireli", "distribuidora"}
MONEY_IN_TEXT = re.compile(r"(R\$\s*)?\d{1,3}(\.\d{3})*,\d{2}|\d+\.\d{2}\b")
MONEY_IN_SUBJECT = re.compile(r"(?:R\$\s*)?\d{1,3}(?:\.\d{3})*,\d{2}")
MONEY_ON_ISBN_LINE = re.compile(r"(?<![\d,.])(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{1,2})(?![\d%])(?!\s*%)")
HTML_TAG = re.compile(r"<[^>]+>")
EDITION_BEFORE_TITLE = re.compile(r"^\d{1,2}\s*[aª]\.?\s*ed(?:ição|icao|\.)?\s+", re.I)
SYNOPSIS_MINIMUM_LENGTH = 40
LONGEST_SUBJECT = 60
TAG_SEPARATOR = re.compile(r"\s*[,;]\s*")
MOST_WORDS_IN_A_TAG = 4
SYNOPSIS_SHARE_OF_SUBJECTS = 0.8
LONGEST_TITLE = 250  # longer text is several rows glued together by the reader
FAIR_PRICE_HINTS = ("desc", "feira", "festa", "%", "promo", "final", "venda", "liquido")
ONLY_COVER_PRICE_NOTICE = "só tem preço de capa; o preço de feira não foi informado"
PRICE_LABEL = re.compile(r"preco|\$|valor")
MONEY_AMOUNT = re.compile(r"r\$\s*\d[\d.]*,\d{1,2}")
FEWEST_ROWS_TO_JUDGE_A_COLUMN = 3
PUBLISHER_NUMBER_IN_ADDRESS = re.compile(r"/publishers/(publisher-\d+)/")
NAMES_IN_OLD_IDS_FILE = "nomes-usados-nos-codigos-antigos.json"
# A spreadsheet saved as XML writes a line break inside a cell as "_x000D_" ("Márcia Arbex_x000d_", Ed. UFMG 2026).
SPREADSHEET_ESCAPE_CODE = re.compile(r"_x[0-9A-Fa-f]{4}_")
FEWEST_BOOKS_TO_COMPARE_READERS = 10
SHARE_READ_THE_SAME_WAY = 0.8
SHORTEST_CUT_TITLE = 10
LOWEST_SHARE_OF_OTHER_READER_ISBNS = 0.5
READ_IN_STRIPS = "tabela em faixas"


@dataclass(frozen=True)
class ParsedPriceList:
    books: list[dict]
    method: str
    plain_text: str
    notice: str = ""


def tidy(text: str) -> str:
    return re.sub(r"\s+", " ", SPREADSHEET_ESCAPE_CODE.sub(" ", text or "")).strip(" ;,-")


def tidy_subject(text: str) -> str:
    """The subject column sometimes carries HTML, a stray price or the end of a broken link instead of a genre."""
    text = html.unescape(HTML_TAG.sub(" ", text or ""))
    if text.lstrip().startswith("/") or URL_IN_TEXT.search(text) or "www." in text:
        return ""
    text = tidy(MONEY_IN_SUBJECT.sub(" ", text))
    if text.isupper():
        text = text.capitalize()
    if len(text) > LONGEST_SUBJECT and is_list_of_tags(text):
        last_whole_tag_end = max(text.rfind(",", 0, LONGEST_SUBJECT + 1), text.rfind(";", 0, LONGEST_SUBJECT + 1))
        if last_whole_tag_end > 0:
            return text[:last_whole_tag_end].strip()
    return text[:LONGEST_SUBJECT]


def is_list_of_tags(text: str) -> bool:
    """Short labels between commas ("Alfabetização, Inglês, Primeiros conceitos, Adição", Ciranda Cultural 2026), unlike a synopsis,
    whose sentences run on between its commas."""
    tags = TAG_SEPARATOR.split(text.strip(" ,;"))
    return len(tags) >= 2 and all(0 < len(tag.split()) <= MOST_WORDS_IN_A_TAG for tag in tags)


def tidy_title(text: str) -> str:
    """Some lists put the edition before the title: "1a ed. ACO EM FLOR"."""
    return EDITION_BEFORE_TITLE.sub("", tidy(text))


def clean_parsed_book(book: dict) -> dict:
    book = dict(book)
    for field in ("title", "author", "imprint", "subject", "url"):
        book[field] = re.sub(r"\s+", " ", book.get(field) or "").strip()
    for field in ("subject", "title", "author"):
        match = URL_IN_TEXT.search(book[field])
        if match:
            if not book["url"]:
                book["url"] = match.group(0)
            book[field] = URL_IN_TEXT.sub("", book[field]).strip()
        # A link wider than its centered cell loses its start to the cell on the left: "Ensaio ps://ercolano.com.br/..." (Ercolano 2026).
        book[field] = LINK_CUT_AT_THE_START.sub("", book[field]).strip()
    if book["url"] and not book["url"].startswith("http"):
        book["url"] = "" if " " in book["url"] or "." not in book["url"] else "https://" + book["url"].lstrip("/")
    book["url"] = book["url"].replace(" ", "")
    book["title"] = re.sub(r"^(ean:?|isbn13:?)\s*\d+\s*", "", book["title"], flags=re.I).strip(" -")
    return book


def fill_missing_isbns_from_text(books: list[dict], plain_text: str) -> None:
    flat_text = re.sub(r"\s+", " ", plain_text)
    for book in books:
        if book["isbn"] or len(book["title"]) < 4:
            continue
        position = flat_text.find(book["title"][:40])
        if position < 0:
            continue
        match = re.search(r"(97[89][\d\-]{10,14})\s?$", flat_text[max(0, position - 22):position])
        if match:
            digits = re.sub(r"\D", "", match.group(1))
            if len(digits) == 13 and is_valid_isbn(digits):
                book["isbn"] = digits


def has_only_cover_prices(plain_text: str) -> bool:
    """The header has one price label, it says "capa" and nothing mentions a discount: the list has no fair price at all. The text
    before the first ISBN can hold the first book's price, when the ISBN comes after it (Uneb 2026), and a price is not a label."""
    first_isbn = re.search(r"97[89][\d\-\s]{10,17}", plain_text)
    header = without_accents_lowercase(plain_text[:first_isbn.start()] if first_isbn else plain_text[:1500]).replace("descricao", "")
    price_labels = len(PRICE_LABEL.findall(MONEY_AMOUNT.sub(" ", header)))
    return "capa" in header and price_labels <= 1 and not any(hint in header for hint in FAIR_PRICE_HINTS)


def has_empty_fair_price_column(table_rows: list[list[str]]) -> bool:
    """The header names a cover price and a fair price, but in nearly every row with an ISBN the fair price is empty and the cover
    price is there: the publisher left the discount column blank (Ed. UFV 2026), so the one price of each book is its cover."""
    for header_index, header in enumerate(table_rows):
        labels = [without_accents_lowercase(cell or "") for cell in header]
        cover_columns = [column for column, label in enumerate(labels) if "capa" in label and PRICE_LABEL.search(label)]
        fair_columns = [
            column for column, label in enumerate(labels)
            if column not in cover_columns and PRICE_LABEL.search(label) and any(hint in label for hint in FAIR_PRICE_HINTS)
        ]
        if not cover_columns or not fair_columns:
            continue
        rows_with_isbn = [row for row in table_rows[header_index + 1:] if len(row) == len(header) and any(isbn_in_cell(cell or "") for cell in row)]
        if len(rows_with_isbn) < FEWEST_ROWS_TO_JUDGE_A_COLUMN:
            continue
        rows_with_only_the_cover = [
            row for row in rows_with_isbn
            if money_values_in_cell(row[cover_columns[0]] or "")
            and not any(money_values_in_cell(row[column] or "") for column in fair_columns)
            and not any(PERCENT_CELL.fullmatch(cell or "") for cell in row)
        ]
        return len(rows_with_only_the_cover) >= SHARE_OF_ROWS_IN_A_COLUMN * len(rows_with_isbn)
    return False


def parse_price_list(pdf_path: Path) -> ParsedPriceList:
    """Runs both readers and keeps the one that read the list better (table_reader_wins). In a list with only cover prices the single
    price is the cover: the book keeps it and has no fair price, instead of showing the cover as the fair price, twice the real one."""
    plain_text = extract_plain_text(pdf_path)
    try:
        table_rows = extract_table_rows(pdf_path)
        from_tables = parse_table_rows(table_rows)
        printed_in_strips = len(join_sheet_printed_in_strips(table_rows)) < len(table_rows)
    except Exception:
        table_rows, from_tables, printed_in_strips = [], [], False
    try:
        from_positions = parse_by_position(extract_text_spans(pdf_path))
    except Exception:
        from_positions = []
    if table_reader_wins(from_tables, from_positions, plain_text):
        # In strips, the ISBN and its prices sit on different pages, so the price check reports them as divergences.
        chosen, other, method = from_tables, from_positions, READ_IN_STRIPS if printed_in_strips else "tabela"
    else:
        chosen, other, method = from_positions, from_tables, "posição do texto"
    books = cleaned_complete_books(chosen)
    fill_missing_isbns_from_text(books, plain_text)
    found_only_by_other_reader = books_only_the_other_reader_found(books, cleaned_complete_books(other))
    books = without_garbled_copies(books, found_only_by_other_reader) + found_only_by_other_reader
    notice = ""
    if has_only_cover_prices(plain_text) or has_empty_fair_price_column(table_rows):
        for book in books:
            if book["cover_price"] is None:
                book["cover_price"], book["fair_price"] = book["fair_price"], None
        notice = ONLY_COVER_PRICE_NOTICE
    return ParsedPriceList(books=books, method=method, plain_text=plain_text, notice=notice)


def table_reader_wins(from_tables: list[dict], from_positions: list[dict], plain_text: str) -> bool:
    """The reader that found more complete books wins, and a tie goes to the table reader. A reader that mixed up the columns can
    read as many rows as the other one, only without their ISBNs (Vozes 2026: 1,099 rows and no ISBN, against 1,092 books that
    have one), so the reader that found less than half the ISBNs of the other one loses first."""
    isbns_in_tables = count_valid_isbns(from_tables, plain_text)
    isbns_in_positions = count_valid_isbns(from_positions, plain_text)
    if lost_the_isbns(isbns_in_tables, isbns_in_positions):
        return False
    if lost_the_isbns(isbns_in_positions, isbns_in_tables):
        return True
    complete = lambda books: sum(1 for book in books if book["title"] and book["fair_price"])
    return complete(from_tables) >= 0.95 * complete(from_positions) and complete(from_tables) > 0


def count_valid_isbns(books: list[dict], plain_text: str) -> int:
    """The ISBNs the books would end up with if this reader were chosen, the ones printed right before a title included."""
    cleaned = cleaned_complete_books(books)
    fill_missing_isbns_from_text(cleaned, plain_text)
    return sum(1 for book in cleaned if is_valid_isbn(book["isbn"]))


def lost_the_isbns(isbns_found: int, isbns_found_by_other_reader: int) -> bool:
    return (
        isbns_found_by_other_reader >= FEWEST_BOOKS_TO_COMPARE_READERS
        and isbns_found < LOWEST_SHARE_OF_OTHER_READER_ISBNS * isbns_found_by_other_reader
    )


def cleaned_complete_books(books: list[dict]) -> list[dict]:
    cleaned = [clean_parsed_book(book) for book in books if book["title"] and book["fair_price"]]
    return [book for book in cleaned if book["title"]]


def books_only_the_other_reader_found(books: list[dict], other_reader_books: list[dict]) -> list[dict]:
    """A row the chosen reader lost, like the last one of a table whose borders break (Unifesp), can still be read by the other
    reader. Only a valid ISBN tells that it is a book the chosen reader missed, and not the same book read another way, and the
    other reader is trusted only when it reads the books both found the same way: in some lists it mixes up the columns."""
    books_by_isbn = {book["isbn"]: book for book in books if is_valid_isbn(book["isbn"])}
    other_books_by_isbn = {}
    for book in other_reader_books:
        if is_valid_isbn(book["isbn"]):
            other_books_by_isbn.setdefault(book["isbn"], book)
    found_by_both = books_by_isbn.keys() & other_books_by_isbn.keys()
    read_the_same_way = sum(1 for isbn in found_by_both if same_reading(books_by_isbn[isbn], other_books_by_isbn[isbn]))
    if len(found_by_both) < FEWEST_BOOKS_TO_COMPARE_READERS or read_the_same_way < SHARE_READ_THE_SAME_WAY * len(found_by_both):
        return []
    return [book for isbn, book in other_books_by_isbn.items() if isbn not in books_by_isbn]


def without_garbled_copies(books: list[dict], found_only_by_other_reader: list[dict]) -> list[dict]:
    """The chosen reader can read a row and lose only its ISBN, like "9786556322001 PRISMA DA RAÇA, O Lehmann, David" in a single
    cell (Unifesp). When the other reader brings that book with its ISBN, the garbled copy goes away instead of showing the book
    twice. Only the whole title counts: volumes 2 and 3 of a series share the price and the start of the title (Vozes)."""
    remaining = list(books)
    for book_with_isbn in found_only_by_other_reader:
        garbled_copy = next((book for book in remaining if is_garbled_copy(book, book_with_isbn)), None)
        if garbled_copy is not None:
            remaining.remove(garbled_copy)
    return remaining


def is_garbled_copy(book: dict, book_with_isbn: dict) -> bool:
    if is_valid_isbn(book["isbn"]) or book["fair_price"] != book_with_isbn["fair_price"]:
        return False
    isbn_inside_title = book_with_isbn["isbn"] in re.sub(r"\D", "", book["title"])
    return isbn_inside_title or comparable_title(book["title"]) == comparable_title(book_with_isbn["title"])


def same_reading(book: dict, other_reading: dict) -> bool:
    """The same title and fair price. The other reader may see the title cut short by its cell, because the table reader reads the
    end a cell hides and the position reader does not (LVM 2026). A longer title from the other reader is not the same reading:
    it can be the title with the author glued to it ("Notas Dissonantes Neves, Juliano C. S.")."""
    title, other_title = comparable_title(book["title"]), comparable_title(other_reading["title"])
    same_title = title == other_title or (len(other_title) >= SHORTEST_CUT_TITLE and title.startswith(other_title))
    return same_title and book["fair_price"] == other_reading["fair_price"]


def comparable_title(title: str) -> str:
    return re.sub(r"\W+", " ", without_accents_lowercase(title)).strip()


def safe_public_url(url: str) -> str:
    """Drops cover-image links, links to a site's front page (never the book's own page, and often cut by the cell) and query parameters that carry a credential."""
    if not url or len(url) < 12:
        return ""
    lowered = url.lower()
    if any(marker in lowered for marker in IMAGE_HOSTS_AND_PATHS) or lowered.split("?")[0].endswith((".jp", ".jpg", ".jpeg", ".png", ".webp")):
        return ""
    parts = urlsplit(url)
    if parts.path in ("", "/") and not parts.query:
        return ""
    kept_query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in CREDENTIAL_QUERY_KEYS]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept_query), parts.fragment))


def publisher_key(publisher: Publisher) -> str:
    """The official site files each publisher's price list under a number ("publisher-474") that stays when the Festa renames the
    publisher, as it did with 55 of them on 18/11/2026. Without that address, the name is the key, as it was until v1.9.0."""
    match = PUBLISHER_NUMBER_IN_ADDRESS.search(publisher.price_list_url)
    return match.group(1) if match else publisher.name


def load_names_in_old_ids(edition_directory: Path) -> dict[str, list[str]]:
    """Every name each publisher had while the ids of books without ISBN came from the publisher's name, by publisher key."""
    path = Path(edition_directory) / NAMES_IN_OLD_IDS_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def stable_book_id(isbn: str, publisher_key: str, title: str) -> str:
    return isbn or "x" + hashlib.md5((publisher_key + title).encode()).hexdigest()[:12]


def old_ids_of_book_without_isbn(book_id: str, old_names: list[str], title: str) -> list[str]:
    """The ids a book without ISBN had under each name of its publisher, so saved lists and shared links made before still find it."""
    if not book_id.startswith("x"):
        return []
    return sorted({stable_book_id("", name, title) for name in old_names} - {book_id})


def exhibitor_suffix(publisher_key: str) -> str:
    return hashlib.md5(publisher_key.encode()).hexdigest()[:6]


def without_quantity_closed_by_a_parenthesis(text: str) -> str:
    """The quantity after the author, glued to it or not, with the parenthesis a spreadsheet number format keeps ("CARLOS, Ana Fani
    Alessandri25)" and "MOURA, Clóvis 24)", Edusp 2026). A year that closes a parenthesis the text opened stays ("Perspectiva, 1974)")."""
    if text.count(")") > text.count("("):
        return re.sub(r"\s*\d+\)$", "", text)
    return text


def without_stray_letters(imprint: str) -> str:
    """Cells often swallow one letter of the neighbouring cell: "oAnita Garibaldi", "MATRIX N". A name cut after a separator
    keeps no dangling separator either: "ESTRALADABAO - U" is "ESTRALADABAO"."""
    imprint = re.sub(r"^[a-z]\s*(?=[A-ZÀ-Ý0-9])", "", (imprint or "").strip())
    return re.sub(r"\s+[A-Za-z]$", "", imprint).strip(" ;,-–")


def imprint_repeats_exhibitor(imprint: str, exhibitor_name: str) -> bool:
    """True when the imprint adds nothing to the exhibitor name (equal, cut short, or followed only by noise)."""
    imprint_key = without_stray_letters(imprint).lower()
    exhibitor_key = exhibitor_name.lower()
    if not imprint_key:
        return True
    if exhibitor_key.startswith(imprint_key):
        return True
    if imprint_key.startswith(exhibitor_key):
        remainder = imprint_key[len(exhibitor_key):].strip()
        only_company_suffixes = all(word in COMPANY_SUFFIX_WORDS for word in re.findall(r"[a-zà-ý]+", remainder))
        return not re.search(r"[a-zà-ý]{2,}", remainder) or remainder == exhibitor_key or only_company_suffixes
    return False


def count_distinct_rows(parsed_books: list[dict]) -> int:
    """The rows read, with a row printed again counted once: the same ISBN, or none, and the same title. catalog_books shows that
    row once, so its copies are no books lost on the way to the catalog (Matrix 2026 prints 137 of its 337 titles two or three times)."""
    return len({
        (book["isbn"] if is_valid_isbn(book["isbn"]) else "", without_accents_lowercase(tidy_title(book["title"])))
        for book in parsed_books
    })


def catalog_books(publishers: list[Publisher], parsed_by_index: dict[int, ParsedPriceList], names_in_old_ids: dict[str, list[str]]) -> list[dict]:
    books = []
    title_by_book_id = {}
    for publisher_index, parsed in sorted(parsed_by_index.items()):
        exhibitor_name = publishers[publisher_index].name
        key = publisher_key(publishers[publisher_index])
        old_names = names_in_old_ids.get(key, [])
        for parsed_book in parsed.books:
            title = tidy_title(parsed_book["title"])
            if not title or re.fullmatch(r"[\d\s\-]{5,}", title) or len(title) > LONGEST_TITLE:
                continue
            isbn = parsed_book["isbn"] if is_valid_isbn(parsed_book["isbn"]) else ""
            if not isbn and without_accents_lowercase(title) == without_accents_lowercase(exhibitor_name):
                continue  # a broken table row that only repeats the publisher's name
            book_id = stable_book_id(isbn, key, title)
            title_key = without_accents_lowercase(title)
            if (book_id, publisher_index) in title_by_book_id:
                if title_by_book_id[(book_id, publisher_index)] == title_key:
                    continue  # the same row twice in the list
                book_id = stable_book_id("", key, title)  # another book printed with the same ISBN
                if (book_id, publisher_index) in title_by_book_id:
                    continue
            title_by_book_id[(book_id, publisher_index)] = title_key
            book = {
                "i": book_id, "t": title, "a": tidy(parsed_book["author"]), "s": tidy(parsed_book["imprint"]),
                "g": tidy_subject(parsed_book["subject"]), "c": parsed_book["cover_price"], "f": parsed_book["fair_price"], "x": publisher_index,
            }
            old_ids = old_ids_of_book_without_isbn(book_id, old_names, title)
            if old_ids:
                book["o"] = old_ids
            url = safe_public_url(parsed_book["url"])
            if url:
                book["u"] = url
            if not book["a"]:
                del book["a"]
            if not book["s"] or book["s"].lower() == exhibitor_name.lower() or re.fullmatch(r"\d+", book["s"]):
                book.pop("s", None)
            if not book["g"]:
                del book["g"]
            if book["c"] is None or (book["f"] is not None and book["c"] < book["f"]):
                book.pop("c")
            if book["f"] is None:
                book.pop("f")  # a list with only cover prices: the fair price is unknown
            if book.get("f", book.get("c", 0)) < 1:
                continue
            books.append(book)
    return books


def text_after_isbn_by_line(plain_text: str) -> dict[str, str]:
    lines = {}
    for line in plain_text.split("\n"):
        match = re.match(r"\s*(?:EAN:?\s*|ISBN13:\s*)?(97[89][\d\-]{10,16})\s*(.*)", line)
        if match:
            lines.setdefault(re.sub(r"\D", "", match.group(1))[:13], match.group(2))
    return lines


def repair_truncated_names(books: list[dict], publishers: list[Publisher], parsed_by_index: dict[int, ParsedPriceList]) -> int:
    """Table cells cut long author and imprint names; the raw text line still has them whole."""
    line_cache: dict[int, dict[str, str]] = {}
    repaired = 0
    for book in books:
        isbn = isbn_of_book_id(book["i"])
        if not isbn or "a" not in book or book["x"] not in parsed_by_index:
            continue
        if book["x"] not in line_cache:
            line_cache[book["x"]] = text_after_isbn_by_line(parsed_by_index[book["x"]].plain_text)
        line = SPREADSHEET_ESCAPE_CODE.sub(" ", EDITION_BEFORE_TITLE.sub("", line_cache[book["x"]].get(isbn, "")))
        if not line or not line.startswith(book["t"]):
            continue
        after_title = line[len(book["t"]):]
        money = MONEY_IN_TEXT.search(after_title)
        segment = (after_title[:money.start()] if money else after_title).strip()
        author = book["a"]
        if len(author) < 4 or not segment.startswith(author) or len(segment) <= len(author):
            continue

        exhibitor_name = publishers[book["x"]].name
        cut = None
        for name in filter(None, [without_stray_letters(book.get("s", "")), exhibitor_name]):
            position = segment.lower().find(name.lower()[:10], len(author) - 2)
            if position > 0:
                cut = position if cut is None else min(cut, position)
        subject_start = (book.get("g") or "").lower()[:8]
        if subject_start:
            position = segment.lower().find(subject_start, len(author) - 2)
            if position > 0:
                cut = position if cut is None else min(cut, position)

        full_author = without_quantity_closed_by_a_parenthesis(segment[:cut] if cut is not None else segment)
        full_author = re.sub(r"(\s+\d+)+\s*$", "", full_author)
        full_author = re.sub(r"\s+[A-Za-z]$", "", full_author.strip()).strip(" ,;")
        publisher_words = {word.lower() for word in re.findall(r"\w+", exhibitor_name + " " + (book.get("s") or "")) if len(word) >= 3}
        tokens = full_author.split()
        while len(tokens) > 1 and tokens[-1].lower().strip(".,;") in publisher_words and tokens[-1].lower() not in author.lower().split():
            tokens.pop()
        full_author = re.sub(r"(?<=[a-zà-ú])\d+$", "", " ".join(tokens))
        if len(author) < len(full_author) < len(author) + 40:
            book["a"] = full_author
            repaired += 1

        if cut is not None and book.get("s"):
            rest = re.sub(r"(\s+\d+(?:[.,]\d+)?)+\s*$", "", segment[cut:]).strip(" ,;")
            truncated = without_stray_letters(book["s"])
            cut_mid_word = len(rest) > len(truncated) and rest[len(truncated)].isalnum()
            if rest.lower().startswith(truncated.lower()) and cut_mid_word and len(rest) <= len(truncated) + 15:
                book["s"] = rest
    normalize_imprints(books, publishers)
    return repaired


def normalize_imprints(books: list[dict], publishers: list[Publisher]) -> None:
    for book in books:
        if book.get("s"):
            book["s"] = without_stray_letters(book["s"])

    frequent_imprints = collections.defaultdict(collections.Counter)
    for book in books:
        if book.get("s"):
            frequent_imprints[book["x"]][book["s"]] += 1

    for book in books:
        imprint = book.get("s")
        if not imprint:
            continue
        exhibitor_name = publishers[book["x"]].name
        # A common imprint cut short ("VALER EDITOR") or with a glued extra first letter ("SCOMPANHIA DAS LETRAS").
        own_count = frequent_imprints[book["x"]][imprint]
        for candidate, count in frequent_imprints[book["x"]].most_common():
            if count < 3 or count <= own_count or candidate == imprint:
                continue
            if candidate.lower().startswith(imprint.lower()) or (len(imprint) > 1 and candidate.lower().startswith(imprint[1:].lower())):
                imprint = candidate
                break
        if not re.search(r"[A-Za-zÀ-ÿ]{2,}", imprint) or imprint_repeats_exhibitor(imprint, exhibitor_name) or imprint_repeats_exhibitor(imprint[1:], exhibitor_name):
            book.pop("s")
        else:
            book["s"] = imprint


def money_value(text: str) -> float:
    return float(text.replace(".", "").replace(",", "."))


def complete_prices_from_isbn_lines(books: list[dict], parsed_by_index: dict[int, ParsedPriceList]) -> None:
    """A reader that finds one price cannot tell cover from fair price; the PDF line of the same ISBN shows both."""
    line_cache: dict[int, dict[str, str]] = {}
    for book in books:
        isbn = isbn_of_book_id(book["i"])
        if "c" in book or not isbn or book["x"] not in parsed_by_index:
            continue
        if book["x"] not in line_cache:
            line_cache[book["x"]] = text_after_isbn_by_line(parsed_by_index[book["x"]].plain_text)
        prices_on_line = [money_value(text) for text in MONEY_ON_ISBN_LINE.findall(line_cache[book["x"]].get(isbn, ""))]
        if len(prices_on_line) != 2 or book["f"] not in prices_on_line:
            continue
        cover, fair = max(prices_on_line), min(prices_on_line)
        if LOWEST_FAIR_SHARE_OF_COVER * cover <= fair < cover:
            book["c"], book["f"] = cover, fair


def give_each_exhibitor_its_own_id(books: list[dict], publishers: list[Publisher], names_in_old_ids: dict[str, list[str]]) -> None:
    """The same ISBN at two stands is two entries with different prices. The suffix comes from the publisher key, so it depends neither
    on list order nor on the publisher's name, and the entry keeps the ids it had under each old name of its publisher."""
    exhibitors_by_book_id = collections.defaultdict(set)
    for book in books:
        exhibitors_by_book_id[book["i"]].add(book["x"])
    for book in books:
        if len(exhibitors_by_book_id[book["i"]]) > 1:
            key = publisher_key(publishers[book["x"]])
            isbn = book["i"]
            book["i"] = f"{isbn}-{exhibitor_suffix(key)}"
            old_ids = {f"{isbn}-{exhibitor_suffix(name)}" for name in names_in_old_ids.get(key, [])} - {book["i"]}
            if old_ids:
                book["o"] = sorted(set(book.get("o", [])) | old_ids)


def drop_synopses_used_as_genre(books: list[dict]) -> None:
    """Some publishers fill the subject column with a synopsis: almost every value is long and different from the others. A list of
    tags is long and different from book to book too, but each tag is a genre, so it stays."""
    subjects_by_exhibitor = collections.defaultdict(list)
    for book in books:
        if book.get("g"):
            subjects_by_exhibitor[book["x"]].append(book["g"])
    exhibitors_with_synopses = {
        exhibitor for exhibitor, subjects in subjects_by_exhibitor.items()
        if len(subjects) >= 5
        and len(set(subjects)) >= SYNOPSIS_SHARE_OF_SUBJECTS * len(subjects)
        and sum(1 for subject in subjects if len(subject) >= SYNOPSIS_MINIMUM_LENGTH and not is_list_of_tags(subject)) >= SYNOPSIS_SHARE_OF_SUBJECTS * len(subjects)
    }
    for book in books:
        if book["x"] in exhibitors_with_synopses:
            book.pop("g", None)


def event_summary(event: EventDetails) -> dict:
    summary = {"edicao": event.edition, "nome": event.name, "periodo": event.period}
    year = edition_year(event.edition)
    if year:
        summary["ano"] = year
    dates = period_dates(event.period, year)
    if dates:
        summary["inicio"], summary["fim"] = dates[0].isoformat(), dates[1].isoformat()
    return summary


def exhibitor_entry(publisher: Publisher, parsed: ParsedPriceList | None) -> dict:
    """The site links each publisher to its price list on the official site and repeats any notice about that list."""
    entry = {"nome": publisher.name, "site": publisher.site}
    if publisher.price_list_url.startswith("https://"):
        entry["lista"] = publisher.price_list_url
    if parsed is not None and parsed.notice:
        entry["aviso"] = parsed.notice
    return entry


def build_catalog(
    event: EventDetails, publishers: list[Publisher], parsed_by_index: dict[int, ParsedPriceList], generated_at: str,
    names_in_old_ids: dict[str, list[str]] | None = None,
) -> dict:
    names_in_old_ids = names_in_old_ids or {}
    books = catalog_books(publishers, parsed_by_index, names_in_old_ids)
    repair_truncated_names(books, publishers, parsed_by_index)
    complete_prices_from_isbn_lines(books, parsed_by_index)
    give_each_exhibitor_its_own_id(books, publishers, names_in_old_ids)
    drop_synopses_used_as_genre(books)
    return {
        "evento": event_summary(event),
        "geradoEm": generated_at,
        "expositores": [exhibitor_entry(publisher, parsed_by_index.get(index)) for index, publisher in enumerate(publishers)],
        "livros": books,
    }


def same_content(first: dict, second: dict) -> bool:
    keys = ("evento", "expositores", "livros")
    return all(first.get(key) == second.get(key) for key in keys)
