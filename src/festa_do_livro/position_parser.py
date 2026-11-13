"""Reads price lists whose PDF has no table cells, using where each piece of text sits on the page."""
import collections
import re
import statistics

from .text_helpers import without_accents_lowercase

ROW_START = re.compile(r"^(?:ean:?|isbn13:?)?\s*(97[89][\d\-\s]{10,17}|\d{10}\b)", re.I)
MONEY = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2}|\d{1,3} \d{2},\d{2}|\d+,\d)")
PRICE_WITH_OR_WITHOUT_CENTS = re.compile(r"(?:R\$\s*)?\d{1,4}(?:,\d{1,2})?")
PRICE_LABEL = re.compile(r"preco|valor")
# Pages, years and stall numbers never have cents, so a few prices like "44,9" among "80" and "40" are enough (Letra Selvagem).
SHARE_WITH_CENTS_IN_A_PRICE_COLUMN = 0.05
HEADER_WORDS = {
    "isbn", "titulo", "autor", "editora", "assunto", "url_livro", "url livro", "url", "preco de", "capa",
    "preco com", "desconto", "preco de capa", "preco com desconto", "autor(es)", "selo", "paginas", "prc.venda", "por", "%",
}


def money_values(text: str) -> list[float]:
    return [float(value.replace(" ", "").replace(".", "").replace(",", ".")) for value in MONEY.findall(text)]


def price_values(text: str) -> list[float]:
    """Values in a column already known to hold prices, where some lists drop the cents ("75" next to "37,5")."""
    whole_number = re.fullmatch(r"(?:R\$\s*)?(\d{1,4})", text.strip())
    return money_values(text) or ([float(whole_number.group(1))] if whole_number else [])


def header_spans(pages: list[list[dict]]) -> list[dict]:
    """The header row, from left to right: the spans level with the first one that starts with ISBN, EAN or código."""
    for spans in pages[:2]:
        for span in spans:
            if without_accents_lowercase(span["text"]).startswith(("isbn", "ean", "codigo")):
                return sorted((other for other in spans if abs(other["middle"] - span["middle"]) < 14), key=lambda other: other["left"])
    return []


def header_roles(pages: list[list[dict]]) -> list[str]:
    roles = []
    for header_span in header_spans(pages):
        for word in re.split(r"\s+", without_accents_lowercase(header_span["text"])):
            role = None
            if word.startswith(("isbn", "ean")):
                role = "isbn"
            elif word.startswith(("titul", "nome", "livro")):
                role = "title"
            elif word.startswith("autor"):
                role = "author"
            elif word.startswith(("editora", "selo")):
                role = "imprint"
            elif word.startswith(("assunt", "area", "genero")):
                role = "subject"
            elif word.startswith("pagina"):
                role = "pages"
            elif word.startswith(("url", "endereco", "link")):
                role = "url"
            if role and role not in roles:
                roles.append(role)
    return roles


def price_labels_in_header(pages: list[list[dict]]) -> int:
    """How many prices the header announces: "Preço R$" and "Preço com desconto" are two."""
    header_text = " ".join(span["text"] for span in header_spans(pages))
    return len(PRICE_LABEL.findall(without_accents_lowercase(header_text)))


def is_isbn_missing_a_digit(digits: str) -> bool:
    """A row whose ISBN was typed with a digit missing ("978-658984119") is still a row; the catalog shows it without ISBN."""
    return len(digits) == 12 and digits.startswith(("978", "979"))


def isbn_continuation(spans: list[dict], anchor: dict, digits_so_far: str):
    """The second line of an ISBN that a narrow cell broke in two ("978-65-87955-" above "23-0")."""
    for span in spans:
        below = span["middle"] - anchor["middle"]
        if abs(span["left"] - anchor["left"]) < 4 and 3 < below < 15 and re.fullmatch(r"[\d\-]{1,8}", span["text"]):
            if len(digits_so_far + re.sub(r"\D", "", span["text"])) == 13:
                return span
    return None


