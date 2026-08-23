from dataclasses import dataclass
from typing import Mapping

import streamlit as st


CONTENT_HTML = """
<div class="carousel-editor" data-role="editor-shell">
  <nav data-role="page-rail" aria-label="七頁導覽"></nav>
  <section data-role="field-panel"></section>
  <section data-role="preview"></section>
  <aside data-role="action-bar"></aside>
</div>
"""

CONTENT_CSS = """
:host {
  --ink: #102f3d;
  --teal: #2f7c87;
  --cyan: #86ccd4;
  --peach: #ec9870;
  --paper: #fafbf8;
  --ice: #edf6f7;
  --line: #b8d7dd;
  --muted: #61747d;
  color: var(--ink);
  font-family: "LINE Seed TW", "PingFang TC", sans-serif;
}
* { box-sizing: border-box; }
.carousel-editor {
  display: grid;
  grid-template-columns: 132px minmax(320px,1fr) minmax(360px,.9fr);
  grid-template-rows: minmax(640px, auto) auto;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--line);
  background: var(--paper);
}
[data-role="page-rail"] {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 18px 10px;
  border-right: 1px solid var(--line);
  background: var(--ice);
}
[data-role="page-rail"] button {
  position: relative;
  min-height: 52px;
  padding: 8px 10px;
  border: 0;
  border-left: 3px solid transparent;
  border-radius: 0;
  color: var(--muted);
  background: transparent;
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  text-align: left;
  transition: background-color 150ms ease, border-color 150ms ease;
}
[data-role="page-rail"] button:hover,
[data-role="page-rail"] button:focus-visible { background: rgba(134,204,212,.22); }
[data-role="page-rail"] button[aria-current="page"] {
  border-left-color: var(--peach);
  color: var(--ink);
  background: white;
}
[data-role="page-rail"] button::after {
  content: attr(data-status-label);
  display: block;
  margin-top: 3px;
  color: var(--teal);
  font-size: 10px;
  font-weight: 700;
}
[data-role="page-rail"] button[data-status="error"]::after { color: #b54232; }
[data-role="page-rail"] button[data-status="warning"]::after { color: #9a5b23; }
[data-role="field-panel"] {
  min-width: 0;
  padding: 26px 28px 100px;
  border-right: 1px solid var(--line);
  background: white;
}
.panel-heading { margin: 0 0 22px; font-size: 24px; letter-spacing: -.03em; }
.field-row { display: block; margin-bottom: 20px; font-size: 13px; font-weight: 800; }
.field-row textarea,
.field-row select {
  display: block;
  width: 100%;
  margin-top: 7px;
  border: 1px solid var(--line);
  border-radius: 0;
  color: var(--ink);
  background: var(--paper);
  font: inherit;
  font-size: 15px;
  font-weight: 500;
  line-height: 1.55;
  outline: none;
}
.field-row textarea { min-height: 84px; padding: 12px 14px; resize: vertical; }
.field-row select { min-height: 44px; padding: 0 12px; }
.field-row textarea:focus,
.field-row select:focus { border-color: var(--teal); box-shadow: 0 0 0 2px rgba(47,124,135,.16); }
.field-row textarea[aria-invalid="true"] { border-color: #b54232; }
[data-role="character-count"] { display: block; margin-top: 5px; color: var(--muted); font-weight: 500; text-align: right; }
[data-role="character-count"][data-limit="near"] { color: #9a5b23; }
[data-role="character-count"][data-limit="hard"] { color: #b54232; font-weight: 800; }
.locked-evidence { margin-top: 24px; border-top: 1px solid var(--line); padding-top: 14px; }
.locked-evidence summary { cursor: pointer; color: var(--teal); font-size: 13px; font-weight: 800; }
.locked-evidence p { color: var(--muted); font-size: 12px; line-height: 1.5; }
[data-role="preview"] { min-width: 0; padding: 26px; background: var(--ice); }
.preview-label { margin: 0 0 14px; font-size: 13px; font-weight: 800; }
.preview-stage { position: relative; width: 100%; aspect-ratio: 4 / 5; overflow: hidden; background: var(--paper); box-shadow: 0 18px 40px rgba(16,47,61,.12); }
.preview-document { position: absolute; inset: 0 auto auto 0; width: 1080px; height: 1350px; transform-origin: top left; }
[data-role="action-bar"] {
  position: sticky;
  bottom: 0;
  z-index: 20;
  grid-column: 2 / 4;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 72px;
  padding: 12px 24px;
  border-top: 1px solid var(--line);
  background: rgba(250,251,248,.96);
  backdrop-filter: blur(12px);
}
.save-status { color: var(--muted); font-size: 13px; font-weight: 700; }
[data-role="action-bar"] button { min-height: 44px; padding: 0 22px; border: 1px solid var(--ink); border-radius: 0; color: white; background: var(--ink); font: inherit; font-weight: 800; transition: transform 140ms ease, background-color 140ms ease; }
[data-role="action-bar"] button:hover:not(:disabled) { transform: translateY(-1px); background: var(--teal); }
[data-role="action-bar"] button:disabled { cursor: not-allowed; opacity: .4; }
.action-buttons { display: flex; align-items: center; gap: 8px; }
[data-role="action-bar"] .secondary-action { padding: 0 12px; border-color: var(--line); color: var(--teal); background: transparent; font-size: 12px; }
@media (max-width: 700px) {
  :host { overflow-x: hidden; }
  .carousel-editor { display: block; width: 100%; min-width: 0; overflow-x: hidden; }
  [data-role="page-rail"] { flex-direction: row; overflow-x: auto; border-right: 0; border-bottom: 1px solid var(--line); padding: 8px; scrollbar-width: none; }
  [data-role="page-rail"] button { flex: 0 0 104px; min-height: 48px; }
  [data-role="field-panel"], [data-role="preview"] { width: 100%; padding: 20px 16px; border-right: 0; }
  [data-role="action-bar"] { position: sticky; display: flex; width: 100%; padding: 12px 16px; }
}
"""

