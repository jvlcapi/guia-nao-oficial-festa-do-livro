"""ISBN check digits. A number that fails them is a typo or a spreadsheet artifact (9788580000000), not a book identifier."""
import re

ISBN_AT_START_OF_BOOK_ID = re.compile(r"^(\d{13}|\d{9}[\dXx])(?:-|$)")
ISBN_PRINTED_WITHOUT_ITS_CHECK_DIGIT = re.compile(r"\s*(97[89][\d\-]*-)\s*")
ISBN13_PREFIXES = ("978", "979")


def isbn13_check_digit(first_twelve_digits: str) -> str:
    weighted_sum = sum(int(digit) * (3 if position % 2 else 1) for position, digit in enumerate(first_twelve_digits))
    return str((10 - weighted_sum % 10) % 10)


def is_valid_isbn(digits: str) -> bool:
    """Ten digits that start like an ISBN-13 are an ISBN-13 cut after its tenth digit (Matrix 2026), which passes the ISBN-10 check
    one time in eleven by chance. An ISBN-10 that really starts that way comes from Nigeria (978) or Indonesia (979), and no list
    of the 27th or the 28th Festa had one."""
    if len(digits) == 13 and digits.isdigit():
        return isbn13_check_digit(digits[:12]) == digits[12]
    if len(digits) == 10 and digits.startswith(ISBN13_PREFIXES):
        return False
    if len(digits) == 10 and digits[:9].isdigit() and (digits[9].isdigit() or digits[9] in "Xx"):
        check_value = 10 if digits[9] in "Xx" else int(digits[9])
        weighted_sum = sum(int(digit) * (10 - position) for position, digit in enumerate(digits[:9]))
        return (weighted_sum + check_value) % 11 == 0
    return False


def isbn_with_restored_check_digit(printed: str) -> str:
    """Some lists print the ISBN without its last digit but keep the hyphen before it ("978-65-81555-00-", Miolo Mole). That digit
    is the check digit, which the other twelve decide, so the ISBN comes back whole. Without the hyphen at the end, as in a typo
    that dropped a digit in the middle ("978-658984119", Letra Selvagem), the missing digit could be any of them."""
    match = ISBN_PRINTED_WITHOUT_ITS_CHECK_DIGIT.fullmatch(printed)
    digits = re.sub(r"\D", "", match.group(1)) if match else ""
    return digits + isbn13_check_digit(digits) if len(digits) == 12 else ""


def isbn_of_book_id(book_id: str) -> str:
    """Catalog ids are the ISBN, the ISBN plus an exhibitor suffix when two exhibitors sell it, or "x" plus a hash when there is no ISBN."""
    match = ISBN_AT_START_OF_BOOK_ID.match(book_id)
    return match.group(1) if match else ""
