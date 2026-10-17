"""ISBN check digits. A number that fails them is a typo or a spreadsheet artifact (9788580000000), not a book identifier."""
import re

ISBN_AT_START_OF_BOOK_ID = re.compile(r"^(\d{13}|\d{9}[\dXx])(?:-|$)")


def is_valid_isbn(digits: str) -> bool:
    if len(digits) == 13 and digits.isdigit():
        weighted_sum = sum(int(digit) * (3 if position % 2 else 1) for position, digit in enumerate(digits[:12]))
        return (10 - weighted_sum % 10) % 10 == int(digits[12])
    if len(digits) == 10 and digits[:9].isdigit() and (digits[9].isdigit() or digits[9] in "Xx"):
        check_value = 10 if digits[9] in "Xx" else int(digits[9])
        weighted_sum = sum(int(digit) * (10 - position) for position, digit in enumerate(digits[:9]))
        return (weighted_sum + check_value) % 11 == 0
    return False


def isbn_of_book_id(book_id: str) -> str:
    """Catalog ids are the ISBN, the ISBN plus an exhibitor suffix when two exhibitors sell it, or "x" plus a hash when there is no ISBN."""
    match = ISBN_AT_START_OF_BOOK_ID.match(book_id)
    return match.group(1) if match else ""
