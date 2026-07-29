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
    material = Material(
        "官方更新",
        "https://example.com/update",
        "一段公開摘要",
    )

    text = prompt.build(
        theme_name="AI 近期大事",
        materials=[material],
        n=2,
    )

    assert "AI 近期大事" in text
    assert "官方更新" in text and material.url in text
    assert "2" in text
    assert "文組視角" in text and "JSON" in text


def test_build_prompt_no_longer_mentions_gate_line():
    text = prompt.build(
        theme_name="AI 近期大事",
        materials=[],
        n=2,
    )

    assert "守門線" not in text
    assert "gate_score" not in text


def test_build_prompt_asks_ai_to_avoid_rejected_titles():
    text = prompt.build(
        theme_name="AI 近期大事",
        materials=[],
        n=2,
        avoid_titles=["舊題"],
    )

    assert "舊題" in text


def test_build_prompt_omits_avoid_section_when_nothing_rejected():
    text = prompt.build(
        theme_name="AI 近期大事",
        materials=[],
        n=2,
        avoid_titles=[],
    )

    assert "請避開" not in text


def test_gemini_provider_maps_model_response(monkeypatch):
    provider = GeminiProvider(api_key="fake")
    prompts = []

    def fake_generate(text):
        prompts.append(text)
        return (
            '[{"title":"題目","angle":"角度","gate_score":90,'
            '"gate_reason":"理由","source_url":""}]'
        )

    monkeypatch.setattr(
        provider,
        "_generate_text",
        fake_generate,
    )

    ideas = provider.generate_ideas(
        "新創介紹",
        [],
        1,
        avoid_titles=["舊題"],
    )

    assert [idea.title for idea in ideas] == ["題目"]
    assert "舊題" in prompts[0]


def test_groq_provider_maps_model_response(monkeypatch):
    provider = GroqProvider(api_key="fake")
    prompts = []

    def fake_generate(text):
        prompts.append(text)
        return (
            '[{"title":"Groq 題目","angle":"角度","gate_score":85,'
            '"gate_reason":"理由","source_url":""}]'
        )

    monkeypatch.setattr(
        provider,
        "_generate_text",
        fake_generate,
    )

    ideas = provider.generate_ideas(
        "新創介紹",
        [],
        1,
        avoid_titles=["舊題"],
    )

    assert [idea.title for idea in ideas] == ["Groq 題目"]
    assert "舊題" in prompts[0]


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
        [],
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
            [],
            1,
        )

    assert error.value.raw_response == "第二次仍壞掉"


def test_parse_ideas_reads_company_and_excerpt():
    raw = """[
      {"company": "ElevenLabs",
       "title": "讓文字開口說話",
       "angle": "配音成本被改寫",
       "source_url": "https://example.com/a",
       "source_excerpt": "2022 年於倫敦成立。"}
    ]"""

    ideas = prompt.parse_ideas(raw)

    assert ideas[0].company == "ElevenLabs"
    assert ideas[0].source_excerpt == "2022 年於倫敦成立。"


def test_build_prompt_demands_a_named_company():
    materials = [
        Material(title="t", url="https://example.com/a", snippet="s")
    ]

    text = prompt.build("AI 新創介紹", materials, 3)

    assert "公司" in text
    assert "company" in text
    assert "source_excerpt" in text
    # 明確禁止產出無公司名的通用觀點文
    assert "沒有公司名" in text
    # 寧可少產也不要湊數
    assert "寧可少產" in text
