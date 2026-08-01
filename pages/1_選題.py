import html
import os
from dataclasses import replace
from datetime import date
from urllib.parse import urlparse

import streamlit as st

from daibu import clock, db, pipeline, selection, workspace
from daibu.cards import assets as carousel_assets
from daibu.cards import bundle as carousel_bundle
from daibu.cards import draft as carousel_draft_service
from daibu.cards import logo as carousel_logo
from daibu.cards import pages as carousel_pages
from daibu.cards import research_draft as carousel_research_draft
from daibu.cards import shoot as carousel_shoot
from daibu.cards import sources as card_sources
from daibu.cards import workbench as carousel_workbench
from daibu.cards.schema import validate_company_headings, validate_draft
from daibu.fetch import page as page_fetch
from daibu.llm import base
from daibu.models import Source, Theme
from daibu.ui import (
    apply_styles,
    connect_app_db,
    mascot_coach,
    page_header,
    queue_toast,
    show_queued_toast,
)

WEEKDAYS = ("週一", "週二", "週三", "週四", "週五", "週六", "週日")
THREADS_CHARACTER_LIMIT = 500
INSTAGRAM_CHARACTER_LIMIT = 2200

st.set_page_config(page_title="內容製作｜呆一布", page_icon="◉", layout="wide")
apply_styles()
show_queued_toast(st.session_state, st.toast)
page_header(
    "CONTENT FLOW",
    "內容製作",
    "選一個內容系列，沿著四個步驟完成一篇貼文；每次只處理眼前這一步。",
)

conn = connect_app_db()


def render_logo_upload_form(idea_id: int, company: str, suffix: str) -> None:
    with st.form(f"carousel-logo-{idea_id}-{suffix}"):
        uploaded_logo = st.file_uploader(
            "上傳官方 Logo",
            type=["png", "svg"],
            key=f"carousel-logo-file-{idea_id}-{suffix}",
        )
        official_source_url = st.text_input(
            "Logo 官方來源網址",
            key=f"carousel-logo-source-{idea_id}-{suffix}",
            help="請填公司官網或官方品牌素材頁。",
        )
        verified_at = st.date_input(
            "Logo 確認日期",
            value=date.today(),
            key=f"carousel-logo-date-{idea_id}-{suffix}",
        )
        if st.form_submit_button("儲存 Logo"):
            if uploaded_logo is None:
                st.error("請先上傳官方 Logo（SVG 或去背 PNG）。")
                return
            if not official_source_url.strip():
                st.error(
                    "請填這個 Logo 的官方來源網址（公司官網或品牌素材頁），"
                    "之後才能追溯是哪裡拿的。"
                )
                return
            try:
                carousel_assets.store_logo(
                    conn,
                    company,
                    uploaded_logo.name,
                    uploaded_logo.getvalue(),
                    official_source_url,
                    verified_at.isoformat(),
                )
            except carousel_logo.InvalidBrandAsset as error:
                st.error(str(error))
                return
            st.session_state.pop(
                f"show-replace-carousel-logo-{idea_id}",
                None,
            )
            queue_toast(st.session_state, "官方 Logo 已儲存。")
            st.rerun()


def save_body_draft(idea_id: int, body_key: str) -> None:
    pipeline.update_body(conn, idea_id, st.session_state[body_key])
    st.session_state[f"body-saved-at-{idea_id}"] = clock.now()[11:16]


def fetch_source_suggestion(
    url_key: str,
    publisher_key: str,
    date_key: str,
    excerpt_key: str,
    error_key: str,
) -> None:
    try:
        suggestion = page_fetch.fetch_suggestion(st.session_state[url_key])
    except ValueError as error:
        st.session_state[error_key] = str(error)
        return
    st.session_state[publisher_key] = suggestion.publisher
    st.session_state[date_key] = suggestion.published_at
    st.session_state[excerpt_key] = suggestion.excerpt
    st.session_state.pop(error_key, None)


def clear_carousel_editor_state(idea_id: int, draft) -> None:
    for carousel_page in draft.pages:
        st.session_state.pop(
            f"carousel-heading-{idea_id}-{carousel_page.page_type}",
            None,
        )
        for section_index, _section in enumerate(carousel_page.sections):
            st.session_state.pop(
                f"carousel-section-{idea_id}-{carousel_page.page_type}-"
                f"{section_index}",
                None,
            )


def trusted_domains_for(
    theme: Theme | None,
    all_sources: list[Source],
) -> tuple[str, ...]:
    if theme is None:
        return ()
    return tuple(
        dict.fromkeys(
            domain
            for source in all_sources
            if source.id in theme.source_ids
            for domain in (urlparse(source.url).hostname or "",)
            if domain
        )
    )


def workflow_journey(current: str, completed: tuple[str, ...]) -> str:
    labels = {
        "research": "找題材",
        "decide": "選一則",
        "write": "寫內容",
        "carousel": "做輪播",
    }
    state_classes = {
        "complete": "workflow-step--complete",
        "current": "workflow-step--current",
        "upcoming": "workflow-step--upcoming",
    }
    steps = []
    for key in workspace.WORKFLOW_STEPS:
        if key in completed:
            state = "complete"
            marker = "✓"
        elif key == current:
            state = "current"
            marker = "•"
        else:
            state = "upcoming"
            marker = ""
        steps.append(
            '<span class="workflow-step '
            f'{state_classes[state]}"><b>{marker}</b>{labels[key]}</span>'
        )
    return '<nav class="workflow-stepper" aria-label="內容製作進度">' + (
        "".join(steps)
    ) + "</nav>"


