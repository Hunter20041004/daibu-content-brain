# 待人類裁決

## 種子來源的穩定抓取方式

- TLDR AI、Ben's Bites 目前沒有確認可長期使用的公開 RSS。v1 先設為 `manual`，不自動抓取；若確認官方 feed URL，再改為 `rss`。
- 「本週熱門 Claude/Codex Skill」沒有穩定排行榜。v1 以 GitHub 搜尋、官方 releases 與 Awesome Claude Code 手動來源並用；未來需決定排名公式（新建時間、增星速度或人工策展）。
- 部分網站的 category/feed URL 可能改版。真實 RSS 契約目前只固定驗證 TechCrunch；其他來源在實際使用後再逐一確認並補契約測試。

## 候選「淘汰」的資料語意

- spec 要求候選卡有「淘汰」，但流水線合法狀態只有候選／採用／草稿／已排程／已發。v1 暫定淘汰即刪除候選，不新增第六種狀態；若未來需要復盤淘汰原因，應改成可封存的 rejected 狀態或獨立淘汰紀錄。

## Streamlit 雙模式圖表色盤

- 2026-07-24 實測 Streamlit 1.60：`chartCategoricalColors` 只能放在共用 `[theme]`，放在 `[theme.light]`／`[theme.dark]` 會出現「not a valid config option」警告。因此 v1 先共用品牌藍綠、次級藍、Highlight 三色；若未來需要各自最佳化深色圖表，再改由圖表層依模式指定。
