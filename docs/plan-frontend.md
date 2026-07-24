# 前端品牌重構 — TDD 實作計畫

> **For agentic workers:** 照本計畫**逐一 Task** 實作。每個 Step 用 `- [ ]` 追蹤。
> **嚴格 TDD**：先寫失敗測試 → 跑它確認紅 → 最小實作 → 跑它確認綠 → 重構 → commit。
> **一次一個失敗測試，垂直切片，禁止水平切片**（不可先寫完所有測試再寫所有實作）。
> 先讀 `docs/specs/2026-07-24-前端品牌重構-design.md` 與 `AGENTS.md`。

**Goal:** 把選題大腦的四頁前端換成 DIVE web 的品牌視覺，並重排版面；後端邏輯零改動。

**指令：** 測試 `.venv/bin/pytest`；啟動 `.venv/bin/streamlit run app.py`。

## Global Constraints

- 只改 `app.py`、`pages/`、`daibu/ui.py`、`.streamlit/config.toml`；新增 `daibu/theme.py`、`tests/test_theme.py`。
  **不得改動** `daibu/db.py`、`selection.py`、`pipeline.py`、`performance.py`、`seeds.py`、`llm/`、`fetch/`。
- `daibu/theme.py` **不得 import streamlit**（要能在沒有 Streamlit runtime 的情況下測）。
- 顏色、字級只能來自 `daibu/theme.py`；`pages/` 與 `ui.py` 不得出現寫死的色碼。
- 白色文字**永遠不可**放在 `#6FC1CC` 上（對比 2.06:1）。

---

## Task 1：先讓測試基線恢復全綠

現在 `tests/test_app_smoke.py::test_selection_uses_configured_gate_line` 在**週一／週三／週五會紅**：
種子資料有三個範例主題分別排在週一、週三、週五，測試又自己加了一個排在今天的主題，
於是「今天該發的主題」變成兩個，`generate_for_theme` 被呼叫兩次，但測試斷言只呼叫一次。
程式行為是對的（一天有幾個主題就跑幾次），是測試把「今天只有一個主題」寫死了。

- [ ] **Step 1: 改測試斷言** — 把 `assert received_gate_lines == ["自訂守門線"]` 改成不依賴數量的斷言：
```python
assert received_gate_lines  # 至少被呼叫一次
assert set(received_gate_lines) == {"自訂守門線"}  # 每一次傳的都是設定的守門線
```
- [ ] **Step 2: 跑測試確認綠** — `.venv/bin/pytest -q` → `44 passed`（3 個 contract 測試維持 deselected）
- [ ] **Step 3: Commit** — `fix: 修正隨星期而失敗的守門線測試`

---

## Task 2：對比度計算（tracer bullet）

**Files:** Create `daibu/theme.py`, `tests/test_theme.py`

**Interfaces — Produces:** `theme.relative_luminance(hex: str) -> float`；`theme.contrast_ratio(a: str, b: str) -> float`

- [ ] **Step 1: 寫失敗測試** `tests/test_theme.py`
```python
from daibu import theme

def test_contrast_ratio_black_on_white_is_21():
    assert round(theme.contrast_ratio("#000000", "#FFFFFF"), 1) == 21.0
```
- [ ] **Step 2: 跑測試確認紅** — 模組不存在
- [ ] **Step 3: 最小實作** — WCAG 相對亮度公式（sRGB 線性化後加權 0.2126/0.7152/0.0722），
      `contrast_ratio = (亮 + 0.05) / (暗 + 0.05)`。大小寫與有無 `#` 都要吃。
- [ ] **Step 4: 跑測試確認綠**
- [ ] **Step 5: Commit** — `feat: 色彩對比度計算`

---

## Task 3：色彩 token 表

**Interfaces — Produces:** `theme.LIGHT: dict[str, str]`、`theme.DARK: dict[str, str]`
（鍵：`BRAND_PRIMARY`、`BRAND_SECONDARY`、`INK`、`SURFACE`、`CANVAS`、`HIGHLIGHT`、`BORDER`）

一次一個測試，寫一個、實作一個、綠了再寫下一個：

- [ ] **Step 1** 測試：淺色 token 值正確（`LIGHT["BRAND_PRIMARY"] == "#6FC1CC"`、`LIGHT["INK"] == "#0E0E2C"`、
      `LIGHT["CANVAS"] == "#E9F6FF"`、`LIGHT["SURFACE"] == "#FAFCFE"`）→ 紅 → 實作 `LIGHT` → 綠
