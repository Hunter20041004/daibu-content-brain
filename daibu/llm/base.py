import os
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol

from dotenv import load_dotenv

from daibu.models import Material


@dataclass(frozen=True)
class Idea:
    title: str
    angle: str
    gate_score: int
    gate_reason: str
    source_url: str


class LLMResponseError(ValueError):
    def __init__(self, raw_response: str) -> None:
        super().__init__("LLM 連續兩次回傳無法解析的內容")
        self.raw_response = raw_response


class LLMProvider(Protocol):
    def generate_ideas(
        self,
        theme_name: str,
        kind: str,
        materials: list[Material],
        gate_line: str,
        n: int,
    ) -> list[Idea]: ...


def generate_and_parse(
    generate_text: Callable[[str], str],
    prompt_text: str,
) -> list[Idea]:
    last_raw_response = ""
    last_error: ValueError | None = None
    for _ in range(2):
        last_raw_response = generate_text(prompt_text)
        try:
            from daibu.llm import prompt

            return prompt.parse_ideas(last_raw_response)
        except ValueError as error:
            last_error = error

    raise LLMResponseError(last_raw_response) from last_error


def get_provider(config: Mapping[str, str]) -> LLMProvider:
    values = {str(key).upper(): str(value) for key, value in config.items()}
    provider_name = values.get("LLM_PROVIDER", "gemini").lower()
    model = values.get("LLM_MODEL")

    if provider_name == "gemini":
        from daibu.llm.gemini import GeminiProvider

        api_key = values.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "缺少 GEMINI_API_KEY，請到設定頁填入 LLM API key。"
            )
        return GeminiProvider(
            api_key=api_key,
            model=model or "gemini-2.5-flash",
        )

    if provider_name == "groq":
        from daibu.llm.groq import GroqProvider

        api_key = values.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "缺少 GROQ_API_KEY，請到設定頁填入 LLM API key。"
            )
        return GroqProvider(
            api_key=api_key,
            model=model or "llama-3.3-70b-versatile",
        )

    raise ValueError(f"不支援的 LLM provider：{provider_name}")


def get_provider_from_env() -> LLMProvider:
    load_dotenv()
    return get_provider(os.environ)
