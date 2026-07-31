import httpx
import pytest
from google.genai import errors

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
        "generate_text",
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
        "generate_text",
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


def test_gemini_provider_defaults_to_current_flash_lite():
    provider = base.get_provider(
        {
            "LLM_PROVIDER": "gemini",
            "GEMINI_API_KEY": "fake",
        }
    )

    assert provider.model == "gemini-3.1-flash-lite"


def test_provider_exposes_public_text_generation_for_carousel_copy():
    provider = GeminiProvider(api_key="fake")

    assert callable(provider.generate_text)


def test_each_provider_exposes_carousel_generation():
    assert "generate_carousel_text" in base.LLMProvider.__dict__
    assert callable(GeminiProvider(api_key="fake").generate_carousel_text)
    assert callable(GroqProvider(api_key="fake").generate_carousel_text)


def test_gemini_carousel_generation_requests_json_schema(monkeypatch):
    calls = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            return type("Response", (), {"text": "[]"})()

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr("daibu.llm.gemini.genai.Client", FakeClient)

    provider = GeminiProvider(api_key="fake")
    provider.generate_carousel_text("輪播 prompt")

    config = calls[0]["config"]
    schema = config["response_json_schema"]
    assert config["response_mime_type"] == "application/json"
    assert config["thinking_config"] == {"thinking_level": "medium"}
    assert schema["minItems"] == schema["maxItems"] == 7
    page_schemas = schema["prefixItems"]
    assert [
        page["properties"]["page_type"]["enum"][0]
        for page in page_schemas
    ] == ["cover", "who", "problem", "how-ai", "results", "why-care", "cta"]
    assert [
        page["properties"]["page_no"]["enum"][0]
        for page in page_schemas
    ] == list(range(1, 8))
    first_section = page_schemas[0]["properties"]["sections"]["prefixItems"][0]
    assert set(first_section["required"]) == {
        "label",
        "text",
        "evidence_quotes",
    }
    assert first_section["properties"]["label"]["enum"] == ["一句話定位"]


def test_gemini_carousel_generation_uses_configured_timeout(monkeypatch):
    client_calls = []

    class FakeModels:
        def generate_content(self, **kwargs):
            return type("Response", (), {"text": "[]"})()

    class FakeClient:
        def __init__(self, **kwargs):
            client_calls.append(kwargs)
            self.models = FakeModels()

    monkeypatch.setattr("daibu.llm.gemini.genai.Client", FakeClient)

    provider = GeminiProvider(api_key="fake", timeout_ms=12_345)
    provider.generate_carousel_text("輪播 prompt")

    assert client_calls[0]["http_options"]["timeout"] == 12_345


def test_gemini_carousel_timeout_has_a_product_error(monkeypatch):
    class FakeModels:
        def generate_content(self, **kwargs):
            raise httpx.ReadTimeout("transport detail")

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr("daibu.llm.gemini.genai.Client", FakeClient)

    provider = GeminiProvider(api_key="fake")

    with pytest.raises(base.LLMTimeoutError, match="Gemini 回應超時"):
        provider.generate_carousel_text("輪播 prompt")


def test_gemini_deadline_exceeded_has_a_product_error(monkeypatch):
    class FakeModels:
        def generate_content(self, **kwargs):
            raise errors.ServerError(
                504,
                {
                    "error": {
                        "status": "DEADLINE_EXCEEDED",
                        "message": "The request timed out.",
                    }
                },
            )

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr("daibu.llm.gemini.genai.Client", FakeClient)

    provider = GeminiProvider(api_key="fake")

    with pytest.raises(base.LLMTimeoutError, match="Gemini 回應超時"):
        provider.generate_carousel_text("輪播 prompt")


def test_gemini_free_quota_exhaustion_has_a_product_error(monkeypatch):
    class FakeModels:
        def generate_content(self, **kwargs):
            raise errors.ClientError(
                429,
                {
                    "error": {
                        "status": "RESOURCE_EXHAUSTED",
                        "message": "Quota exceeded.",
                    }
                },
            )

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr("daibu.llm.gemini.genai.Client", FakeClient)

    provider = GeminiProvider(api_key="fake")

    with pytest.raises(base.LLMQuotaError, match="免費額度已用完"):
        provider.generate_carousel_text("輪播 prompt")


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

    monkeypatch.setattr(provider, "generate_text", fake_generate)

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
        "generate_text",
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


