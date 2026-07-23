import logging
from urllib.parse import urlparse

from daibu.fetch import rss, search
from daibu.models import Material, Source, Theme

logger = logging.getLogger(__name__)


def collect(theme: Theme, sources: list[Source]) -> list[Material]:
    if theme.kind == "evergreen":
        return []

    materials: list[Material] = []
    for source in sources:
        if (
            not source.enabled
            or source.layer not in theme.source_layers
        ):
            continue
        try:
            if source.fetch_type == "rss":
                fetched = rss.fetch(source.url, limit=10)
            elif source.fetch_type == "search":
                domain = urlparse(source.url).hostname
                if not domain:
                    raise ValueError("搜尋來源缺少有效網域")
                fetched = search.search(
                    theme.name,
                    allowed_domains=[domain],
                    limit=10,
                )
            else:
                continue
            materials.extend(fetched)
        except Exception as error:
            logger.warning("來源 %s 本次未取得：%s", source.name, error)
    return materials
