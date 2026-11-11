import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .fair_site import HttpResponse, Publisher, http_get

NO_PRICE_LIST_YET = "sem lista de preços"


@dataclass(frozen=True)
class DownloadResult:
    publisher_index: int
    publisher: Publisher
    path: Optional[Path]
    problem: str = ""


def cached_file_name(publisher_index: int, url: str) -> str:
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    return f"{publisher_index:03d}-{digest}.pdf"


def download_price_lists(
    publishers: list[Publisher],
    cache_directory: Path,
    fetch: Callable[[str], HttpResponse] = http_get,
    parallel_downloads: int = 8,
) -> list[DownloadResult]:
    cache_directory = Path(cache_directory)
    cache_directory.mkdir(parents=True, exist_ok=True)

    def download_one(indexed_publisher):
        publisher_index, publisher = indexed_publisher
        if not publisher.price_list_url:
            return DownloadResult(publisher_index, publisher, None, NO_PRICE_LIST_YET)
        target = cache_directory / cached_file_name(publisher_index, publisher.price_list_url)
        if target.exists() and target.stat().st_size > 0:
            return DownloadResult(publisher_index, publisher, target)
        try:
            response = fetch(publisher.price_list_url)
        except OSError as error:
            return DownloadResult(publisher_index, publisher, None, f"falha de rede: {error}")
        if response.status != 200 or not response.body.startswith(b"%PDF"):
            return DownloadResult(publisher_index, publisher, None, f"resposta inesperada: {response.status} {response.content_type}")
        target.write_bytes(response.body)
        return DownloadResult(publisher_index, publisher, target)

    with ThreadPoolExecutor(parallel_downloads) as executor:
        return list(executor.map(download_one, enumerate(publishers)))
