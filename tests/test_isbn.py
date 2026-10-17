import pytest

from festa_do_livro.isbn import is_valid_isbn, isbn_of_book_id


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
