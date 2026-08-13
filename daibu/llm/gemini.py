import httpx
from google import genai
from google.genai import errors

from daibu.llm import prompt
from daibu.llm.base import (
    DEFAULT_GOOGLE_FALLBACK_MODEL,
    Idea,
    LLMQuotaError,
    LLMTimeoutError,
    LLMUnavailableError,
    generate_and_parse,
)
from daibu.cards import pages as carousel_pages
from daibu.models import Material


def _evidence_schema() -> dict[str, object]:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["source_id", "quote"],
            "properties": {
                "source_id": {"type": "string"},
                "quote": {"type": "string"},
            },
            "additionalProperties": False,
        },
    }


def _section_schema(labels: list[str]) -> dict[str, object]:
    return {
        "type": "object",
        "required": ["label", "text", "evidence_quotes"],
        "properties": {
            "label": {"type": "string", "enum": labels},
            "text": {"type": "string"},
            "evidence_quotes": _evidence_schema(),
        },
        "additionalProperties": False,
    }


def _diagram_schema() -> dict[str, object]:
    kinds = sorted(
        {
            kind
            for allowed in carousel_pages.DIAGRAM_FOR.values()
            for kind in allowed
        }
    )
    return {
        "anyOf": [
            {"type": "null"},
            {
                "type": "object",
                "required": ["kind", "nodes"],
                "properties": {
                    "kind": {"type": "string", "enum": kinds},
                    "nodes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["title", "text", "expression"],
                            "properties": {
                                "title": {"type": "string"},
                                "text": {"type": "string"},
                                "expression": {"type": "string"},
                            },
                            "additionalProperties": False,
                        },
                    },
                },
                "additionalProperties": False,
            },
        ],
    }


def build_carousel_schema() -> dict[str, object]:
    labels_by_page = {
        **carousel_pages.SECTION_LABELS,
        "why-care": (
            "觀察訊號 1",
            "觀察訊號 2",
            "觀察訊號 3",
            "證據限制",
        ),
        "cta": ("收束結論", "給讀者的問題", "互動邀請"),
    }
    labels = list(
        dict.fromkeys(
            label
            for page_labels in labels_by_page.values()
            for label in page_labels
        )
    )
    return {
        "type": "array",
        "minItems": 7,
        "maxItems": 7,
        "items": {
            "type": "object",
            "required": [
                "page_no",
                "page_type",
                "heading",
                "sections",
                "diagram",
            ],
            "properties": {
                "page_no": {"type": "integer", "minimum": 1, "maximum": 7},
                "page_type": {
                    "type": "string",
                    "enum": list(carousel_pages.PAGE_TYPES),
                },
                "heading": {"type": "string"},
                "sections": {
                    "type": "array",
                    "items": _section_schema(labels),
                },
                "diagram": _diagram_schema(),
            },
            "additionalProperties": False,
        },
    }


CAROUSEL_RESPONSE_SCHEMA = build_carousel_schema()


class GeminiProvider:
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_GOOGLE_FALLBACK_MODEL,
        timeout_ms: int = 45_000,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_ms = timeout_ms

    def generate_text(self, text: str) -> str:
        return self._generate_content(text)

    def generate_carousel_text(self, text: str) -> str:
        config = {
            "response_mime_type": "application/json",
            "response_json_schema": CAROUSEL_RESPONSE_SCHEMA,
        }
        if self.model.startswith("gemini-2.5"):
            config["thinking_config"] = {"thinking_budget": 0}
        elif self.model.startswith("gemini-3"):
            config["thinking_config"] = {"thinking_level": "medium"}
        return self._generate_content(
            text,
            config=config,
            use_timeout=True,
        )

    def _generate_content(
        self,
        text: str,
        config: dict[str, object] | None = None,
        use_timeout: bool = False,
    ) -> str:
        client_kwargs: dict[str, object] = {"api_key": self.api_key}
        if use_timeout:
            client_kwargs["http_options"] = {"timeout": self.timeout_ms}
        client = genai.Client(**client_kwargs)
        request: dict[str, object] = {
            "model": self.model,
            "contents": text,
        }
        if config is not None:
            request["config"] = config
        try:
            response = client.models.generate_content(**request)
        except httpx.TimeoutException as error:
            raise LLMTimeoutError(
                "免費 Gemini 回應超時，請稍後重試。"
            ) from error
        except errors.ServerError as error:
            if error.code == 504:
                raise LLMTimeoutError(
                    "免費 Gemini 回應超時，請稍後重試。"
                ) from error
            if error.code == 503:
                raise LLMUnavailableError(
                    "Gemini 暫時繁忙，請稍後再試。"
                ) from error
            raise
        except errors.ClientError as error:
            if error.code != 429:
                raise
            raise LLMQuotaError(
                "Gemini 免費額度已用完，請稍後再試或切換 Groq。"
            ) from error
        return response.text or ""

    def generate_ideas(
        self,
        theme_name: str,
        materials: list[Material],
        n: int,
        avoid_titles: list[str] | None = None,
        content_kind: str = "general",
        avoid_companies: list[str] | None = None,
    ) -> list[Idea]:
        text = prompt.build(
            theme_name,
            materials,
            n,
            avoid_titles,
            content_kind,
            avoid_companies,
        )
        return generate_and_parse(self.generate_text, text)