CONTENT_JS = r"""
function pageStatus(page, state, fieldsByKey, savedValues, serverIssues) {
  if ((serverIssues || []).some(issue => issue.pageType === page.pageType)) return "error";
  let status = "saved";
  for (const item of page.fields) {
    const field = fieldsByKey[item.key];
    const value = state.values[item.key] || "";
    if (field.inputKind === "text" && value.length > field.hardChars) return "error";
    if (field.inputKind === "text" && value.length > field.recommendedChars) status = "warning";
    else if (value !== savedValues[item.key] && status === "saved") status = "dirty";
  }
  return status;
}

function statusLabel(status) {
  return {saved: "已儲存", dirty: "未儲存", warning: "接近上限", error: "需修正"}[status];
}

function fitPreview(root) {
  const stage = root.querySelector(".preview-stage");
  const documentRoot = root.querySelector(".preview-document");
  if (!stage || !documentRoot) return;
  documentRoot.style.transform = `scale(${stage.clientWidth / 1080})`;
}

function renderEditor(root, data, state, actions) {
  root.replaceChildren();
  root.className = "carousel-editor";
  root.dataset.role = "editor-shell";
  const rail = document.createElement("nav");
  rail.dataset.role = "page-rail";
  rail.setAttribute("aria-label", "七頁導覽");
  const form = document.createElement("section");
  form.dataset.role = "field-panel";
  const preview = document.createElement("section");
  preview.dataset.role = "preview";
  const current = data.pages.find(page => page.pageType === state.pageType);

  for (const page of data.pages) {
    const status = pageStatus(page, state, data.fieldsByKey, data.values, data.serverIssues);
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `${String(page.number).padStart(2, "0")} ${page.label}`;
    button.dataset.pageType = page.pageType;
    button.dataset.status = status;
    button.dataset.statusLabel = statusLabel(status);
    button.setAttribute("aria-current", page.pageType === state.pageType ? "page" : "false");
    button.addEventListener("click", () => {
      state.pageType = page.pageType;
      actions.persist();
      renderEditor(root, data, state, actions);
    });
    rail.append(button);
  }

  const heading = document.createElement("h3");
  heading.className = "panel-heading";
  heading.textContent = `${String(current.number).padStart(2, "0")}｜${current.label}`;
  form.append(heading);
  for (const field of current.fields) {
    const label = document.createElement("label");
    label.className = "field-row";
    label.textContent = field.label;
    const input = document.createElement(field.inputKind === "expression" ? "select" : "textarea");
    input.name = field.key;
    if (field.inputKind === "expression") {
      for (const value of field.options) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = data.expressionLabels[value];
        input.append(option);
      }
    }
    input.value = state.values[field.key];
    const refreshLimit = () => {
      if (field.inputKind !== "text") return;
      const counter = label.querySelector('[data-role="character-count"]');
      const count = input.value.length;
      counter.textContent = `${count} / ${field.recommendedChars}`;
      counter.dataset.limit = count > field.hardChars ? "hard" : count > field.recommendedChars ? "near" : "normal";
      input.setAttribute("aria-invalid", count > field.hardChars ? "true" : "false");
    };
    input.addEventListener("input", event => {
      state.values[field.key] = event.currentTarget.value;
      actions.markDirty();
      actions.updatePreview(field.key, event.currentTarget.value);
      refreshLimit();
      renderActionBar();
      for (const button of rail.querySelectorAll("button")) {
        const page = data.pages.find(item => item.pageType === button.dataset.pageType);
        const status = pageStatus(page, state, data.fieldsByKey, data.values, data.serverIssues);
        button.dataset.status = status;
        button.dataset.statusLabel = statusLabel(status);
      }
    });
    label.append(input);
    if (field.inputKind === "text") {
      const counter = document.createElement("small");
      counter.dataset.role = "character-count";
      label.append(counter);
      refreshLimit();
    }
    form.append(label);
  }

  const evidence = document.createElement("details");
  evidence.className = "locked-evidence";
  const evidenceLabel = document.createElement("summary");
  evidenceLabel.textContent = "查證來源（鎖定）";
  evidence.append(evidenceLabel);
  for (const item of current.lockedEvidence) {
    const line = document.createElement("p");
    const source = item.sourceIds.length ? ` [${item.sourceIds.join("、")}]` : "";
    line.textContent = `${item.label}${source}：${item.quotes.join("／") || "這段不需來源"}`;
    evidence.append(line);
  }
  form.append(evidence);

  const previewLabel = document.createElement("p");
  previewLabel.className = "preview-label";
  previewLabel.textContent = "同頁即時預覽";
  const stage = document.createElement("div");
  stage.className = "preview-stage";
  const previewRoot = document.createElement("div");
  previewRoot.className = "preview-document";
  previewRoot.innerHTML = current.previewHtml;
  stage.append(previewRoot);
  preview.append(previewLabel, stage);

  const actionBar = document.createElement("aside");
  actionBar.dataset.role = "action-bar";
  const statusText = document.createElement("span");
  statusText.className = "save-status";
  const save = document.createElement("button");
  save.type = "button";
  save.textContent = "儲存全部變更";
  save.addEventListener("click", actions.saveAll);
  const actionsGroup = document.createElement("div");
  actionsGroup.className = "action-buttons";
  const regenerate = document.createElement("button");
  regenerate.type = "button";
  regenerate.className = "secondary-action";
  regenerate.textContent = "重新產生";
  regenerate.addEventListener("click", actions.requestRegenerate);
  const research = document.createElement("button");
  research.type = "button";
  research.className = "secondary-action";
  research.textContent = "重新查證";
  research.addEventListener("click", actions.requestResearch);
  actionsGroup.append(regenerate, research, save);
  actionBar.append(statusText, actionsGroup);
  function renderActionBar() {
    const hardIssue = Object.entries(state.values).some(([key, value]) => {
      const field = data.fieldsByKey[key];
      return field && field.inputKind === "text" && value.length > field.hardChars;
    });
    save.disabled = !state.dirty || hardIssue;
    actionBar.dataset.status = hardIssue ? "invalid" : state.dirty ? "dirty" : "saved";
    statusText.textContent = hardIssue ? "有欄位超過上限" : state.dirty ? "有未儲存變更" : "所有變更已儲存";
  }
  renderActionBar();
  root.append(rail, form, preview, actionBar);
  for (const [key, value] of Object.entries(state.values)) actions.updatePreview(key, value);
  requestAnimationFrame(() => fitPreview(root));
}

export default function(component) {
  const {data, parentElement, setStateValue, setTriggerValue} = component;
  const editorRoot = parentElement.querySelector('[data-role="editor-shell"]');
  const storageKey = `daibu-carousel-${data.ideaId}`;
  const saved = JSON.parse(sessionStorage.getItem(storageKey) || "null");
  const preservedPageType = saved && data.pages.some(
    page => page.pageType === saved.pageType
  ) ? saved.pageType : data.pages[0].pageType;
  if (saved && saved.revision !== data.revision) sessionStorage.removeItem(storageKey);
  const state = saved && saved.revision === data.revision
    ? saved
    : {revision: data.revision, pageType: preservedPageType, values: {...data.values}, dirty: false};
  const persist = () => sessionStorage.setItem(storageKey, JSON.stringify(state));
  const beforeUnload = event => { if (state.dirty) { event.preventDefault(); event.returnValue = ""; } };
  const syncBeforeUnload = () => {
    window.removeEventListener("beforeunload", window.__daibuCarouselBeforeUnload);
    window.__daibuCarouselBeforeUnload = beforeUnload;
    if (state.dirty) window.addEventListener("beforeunload", beforeUnload);
  };
  const markDirty = () => {
    if (!state.dirty) {
      state.dirty = true;
      setStateValue("dirty", true);
      syncBeforeUnload();
    }
    persist();
  };
  const updatePreview = (key, value) => {
    const field = data.fieldsByKey[key];
    editorRoot.querySelectorAll(`[data-edit-key="${CSS.escape(key)}"]`).forEach(node => {
      if (field.inputKind === "expression") {
        const template = document.createElement("template");
        template.innerHTML = data.expressionPreviews[value];
        node.replaceChildren(template.content.cloneNode(true));
      } else node.textContent = value;
    });
  };
  const saveAll = () => setTriggerValue("save", {revision: data.revision, values: state.values});
  const requestRegenerate = () => setTriggerValue("requestRegenerate", true);
  const requestResearch = () => setTriggerValue("requestResearch", true);
  syncBeforeUnload();
  renderEditor(editorRoot, data, state, {
    persist, markDirty, updatePreview, saveAll, requestRegenerate, requestResearch
  });
  new ResizeObserver(() => fitPreview(editorRoot)).observe(editorRoot);
}
"""


