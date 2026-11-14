import pytest

from festa_do_livro.isbn import is_valid_isbn, isbn_of_book_id, isbn_with_restored_check_digit


@pytest.mark.parametrize("digits", ["9788535914849", "9786587955230", "0306406152", "080442957X"])
def test_valid_isbns(digits):
    assert is_valid_isbn(digits)


@pytest.mark.parametrize("digits, reason", [
    ("9788580000000", "planilha que gravou o ISBN em notação científica"),
    ("9786587955", "ISBN cortado no fim da linha"),
    ("9788535914840", "dígito verificador errado"),
    ("26004235", "código interno da editora"),
    ("", "sem ISBN"),
])
def test_invalid_isbns(digits, reason):
    assert not is_valid_isbn(digits), reason


@pytest.mark.parametrize("book_id, isbn", [
    ("9788535914849", "9788535914849"),
    ("9788575593646-3f2a1c", "9788575593646"),
    ("080442957X", "080442957X"),
    ("x2788d8d5f14e", ""),
])
def test_isbn_inside_a_book_id(book_id, isbn):
    assert isbn_of_book_id(book_id) == isbn


@pytest.mark.parametrize("printed, isbn", [
    ("978-65-81555-00-", "9786581555009"),
    ("978-65-88749-03-", "9786588749036"),
    (" 978-65-991456-2- ", "9786599145629"),
])
def test_isbn_printed_without_its_check_digit_gets_it_back(printed, isbn):
    assert isbn_with_restored_check_digit(printed) == isbn


@pytest.mark.parametrize("printed, reason", [
    ("978-658984119", "faltou um dígito no meio: sem o hífen do fim, o dígito que falta pode ser qualquer um"),
    ("978-65-81555-0-", "faltam dois dígitos"),
    ("123-45-67890-12-", "não começa com 978 nem 979"),
    ("978-65-81555-00-9", "ISBN inteiro"),
    ("978-65-81555-00- GAROTO AVATAR", "texto depois do hífen"),
    ("", "sem ISBN"),
])
def test_other_numbers_get_no_check_digit(printed, reason):
    assert isbn_with_restored_check_digit(printed) == "", reason
