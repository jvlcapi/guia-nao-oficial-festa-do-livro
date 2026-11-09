import json

from festa_do_livro.__main__ import publishers_in_previous_edition


def write_catalog(data_directory, edition, exhibitors_with_books, exhibitors_without_books=0):
    folder = data_directory / edition
    folder.mkdir(parents=True)
    exhibitors = [{"nome": f"Editora {number}", "site": ""} for number in range(exhibitors_with_books + exhibitors_without_books)]
    books = [{"i": f"x{number:012d}", "t": "Livro", "f": 10.0, "x": number} for number in range(exhibitors_with_books)]
    (folder / "catalogo.json").write_text(json.dumps({"expositores": exhibitors, "livros": books}))


def test_counts_publishers_with_books_in_the_edition_before(tmp_path):
    write_catalog(tmp_path, "26-festa-do-livro-da-usp", 150)
    write_catalog(tmp_path, "27-festa-do-livro-da-usp", 191, exhibitors_without_books=1)
    write_catalog(tmp_path, "28-festa-do-livro-da-usp", 15)
    assert publishers_in_previous_edition(tmp_path, "28-festa-do-livro-da-usp") == 191


def test_first_edition_in_the_folder_has_no_previous_count(tmp_path):
    write_catalog(tmp_path, "28-festa-do-livro-da-usp", 15)
    assert publishers_in_previous_edition(tmp_path, "28-festa-do-livro-da-usp") is None