def carousel_checklist_markup(items: tuple[workspace.ChecklistItem, ...]) -> str:
    state_classes = {
        "complete": "carousel-checklist__item--complete",
        "current": "carousel-checklist__item--current",
        "blocked": "carousel-checklist__item--blocked",
    }
    state_labels = {
        "complete": "完成",
        "current": "現在",
        "blocked": "等待",
    }
    rows = []
    for index, item in enumerate(items, start=1):
        rows.append(
            '<li class="carousel-checklist__item '
            f'{state_classes[item.state]}">'
            f"<span>{index:02d}</span>"
            f"<strong>{html.escape(item.label)}</strong>"
            f"<small>{state_labels[item.state]}</small>"
            "</li>"
        )
    return (
        '<ol class="carousel-checklist" aria-label="輪播前置條件">'
        + "".join(rows)
        + "</ol>"
    )


themes = db.get_themes(conn)
sources = db.get_sources(conn)
candidates = db.get_ideas(conn, status="候選")
adopted_ideas = db.get_ideas(conn, status="採用")
published_ideas = db.get_ideas(conn, status="已發")
provider_config = dict(os.environ)
provider_config["LLM_PROVIDER"] = db.get_config(
    conn,
    "llm_provider",
    provider_config.get("LLM_PROVIDER", "gemini"),
)
provider_config["LLM_MODEL"] = db.get_config(
    conn,
    "llm_model",
    provider_config.get("LLM_MODEL", ""),
)

context_column, candidate_column = st.columns([1, 2], gap="medium")
context_panel = context_column.container(key="context-column")

with context_panel:
    st.subheader("我的內容系列")
    if themes and st.session_state.get("selected_theme_id") not in {
        theme.id for theme in themes
    }:
        st.session_state.selected_theme_id = themes[0].id
    for theme in themes:
        theme_candidates = sum(
            idea.theme_id == theme.id for idea in candidates
        )
        with st.container(key=f"theme-item-{theme.id}"):
            is_current_theme = (
                theme.id == st.session_state.selected_theme_id
            )
            if st.button(
                theme.name,
                key=f"select-theme-{theme.id}",
                type="secondary",
                width="stretch",
            ):
                st.session_state.selected_theme_id = theme.id
                st.session_state.scroll_to_workspace = True
                st.rerun()
            st.markdown(
                '<p class="theme-item__meta">'
                + (
                    '<span class="theme-item__current">'
                    f"目前 · {html.escape(theme.name)}</span>"
                    if is_current_theme
                    else ""
                )
                + f"{WEEKDAYS[theme.weekday]} · "
                f"{len(theme.source_ids)} 來源 · {theme_candidates} 候選"
                "</p>",
                unsafe_allow_html=True,
            )

    with st.popover("＋ 新增內容系列", width="stretch"):
        with st.form("new-theme"):
            new_theme_name = st.text_input("內容系列名稱")
            new_theme_weekday = st.selectbox("提醒星期", WEEKDAYS)
            new_theme_count = st.number_input(
                "每次產生幾則",
                min_value=1,
                max_value=12,
                value=3,
            )
            if st.form_submit_button("建立內容系列"):
                if not new_theme_name.strip():
                    st.error("請輸入內容系列名稱。")
                else:
                    theme_id = db.add_theme(
                        conn,
                        Theme(
                            None,
                            new_theme_name.strip(),
                            WEEKDAYS.index(new_theme_weekday),
                            [],
                            int(new_theme_count),
                        ),
                    )
                    st.session_state.selected_theme_id = theme_id
                    st.rerun()

    with st.expander("素材來源庫"):
        st.caption("來源可被多個內容系列共用；停用後不會再抓取。")
        with st.form("new-source"):
            new_source_name = st.text_input("新來源名稱")
            new_source_url = st.text_input("新來源網址")
            new_source_type = st.selectbox(
                "新來源抓取方式",
                ("rss", "search"),
            )
            if st.form_submit_button("新增來源"):
                if not new_source_name.strip() or not new_source_url.strip():
                    st.error("來源名稱與網址都要填寫。")
                else:
                    db.add_source(
                        conn,
                        Source(
                            None,
                            new_source_name.strip(),
                            new_source_url.strip(),
                            new_source_type,
                            True,
                        ),
                    )
                    st.rerun()

        for source in sources:
            usage_count = db.count_themes_using_source(conn, source.id)
            parsed_url = urlparse(
                source.url
                if "://" in source.url
                else f"//{source.url}"
            )
            source_domain = (
                parsed_url.netloc
                or parsed_url.path.split("/", maxsplit=1)[0]
            )
            with st.container(key=f"source-row-{source.id}"):
                summary_column, edit_column = st.columns(
                    [5, 1],
                    gap="small",
                    vertical_alignment="center",
                )
                summary_column.markdown(
                    '<div class="source-row__summary">'
                    '<span class="source-row__name">'
                    f"{html.escape(source.name)}"
                    "</span>"
                    '<span class="source-row__badge">'
                    f"{html.escape(source.fetch_type.upper())}"
                    "</span>"
                    '<span class="source-row__usage">'
                    f"{usage_count} 個內容系列在用"
                    "</span>"
                    '<span class="source-row__domain">'
                    f"{html.escape(source_domain)}"
                    "</span>"
                    "</div>",
                    unsafe_allow_html=True,
                )
                source_editor = edit_column.popover("編輯", width="stretch")

            with source_editor:
                with st.form(f"edit-source-{source.id}"):
                    edited_source_name = st.text_input(
                        "來源名稱",
                        value=source.name,
                    )
                    edited_source_url = st.text_input(
                        "來源網址",
                        value=source.url,
                    )
                    edited_source_type = st.selectbox(
                        "抓取方式",
                        ("rss", "search"),
                        index=("rss", "search").index(source.fetch_type),
                    )
                    edited_source_enabled = st.checkbox(
                        "啟用",
                        value=source.enabled,
                    )
                    if st.form_submit_button("儲存來源"):
                        db.update_source(
                            conn,
                            Source(
                                source.id,
                                edited_source_name.strip(),
                                edited_source_url.strip(),
                                edited_source_type,
                                edited_source_enabled,
                            ),
                        )
                        st.rerun()
                st.warning(
                    f"這個來源正被 {usage_count} 個內容系列使用；"
                    "刪除後會解除這些內容系列的來源綁定。"
                )
                confirm_delete_source = st.checkbox(
                    "確認從素材來源庫刪除",
                    key=f"confirm-delete-source-{source.id}",
                )
                if st.button(
                    "刪除來源",
                    key=f"delete-source-{source.id}",
                    disabled=not confirm_delete_source,
                    width="stretch",
                ):
                    db.delete_source(conn, source.id)
                    st.rerun()

