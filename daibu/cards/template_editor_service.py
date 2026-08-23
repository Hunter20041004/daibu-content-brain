from dataclasses import dataclass
import sqlite3
from typing import Mapping

from daibu import db
from daibu.cards import layout_repository, layout_validation, render
from daibu.cards.layout_schema import LayoutValidationError, parse_layout
from daibu.cards.template_stress import TemplateStressCase


@dataclass(frozen=True)
class TemplateIssue:
    page_type: str | None
    element_id: str | None
    message: str


@dataclass(frozen=True)
class TemplateSaveResult:
    version: layout_repository.TemplateVersion | None
    issues: tuple[TemplateIssue, ...]


@dataclass(frozen=True)
class TemplateUpgradeResult:
    meta: db.CarouselDraftMeta | None
    issues: tuple[TemplateIssue, ...]


def _validate(layout, stress_cases):
    issues=[]
    for case in stress_cases:
        pages_html=render.draft_html_pages(case.draft,case.company,case.asset,layout)
        for issue in layout_validation.inspect_pages(pages_html):
            converted=TemplateIssue(issue.page_type,issue.element_id,f"{case.label}：{issue.message}")
            if converted not in issues: issues.append(converted)
    return tuple(issues)


def save_template_version(conn: sqlite3.Connection,theme_id:int,base_version_id:int,raw_layout:Mapping[str,object],stress_cases:tuple[TemplateStressCase,...])->TemplateSaveResult:
    try: base=layout_repository.get_version(conn,base_version_id)
    except ValueError as error: return TemplateSaveResult(None,(TemplateIssue(None,None,str(error)),))
    if base.theme_id!=theme_id: return TemplateSaveResult(None,(TemplateIssue(None,None,"基礎版本不屬於這個內容系列。"),))
    try: layout=parse_layout(raw_layout)
    except LayoutValidationError as error: return TemplateSaveResult(None,(TemplateIssue(None,error.element_id,str(error)),))
    issues=_validate(layout,stress_cases)
    if issues:return TemplateSaveResult(None,issues)
    return TemplateSaveResult(layout_repository.create_version(conn,theme_id,layout),())


def set_active_template_version(conn,theme_id,version_id):
    layout_repository.set_active_version(conn,theme_id,version_id)
    return layout_repository.get_version(conn,version_id)


def upgrade_draft_template(conn,idea_id,theme_id,draft,company,asset,target_version_id):
    current=db.get_carousel_draft_meta(conn,idea_id)
    try: target=layout_repository.get_version(conn,target_version_id)
    except ValueError as error:return TemplateUpgradeResult(current,(TemplateIssue(None,None,str(error)),))
    if current is None or target.theme_id!=theme_id:return TemplateUpgradeResult(current,(TemplateIssue(None,None,"目標模板不屬於這篇貼文的內容系列。"),))
    rendered=render.draft_html_pages(draft,company,asset,target.layout,allow_logo_placeholder=True)
    issues=layout_validation.inspect_pages(rendered)
    if issues:return TemplateUpgradeResult(current,tuple(TemplateIssue(i.page_type,i.element_id,i.message) for i in issues))
    return TemplateUpgradeResult(db.upgrade_carousel_template(conn,idea_id,target.id),())
