"""Pure state decisions for the guided content workstation."""

from dataclasses import dataclass
from typing import Protocol, Sequence


WORKFLOW_STEPS = ("research", "decide", "write", "carousel")


class _IdeaState(Protocol):
    status: str
    body: str
    theme_id: int | None


class _SeriesState(Protocol):
    id: int | None
    name: str
    weekday: int


@dataclass(frozen=True)
class WorkflowState:
    current: str
    completed: tuple[str, ...]
    candidate_count: int
    adopted_count: int


@dataclass(frozen=True)
class Mission:
    theme_id: int | None
    step: str
    label: str


@dataclass(frozen=True)
class ChecklistItem:
    key: str
    label: str
    state: str


def derive_workflow(ideas: Sequence[_IdeaState]) -> WorkflowState:
    candidates = [idea for idea in ideas if idea.status == "候選"]
    adopted = [idea for idea in ideas if idea.status == "採用"]
    if any(not idea.body.strip() for idea in adopted):
        return WorkflowState(
            current="write",
            completed=("research", "decide"),
            candidate_count=len(candidates),
            adopted_count=len(adopted),
        )
    if adopted:
        return WorkflowState(
            current="carousel",
            completed=("research", "decide", "write"),
            candidate_count=len(candidates),
            adopted_count=len(adopted),
        )
    if candidates:
        return WorkflowState(
            current="decide",
            completed=("research",),
            candidate_count=len(candidates),
            adopted_count=len(adopted),
        )
    return WorkflowState(
        current="research",
        completed=(),
        candidate_count=0,
        adopted_count=len(adopted),
    )


def next_mission(
    themes: Sequence[_SeriesState],
    ideas: Sequence[_IdeaState],
    today_weekday: int,
) -> Mission:
    for theme in themes:
        theme_ideas = [idea for idea in ideas if idea.theme_id == theme.id]
        state = derive_workflow(theme_ideas)
        if state.current == "write":
            return Mission(
                theme_id=theme.id,
                step="write",
                label=f"完成「{theme.name}」的貼文內容",
            )
        if state.current == "carousel":
            return Mission(
                theme_id=theme.id,
                step="carousel",
                label=f"完成「{theme.name}」的輪播圖片",
            )
        if state.current == "decide":
            return Mission(
                theme_id=theme.id,
                step="decide",
                label=(
                    f"挑選「{theme.name}」的 "
                    f"{state.candidate_count} 則候選"
                ),
            )
    if themes:
        theme = next(
            (item for item in themes if item.weekday == today_weekday),
            themes[0],
        )
        return Mission(
            theme_id=theme.id,
            step="research",
            label=f"替「{theme.name}」找題材",
        )
    return Mission(None, "research", "建立第一個內容系列")


def carousel_checklist(
    *,
    has_company: bool,
    source_count: int,
    has_logo: bool,
    has_draft: bool,
    has_pngs: bool,
) -> tuple[ChecklistItem, ...]:
    requirements = (
        ("company", "公司名稱", has_company),
        ("evidence", "這篇內容的查證證據", source_count > 0),
        ("logo", "官方 Logo", has_logo),
        ("draft", "七頁草稿", has_draft),
        ("images", "七張圖片", has_pngs),
    )
    current_found = False
    items = []
    for key, label, complete in requirements:
        if complete:
            state = "complete"
        elif not current_found:
            state = "current"
            current_found = True
        else:
            state = "blocked"
        items.append(ChecklistItem(key=key, label=label, state=state))
    return tuple(items)
