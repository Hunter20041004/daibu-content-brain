import html
import os
from urllib.parse import urlparse

import streamlit as st

from daibu import clock, db, pipeline, selection
from daibu.cards import sources as card_sources
from daibu.cards import workbench as carousel_workbench
from daibu.fetch import page as page_fetch
from daibu.llm import base
from daibu.models import Source, Theme
from daibu.ui import (
    apply_styles,
    connect_app_db,
    page_header,
    queue_toast,
    show_queued_toast,
)

WEEKDAYS = ("週一", "週二", "週三", "週四", "週五", "週六", "週日")
THREADS_CHARACTER_LIMIT = 500
INSTAGRAM_CHARACTER_LIMIT = 2200

st.set_page_config(page_title="選題｜呆一布", page_icon="◉", layout="wide")
apply_styles()
show_queued_toast(st.session_state, st.toast)
page_header(
    "Radar",
    "選題工作台",
    "以主題為中心管理來源、產生候選，並把採用內容一路寫到發布。",
)

conn = connect_app_db()


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
    st.subheader("我的主題")
    if themes and st.session_state.get("selected_theme_id") not in {
        theme.id for theme in themes
    }:
        st.session_state.selected_theme_id = themes[0].id
    for theme in themes:
        theme_candidates = sum(
            idea.theme_id == theme.id for idea in candidates
        )
        with st.container(key=f"theme-item-{theme.id}"):
            if st.button(
                theme.name,
                key=f"select-theme-{theme.id}",
                type=(
                    "primary"
                    if theme.id == st.session_state.selected_theme_id
                    else "secondary"
                ),
                width="stretch",
            ):
                st.session_state.selected_theme_id = theme.id
                st.session_state.scroll_to_workspace = True
                st.rerun()
            st.markdown(
                '<p class="theme-item__meta">'
                f"{WEEKDAYS[theme.weekday]} · "
                f"{len(theme.source_ids)} 來源 · {theme_candidates} 候選"
                "</p>",
                unsafe_allow_html=True,
            )

    with st.popover("＋ 新增主題", width="stretch"):
        with st.form("new-theme"):
            new_theme_name = st.text_input("主題名稱")
            new_theme_weekday = st.selectbox("提醒星期", WEEKDAYS)
            new_theme_count = st.number_input(
                "每次產生幾則",
                min_value=1,
                max_value=12,
                value=3,
            )
            if st.form_submit_button("建立主題", type="primary"):
                if not new_theme_name.strip():
                    st.error("請輸入主題名稱。")
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

    with st.expander("來源庫"):
        st.caption("來源可被多個主題共用；停用後不會再抓取。")
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
                    f"{usage_count} 個主題在用"
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
                    f"這個來源正被 {usage_count} 個主題使用；"
                    "刪除後會解除這些主題的來源綁定。"
                )
                confirm_delete_source = st.checkbox(
                    "確認從來源庫刪除",
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

        with st.expander("主題設定"):
            with st.form(f"theme-settings-{selected_theme.id}"):
                edited_theme_name = st.text_input(
                    "主題名稱",
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
                if st.form_submit_button("儲存主題設定"):
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
                else "這會刪除主題，且無法復原。"
            )
            st.warning(warning_message)
            confirm_delete_theme = st.checkbox(
                "確認刪除這個主題",
                key=f"confirm-delete-theme-{selected_theme.id}",
            )
            if st.button(
                "刪除主題",
                key=f"delete-theme-{selected_theme.id}",
                disabled=not confirm_delete_theme,
            ):
                db.delete_theme(conn, selected_theme.id)
                st.session_state.pop("selected_theme_id", None)
                st.rerun()

        with st.expander("這個主題抓哪些來源"):
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
                if st.form_submit_button("儲存來源綁定"):
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
            st.warning("這個主題沒綁來源，AI 會只靠主題名發想。")

        if st.button(
            "產生候選",
            type="primary",
            width="stretch",
        ):
            try:
                provider = base.get_provider(provider_config)
                with st.spinner("正在閱讀來源並整理候選…"):
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
                st.error(f"產生失敗：{error}")
    else:
        st.markdown(
            '<div class="empty-state">'
            "先在左欄新增一個主題，再開始建立選題。"
            "</div>",
            unsafe_allow_html=True,
        )

    selected_candidates = [
        idea for idea in candidates
        if selected_theme and idea.theme_id == selected_theme.id
    ]
    st.subheader(f"候選（{len(selected_candidates)}）")
    last_rejected = st.session_state.get("last_rejected_idea")
    if (
        selected_theme
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
    if not selected_candidates:
        st.markdown(
            '<div class="empty-state">'
            "<p>這個主題尚無候選，按上方的「產生候選」"
            "讓 AI 先整理一輪。</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    for idea in selected_candidates:
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
                "採用",
                key=f"adopt-{idea.id}",
                type="primary",
                width="stretch",
            ):
                pipeline.set_status(conn, idea.id, "採用")
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
        st.caption("這個主題還沒有已採用的題目。")
    for idea in selected_adopted:
        with st.expander(idea.title):
            st.caption(idea.angle)
            body_key = f"body-{idea.id}"
            body = st.text_area(
                "正文",
                value=idea.body,
                key=body_key,
                height=240,
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
            with st.expander("輪播圖"):
                source_pack = db.get_idea_sources(conn, idea.id)
                brand_asset = (
                    db.get_brand_asset(conn, idea.company)
                    if idea.company.strip()
                    else None
                )
                missing = carousel_workbench.missing_requirements(
                    idea,
                    source_pack,
                    brand_asset,
                )
                if missing:
                    st.markdown(
                        '<div class="carousel-status carousel-status--missing">'
                        "<strong>資料還沒齊</strong>"
                        + "".join(
                            f"<p>{html.escape(message)}</p>"
                            for message in missing
                        )
                        + "</div>",
                        unsafe_allow_html=True,
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
                st.markdown("#### 已查證來源")
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
                for verified_source in source_pack:
                    st.markdown(
                        '<div class="verified-source">'
                        f"<strong>{html.escape(verified_source.source_id)} · "
                        f"{html.escape(verified_source.publisher)}</strong>"
                        f"<span>{html.escape(verified_source.published_at)}</span>"
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
            save_column, return_column, publish_column = st.columns(3)
            if save_column.button(
                "儲存正文",
                key=f"save-body-{idea.id}",
                type="primary",
                width="stretch",
            ):
                save_body_draft(idea.id, body_key)
                queue_toast(st.session_state, "正文已儲存。")
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