def test_carousel_prompt_limits_copy_to_verified_sources():
    from tests.card_fixtures import verified_sources

    text = prompt.build_carousel(
        "ElevenLabs",
        "t",
        "a",
        verified_sources(),
    )

    assert "140–220 字是建議目標" in text
    assert "不為湊字數" in text
    assert "ai-infrastructure" in text
    assert "來源中沒有的公司、人物、客戶、數字或能力" in text
    assert "目前公開證據有限" in text
    assert "evidence_quotes" in text
    assert "quote 必須從對應 excerpt 逐字抄錄" in text


def test_carousel_prompt_defers_exact_shape_to_the_api_schema():
    from tests.card_fixtures import verified_sources

    text = prompt.build_carousel(
        "ElevenLabs",
        "t",
        "a",
        verified_sources(),
    )

    assert "精確欄位、頁序與區塊名稱由 API 提供的 JSON Schema 約束" in text
    assert '"page_no": 1, "page_type": "cover"' not in text
    assert '"cover": ["一句話定位", "產業分類"]' not in text


def test_carousel_schema_fixes_the_why_care_label_sequence():
    from daibu.llm.gemini import build_carousel_schema

    why_care = build_carousel_schema()["prefixItems"][5]
    sections = why_care["properties"]["sections"]["prefixItems"]

    assert [item["properties"]["label"]["enum"][0] for item in sections] == [
        "觀察訊號 1",
        "觀察訊號 2",
        "觀察訊號 3",
        "證據限制",
    ]


def test_carousel_prompt_checks_company_subject_and_verbatim_evidence():
    from tests.card_fixtures import verified_sources

    text = prompt.build_carousel(
        "ElevenLabs",
        "t",
        "a",
        verified_sources(),
    )

    assert "第 4–7 頁的 heading" in text
    assert "ElevenLabs" in text
    assert "事實都有逐字引句" in text


def test_carousel_prompt_does_not_force_per_section_length_targets():
    from tests.card_fixtures import verified_sources

    text = prompt.build_carousel(
        "ElevenLabs",
        "t",
        "a",
        verified_sources(),
    )

    assert "140–220 字是建議目標" in text
    assert "每段 85–95 字" not in text
    assert "每段 55–65 字" not in text


def test_carousel_prompt_has_no_second_call_repair_builder():
    assert not hasattr(prompt, "build_carousel_repair")


def test_carousel_parser_builds_a_validated_sourced_draft():
    from daibu.cards import pages
    from tests.card_fixtures import (
        structured_llm_response,
        verified_sources,
    )

    draft = prompt.parse_carousel(
        structured_llm_response(),
        verified_sources(),
    )

    assert [page.page_type for page in draft.pages] == list(pages.PAGE_TYPES)
    assert draft.pages[3].diagram.kind == "ai-generate"
    assert draft.pages[0].source_label.startswith("來源：ElevenLabs")


def test_carousel_decoder_reports_missing_required_page_fields():
    from tests.card_fixtures import verified_sources

    with pytest.raises(ValueError, match="page_no"):
        prompt.decode_carousel(
            '[{"page_type": "cover"}]',
            verified_sources(),
        )


def test_carousel_decoder_reports_non_list_sections():
    from tests.card_fixtures import verified_sources

    raw = (
        '[{"page_no": 1, "page_type": "cover", "heading": "標題",'
        ' "sections": null, "diagram": null}]'
    )

    with pytest.raises(ValueError, match="sections 必須是陣列"):
        prompt.decode_carousel(raw, verified_sources())


def test_carousel_decoder_reports_non_list_diagram_nodes():
    from tests.card_fixtures import verified_sources

    raw = (
        '[{"page_no": 3, "page_type": "problem", "heading": "標題",'
        ' "sections": [],'
        ' "diagram": {"kind": "problem-chain", "nodes": null}}]'
    )

    with pytest.raises(ValueError, match="diagram.nodes 必須是陣列"):
        prompt.decode_carousel(raw, verified_sources())


def test_carousel_decoder_reports_non_object_sections():
    from tests.card_fixtures import verified_sources

    raw = (
        '[{"page_no": 1, "page_type": "cover", "heading": "標題",'
        ' "sections": [null], "diagram": null}]'
    )

    with pytest.raises(ValueError, match="section 必須是物件"):
        prompt.decode_carousel(raw, verified_sources())


def test_carousel_decoder_reports_missing_section_fields():
    from tests.card_fixtures import verified_sources

    raw = (
        '[{"page_no": 1, "page_type": "cover", "heading": "標題",'
        ' "sections": [{"label": "一句話定位"}], "diagram": null}]'
    )

    with pytest.raises(ValueError, match="section 缺少必要欄位：text"):
        prompt.decode_carousel(raw, verified_sources())


