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
from daibu.models import Material


CAROUSEL_RESPONSE_SCHEMA = {
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
                "enum": [
                    "cover",
                    "who",
                    "problem",
                    "how-ai",
                    "results",
                    "why-care",
                    "cta",
                ],
            },
            "heading": {"type": "string"},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["label", "text", "source_ids"],
                    "properties": {
                        "label": {"type": "string"},
                        "text": {"type": "string"},
                        "source_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "additionalProperties": False,
                },
            },
            "diagram": {
                "anyOf": [
                    {"type": "null"},
                    {
                        "type": "object",
                        "required": ["kind", "nodes"],
                        "properties": {
                            "kind": {"type": "string"},
                            "nodes": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": [
                                        "title",
                                        "text",
                                        "expression",
                                    ],
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
            },
        },
        "additionalProperties": False,
    },
}


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
