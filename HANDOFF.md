# HANDOFF — 呆一布選題大腦

> 2026-07-31 更新。「一布懂 AI 新創」七頁輪播敘事視覺已完成，待分支合併與 main 複驗。

## 本輪目標與驗收

依 `docs/superpowers/specs/2026-07-31-一布懂-ai-新創輪播敘事視覺-design.md`
把輪播改成：系列縮圖可辨識、封面以好奇鉤子開場、角色參與敘事、七張有不同節奏，
最後才加入少量「呆一布 AI 實驗室」裝飾。只改渲染、prompt 與預覽，不改資料庫 schema、
來源證據或官方 Logo 規則。

## 本輪狀態

- **系列與封面**：封面固定顯示 80px「一布懂 AI 新創」，以既有 `cover.heading`
  當主鉤子；不再顯示產業分類與來源。新草稿 prompt 要求 12–24 字、有來源、非
  clickbait 的好奇句。公司名依長度使用 short／medium／long 三段字級。
- **七頁節奏**：01／07 為 Hero、02／03 為 Editorial、04／05／06 為 Evidence；
  閱讀情緒為好奇 → 輪廓 → 痛點 → 理解 → 改變 → 判斷 → 記住。
- **角色敘事**：七頁都使用 `assets/mascot/` 既有 SVG。封面改 `think`；右側的
  `point` 會翻向正文；02／05／06 的角色移到下半部承接原本空白。真實 DOM 量測確認
  角色、文字、Logo、圖解與來源沒有重疊。
- **去 AI 模板感**：移除 dots／stripes、tiny 英文 Lab 標籤與單側 accent border；
  只保留中文「呆一布 AI 實驗室」與頁次。內容區塊改完整輪廓，配色限品牌藍、淺藍、
  珊瑚橘與灰階。
- **來源**：第 2–7 張使用卡片底部保留帶，30px、對比至少 4.5:1；封面完全不放來源。
- **響應式**：Streamlit 預覽桌機兩欄、375px 手機單欄；實測
  `scrollWidth = innerWidth = 375`、七張 client width 275／natural width 1080，
  DOM 順序 01→07，console 0 errors／0 warnings。
- **視覺自檢**：兩輪各只截桌機與手機；最終檔案為 `.screenshots/desktop.png`、
  `.screenshots/mobile.png`。層次、留白、字體、配色、對齊、響應式、狀態、動效皆通過。
- **測試**：相關測試 `115 passed in 22.89s`；feature branch 全套
  `383 passed, 11 deselected, 1 warning in 44.42s`，`git diff --check` 待文件提交前複驗。
- **資料安全**：視覺操作只用 `/tmp/daibu-carousel-story-test.db`、port 8502、
  `/tmp/daibu-carousel-story-logos/`。真實 `daibu.db` mtime 前後均為 `1785433278`。

## 下一步

1. 提交本交接文件。
2. 合併 `codex/carousel-story-redesign` 回 `main`，在 main 重跑全套測試。
3. 推送 `origin/main`；本專案沒有 production 部署流程，不另建正式站。

## 最容易踩的坑

- 舊草稿重新出圖就會套新版；只有重新產生草稿才會得到新的好奇鉤子 prompt。
- 封面仍保留「產業分類」資料欄位以相容舊 DB，只是不渲染；不要為了隱藏它做 migration。
- 來源底帶是保留的 grid row，不要改成 absolute overlay 或 `margin-top: auto` 壓住內容。
