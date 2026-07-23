import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from tavily import TavilyClient

from daibu.models import Material


def _raw_search(
    query: str, domains: list[str], limit: int
) -> dict[str, object]:
    load_dotenv()
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError(
            "缺少 TAVILY_API_KEY，請到設定頁填入搜尋 API key。"
        )
    client = TavilyClient(api_key=api_key)
    return client.search(
        query=query,
        include_domains=domains,
        max_results=limit,
    )


def _is_allowed(url: str, allowed_domains: list[str]) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return any(
        hostname == domain.lower()
        or hostname.endswith(f".{domain.lower()}")
        for domain in allowed_domains
    )


def search(
    query: str, allowed_domains: list[str], limit: int = 5
) -> list[Material]:
    response = _raw_search(query, allowed_domains, limit)
    results = response.get("results", [])
    return [
        Material(
            title=str(result.get("title", "")),
            url=str(result.get("url", "")),
            snippet=str(result.get("content", "")),
        )
        for result in results
        if _is_allowed(str(result.get("url", "")), allowed_domains)
    ][:limit]
