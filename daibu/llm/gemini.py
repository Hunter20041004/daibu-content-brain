import httpx
from google import genai
from google.genai import errors

from daibu.llm import prompt
from daibu.llm.base import (
    Idea,
    LLMQuotaError,
    LLMTimeoutError,
    generate_and_parse,
)
from daibu.cards import pages as carousel_pages
from daibu.models import Material


def _evidence_schema(required: bool) -> dict[str, object]:
    return {
        "type": "array",
        "minItems": 1 if required else 0,
        "maxItems": 3,
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


def _section_schema(label: str) -> dict[str, object]:
    may_be_unsourced = label in {
        "證據限制",
        "給讀者的問題",
        "互動邀請",
    }
    return {
        "type": "object",
        "required": ["label", "text", "evidence_quotes"],
        "properties": {
            "label": {"type": "string", "enum": [label]},
            "text": {"type": "string"},
            "evidence_quotes": _evidence_schema(not may_be_unsourced),
        },
        "additionalProperties": False,
    }


def _diagram_schema(page_type: str) -> dict[str, object]:
    kinds = carousel_pages.DIAGRAM_FOR.get(page_type)
    if kinds is None:
        return {"type": "null"}
    return {
        "type": "object",
        "required": ["kind", "nodes"],
        "properties": {
            "kind": {"type": "string", "enum": sorted(kinds)},
            "nodes": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
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
    page_schemas = []
    for page_no, page_type in enumerate(carousel_pages.PAGE_TYPES, start=1):
        labels = labels_by_page[page_type]
        page_schemas.append(
            {
                "type": "object",
                "required": [
                    "page_no",
                    "page_type",
                    "heading",
                    "sections",
                    "diagram",
                ],
                "properties": {
                    "page_no": {"type": "integer", "enum": [page_no]},
                    "page_type": {"type": "string", "enum": [page_type]},
                    "heading": {"type": "string"},
                    "sections": {
                        "type": "array",
                        "prefixItems": [
                            _section_schema(label) for label in labels
                        ],
                        "minItems": len(labels),
                        "maxItems": len(labels),
                    },
                    "diagram": _diagram_schema(page_type),
                },
                "additionalProperties": False,
            }
        )
    return {
        "type": "array",
        "prefixItems": page_schemas,
        "minItems": 7,
        "maxItems": 7,
    }


CAROUSEL_RESPONSE_SCHEMA = build_carousel_schema()


class GeminiProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.1-flash-lite",
        timeout_ms: int = 45_000,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_ms = timeout_ms

    def generate_text(self, text: str) -> str:
        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=text,
        )
        return response.text or ""

    def generate_carousel_text(self, text: str) -> str:
        client = genai.Client(
            api_key=self.api_key,
            http_options={"timeout": self.timeout_ms},
        )
        config = {
            "response_mime_type": "application/json",
            "response_json_schema": CAROUSEL_RESPONSE_SCHEMA,
        }
        if self.model.startswith("gemini-2.5"):
            config["thinking_config"] = {"thinking_budget": 0}
        elif self.model.startswith("gemini-3"):
            config["thinking_config"] = {"thinking_level": "medium"}
        try:
            response = client.models.generate_content(
                model=self.model,
                contents=text,
                config=config,
            )
        except httpx.TimeoutException as error:
            raise LLMTimeoutError(
                "免費 Gemini 回應超時，請稍後重試。"
            ) from error
        except errors.ServerError as error:
            if error.code != 504:
                raise
            raise LLMTimeoutError(
                "免費 Gemini 回應超時，請稍後重試。"
            ) from error
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
    ) -> list[Idea]:
        text = prompt.build(
            theme_name,
            materials,
            n,
            avoid_titles,
        )
        return generate_and_parse(self.generate_text, text)
