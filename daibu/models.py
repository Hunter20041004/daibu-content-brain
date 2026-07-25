from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    id: int | None
    name: str
    weekday: int
    source_ids: list[int]
    n_ideas: int


@dataclass(frozen=True)
class Source:
    id: int | None
    name: str
    url: str
    fetch_type: str
    enabled: bool


@dataclass(frozen=True)
class Material:
    title: str
    url: str
    snippet: str


@dataclass(frozen=True)
class StoredIdea:
    id: int
    theme_id: int | None
    title: str
    angle: str
    source_url: str
    status: str
    body: str
    created_at: str
    published_at: str | None
