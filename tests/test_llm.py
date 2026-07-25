import pytest

from daibu.llm import base, prompt
from daibu.llm.gemini import GeminiProvider
from daibu.llm.groq import GroqProvider
from daibu.models import Material


def test_parse_ideas_tolerates_codefence():
    raw = """```json
    [{"title":"NotebookLM 整理期中報告","angle":"文組視角拆解",
      "source_url":"https://x.com/a"}]
    ```"""

    ideas = prompt.parse_ideas(raw)

    assert len(ideas) == 1
    assert ideas[0].title == "NotebookLM 整理期中報告"
    assert ideas[0].angle == "文組視角拆解"
    assert ideas[0].source_url == "https://x.com/a"


def test_parse_ideas_ignores_leftover_gate_fields():
    raw = """[
    {
      "title": "舊格式題目",
      "angle": "仍可解析",
      "gate_score": 88,
      "gate_reason": "已廢除欄位",
      "source_url": "https://example.com/legacy"
    }
    ]"""

    ideas = prompt.parse_ideas(raw)

    assert ideas[0].title == "舊格式題目"
    assert not hasattr(ideas[0], "gate_score")


def test_build_prompt_contains_product_context():
    gate_line = "怕 AI 的文組同學看完，會不會覺得原來我也可以？"
    material = Material(
        "官方更新",
        "https://example.com/update",
        "一段公開摘要",
    )

    text = prompt.build(
        theme_name="AI 近期大事",
        kind="timely",
        materials=[material],
        gate_line=gate_line,
        n=2,
    )

    assert "AI 近期大事" in text
    assert gate_line in text
    assert "官方更新" in text and material.url in text
    assert "2" in text
    assert "文組視角" in text and "JSON" in text


def test_gemini_provider_maps_model_response(monkeypatch):
    provider = GeminiProvider(api_key="fake")
    monkeypatch.setattr(
        provider,
        "_generate_text",
        lambda text: (
            '[{"title":"題目","angle":"角度","gate_score":90,'
            '"gate_reason":"理由","source_url":""}]'
        ),
    )

    ideas = provider.generate_ideas(
        "新創介紹",
        "evergreen",
        [],
        "守門線",
        1,
    )

    assert [idea.title for idea in ideas] == ["題目"]


def test_groq_provider_maps_model_response(monkeypatch):
    provider = GroqProvider(api_key="fake")
    monkeypatch.setattr(
        provider,
        "_generate_text",
        lambda text: (
            '[{"title":"Groq 題目","angle":"角度","gate_score":85,'
            '"gate_reason":"理由","source_url":""}]'
        ),
    )

    ideas = provider.generate_ideas(
        "新創介紹",
        "evergreen",
        [],
        "守門線",
        1,
    )

    assert [idea.title for idea in ideas] == ["Groq 題目"]


def test_get_provider_selects_configured_adapter():
    provider = base.get_provider(
        {
            "LLM_PROVIDER": "groq",
            "GROQ_API_KEY": "fake",
            "LLM_MODEL": "test-model",
        }
    )

    assert isinstance(provider, GroqProvider)
    assert provider.model == "test-model"


def test_provider_retries_once_after_unparseable_response(monkeypatch):
    provider = GeminiProvider(api_key="fake")
    responses = iter(
        [
            "不是 JSON",
            (
                '[{"title":"重試成功","angle":"角度","gate_score":80,'
                '"gate_reason":"理由","source_url":""}]'
            ),
        ]
    )
    calls = []

    def fake_generate(text):
        calls.append(text)
        return next(responses)

    monkeypatch.setattr(provider, "_generate_text", fake_generate)

    ideas = provider.generate_ideas(
        "新創介紹",
        "evergreen",
        [],
        "守門線",
        1,
    )

    assert [idea.title for idea in ideas] == ["重試成功"]
    assert len(calls) == 2


def test_provider_exposes_last_raw_response_after_retry_fails(monkeypatch):
    provider = GeminiProvider(api_key="fake")
    responses = iter(["第一次壞掉", "第二次仍壞掉"])
    monkeypatch.setattr(
        provider,
        "_generate_text",
        lambda text: next(responses),
    )

    with pytest.raises(base.LLMResponseError) as error:
        provider.generate_ideas(
            "新創介紹",
            "evergreen",
            [],
            "守門線",
            1,
        )

    assert error.value.raw_response == "第二次仍壞掉"
