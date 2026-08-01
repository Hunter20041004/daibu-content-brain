from groq import Groq

from daibu.llm import prompt
from daibu.llm.base import Idea, generate_and_parse
from daibu.models import Material


class GroqProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
    ) -> None:
        self.api_key = api_key
        self.model = model

    def generate_text(self, text: str) -> str:
        client = Groq(api_key=self.api_key)
        completion = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": text}],
        )
        return completion.choices[0].message.content or ""

    def generate_carousel_text(self, text: str) -> str:
        return self.generate_text(text)

    def generate_ideas(
        self,
        theme_name: str,
        materials: list[Material],
        n: int,
        avoid_titles: list[str] | None = None,
        content_kind: str = "general",
    ) -> list[Idea]:
        text = prompt.build(
            theme_name,
            materials,
            n,
            avoid_titles,
            content_kind,
        )
        return generate_and_parse(self.generate_text, text)
