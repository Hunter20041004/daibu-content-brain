"""Rules for editing a per-idea pack of verified sources."""

from daibu.cards.schema import VerifiedSource, validate_sources

MAX_SOURCES = 8


def next_source_id(pack: tuple[VerifiedSource, ...]) -> str:
    used = {source.source_id for source in pack}
    for number in range(1, MAX_SOURCES + 1):
        candidate = f"S{number}"
        if candidate not in used:
            return candidate
    raise ValueError("每則題目最多 8 筆來源")


def remove(
    pack: tuple[VerifiedSource, ...],
    source_id: str,
) -> tuple[VerifiedSource, ...]:
    return tuple(source for source in pack if source.source_id != source_id)


def add(
    pack: tuple[VerifiedSource, ...],
    publisher: str,
    published_at: str,
    url: str,
    excerpt: str,
) -> tuple[VerifiedSource, ...]:
    if len(pack) >= MAX_SOURCES:
        raise ValueError("每則題目最多 8 筆來源")

    fields = (
        ("出版方", publisher),
        ("日期", published_at),
        ("網址", url),
        ("引文", excerpt),
    )
    for label, value in fields:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"請填{label}")

    updated = pack + (
        VerifiedSource(
            next_source_id(pack),
            publisher.strip(),
            published_at.strip(),
            url.strip(),
            excerpt.strip(),
        ),
    )
    validate_sources(updated)
    return updated