- [ ] **Step 2** 測試：深色 token 值正確（`DARK["INK"] == "#FAFCFE"`、`DARK["CANVAS"] == "#0E0E2C"`、
      `DARK["SURFACE"] == "#171733"`）→ 紅 → 實作 `DARK` → 綠
- [ ] **Step 3** 測試 **主要按鈕不可白字**（本次最重要的一條）：
```python
def test_primary_button_must_use_ink_not_white():
    primary = theme.LIGHT["BRAND_PRIMARY"]
    assert theme.contrast_ratio(theme.LIGHT["INK"], primary) >= 4.5
    assert theme.contrast_ratio("#FFFFFF", primary) < 4.5   # 證明白字不合格，別再用
```
      → 紅或綠視實作而定 → 補齊 → 綠
- [ ] **Step 4** 測試：兩種模式的內文對比都過 AA
```python
import pytest

@pytest.mark.parametrize("palette", [theme.LIGHT, theme.DARK])
def test_body_text_passes_aa(palette):
    assert theme.contrast_ratio(palette["INK"], palette["CANVAS"]) >= 4.5
    assert theme.contrast_ratio(palette["INK"], palette["SURFACE"]) >= 4.5
```
- [ ] **Step 5** 測試：深色模式的次級色不得沿用 `#32738F`（對比只有 3.56:1）
```python
def test_dark_secondary_is_readable():
    assert theme.DARK["BRAND_SECONDARY"] != "#32738F"
    assert theme.contrast_ratio(theme.DARK["BRAND_SECONDARY"], theme.DARK["CANVAS"]) >= 4.5
```
- [ ] **Step 6: 重構**（兩份 dict 的共用鍵抽成常數清單）後全綠
- [ ] **Step 7: Commit** — `feat: 品牌色 token 與無障礙紅線`

---

## Task 4：字型與字級 token

**Interfaces — Produces:** `theme.FONT_STACK: str`、`theme.TYPE_SCALE: list[str]`、`theme.TYPE_WEIGHTS: list[int]`

- [ ] **Step 1: 失敗測試**
```python
def test_font_stack_covers_latin_and_chinese():
    assert "Figtree" in theme.FONT_STACK
    assert "Noto Sans TC" in theme.FONT_STACK

def test_type_scale_covers_h1_to_h6():
    assert len(theme.TYPE_SCALE) == 6 and len(theme.TYPE_WEIGHTS) == 6
    assert theme.TYPE_SCALE[0] == "2.5rem"      # h1 = 設計稿 Header 1 的 40px
    assert theme.TYPE_WEIGHTS[0] == 800          # Extra Bold
```
- [ ] **Step 2: 紅** → **Step 3: 實作**（依 spec 第 4.3、4.4 節）→ **Step 4: 綠** → **Step 5: Commit** `feat: 字型與字級 token`

---

## Task 5：設定檔契約測試 + 改寫 config.toml

防止「改了 Python、忘了改設定檔」的漂移。

- [ ] **Step 1: 失敗測試** `tests/test_theme.py`
```python
import tomllib, pathlib

def test_config_toml_matches_tokens():
    cfg = tomllib.loads(pathlib.Path(".streamlit/config.toml").read_text())
    light, dark = cfg["theme"]["light"], cfg["theme"]["dark"]
    assert light["backgroundColor"].upper() == theme.LIGHT["CANVAS"]
    assert light["textColor"].upper() == theme.LIGHT["INK"]
    assert light["primaryColor"].upper() == theme.LIGHT["BRAND_PRIMARY"]
    assert dark["backgroundColor"].upper() == theme.DARK["CANVAS"]
    assert dark["textColor"].upper() == theme.DARK["INK"]
```
- [ ] **Step 2: 紅** → **Step 3: 改寫 `.streamlit/config.toml`**：`[theme]` 放字型／圓角／字級，
      `[theme.light]`、`[theme.dark]` 各放一套顏色（鍵名見 spec 7.2）。
      `font` 用 `"Figtree:https://fonts.googleapis.com/css2?family=Figtree:wght@400..900&display=swap"` 格式。
- [ ] **Step 4: 綠** → **Step 5: Commit** — `feat: Streamlit 雙模式主題設定`

---

## Task 6：CSS 產生

**Interfaces — Produces:** `theme.css(mode: str = "light") -> str`