@dataclass(frozen=True)
class ContentEditorEvent:
    dirty: bool
    save_payload: Mapping[str, object] | None
    request_regenerate: bool = False
    request_research: bool = False


def normalize_event(result) -> ContentEditorEvent:
    if result is None:
        return ContentEditorEvent(False, None)
    dirty = bool(getattr(result, "dirty", False))
    save = getattr(result, "save", None)
    save_payload = dict(save) if isinstance(save, Mapping) else None
    return ContentEditorEvent(
        dirty,
        save_payload,
        bool(getattr(result, "requestRegenerate", False)),
        bool(getattr(result, "requestResearch", False)),
    )


def mount_content_editor(
    payload: Mapping[str, object],
    *,
    key: str,
) -> ContentEditorEvent:
    content_component = st.components.v2.component(
        "daibu_carousel_content_editor",
        html=CONTENT_HTML,
        css=CONTENT_CSS,
        js=CONTENT_JS,
        isolate_styles=True,
    )
    result = content_component(
        key=key,
        data=dict(payload),
        default={"dirty": False},
        height="content",
        on_dirty_change=lambda: None,
        on_save_change=lambda: None,
        on_requestRegenerate_change=lambda: None,
        on_requestResearch_change=lambda: None,
    )
    return normalize_event(result)
