from datetime import date

import pytest

from festa_do_livro.fair_dates import edition_year, period_dates


@pytest.mark.parametrize("edition, year", [
    ("27-festa-do-livro-da-usp", 2025),
    ("28-festa-do-livro-da-usp", 2026),
    ("festa-do-livro-sem-numero", None),
])
def test_year_comes_from_the_edition_number(edition, year):
    assert edition_year(edition) == year


@pytest.mark.parametrize("period, year, expected", [
    ("26 e 30 de novembro", 2025, (date(2025, 11, 26), date(2025, 11, 30))),
    ("26 a 30 de novembro", 2025, (date(2025, 11, 26), date(2025, 11, 30))),
    ("29 de novembro a 3 de dezembro", 2026, (date(2026, 11, 29), date(2026, 12, 3))),
    ("29 de novembro e 3 de dezembro", 2026, (date(2026, 11, 29), date(2026, 12, 3))),
])
def test_first_and_last_day_of_the_fair(period, year, expected):
    assert period_dates(period, year) == expected


@pytest.mark.parametrize("period, year", [("", 2025), ("em breve", 2025), ("26 e 30 de novembro", None)])
def test_unreadable_period_has_no_dates(period, year):
    assert period_dates(period, year) is None
