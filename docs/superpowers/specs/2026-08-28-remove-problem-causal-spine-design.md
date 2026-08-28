# 第 3 頁移除因果導引線設計

日期：2026-08-28

## 目標

從公司介紹輪播第 3 頁「它想優化什麼」完整移除三張問題卡左側的粉紅因果導引圖形，包括垂直虛線、三個圓點與底部箭頭。三張問題卡、卡片內文字與既有座標維持不變。

## 核准方案

直接從正式 Renderer 移除 `causal-spine` 裝飾 DOM，並刪除只服務這個圖形的 CSS。既有 v4 layout registry 仍保留 `spine` 幾何資料，以便舊版型能正常讀取；規則新增 `rendered=False`，讓驗證器與編輯器知道它是已退役、不可見也不可選取的相容欄位。不修改 schema 版本、layout JSON、migration 或 SQLite 資料。

不採用只加 `display: none` 的方案，因為那會留下沒有產品作用的 DOM 與 CSS；也不以其他線條或圖示取代，避免超出「整條拿掉」的要求。

## 影響範圍

- `daibu/cards/render.py`：第 3 頁不再輸出 `data-visual="causal-spine"`。
- `daibu/cards/templates/sticky-notebook-v1.css`：刪除 `.causal-spine`、`::before`、`::after` 規則。
- `daibu/cards/layout_registry.py`：將 v4 `spine` 標成不呈現；v3 定義維持原狀，確保 migration 契約不變。
- `daibu/cards/layout_validation.py`、`template_editor_payload.py`、`template_editor_component.py`：忽略已退役元素，且不把它送進可選取的編輯器清單。
- `tests/test_cards_render.py`：把舊「必須存在一次」斷言改為「正式 DOM 不存在」，並保留三張問題卡與其文字層存在的驗證。
- `HANDOFF.md`：記錄產品結果、測試、視覺 QA、推送與正式服務證據。

## 資料流與相容性

既有內容與版型資料照常交給 Renderer；Renderer 仍產出第 3 頁標題、兩張脈絡卡、三張問題卡、文字與吉祥物，只略過純裝飾的因果線。編輯器預覽與 PNG 共用 Renderer，因此兩邊會同步消失，不會產生版本分岔。

歷史 v3／v4 模板可能包含 `spine` 幾何欄位，因此仍接受並保留該欄位；只是正式 Renderer、版面驗證與編輯器不再呈現或要求它可見。不建立新 schema 或模板版本，也不改 SUN 草稿綁定或 content revision。

## TDD 與驗收

1. Red：Renderer 測試先要求第 3 頁 DOM 不含 `causal-spine`，現況會因仍輸出該元素而失敗。
2. Green：移除 Renderer 裝飾節點，使測試通過。
3. Refactor：刪除失去用途的 CSS，確認 repository 內沒有正式程式仍引用 `causal-spine`。
4. 相容性驗證：舊 v3 migration 與 v4 layout 仍可讀取；payload 不暴露 `spine`；瀏覽器不出現同步錯誤或透明選取區。
5. 聚焦驗證：Renderer、layout validation、PNG 與模板編輯器相關測試全綠；第 3 頁仍有三張問題卡且版面檢查零問題。
6. 視覺 QA：隔離服務完成兩輪 1280×800 與 375×812 截圖，確認線、圓點、箭頭完全消失，卡片與文字未位移，手機 overflow 為 0，無 Streamlit exception 或 critical console error。
7. 收尾：功能分支與 main 各跑一次完整 pytest；合併、推送並核對遠端 SHA；重啟既有 `io.daibu.content-brain`，從正式 8501 驗證第 3 頁與服務健康。

## 安全、成本與限制

沒有資料遷移、新套件、外部 API、LLM 或付費呼叫。唯一使用者可見變化是第 3 頁不再顯示該裝飾圖形；本輪不重新排列卡片，也不修改其他頁面。