- [ ] **Step 1: 失敗測試**（一次一個，逐條加）
```python
def test_css_declares_tokens_as_variables():
    css = theme.css()
    assert "--brand-primary: #6FC1CC" in css
    assert theme.FONT_STACK in css

def test_css_forces_dark_text_on_primary_button():
    css = theme.css()
    assert "#FFFFFF" not in css.upper().split("--brand")[0]  # 主要按鈕區塊不得出現白字
    assert "scale(0.97)" in css          # 按下回饋
    assert "focus-visible" in css        # 焦點樣式
    assert "prefers-reduced-motion" in css
```
- [ ] **Step 2: 紅** → **Step 3: 實作** `css()`：輸出 CSS 變數、按鈕（含 `:active` 縮放與 `transition: transform 160ms`）、
      焦點框、卡片、chip、`@media (hover: hover) and (pointer: fine)` 的 hover、`prefers-reduced-motion` 區塊。
      **禁止 `transition: all`。**
- [ ] **Step 4: 綠** → **Step 5: 重構** → **Step 6: Commit** — `feat: 品牌 CSS 產生器`

---

## Task 7：品牌標誌元件

**Interfaces — Produces:** `ui.brand_lockup(size: int = 44) -> str`（回傳 HTML 字串，供 `st.markdown(..., unsafe_allow_html=True)`）

- [ ] **Step 1: 失敗測試** `tests/test_ui.py`
```python
def test_brand_lockup_inlines_svg_not_img():
    html = ui.brand_lockup()
    assert "<svg" in html          # 必須內嵌，CSS 變數才會生效
    assert "<img" not in html
    assert "呆一布" in html
```
- [ ] **Step 2: 紅** → **Step 3: 實作**（讀 `assets/mascot.svg` 內嵌）→ **Step 4: 綠** → **Step 5: Commit** `feat: 品牌標誌元件`

---

## Task 8：首頁重排（今日戰情）

- [ ] **Step 1: 失敗測試** `tests/test_app_smoke.py`
```python
def test_home_shows_single_primary_action(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))
    app = AppTest.from_file(PROJECT_ROOT / "app.py"); app.run()
    assert not app.exception
    primary = [b for b in app.button if b.type == "primary"]
    assert len(primary) == 1          # 首頁只有一個主要行動
```
- [ ] **Step 2: 紅** → **Step 3: 實作** spec 5.1（hero + 今日焦點列 + 流水線縮影）→ **Step 4: 綠** → **Step 5: Commit** `feat: 首頁改為今日戰情版面`

---

## Task 9：選題頁左右分欄

- [ ] **Step 1: 失敗測試** — 頁面載入不報錯、候選卡顯示守門線分數、守門線全文出現在左欄。
- [ ] **Step 2: 紅** → **Step 3: 實作** spec 5.2（分欄、分數視覺化、採用／微調／淘汰一列、空狀態）
      → **Step 4: 綠** → **Step 5: Commit** `feat: 選題頁改為審核式分欄版面`

---

## Task 10：流水線改真看板

- [ ] **Step 1: 失敗測試** — 五個狀態的欄頭都在、卡片不再內嵌編輯表單（`len(app.text_area) == 0`）。
- [ ] **Step 2: 紅** → **Step 3: 實作** spec 5.3（極簡卡片 + `st.dialog` 編輯）
      → **Step 4: 綠** → **Step 5: Commit** `feat: 流水線改為可掃視看板`

---

## Task 11：成效頁重排

- [ ] **Step 1: 失敗測試** — 「下週建議」出現在圖表之前（比對元素順序）、頁面載入不報錯。
- [ ] **Step 2: 紅** → **Step 3: 實作** spec 5.4 → **Step 4: 綠** → **Step 5: Commit** `feat: 成效頁以建議為主體`

---

## 收尾檢查（全部 Task 做完後）

- [ ] `.venv/bin/pytest` 全綠。
- [ ] `streamlit run app.py` 人工走一遍四頁，對照 spec 第 8 節的驗收標準逐條打勾。
- [ ] 把系統外觀切成深色再走一遍，確認沒有「一半白一半黑」。
- [ ] 開啟系統的「減少動態效果」再走一遍。
- [ ] 用鍵盤 Tab 走完四頁，確認每個可聚焦元素都看得到焦點框。
- [ ] 有疑點寫進 `docs/open-questions.md`，不自行更動產品方向。