def test_carousel_decoder_reports_non_list_section_source_ids():
    from tests.card_fixtures import verified_sources

    raw = (
        '[{"page_no": 1, "page_type": "cover", "heading": "標題",'
        ' "sections": [{"label": "一句話定位", "text": "內容",'
        ' "source_ids": null}], "diagram": null}]'
    )

    with pytest.raises(ValueError, match="section.source_ids 必須是陣列"):
        prompt.decode_carousel(raw, verified_sources())


def test_carousel_decoder_rejects_non_string_source_ids():
    from dataclasses import replace

    from tests.card_fixtures import verified_sources

    sources = verified_sources()
    numeric_id_source = replace(sources[0], source_id="1")
    raw = (
        '[{"page_no": 1, "page_type": "cover", "heading": "標題",'
        ' "sections": [{"label": "一句話定位", "text": "內容",'
        ' "source_ids": [1]}], "diagram": null}]'
    )

    with pytest.raises(ValueError, match="source_ids 每一項都必須是非空字串"):
        prompt.decode_carousel(
            raw,
            (numeric_id_source, *sources[1:]),
        )


def test_carousel_decoder_reports_missing_section_source_ids():
    from tests.card_fixtures import verified_sources

    raw = (
        '[{"page_no": 7, "page_type": "cta", "heading": "標題",'
        ' "sections": [{"label": "互動邀請", "text": "歡迎追蹤"}],'
        ' "diagram": null}]'
    )

    with pytest.raises(ValueError, match="section 缺少必要欄位：source_ids"):
        prompt.decode_carousel(raw, verified_sources())


def test_carousel_decoder_reports_non_integer_page_numbers():
    from tests.card_fixtures import verified_sources

    raw = (
        '[{"page_no": null, "page_type": "cover", "heading": "標題",'
        ' "sections": [], "diagram": null}]'
    )

    with pytest.raises(ValueError, match="page_no 必須是整數"):
        prompt.decode_carousel(raw, verified_sources())


def test_carousel_decoder_reports_non_string_page_text_fields():
    from tests.card_fixtures import verified_sources

    raw = (
        '[{"page_no": 1, "page_type": "cover", "heading": null,'
        ' "sections": [], "diagram": null}]'
    )

    with pytest.raises(ValueError, match="heading 必須是字串"):
        prompt.decode_carousel(raw, verified_sources())


def test_carousel_decoder_reports_non_string_section_text():
    from tests.card_fixtures import verified_sources

    raw = (
        '[{"page_no": 1, "page_type": "cover", "heading": "標題",'
        ' "sections": [{"label": "一句話定位", "text": null,'
        ' "source_ids": ["S1"]}], "diagram": null}]'
    )

    with pytest.raises(ValueError, match="section.text 必須是字串"):
        prompt.decode_carousel(raw, verified_sources())


def test_carousel_decoder_reports_non_string_diagram_node_text():
    from tests.card_fixtures import verified_sources

    raw = (
        '[{"page_no": 3, "page_type": "problem", "heading": "標題",'
        ' "sections": [], "diagram": {"kind": "problem-chain",'
        ' "nodes": [{"title": null, "text": "內容"}]}}]'
    )

    with pytest.raises(ValueError, match="diagram node.title 必須是字串"):
        prompt.decode_carousel(raw, verified_sources())


def test_carousel_decoder_rejects_non_object_page_items():
    import json

    from tests.card_fixtures import (
        structured_llm_response,
        verified_sources,
    )

    payload = json.loads(structured_llm_response())
    payload.append(None)

    with pytest.raises(ValueError, match="每一頁必須是物件"):
        prompt.decode_carousel(
            json.dumps(payload, ensure_ascii=False),
            verified_sources(),
        )


def test_carousel_decoder_rejects_non_object_diagrams():
    from tests.card_fixtures import verified_sources

    raw = (
        '[{"page_no": 1, "page_type": "cover", "heading": "標題",'
        ' "sections": [], "diagram": []}]'
    )

    with pytest.raises(ValueError, match="diagram 必須是物件或 null"):
        prompt.decode_carousel(raw, verified_sources())


def test_build_carousel_prompt_forbids_anxiety_framing():
    """網站 PRD 第二條營運鐵律：降低焦慮，不製造焦慮。"""
    from tests.card_fixtures import verified_sources

    text = prompt.build_carousel(
        "ElevenLabs",
        "t",
        "a",
        verified_sources(),
    )

    assert "焦慮" in text
    assert "落伍" in text
    assert "取代" in text