def parse_by_position(pages: list[list[dict]]) -> list[dict]:
    roles = header_roles(pages)

    row_anchors = []
    isbn_endings = set()
    for page_index, spans in enumerate(pages):
        for span in spans:
            match = ROW_START.match(span["text"])
            if not match:
                continue
            digits = re.sub(r"\D", "", match.group(1))
            if len(digits) < 13 and match.group(1).rstrip().endswith("-"):
                ending = isbn_continuation(spans, span, digits)
                if ending:
                    digits += re.sub(r"\D", "", ending["text"])
                    isbn_endings.add(id(ending))
            if len(digits) >= 13:
                digits = digits[:13]
            if len(digits) in (10, 13) or is_isbn_missing_a_digit(digits):
                row_anchors.append((page_index, span["middle"], digits, span))
    if not row_anchors:
        return []

    left_edge_counts = collections.Counter()
    row_spans = []
    for position, (page_index, middle, isbn, anchor) in enumerate(row_anchors):
        previous = row_anchors[position - 1] if position > 0 and row_anchors[position - 1][0] == page_index else None
        following = row_anchors[position + 1] if position + 1 < len(row_anchors) and row_anchors[position + 1][0] == page_index else None
        top = (previous[1] + middle) / 2 if previous else middle - 8
        bottom = (following[1] + middle) / 2 if following else middle + 12
        spans = [
            span for span in pages[page_index]
            if top <= span["middle"] < bottom and span is not anchor and id(span) not in isbn_endings
            and without_accents_lowercase(span["text"]).strip(" _:") not in HEADER_WORDS
        ]
        text_after_isbn = ROW_START.sub("", anchor["text"], count=1).strip()
        if text_after_isbn:
            spans.append({"left": anchor["left"] + 1, "right": anchor["right"], "middle": anchor["middle"], "text": text_after_isbn, "glued": True})
        row_spans.append(spans)
        for span in spans:
            if not span.get("glued"):
                left_edge_counts[round(span["left"] / 3)] += 1

    row_count = len(row_anchors)
    frequent_edges = sorted(edge * 3 for edge, count in left_edge_counts.items() if count >= max(3, 0.15 * row_count))
    column_starts = []
    for edge in frequent_edges:
        if column_starts and edge - column_starts[-1] < 14:
            continue
        column_starts.append(edge)

    def column_of(left):
        found = None
        for column, start in enumerate(column_starts):
            if left >= start - 4:
                found = column
        return found

    texts_by_column = collections.defaultdict(list)
    right_edges_by_column = collections.defaultdict(list)
    for spans in row_spans:
        for span in spans:
            column = column_of(span["left"])
            if column is not None:
                texts_by_column[column].append(span["text"])
                right_edges_by_column[column].append(span["right"])

    kinds = {}
    for column in range(len(column_starts)):
        texts = texts_by_column[column]
        if not texts:
            kinds[column] = "unknown"
            continue
        share = lambda predicate: sum(1 for text in texts if predicate(text)) / len(texts)
        if share(lambda text: re.fullmatch(r"(R\$\s*)?[\d\.\s]+,\d{1,2}(\s*R\$)?|R\$", text.strip())) > 0.5:
            kinds[column] = "money"
        elif share(lambda text: PRICE_WITH_OR_WITHOUT_CENTS.fullmatch(text.strip())) > 0.9 and share(lambda text: "," in text) > SHARE_WITH_CENTS_IN_A_PRICE_COLUMN:
            kinds[column] = "money"
        elif share(lambda text: "http" in text or "www" in text) > 0.5:
            kinds[column] = "url"
        elif share(lambda text: "%" in text) > 0.5:
            kinds[column] = "percent"
        elif share(lambda text: re.fullmatch(r"\d{1,4}", text.strip())) > 0.6:
            kinds[column] = "number"
        else:
            kinds[column] = "text"

    money_columns = [column for column in range(len(column_starts)) if kinds[column] == "money"]
    # The header announces two prices but only one column has cents: the whole numbers right before it are the cover price (Nós).
    if len(money_columns) == 1 and kinds.get(money_columns[0] - 1) == "number" and price_labels_in_header(pages) >= 2:
        kinds[money_columns[0] - 1] = "money"

    text_columns = [column for column in range(len(column_starts)) if kinds[column] == "text"]
    money_columns = [column for column in range(len(column_starts)) if kinds[column] == "money"]
    money_right_edges = {column: statistics.median(right_edges_by_column[column]) for column in money_columns}

    def money_column_ending_at(span):
        """Prices are aligned to the right, so a longer one ("257" above "75") starts before its column does."""
        if not PRICE_WITH_OR_WITHOUT_CENTS.fullmatch(span["text"].strip()):
            return None
        return next((column for column, right in money_right_edges.items() if abs(span["right"] - right) < 3), None)

    def money_column_starting_near(span):
        """A price written at the left of its cell ("60" above "70" aligned to the right) sits closer to the start of its money
        column than to the start of the text column it falls in."""
        if not PRICE_WITH_OR_WITHOUT_CENTS.fullmatch(span["text"].strip()) or not column_starts:
            return None
        nearest = min(range(len(column_starts)), key=lambda column: abs(span["left"] - column_starts[column]))
        return nearest if kinds.get(nearest) == "money" else None

    first_money_column = min(money_columns) if money_columns else 99
    header_text_roles = [role for role in roles if role in ("title", "author", "imprint", "subject")]
    role_of_column = {}
    if len(header_text_roles) == len(text_columns):
        role_of_column.update(zip(text_columns, header_text_roles))
    else:
        before = [column for column in text_columns if column < first_money_column]
        after = [column for column in text_columns if column > first_money_column]
        role_of_column.update(zip(before, ["title", "author", "imprint", "extra", "extra"]))
        role_of_column.update({column: "subject" for column in after})
    for column in range(len(column_starts)):
        if kinds[column] == "url":
            role_of_column[column] = "url"

    books = []
    for (page_index, middle, isbn, anchor), spans in zip(row_anchors, row_spans):
        texts_by_role = collections.defaultdict(list)
        prices = []
        for span in sorted(spans, key=lambda span: (round(span["middle"]), span["left"])):
            if span.get("glued"):
                texts_by_role["glued"].append(span["text"])
                prices += money_values(span["text"])
                continue
            column = column_of(span["left"])
            if kinds.get(column) != "money":
                misaligned_money_column = money_column_ending_at(span)
                if misaligned_money_column is None:
                    misaligned_money_column = money_column_starting_near(span)
                if misaligned_money_column is not None:
                    column = misaligned_money_column
            if column is None:
                continue
            if kinds[column] == "money":
                prices += price_values(span["text"])
            elif column in role_of_column:
                texts_by_role[role_of_column[column]].append(span["text"])
        if not prices:
            prices = money_values(" ".join(span["text"] for span in spans))
        if not prices:
            continue
        joined = lambda role: " ".join(texts_by_role.get(role, [])).strip()
        books.append({
            "isbn": isbn,
            "title": joined("title") or joined("glued"),
            "author": joined("author"),
            "imprint": joined("imprint"),
            "subject": joined("subject"),
            "url": joined("url").replace(" ", ""),
            "cover_price": max(prices[:2]) if len(prices) >= 2 else None,
            "fair_price": min(prices[:2]),
        })
    return books
