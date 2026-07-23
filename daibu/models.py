from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    id: int | None
    name: str
    weekday: int
    kind: str
    source_layers: list[str]
    n_ideas: int


@dataclass(frozen=True)
class Source:
    id: int | None
    name: str
    url: str
    layer: str
    fetch_type: str
    enabled: bool


@dataclass(frozen=True)
class Material:
    title: str
    url: str
    snippet: str
