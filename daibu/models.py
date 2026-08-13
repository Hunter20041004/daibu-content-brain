from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    id: int | None
    name: str
    weekday: int
    source_ids: list[int]
    n_ideas: int
    content_kind: str = "general"


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
class CompanyLead:
    company: str
    description: str
    discovery_url: str
    profile_url: str = ""
    official_url: str = ""
    founded_year: int | None = None
    ownership_status: str = "unknown"
    batch_or_cohort: str = ""
    tags: tuple[str, ...] = ()
    published_at: str = ""
    source_name: str = ""


@dataclass(frozen=True)
class DiscoveryStats:
    fetched_by_source: tuple[tuple[str, int], ...] = ()
    filtered_non_ai: int = 0
    filtered_duplicate: int = 0
    filtered_status: int = 0
    matched_news: int = 0


@dataclass(frozen=True)
class DiscoveryResult:
    leads: tuple[CompanyLead, ...]
    warnings: tuple[str, ...] = ()
    stats: DiscoveryStats = DiscoveryStats()


@dataclass(frozen=True)
class SourceSuggestion:
    publisher: str
    published_at: str
    url: str
    excerpt: str


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
    company: str = ""
    source_excerpt: str = ""


@dataclass(frozen=True)
class EligibilityEvidence:
    claim: str
    source_url: str
    quote: str


@dataclass(frozen=True)
class CompanyEligibility:
    company_key: str
    company: str
    verdict: str
    founded_year: int | None
    ownership_status: str
    reason: str
    evidence: tuple[EligibilityEvidence, ...]
    checked_at: str
