import html
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable

USER_AGENT = "guia-nao-oficial-festa-do-livro/0.1 (+https://github.com/jvlcapi/guia-nao-oficial-festa-do-livro)"
CURRENT_EDITION_PATTERN = re.compile(r'const\s+event\s*=\s*"([^"]+)"')
ANY_EDITION_PATTERN = re.compile(r"\b(\d+-festa-do-livro[a-z0-9\-]*)")
PERIOD_PATTERN = re.compile(r"entre os dias ([^,.]+)", re.IGNORECASE)
PUBLISHER_LIST_READINGS = 3


class EditionNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class HttpResponse:
    status: int
    content_type: str
    body: bytes

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def is_json(self) -> bool:
        return self.status == 200 and "json" in self.content_type


@dataclass(frozen=True)
class EventDetails:
    edition: str
    name: str
    period: str


@dataclass(frozen=True)
class Publisher:
    name: str
    slug: str
    price_list_url: str
    site: str


def http_get(url: str, timeout_seconds: int = 60) -> HttpResponse:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return HttpResponse(response.status, response.headers.get("Content-Type", ""), response.read())
    except urllib.error.HTTPError as error:
        return HttpResponse(error.code, error.headers.get("Content-Type", ""), error.read())


class FairSite:
    def __init__(self, base_url: str, fetch: Callable[[str], HttpResponse] = http_get):
        self.base_url = base_url.rstrip("/")
        self.fetch = fetch

    def detect_current_edition(self) -> str:
        homepage = self.fetch(f"{self.base_url}/").text()
        declared = CURRENT_EDITION_PATTERN.search(homepage)
        if declared and declared.group(1).strip():
            return declared.group(1).strip()
        mentioned = ANY_EDITION_PATTERN.findall(homepage)
        if mentioned:
            return max(mentioned, key=lambda edition: int(edition.split("-")[0]))
        raise EditionNotFoundError(
            f"Não encontrei a edição atual na página inicial {self.base_url}/. "
            'Fixe a edição em settings.json (campo "edition") ou na variável FESTA_EDITION.'
        )

    def event_details(self, edition: str) -> EventDetails:
        response = self.fetch(f"{self.base_url}/api/v1/event?flag={edition}")
        if not response.is_json():
            raise EditionNotFoundError(
                f'A edição "{edition}" não existe no site (a API respondeu {response.status} {response.content_type}). '
                "Confira o identificador na página de editoras do site."
            )
        data = json.loads(response.body)["data"]
        description = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(data.get("description") or "")))
        period = PERIOD_PATTERN.search(description)
        return EventDetails(edition=edition, name=data.get("name", edition).strip(), period=period.group(1).strip() if period else "")

    def list_publishers(self, edition: str) -> list[Publisher]:
        """The site lists the publishers a page at a time. One that signs up while the pages are read moves the others one place, so
        one comes twice and another never comes (16/11/2026: Sisko twice, Seja Breve missing). The pages are read again until every
        page gives the same total and the reading has that many different publishers. A list that keeps changing gives its last
        reading without repeats, and the next update brings whoever is missing."""
        for _ in range(PUBLISHER_LIST_READINGS):
            publishers, totals = self.read_publisher_pages(edition)
            different_publishers = list(dict.fromkeys(publishers))
            if len(different_publishers) == len(publishers) and totals == {len(publishers)}:
                return publishers
        return different_publishers

    def read_publisher_pages(self, edition: str) -> tuple[list[Publisher], set[int | None]]:
        publishers: list[Publisher] = []
        totals: set[int | None] = set()
        page = 1
        while True:
            response = self.fetch(f"{self.base_url}/api/v1/event-publishers?page={page}&flag={edition}&filter=")
            if not response.is_json():
                raise EditionNotFoundError(f'A lista de editoras da edição "{edition}" não respondeu na página {page}.')
            payload = json.loads(response.body)
            for item in payload.get("data", []):
                publishers.append(Publisher(
                    name=(item.get("name") or "").strip(),
                    slug=(item.get("url") or "").strip(),
                    price_list_url=(item.get("price_list") or "").strip(),
                    site=(item.get("site") or "").strip(),
                ))
            totals.add(payload.get("meta", {}).get("total"))
            if page >= int(payload.get("meta", {}).get("last_page", page)):
                return publishers, totals
            page += 1
