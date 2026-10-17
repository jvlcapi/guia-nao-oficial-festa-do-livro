"""Year and dates of an edition. The official API has no date field, only a sentence such as "entre os dias 26 e 30 de novembro"."""
import re
from datetime import date
from typing import Optional

from .text_helpers import without_accents_lowercase

FIRST_EDITION_YEAR = 1999
MONTH_NUMBERS = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
DAY_OR_MONTH = re.compile(r"\b(\d{1,2})\b|\b(" + "|".join(MONTH_NUMBERS) + r")\b")


def edition_year(edition: str) -> Optional[int]:
    """The official site says the Festa is held every year since 1999, the year of the 1st edition."""
    number = re.match(r"(\d+)-", edition or "")
    return FIRST_EDITION_YEAR + int(number.group(1)) - 1 if number else None


def period_dates(period: str, year: Optional[int]) -> Optional[tuple[date, date]]:
    """First and last day from "26 e 30 de novembro" or "29 de novembro a 3 de dezembro"."""
    if not year:
        return None
    days_waiting_for_month: list[int] = []
    days: list[date] = []
    for day_text, month_name in DAY_OR_MONTH.findall(without_accents_lowercase(period)):
        if day_text:
            days_waiting_for_month.append(int(day_text))
        elif days_waiting_for_month:
            try:
                days += [date(year, MONTH_NUMBERS[month_name], day) for day in days_waiting_for_month]
            except ValueError:
                return None
            days_waiting_for_month = []
    return (days[0], days[-1]) if days else None
