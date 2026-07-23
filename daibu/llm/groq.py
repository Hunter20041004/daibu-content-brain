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

    def _generate_text(self, text: str) -> str:
        client = Groq(api_key=self.api_key)
        completion = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": text}],
        )
        return completion.choices[0].message.content or ""

    def generate_ideas(
        self,
        theme_name: str,
        kind: str,
        materials: list[Material],
        gate_line: str,
        n: int,
    ) -> list[Idea]:
        text = prompt.build(
            theme_name,
            kind,
            materials,
            gate_line,
            n,
        )
        return generate_and_parse(self._generate_text, text)