with candidate_column:
    scroll_to_workspace = st.session_state.pop(
        "scroll_to_workspace",
        False,
    )
    scroll_marker = (
        ' data-scroll-requested="true"'
        if scroll_to_workspace
        else ""
    )
    with st.container(key="workspace-scroll-bridge"):
        st.markdown(
            f'<span id="theme-workspace"{scroll_marker}></span>',
            unsafe_allow_html=True,
        )
        if scroll_to_workspace:
            st.iframe(
                """
                <!doctype html>
                <html>
                <body>
                <script>
                    const parentWindow = window.parent;
                    const anchor = parentWindow.document.getElementById(
                        "theme-workspace"
                    );
                    const isMobile = parentWindow.matchMedia(
                        "(max-width: 700px)"
                    ).matches;
                    const reduceMotion = parentWindow.matchMedia(
                        "(prefers-reduced-motion: reduce)"
                    ).matches;
                    if (anchor && isMobile) {
                        parentWindow.requestAnimationFrame(() => {
                            anchor.scrollIntoView({
                                behavior: reduceMotion ? "auto" : "smooth",
                                block: "start",
                            });
                        });
                    }
                </script>
                </body>
                </html>
                """,
                height="content",
                tab_index=-1,
            )

    selected_theme = next(
        (
            theme for theme in themes
            if theme.id == st.session_state.get("selected_theme_id")
        ),
        None,
    )
    if selected_theme:
        st.subheader(f"{selected_theme.name}工作區")

        series_ideas = [
            idea
            for idea in [*candidates, *adopted_ideas]
            if idea.theme_id == selected_theme.id
        ]
        journey = workspace.derive_workflow(series_ideas)
        st.markdown(
            workflow_journey(journey.current, journey.completed),
            unsafe_allow_html=True,
        )
        coach_copy = {
            "research": (
                "point",
                "先替這個系列找題材",
                "系統會閱讀已設定的可信網域；手動來源只在需要時補充。",
            ),
            "decide": (
                "think",
                "一次比較一則候選",
                "看不懂或不通順就微調；內容值不值得發，由你決定。",
            ),
            "write": (
                "note",
                "已採用，接著把內容寫完整",
                "正文會自動保存；完成後沿同一條路進入輪播。",
            ),
            "carousel": (
                "point",
                "正文完成，接著準備輪播",
                "照五項檢查清單往下走，不必猜哪個工具要先用。",
            ),
        }
        generated_ids = st.session_state.get("new_candidate_ids", [])
        just_generated_here = any(
            idea.id in generated_ids and idea.theme_id == selected_theme.id
            for idea in candidates
        )
        just_completed_step = st.session_state.get("just_completed_step")
        if just_generated_here:
            pose = "happy"
            coach_title = "候選整理好了"
            coach_message = "從比較清單挑一則來看；是否採用，最後由你決定。"
            coach_tone = "success"
        elif just_completed_step == "decide" and journey.current == "write":
            pose = "happy"
            coach_title = "決定好了，現在接著寫"
            coach_message = "剛採用的題目已經打開，不用再回頭找。"
            coach_tone = "success"
        elif just_completed_step == "write" and journey.current == "carousel":
            pose = "happy"
            coach_title = "正文存好了"
            coach_message = "接著照輪播清單補齊資料，就能產出七張圖。"
            coach_tone = "success"
        else:
            pose, coach_title, coach_message = coach_copy[journey.current]
            coach_tone = "guide"
        st.markdown(
            mascot_coach(
                pose,
                coach_title,
                coach_message,
                tone=coach_tone,
            ),
            unsafe_allow_html=True,
        )

        with st.expander("管理內容系列"):
            with st.form(f"theme-settings-{selected_theme.id}"):
                edited_theme_name = st.text_input(
                    "內容系列名稱",
                    value=selected_theme.name,
                )
                edited_theme_weekday = st.selectbox(
                    "提醒星期",
                    WEEKDAYS,
                    index=selected_theme.weekday,
                )
                edited_theme_count = st.number_input(
                    "每次產生幾則",
                    min_value=1,
                    max_value=12,
                    value=selected_theme.n_ideas,
                )
                if st.form_submit_button("儲存內容系列設定"):
                    db.update_theme(
                        conn,
                        Theme(
                            selected_theme.id,
                            edited_theme_name.strip(),
                            WEEKDAYS.index(edited_theme_weekday),
                            selected_theme.source_ids,
                            int(edited_theme_count),
                        ),
                    )
                    st.rerun()
            content_counts = db.count_theme_content(
                conn,
                selected_theme.id,
            )
            content_parts = [
                f"{content_counts[status]} 則{status}"
                for status in ("候選", "採用", "已發")
                if content_counts[status]
            ]
            if content_counts["輪播草稿"]:
                content_parts.append(
                    f"{content_counts['輪播草稿']} 份輪播草稿"
                )
            content_summary = "、".join(content_parts)
            warning_message = (
                f"這會一併刪掉 {content_summary}，且無法復原。"
                if content_summary
                else "這會刪除內容系列，且無法復原。"
            )
            st.warning(warning_message)
            confirm_delete_theme = st.checkbox(
                "確認刪除這個內容系列",
                key=f"confirm-delete-theme-{selected_theme.id}",
            )
            if st.button(
                "刪除內容系列",
                key=f"delete-theme-{selected_theme.id}",
                disabled=not confirm_delete_theme,
            ):
                db.delete_theme(conn, selected_theme.id)
                st.session_state.pop("selected_theme_id", None)
                st.rerun()

        with st.expander("系列素材來源"):
            with st.form(f"theme-sources-{selected_theme.id}"):
                selected_source_ids = []
                for source in sources:
                    source_label = (
                        source.name
                        if source.enabled
                        else f"{source.name}（已停用）"
                    )
                    if st.checkbox(
                        source_label,
                        value=source.id in selected_theme.source_ids,
                        key=f"theme-source-{selected_theme.id}-{source.id}",
                    ):
                        selected_source_ids.append(source.id)
                if st.form_submit_button("儲存系列素材來源"):
                    db.update_theme(
                        conn,
                        Theme(
                            selected_theme.id,
                            selected_theme.name,
                            selected_theme.weekday,
                            selected_source_ids,
                            selected_theme.n_ideas,
                        ),
                    )
                    queue_toast(st.session_state, "來源綁定已儲存。")
                    st.rerun()
        if not selected_theme.source_ids:
            st.warning("這個內容系列未設定素材來源，AI 會只依系列名稱發想。")

        find_topics_clicked = False
        if journey.current in {"research", "decide"}:
            find_topics_clicked = st.button(
                (
                    f"再產生 {selected_theme.n_ideas} 則"
                    if any(
                        idea.theme_id == selected_theme.id
                        for idea in candidates
                    )
                    else "開始找題材"
                ),
                type=(
                    "primary"
                    if journey.current == "research"
                    else "secondary"
                ),
                width="stretch",
            )
        if find_topics_clicked:
            try:
                provider = base.get_provider(provider_config)
                with st.spinner("正在閱讀來源並整理候選…"):
                    st.markdown(
                        mascot_coach(
                            "think",
                            "呆一布正在讀資料",
                            "正在比對可信網域與文章內容，完成後會帶你逐則比較。",
                        ),
                        unsafe_allow_html=True,
                    )
                    generated_idea_ids = selection.generate_for_theme(
                        conn,
                        selected_theme,
                        provider,
                        sources,
                    )
                st.session_state.new_candidate_ids = generated_idea_ids
                queue_toast(st.session_state, "候選已產生。")
                st.rerun()
            except Exception as error:
                st.markdown(
                    mascot_coach(
                        "confused",
                        "這次沒有成功，但原本內容都還在",
                        "可以檢查連線或模型設定後再試一次。",
                        tone="warning",
                    ),
                    unsafe_allow_html=True,
                )
                st.error(f"產生失敗：{error}")
    else:
        st.markdown(
            '<div class="empty-state">'
            "先建立一個內容系列，再開始找題材。"
            "</div>",
            unsafe_allow_html=True,
        )

    selected_candidates = [
        idea for idea in candidates
        if selected_theme and idea.theme_id == selected_theme.id
    ]
    show_candidate_stage = bool(
        selected_theme
        and journey.current in {"research", "decide"}
    )
    decision_candidates = (
        selected_candidates if show_candidate_stage else []
    )
    if show_candidate_stage:
        st.subheader(f"候選（{len(selected_candidates)}）")
    last_rejected = st.session_state.get("last_rejected_idea")
    if (
        show_candidate_stage
        and last_rejected
        and last_rejected["theme_id"] == selected_theme.id
    ):
        if st.button(
            f"復原剛剛淘汰的「{last_rejected['title']}」",
            key="restore-last-rejected",
        ):
            pipeline.restore(conn, last_rejected["id"])
            st.session_state.pop("last_rejected_idea", None)
            queue_toast(
                st.session_state,
                f"已復原「{last_rejected['title']}」。",
            )
            st.rerun()
    if show_candidate_stage and not selected_candidates:
        st.markdown(
            '<div class="empty-state">'
            "<p>這個內容系列尚無候選，按上方的「開始找題材」"
            "讓 AI 先整理一輪。</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    selected_candidate_ids = {idea.id for idea in decision_candidates}
    if decision_candidates and st.session_state.get(
        "selected_candidate_id"
    ) not in selected_candidate_ids:
        st.session_state.selected_candidate_id = decision_candidates[0].id

    if decision_candidates:
        with st.container(key="candidate-comparison"):
            st.caption("先比較標題與公司，再一次專心判斷一則。")
            comparison_columns = st.columns(
                min(len(decision_candidates), 3),
                gap="small",
            )
            for index, candidate in enumerate(decision_candidates):
                if comparison_columns[index % len(comparison_columns)].button(
                    f"比較｜{candidate.title}",
                    key=f"compare-candidate-{candidate.id}",
                    type="secondary",
                    width="stretch",
                ):
                    st.session_state.selected_candidate_id = candidate.id
                    st.rerun()

    selected_candidate = next(
        (
            idea
            for idea in decision_candidates
            if idea.id == st.session_state.get("selected_candidate_id")
        ),
        None,
    )
    for idea in [selected_candidate] if selected_candidate else []:
        with st.container(border=True):
            new_badge = (
                '<span class="candidate-card__new">新</span>'
                if idea.id in st.session_state.get("new_candidate_ids", [])
                else ""
            )
            company_label = idea.company or "未指定公司"
            st.markdown(
                '<div class="idea-company">'
                f"{html.escape(company_label)}"
                "</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                '<h3 class="candidate-card__title">'
                f"{new_badge}"
                f"{html.escape(idea.title)}"
                "</h3>",
                unsafe_allow_html=True,
            )
            st.markdown(
                '<p class="candidate-card__angle">'
                f"{html.escape(idea.angle)}"
                "</p>",
                unsafe_allow_html=True,
            )
            if idea.source_url:
                st.link_button("查看來源", idea.source_url)

            adopt_column, tweak_column, reject_column = st.columns(3)
            if adopt_column.button(
                "採用並繼續寫內容",
                key=f"adopt-{idea.id}",
                type=(
                    "primary"
                    if journey.current == "decide"
                    else "secondary"
                ),
                width="stretch",
            ):
                pipeline.set_status(conn, idea.id, "採用")
                st.session_state.selected_adopted_id = idea.id
                st.session_state.workflow_step = "write"
                st.session_state.just_completed_step = "decide"
                queue_toast(
                    st.session_state,
                    f"已採用「{idea.title}」。",
                )
                st.rerun()

            with tweak_column.popover("微調", width="stretch"):
                with st.form(f"tweak-{idea.id}"):
                    tweaked_title = st.text_input(
                        "標題",
                        value=idea.title,
                        key=f"tweak-title-{idea.id}",
                    )
                    tweaked_angle = st.text_area(
                        "切入角度",
                        value=idea.angle,
                        key=f"tweak-angle-{idea.id}",
                    )
                    if st.form_submit_button("儲存微調"):
                        db.update_idea_content(
                            conn,
                            idea.id,
                            tweaked_title.strip(),
                            tweaked_angle.strip(),
                        )
                        queue_toast(st.session_state, "微調已儲存。")
                        st.rerun()

            if reject_column.button(
                "淘汰",
                key=f"reject-{idea.id}",
                width="stretch",
            ):
                pipeline.set_status(conn, idea.id, pipeline.REJECTED)
                st.session_state.last_rejected_idea = {
                    "id": idea.id,
                    "title": idea.title,
                    "theme_id": idea.theme_id,
                }
                queue_toast(
                    st.session_state,
                    f"已淘汰「{idea.title}」，可在候選區復原。",
                )
                st.rerun()

    selected_adopted = [
        idea for idea in adopted_ideas
        if selected_theme and idea.theme_id == selected_theme.id
    ]
    st.subheader(f"已採用（{len(selected_adopted)}）")
    if not selected_adopted:
        st.caption("這個內容系列還沒有已採用的題目。")
    selected_adopted_ids = {idea.id for idea in selected_adopted}
    if selected_adopted and st.session_state.get(
        "selected_adopted_id"
    ) not in selected_adopted_ids:
        st.session_state.selected_adopted_id = selected_adopted[0].id
    if selected_adopted:
        with st.container(key="writing-queue"):
            writing_columns = st.columns(
                min(len(selected_adopted), 3),
                gap="small",
            )
            for index, adopted_idea in enumerate(selected_adopted):
                if writing_columns[index % len(writing_columns)].button(
                    f"編輯｜{adopted_idea.title}",
                    key=f"edit-adopted-{adopted_idea.id}",
                    type="secondary",
                    width="stretch",
                ):
                    st.session_state.selected_adopted_id = adopted_idea.id
                    st.rerun()
    selected_adopted_idea = next(
        (
            idea
            for idea in selected_adopted
            if idea.id == st.session_state.get("selected_adopted_id")
        ),
        None,
    )
    for idea in [selected_adopted_idea] if selected_adopted_idea else []:
        with st.expander(
            idea.title,
            expanded=journey.current in {"write", "carousel"},
        ):
            st.caption(idea.angle)
            body_key = f"body-{idea.id}"
            body = st.text_area(
                "正文",
                value=idea.body,
                key=body_key,
                height=180,
                on_change=save_body_draft,
                args=(idea.id, body_key),
            )
            body_length = len(body)
            st.caption(
                f"{body_length} 字 · "
                "Threads 還可寫 "
                f"{max(THREADS_CHARACTER_LIMIT - body_length, 0)} · "
                "Instagram 還可寫 "
                f"{max(INSTAGRAM_CHARACTER_LIMIT - body_length, 0)}"
            )
            saved_at = st.session_state.get(f"body-saved-at-{idea.id}")
            if saved_at:
                st.caption(f"已自動儲存於 {saved_at}")
            with st.expander(
                "輪播製作",
                expanded=st.session_state.get("workflow_step") == "carousel",
            ):
                source_pack = db.get_idea_sources(conn, idea.id)
                brand_asset = (
                    db.get_brand_asset(conn, idea.company)
                    if idea.company.strip()
                    else None
                )
                checklist_draft = db.get_carousel_draft(conn, idea.id)
                checklist_pngs = (
                    carousel_workbench.cached_pngs(
                        st.session_state,
                        idea.id,
                        checklist_draft,
                    )
                    if checklist_draft is not None
                    else None
                )
                checklist_items = workspace.carousel_checklist(
                    has_company=bool(idea.company.strip()),
                    source_count=len(source_pack),
                    has_logo=brand_asset is not None,
                    has_draft=checklist_draft is not None,
                    has_pngs=checklist_pngs is not None,
                )
                st.markdown(
                    carousel_checklist_markup(checklist_items),
                    unsafe_allow_html=True,
                )
                if idea.company.strip() and not source_pack:
                    st.info(
                        "尚未建立查證證據。按「產生輪播草稿」後，"
                        "系統會先搜尋可信網域、驗證內文，再產生草稿。"
                    )
                if not idea.company.strip():
                    with st.form(f"carousel-company-{idea.id}"):
                        company_name = st.text_input(
                            "公司名稱",
                            key=f"carousel-company-name-{idea.id}",
                            help="會用在輪播封面、Logo 對應與 ZIP 檔名。",
                        )
                        if st.form_submit_button("儲存公司名"):
                            if not company_name.strip():
                                st.error("請填公司名稱。")
                            else:
                                db.set_idea_company(
                                    conn,
                                    idea.id,
                                    company_name,
                                )
                                queue_toast(
                                    st.session_state,
                                    "公司名稱已儲存。",
                                )
                                st.rerun()
                st.markdown("#### 這篇內容的查證證據")
                st.caption(
                    "每則題目可存 1–8 筆；加入前請確認出版方、日期與引文。"
                )
                source_url_key = f"carousel-source-url-{idea.id}"
                source_publisher_key = (
                    f"carousel-source-publisher-{idea.id}"
                )
                source_date_key = f"carousel-source-date-{idea.id}"
                source_excerpt_key = (
                    f"carousel-source-excerpt-{idea.id}"
                )
                source_fetch_error_key = (
                    f"carousel-source-fetch-error-{idea.id}"
                )
                for verified_source in source_pack:
                    source_kind_label = {
                        "official": "官方說法",
                        "third_party": "第三方報導",
                        "manual": "手動加入",
                    }[verified_source.source_kind]
                    st.markdown(
                        '<div class="verified-source">'
                        "<div>"
                        f"<strong>{html.escape(verified_source.source_id)} · "
                        f"{html.escape(verified_source.publisher)}</strong>"
                        '<span class="source-kind" data-kind="'
                        f'{html.escape(verified_source.source_kind)}">'
                        f"{html.escape(source_kind_label)}</span>"
                        "</div>"
                        f'<time>{html.escape(verified_source.published_at)}</time>'
                        "</div>",
                        unsafe_allow_html=True,
                    )
                    st.link_button(
                        "開啟來源",
                        verified_source.url,
                        key=(
                            f"open-carousel-source-{idea.id}-"
                            f"{verified_source.source_id}"
                        ),
                    )
                    if st.button(
                        f"刪除 {verified_source.source_id}",
                        key=(
                            f"delete-carousel-source-{idea.id}-"
                            f"{verified_source.source_id}"
                        ),
                    ):
                        updated_pack = card_sources.remove(
                            source_pack,
                            verified_source.source_id,
                        )
                        db.save_idea_sources(
                            conn,
                            idea.id,
                            updated_pack,
                        )
                        queue_toast(
                            st.session_state,
                            f"已刪除來源 {verified_source.source_id}。",
                        )
                        st.rerun()
                if source_pack:
                    official_count = sum(
                        source.source_kind == "official"
                        for source in source_pack
                    )
                    third_party_count = sum(
                        source.source_kind == "third_party"
                        for source in source_pack
                    )
                    manual_count = (
                        len(source_pack)
                        - official_count
                        - third_party_count
                    )
                    st.caption(
                        f"查證證據共 {len(source_pack)} 筆："
                        f"官方 {official_count}、第三方 {third_party_count}、"
                        f"手動 {manual_count}。"
                    )
                with st.expander(
                    "＋ 新增來源",
                    expanded=not source_pack,
                ):
                    with st.form(f"carousel-source-{idea.id}"):
                        source_url = st.text_input(
                            "來源網址",
                            value=(
                                idea.source_url
                                if not source_pack
                                else ""
                            ),
                            key=source_url_key,
                            help="只接受公開可讀的 https 網址。",
                        )
                        source_publisher = st.text_input(
                            "出版方",
                            key=source_publisher_key,
                        )
                        source_date = st.text_input(
                            "發布日期",
                            key=source_date_key,
                            placeholder="YYYY-MM-DD",
                        )
                        source_excerpt = st.text_area(
                            "查證引文",
                            value=(
                                idea.source_excerpt
                                if not source_pack
                                else ""
                            ),
                            key=source_excerpt_key,
                            height=120,
                        )
                        fetch_column, add_column = st.columns(2)
                        fetch_column.form_submit_button(
                            "抓取內容",
                            on_click=fetch_source_suggestion,
                            args=(
                                source_url_key,
                                source_publisher_key,
                                source_date_key,
                                source_excerpt_key,
                                source_fetch_error_key,
                            ),
                            width="stretch",
                        )
                        if add_column.form_submit_button(
                            "加入來源",
                            width="stretch",
                        ):
                            try:
                                updated_pack = card_sources.add(
                                    source_pack,
                                    source_publisher,
                                    source_date,
                                    source_url,
                                    source_excerpt,
                                )
                                db.save_idea_sources(
                                    conn,
                                    idea.id,
                                    updated_pack,
                                )
                                queue_toast(
                                    st.session_state,
                                    "已加入查證來源。",
                                )
                                st.rerun()
                            except ValueError as error:
                                st.error(str(error))
                        source_fetch_error = st.session_state.get(
                            source_fetch_error_key
                        )
                        if source_fetch_error:
                            st.error(source_fetch_error)
                if idea.company.strip():
                    st.markdown("#### 官方 Logo")
                    if brand_asset is None:
                        st.markdown(
                            '<div class="carousel-status '
                            'carousel-status--missing">'
                            f"<strong>還沒有 {html.escape(idea.company)} "
                            "的官方 Logo</strong>"
                            "<p>草稿仍可產生；上傳 Logo 後才能輸出七張圖。</p>"
                            "</div>",
                            unsafe_allow_html=True,
                        )
                        render_logo_upload_form(
                            idea.id,
                            idea.company,
                            "new",
                        )
                    else:
                        st.markdown(
                            '<div class="verified-logo">'
                            f"<strong>{html.escape(idea.company)} "
                            "官方 Logo</strong>"
                            "</div>",
                            unsafe_allow_html=True,
                        )
                        st.image(
                            str(brand_asset.local_path),
                            caption=f"{idea.company} 官方 Logo",
                            width=240,
                        )
                        st.link_button(
                            "查看 Logo 官方來源",
                            brand_asset.official_source_url,
                        )
                        st.caption(
                            f"確認日期：{brand_asset.verified_at}"
                        )
                        if st.button(
                            "換一張",
                            key=f"replace-carousel-logo-{idea.id}",
                        ):
                            st.session_state[
                                f"show-replace-carousel-logo-{idea.id}"
                            ] = True
                        if st.session_state.get(
                            f"show-replace-carousel-logo-{idea.id}"
                        ):
                            render_logo_upload_form(
                                idea.id,
                                idea.company,
                                "replace",
                            )
                stored_draft = db.get_carousel_draft(conn, idea.id)
                if stored_draft is None:
                    st.caption("會先查證公司資料，再呼叫一次 AI，約 10–40 秒。")
                    if st.button(
                        "產生輪播草稿",
                        key=f"generate-carousel-draft-{idea.id}",
                        type=(
                            "primary"
                            if journey.current == "carousel"
                            else "secondary"
                        ),
                        disabled=not idea.company.strip(),
                        width="stretch",
                    ):
                        try:
                            provider = base.get_provider(provider_config)
                            configured_domains = trusted_domains_for(
                                selected_theme,
                                sources,
                            )
                            with st.status(
                                "正在查證公司資料…",
                                expanded=True,
                            ) as research_status:
                                research_status.write("搜尋可信網域")
                                research_status.write("驗證文章與來源類別")
                                research_status.write("擷取可逐字核對的證據")
                                carousel_research_draft.generate(
                                    conn,
                                    idea,
                                    configured_domains,
                                    brand_asset,
                                    None,
                                    None,
                                    provider.generate_carousel_text,
                                )
                                research_status.update(
                                    label="公司資料已查證，七頁草稿已產生",
                                    state="complete",
                                    expanded=False,
                                )
                            queue_toast(
                                st.session_state,
                                "七頁輪播草稿已產生。",
                            )
                            st.rerun()
                        except (
                            base.LLMResponseError,
                            RuntimeError,
                            ValueError,
                        ) as error:
                            st.error(
                                "輪播草稿產生失敗，既有內容沒有被刪除。"
                                f"請稍後重試；原因：{error}"
                            )
                if stored_draft is not None:
                    st.markdown("#### 七頁草稿")
                    st.caption(
                        "可修改標題與文字；段落標籤和來源 ID 會保持不變。"
                    )
                    for carousel_page in stored_draft.pages:
                        page_label = carousel_pages.label(
                            carousel_page.page_type
                        )
                        with st.container(
                            border=True,
                            key=(
                                f"carousel-page-{idea.id}-"
                                f"{carousel_page.page_type}"
                            ),
                        ):
                            st.markdown(
                                '<div class="carousel-page-heading">'
                                f"<span>{carousel_page.page_no:02d}</span>"
                                f"<strong>{html.escape(page_label)}</strong>"
                                "</div>",
                                unsafe_allow_html=True,
                            )
                            st.text_input(
                                f"頁面標題｜{page_label}",
                                value=carousel_page.heading,
                                key=(
                                    f"carousel-heading-{idea.id}-"
                                    f"{carousel_page.page_type}"
                                ),
                            )
                            for section_index, section in enumerate(
                                carousel_page.sections
                            ):
                                st.text_area(
                                    section.label,
                                    value=section.text,
                                    key=(
                                        f"carousel-section-{idea.id}-"
                                        f"{carousel_page.page_type}-"
                                        f"{section_index}"
                                    ),
                                    height=120,
                                )
                                if section.source_ids:
                                    st.caption(
                                        "來源 ID："
                                        + "、".join(section.source_ids)
                                    )
                                else:
                                    st.caption("這段不是事實陳述，不需來源。")
                                for evidence in section.evidence_quotes:
                                    st.caption(
                                        f"查證引文 {evidence.source_id}："
                                        f"「{evidence.quote}」"
                                    )
                            st.caption(carousel_page.source_label)
                    if st.button(
                        "儲存草稿",
                        key=f"save-carousel-draft-{idea.id}",
                        type="secondary",
                    ):
                        edited_pages = tuple(
                            replace(
                                carousel_page,
                                heading=st.session_state[
                                    f"carousel-heading-{idea.id}-"
                                    f"{carousel_page.page_type}"
                                ],
                                sections=tuple(
                                    replace(
                                        section,
                                        text=st.session_state[
                                            f"carousel-section-{idea.id}-"
                                            f"{carousel_page.page_type}-"
                                            f"{section_index}"
                                        ],
                                    )
                                    for section_index, section in enumerate(
                                        carousel_page.sections
                                    )
                                ),
                            )
                            for carousel_page in stored_draft.pages
                        )
                        edited_draft = replace(
                            stored_draft,
                            pages=edited_pages,
                        )
                        try:
                            validate_draft(edited_draft)
                            validate_company_headings(
                                edited_draft,
                                idea.company,
                            )
                            db.save_carousel_draft(
                                conn,
                                idea.id,
                                edited_draft,
                            )
                        except ValueError as error:
                            for message in str(error).splitlines():
                                st.error(message.removeprefix("- "))
                        else:
                            queue_toast(
                                st.session_state,
                                "輪播草稿已儲存。",
                            )
                            st.rerun()
                    with st.popover("重新產生"):
                        st.caption(
                            "會覆蓋目前的七頁內容，且無法復原；"
                            "也會再使用一次免費 AI 額度。"
                        )
                        if st.button(
                            "確認重新產生",
                            key=f"regenerate-carousel-draft-{idea.id}",
                            width="stretch",
                        ):
                            try:
                                provider = base.get_provider(provider_config)
                                with st.spinner(
                                    "正在重新整理七頁輪播草稿…"
                                ):
                                    carousel_draft_service.generate(
                                        conn,
                                        idea,
                                        stored_draft.sources,
                                        provider.generate_carousel_text,
                                    )
                                clear_carousel_editor_state(
                                    idea.id,
                                    stored_draft,
                                )
                                queue_toast(
                                    st.session_state,
                                    "七頁輪播草稿已重新產生。",
                                )
                                st.rerun()
                            except (
                                base.LLMResponseError,
                                RuntimeError,
                                ValueError,
                            ) as error:
                                st.error(
                                    "重新產生失敗，原本草稿仍保留。"
                                    f"請稍後重試；原因：{error}"
                                )
                    with st.popover("重新搜尋公司資料"):
                        st.caption(
                            "會重新搜尋可信網域並覆蓋目前的查證證據與七頁草稿；"
                            "只有整套新資料成功時才會換掉舊版本。"
                        )
                        if st.button(
                            "確認重新搜尋",
                            key=f"research-carousel-again-{idea.id}",
                            width="stretch",
                        ):
                            try:
                                provider = base.get_provider(provider_config)
                                with st.status(
                                    "正在重新查證公司資料…",
                                    expanded=True,
                                ) as research_status:
                                    research_status.write("搜尋可信網域")
                                    research_status.write("驗證文章與逐字證據")
                                    carousel_research_draft.generate(
                                        conn,
                                        idea,
                                        trusted_domains_for(
                                            selected_theme,
                                            sources,
                                        ),
                                        brand_asset,
                                        None,
                                        None,
                                        provider.generate_carousel_text,
                                        reuse_existing_sources=False,
                                    )
                                    research_status.update(
                                        label="查證證據與七頁草稿已換新",
                                        state="complete",
                                        expanded=False,
                                    )
                                clear_carousel_editor_state(
                                    idea.id,
                                    stored_draft,
                                )
                                st.session_state.pop(
                                    f"carousel-png-{idea.id}",
                                    None,
                                )
                                queue_toast(
                                    st.session_state,
                                    "公司資料與七頁草稿已重新查證。",
                                )
                                st.rerun()
                            except (
                                base.LLMResponseError,
                                RuntimeError,
                                ValueError,
                            ) as error:
                                st.error(
                                    "重新搜尋失敗，原本來源、草稿與圖片仍保留。"
                                    f"請稍後重試；原因：{error}"
                                )
                render_disabled = (
                    stored_draft is None
                    or not carousel_workbench.can_render(
                        idea,
                        source_pack,
                        brand_asset,
                    )
                )
                if st.button(
                    "產生七張圖",
                    key=f"render-carousel-{idea.id}",
                    disabled=render_disabled,
                    type=(
                        "primary"
                        if journey.current == "carousel"
                        and checklist_pngs is None
                        else "secondary"
                    ),
                    width="stretch",
                ):
                    try:
                        with st.spinner("正在出圖，約 10 秒…"):
                            rendered_pngs = carousel_shoot.carousel_pngs(
                                stored_draft,
                                idea.company,
                                brand_asset,
                            )
                    except (
                        RuntimeError,
                        carousel_logo.BrandAssetRequired,
                        carousel_logo.InvalidBrandAsset,
                    ) as error:
                        st.error(
                            "七張圖產生失敗，草稿與 Logo 都沒有被改動。"
                            f"請依訊息修正後再試；原因：{error}"
                        )
                    else:
                        st.session_state[
                            f"carousel-png-{idea.id}"
                        ] = (
                            carousel_workbench.draft_fingerprint(
                                stored_draft
                            ),
                            rendered_pngs,
                        )
                if stored_draft is not None:
                    cached_pngs = carousel_workbench.cached_pngs(
                        st.session_state,
                        idea.id,
                        stored_draft,
                    )
                else:
                    cached_pngs = None
                if cached_pngs is not None:
                    st.markdown("#### 七張圖預覽")
                    with st.container(
                        key=f"carousel-preview-grid-{idea.id}"
                    ):
                        for index, png in enumerate(cached_pngs):
                            page_type = carousel_pages.PAGE_TYPES[index]
                            st.image(
                                png,
                                caption=(
                                    f"{index + 1:02d} · "
                                    f"{carousel_pages.label(page_type)}"
                                ),
                                width="stretch",
                            )
                    archive = carousel_bundle.carousel_zip(cached_pngs)
                    st.download_button(
                        "下載全部（ZIP）",
                        data=archive,
                        file_name=carousel_bundle.zip_name(
                            idea.company,
                            date.today(),
                        ),
                        mime="application/zip",
                        key=f"download-carousel-{idea.id}",
                        type="primary",
                        width="stretch",
                    )
            save_column, return_column, publish_column = st.columns(3)
            if save_column.button(
                "儲存並繼續做輪播",
                key=f"save-body-{idea.id}",
                type=(
                    "primary"
                    if journey.current == "write"
                    else "secondary"
                ),
                disabled=not body.strip(),
                width="stretch",
            ):
                save_body_draft(idea.id, body_key)
                st.session_state.workflow_step = "carousel"
                st.session_state.selected_adopted_id = idea.id
                st.session_state.just_completed_step = "write"
                queue_toast(
                    st.session_state,
                    "正文已儲存，接著完成輪播清單。",
                )
                st.rerun()
            if return_column.button(
                "退回候選",
                key=f"return-candidate-{idea.id}",
                width="stretch",
            ):
                pipeline.set_status(conn, idea.id, "候選")
                queue_toast(st.session_state, "已退回候選。")
                st.rerun()
            if publish_column.button(
                "標記已發",
                key=f"publish-{idea.id}",
                disabled=not body.strip(),
                width="stretch",
            ):
                pipeline.update_body(conn, idea.id, body)
                pipeline.set_status(conn, idea.id, "已發")
                queue_toast(st.session_state, "已標記為已發。")
                st.rerun()

    selected_published = [
        idea for idea in published_ideas
        if selected_theme and idea.theme_id == selected_theme.id
    ]
    if selected_published:
        with st.expander(f"已發（{len(selected_published)}）"):
            for idea in selected_published:
                st.markdown(f"**{idea.title}**")
                st.caption(idea.published_at or "發布時間未知")
                if st.button(
                    "退回已採用",
                    key=f"return-adopted-{idea.id}",
                ):
                    pipeline.set_status(conn, idea.id, "採用")
                    queue_toast(st.session_state, "已退回已採用。")
                    st.rerun()
