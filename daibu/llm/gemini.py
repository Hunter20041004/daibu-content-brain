from google import genai

from daibu.llm import prompt
from daibu.llm.base import Idea, generate_and_parse
from daibu.models import Material


class GeminiProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
    ) -> None:
        self.api_key = api_key
        self.model = model

    def generate_text(self, text: str) -> str:
        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=text,
        )
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
