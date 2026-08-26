# HANDOFF — 七頁內容與系列模板編輯器完成

> 2026-08-23 更新。使用者選擇的 A→B→C 已完整實作：安全排版基礎、七頁內容編輯器、系列模板畫布與不可變版本生命週期均完成。

## 2026-08-26 六頁公司介紹輪播 v56 精修

- **產品能力**：保留 v55 為不可變版本，新增 `company-neutral-seven-pages-sticky-56.html`；第 2–5 頁標題放大並下移，第 2 頁定位圖與 Logo 分離，第 3 頁內容上移、因果線右移且正文放大，第 4 頁流程與補充卡放大，第 5 頁改用「帶來的價值」，第 6 頁收斂成兩句品牌 CTA。
- **使用者體驗**：內頁標題依序為「它在做什麼？」、「它想優化什麼？」、「AI 扮演什麼樣的角色？」、「它怎麼實際改善現有流程？」；兩個長標題採均衡兩行，沒有孤立尾詞。CTA 只顯示「追蹤呆一布 AI 共學實驗室」與「帶你看更多最新 AI 資訊」。
- **技術結構**：所有 v56 幾何覆寫集中在 `data-v56-layout="expanded-interiors"` 範圍內；新增 `v56-copy-contract.py` 與 `v56-layout-contract.py`，既有敘事與 CTA 契約同步改為本輪核可文字。v48、v50、v53、v54、v55 均未覆蓋。
- **資料流程**：既有 `CarouselDraft` 內容鍵 → 六頁語意 DOM → v56 範圍化排版 → 瀏覽器預覽。所有 `data-content-key` 與 hidden 相容欄位保留；正式 Renderer、AI 提示詞、SQLite 與正式服務未修改。
- **設計理由與備援**：主方案用同一組 7.8cqw 內頁標題建立跨頁層次，再針對第二至四頁調整內容群組，不以縮小正文換取空間。備援是正式接線後依真實最長文案為個別頁建立流體字級；目前不採用，因原型仍需先鎖住一致視覺語言。
- **安全與成本**：沒有外部 API、付費操作、資料寫入、新依賴或正式部署；v56 與契約仍在 `.gitignore` 內的本機原型資料夾。剩餘風險是極長公司名、真實 Logo 比例與生成文字長度，正式接線時仍需三公司以上壓力 fixture。
- **TDD 證據**：文案契約先在 v55 抓到舊標題、舊摘要與三段 CTA；標題契約先抓到缺少 v56 marker；第 2 頁先量到定位圖與 Logo 僅 1px；第 3 頁先量到因果線位於欄間中心左側 1.91px、正文僅畫布寬 1.55%；第 4 頁先量到標題與流程間距僅 0.35%。第一輪視覺 QA 再以長標題行寬比抓到第 4 頁第二行過短（0.418），加上均衡換行後轉綠。
- **原型驗證**：v56 文案、幾何、六頁結構、簡潔敘事、圖示分配、公司優先封面、逐頁精修、敘事密度、直角密度、便利貼系統、便利貼材質、第 3／4 頁密度、第 3 頁故事、社群 CTA，以及兩個 JS schema／手帳連續性契約全部通過。
- **完整測試**：隔離分支為 `739 passed, 16 deselected, 1 warning in 199.97s`；fast-forward 合回 `main` 後重跑為 `739 passed, 16 deselected, 1 warning in 223.29s`。唯一 warning 是既有 Starlette／httpx 棄用提醒。
- **視覺 QA**：兩輪各完成 1280×800／375×812。最終層次、間距節奏、LINE Seed 字體、粉彩三色、左右基線與微動效皆合格；靜態原型不涉及載入／錯誤／空資料狀態。375px 為 `scrollWidth=clientWidth=375`、六頁均 `overflow:false`、console 0 errors／0 warnings。截圖：`.screenshots/v56-polish-final-desktop.png`、`.screenshots/v56-polish-final-mobile.png`。
- **剩餘限制**：v56 仍是本機核可原型，尚未接入正式自動產圖。下一輪接線需同步調整生成提示詞、正式六頁資料契約、Renderer 與 PNG 長文字壓力測試。
- **規格與計畫**：`docs/superpowers/specs/2026-08-26-six-page-carousel-v56-polish-design.md`、`docs/superpowers/plans/2026-08-26-six-page-carousel-v56-polish.md`。

## 2026-08-26 六頁公司介紹輪播 v55

- **產品能力**：將 v54 收斂為六張可見頁面：公司主體封面、公司定位、流程優化機會、AI 運作方式、使用前後差異、置中社群 CTA。原本「哪些訊號證明它值得關注」頁已移除。
- **使用者體驗**：封面不再顯示右上產業分類；第 2–5 頁標題改為「它在做什麼？」、「它想優化什麼？」、「AI 怎麼做到的？」、「用了，差在哪？」。第 3 頁改以既有流程、優化空間、釋放價值說明，不預設舊流程失效。桌機預覽由四欄改成均衡 3×2，手機維持單欄。
- **技術結構**：v48、v50、v53、v54 全部保留，新候選為 `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-55.html`。可見 DOM 角色為 `hook → identity → opportunity → mechanism → outcome → cta`；原 why-care 與產業分類鍵放入 hidden 相容區。
- **資料流程**：現有 `CarouselDraft` 仍可提供全部舊內容鍵；v55 只顯示六頁需要的欄位，被刪除頁面的 14 個 why-care 欄位與產業欄位不渲染。正式 schema、Renderer、AI 提示詞與 SQLite 未修改。
- **設計理由與備援**：主方案直接刪除使用者不需要的第 6 頁，將靶心、循環、成長 SVG 分別移到第 2、3、5 頁支援閱讀；比勉強替弱頁換題更俐落。備援是在正式接線時再做欄位 schema 遷移；目前先隱藏舊欄位，換取回溯相容。
- **安全與成本**：沒有資料寫入、外部 API、新依賴、付費操作或正式服務異動；v55 仍是 `.gitignore` 內的本機視覺原型。
- **TDD 證據**：六頁結構契約先在 v54 抓到 7 頁／`07` 頁碼；簡潔敘事契約先抓到四個舊長標題；圖示分配契約先得到空陣列。三個垂直切片各自紅→綠。最終 14 項原型契約全部通過。
- **完整測試**：隔離分支為 `739 passed, 16 deselected, 1 warning in 176.51s`；fast-forward 合回 `main` 後重跑為 `739 passed, 16 deselected, 1 warning in 221.51s`。唯一 warning 是既有 Starlette／httpx 棄用提醒。
- **視覺 QA**：第一輪抓到沿用四欄造成卡片過小與第二列大片空白，改為 3×2。最終又以長公司名壓力契約抓到三行裁切，改為 `7.2cqw` 加底部字形安全內距；第 4 頁間距契約由未校準的絕對 px 改成已知 220px 合格版校準出的比例。最終 375px 為 `scrollWidth=clientWidth=375`、六頁均 `overflow:false`、console 0 errors／0 warnings。截圖為 `.screenshots/six-page-narrative-final-desktop.png` 與 `.screenshots/six-page-narrative-final-mobile.png`。
- **剩餘限制**：目前仍是核可用原型，尚未接入自動產圖 Renderer。正式接線時需同步調整生成提示詞、六頁資料契約與 PNG 長文字壓力測試，之後才能讓工具真正逐頁產出這個版型。
- **規格與計畫**：`docs/superpowers/specs/2026-08-26-six-page-carousel-narrative-design.md`、`docs/superpowers/plans/2026-08-26-six-page-carousel-narrative.md`。

## 2026-08-25 粉彩手帳原型對齊現有自動產圖內容契約

- **產品能力**：保留使用者核可的粉彩手帳視覺與四種手繪呆一布動作，將七頁所有內容槽改為現有 `CarouselDraft` 的正式欄位；不用修改 AI 生成器就能在下一輪搬入正式 Renderer。
- **逐頁對照**：封面為定位／產業，公司檔案為白話定位／基本資料，問題頁為兩段敘事＋三節點問題鏈，AI 解法為四段敘事＋三節點流程，成果頁為三段敘事＋三節點前後對照，關注頁為三個訊號＋證據限制＋三節點圖解，結尾為結論／問題／互動邀請。
- **重要修正**：第 5 頁由工具沒有提供的商業模式改為 `results` 使用前後；第 6 頁移除必須有百分比的假設。原型不再出現 `BUSINESS MODEL`、收入來源、成長飛輪或 `XX%`。
- **技術結構**：新版為 `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-schema-aligned-31.html`；每個可替換文字以正式 `data-content-key` 標記，`schema-aligned-contract.js` 對齊 `daibu/cards/pages.py` 與圖解節點欄位。正式模板、Renderer、提示詞與 SQLite 未修改。
- **TDD 證據**：新契約先在 v30 以 `missing page.cover.heading` 正確失敗；重綁後內容契約與共用手帳外殼契約均通過。過時的 `seven-pages-contract.js` 仍要求舊展示假字「問題一」，不再作為 v31 的驗收契約。
- **視覺 QA**：完成三輪桌機／手機檢查；第一輪修正 favicon 404，最終 375px 為 `scrollWidth=clientWidth=375`，七頁共 63 個正式內容元素全部位於各自 4:5 畫布內，console 0 errors／0 warnings。最終截圖為 `.screenshots/schema-aligned-final-desktop.png` 與 `.screenshots/schema-aligned-final-mobile.png`。
- **安全與成本**：沒有資料寫入、外部 API、新依賴、付費操作或正式服務異動；原型仍在 `.gitignore` 範圍。
- **剩餘限制**：相容版目前只證明視覺原型可容納正式資料；正式 PNG 輸出尚未切換到此模板，後續需另案把 DOM、CSS、角色 SVG 與 layout registry 搬入正式 Renderer 並做長文字壓力測試。
- **規格與計畫**：`docs/superpowers/specs/2026-08-25-pastel-notebook-schema-alignment-design.md`、`docs/superpowers/plans/2026-08-25-pastel-notebook-schema-alignment.md`。
- **直角密度迭代**：使用者指出空白過多、框線歪斜。最終 v35 將主要紙框、問題便條、AI 步驟、訊號、成果與結尾框全部回正；手帳感只保留在方格底、色紙、膠帶與角色。每頁最後一個主要內容模組延伸到畫布至少 74%，不把角色算成內容；第 5 頁摘要改為淡藍／淡黃實色色面，第 7 頁結論卡加高。
- **量測校準**：第一次只量文字最後一行，無法辨識容器加高，已停止使用；正式契約改量每頁最後一個主要內容模組的底邊。v33 在 74% 新門檻下正確抓到第 1、2、6 頁不足，再調整轉綠。
- **直角密度驗證**：v35 的直角密度、內容 schema、共用手帳外殼三項契約通過；375px 為 `scrollWidth=clientWidth=375`，可替換內容 0 個越出畫布，主要框旋轉數 0，console 0 errors／0 warnings。最終截圖為 `.screenshots/straight-dense-v35-desktop.png` 與 `.screenshots/straight-dense-v35-mobile.png`。
- **全頁便利貼迭代**：依使用者要求，把封面定位、公司資料、問題脈絡、AI 步驟、成果對照、訊號、證據限制與結論共 29 個語意內容面統一成第 3 頁的便利貼語言；採粉彩紙面、無完整描邊與紙片陰影，仍維持直角。Logo 區與外層白紙不算內容格，保持原結構。
- **便利貼 TDD 與 QA**：新契約先在 v35 以 `missing straight-sticky note-system marker` 正確失敗；v36 轉綠後，第一輪截圖發現縮小時陰影太淡，v37 加強陰影再複驗。最終 29 個便利貼面、內容密度、內容 schema、共用手帳外殼四項契約通過；375px 無水平捲動、內容越界 0、旋轉框 0、console 0 errors／0 warnings。截圖為 `.screenshots/sticky-notes-final-desktop.png` 與 `.screenshots/sticky-notes-final-mobile.png`。
- **便利貼材質迭代**：使用者指出 v37 仍較像粉彩卡片。v39 為 29 個便利貼加入上緣 15% 黏膠層、極淡紙纖維顆粒與右下小幅掀角；所有框保持直角，內容幾何與正式欄位不變。
- **材質 TDD 與 QA**：新契約先在 v37 以 `missing adhesive-texture-fold marker` 正確失敗；第一次實作又抓到高優先級背景覆蓋紙紋，以及 AI 步驟／CTA 不可改為一般定位，修正為保留絕對定位、只提高材質層優先級。第一輪截圖再抓到黏膠層縮小後太淡，v39 加深後完成第二輪。五項原型契約通過；375px 無水平捲動、內容越界 0、旋轉框 0、console 0 errors／0 warnings。截圖為 `.screenshots/sticky-material-final-desktop.png` 與 `.screenshots/sticky-material-final-mobile.png`。
- **第 3／4 頁密度與社群 CTA 迭代**：v43 將問題頁三張問題便利貼改成等寬直立列，AI 解法頁改成等寬三步流程＋四格補充，消除原本中段與底部的大塊斷層。第 7 頁不再顯示「最後，帶走這個觀察」或收束結論，改為社群帳號、每週內容承諾、下一家公司留言提示，以及追蹤／收藏／留言三個行動。
- **CTA 舊草稿相容**：現有 `CarouselDraft` 仍會提供 `cta.heading` 與第一段收束結論；原型先保留這兩個 `data-content-key` 但隱藏，不讓舊草稿載入失敗。正式 Renderer 接線時應把社群帳號改由系列品牌設定注入，並決定是否正式移除不再顯示的生成欄位，避免讓 AI 長期產生無用內容。
- **本輪 TDD 與視覺 QA**：密度契約先在 v39 因缺少 `tight-three-four` 標記失敗；CTA 契約先在 v40 因缺少 `social-account` 失敗；第二輪再以實測 21.35% 的提問至行動列空洞建立失敗門檻，最後加入公司名稱／產業／最想知道的問題三個通用留言提示。v43 的內容 schema、直角密度、便利貼系統、材質、第 3／4 頁密度與 CTA 契約皆通過；375px 無水平破版，console 0 errors／0 warnings。最終截圖為 `.screenshots/cta-density-approved-desktop.png` 與 `.screenshots/cta-density-approved-mobile.png`。
- **完整測試**：第一次全套為 `738 passed, 1 failed, 16 deselected`，失敗是既有模板編輯器版本儲存瀏覽器流程在 60 秒內未更新下拉值；同一流程單獨重跑為 `1 passed in 19.77s`。未修改測試或正式程式後，第二次完整套件為 `739 passed, 16 deselected, 1 warning in 265.50s`；唯一 warning 仍是既有 Starlette／httpx 棄用提醒。
- **置中 CTA 修正**：使用者否決 v43 的帳號卡、提問卡、提示膠囊與底部行動列。v45 將第 7 頁簡化為紙張正中央三句：「喜歡這類內容嗎？」、「追蹤 @社群帳號」、「下一間想看哪家公司？留言告訴我們。」；只有帳號是品牌欄位，四個舊 `cta` 生成欄位全部隱藏作相容用途。右下角色與頁碼保留。
- **置中 CTA TDD 與 QA**：新契約先在 v43 以 `missing centered-copy CTA marker` 失敗；移除三個內容面後，便利貼系統與材質契約由 29 面更新為 26 面，並以 v43 紅、v44 綠校準。第一輪截圖抓到字級只佔畫布寬 2.45%–6.1%、不像主視覺，再新增字級比例契約並於 v45 放大。最終 CTA 垂直中心偏差為 0、舊 CTA 區塊數 0、console 0 errors／0 warnings；截圖為 `.screenshots/cta-centered-final-desktop.png` 與 `.screenshots/cta-centered-final-mobile.png`。
- **置中 CTA 完整測試**：`PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q` → `739 passed, 16 deselected, 1 warning in 255.51s`；唯一 warning 是既有 Starlette／httpx 棄用提醒。
- **第 3 頁敘事重排**：v48 不再使用「上方兩格＋下方三根長柱」。左欄先交代誰受影響與原本代價，右欄由上往下排列問題出現、摩擦累積、形成代價；角色移到標題區，避免蓋住因果內容。`problem-story-layout-contract.py` 先在 v45 以缺少 `context-chain` 正確失敗，再鎖住左右關係、三節點順序、等寬與零重疊。
- **第 2–6 頁內容密度與連貫性**：頁面角色固定為 `identity → problem → mechanism → outcome → proof`，示範文字不再是單行欄位說明，而是可連續閱讀的公司介紹。可見正式欄位字數由原本第 2–6 頁 `62／74／81／84／93` 提高為 `138／226／229／242／249`；量測直接加總可見 `data-content-key` 文字，不含標籤、角色與隱藏 CTA。
- **密度 TDD 與視覺 QA**：`narrative-density-contract.py` 先在 v46 因缺少故事流程標記失敗；v47 增加敘事後，第一輪截圖發現第 4、6 頁最低正文只有畫布寬 1.35%／1.45%，判定不能靠小字換密度。v48 將第 2–6 頁正文下限鎖在 1.55%，同步縮減卡片內距；九項原型契約通過、375px 無水平捲動、console 0 errors／0 warnings。最終截圖為 `.screenshots/narrative-density-final-desktop.png` 與 `.screenshots/narrative-density-final-mobile.png`。
- **正式接線注意**：目前增加的是原型長文 fixture 與版面容量；正式 AI 生成器尚未被要求輸出這種篇幅與跨頁承接。正式 Renderer 接線時必須同步修改生成提示詞與驗證，讓第 3 頁承接第 2 頁的服務對象、第 4 頁逐項回答第 3 頁問題、第 5 頁對應第 4 頁機制、第 6 頁用證據支持第 5 頁結果，否則只換版型仍會得到薄而斷裂的貼文。
- **敘事密度完整測試**：`PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q` → `739 passed, 16 deselected, 1 warning in 264.81s`；唯一 warning 是既有 Starlette／httpx 棄用提醒。
- **視覺化實驗版並存**：使用者要求保留長文 v48，再試更視覺化的版本。v50 是獨立候選，不覆蓋 v48；第 2 頁新增「AI 產品 → 目標使用者 → 核心價值」定位圖，第 3 頁以帶箭頭的因果軸串起三節點，第 4 頁加入兩個流程箭頭，第 5 頁放大轉變箭頭，第 6 頁加入使用循環／市場擴散／商業成長三個非量化 SVG 水印。
- **視覺層資料安全**：`visual-storytelling-contract.py` 逐鍵比較 v48 與 v50 的全部 `data-content-key`，內容完全相同；視覺元素皆為 `aria-hidden`、留在各自畫布內，且沒有新增百分比或公司專屬圖像。第一輪截圖發現第 3 頁只有關聯線、沒有向下方向，第 4 頁箭頭像漂浮符號；v50 改成明確箭頭後完成第二輪。十項原型契約通過、console 0 errors／0 warnings；最終截圖為 `.screenshots/visual-story-final-desktop.png` 與 `.screenshots/visual-story-final-mobile.png`。
- **選版狀態**：v48 是目前保留版，v50 是待使用者比較的視覺化候選。正式 Renderer、生成提示詞、SQLite 與正式站均未修改；使用者可選 v48、v50，或逐頁指定混合。
- **視覺化候選完整測試**：`PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q` → `739 passed, 16 deselected, 1 warning in 263.43s`；唯一 warning 是既有 Starlette／httpx 棄用提醒。
- **逐頁細節精修**：v53 延續 v50 的圖解方向但不覆蓋 v48／v50。第 2 頁拉開標題與定位圖，第 3 頁把三個因果節點圓點精確對齊便利貼中心，第 4 頁收斂流程與補充敘事的間距，第 5 頁讓轉變箭頭避開便利貼黏膠層；第 2–6 頁正文行高統一至少 `1.3`，各頁標題重新分配寬度，避免短詞孤立成尾行。
- **角色與 CTA 細節**：第一輪截圖發現把角色移出文字區後反而裁出畫布，因此契約新增「角色完整留在紙張內」；第 2–6 頁角色改置於右上安全區且不遮內容，第 1、7 頁分別留在右下作開場與 CTA 收尾。第 7 頁仍只有置中 2–3 句 CTA，沒有恢復任何內容卡。
- **逐頁精修 TDD 與 QA**：`page-polish-contract.py` 先在 v50 因缺少逐頁精修標記失敗；v51 依幾何量測修正後，第一輪截圖抓到角色被裁切，再補邊界失敗案例並建立 v52；第二輪截圖再抓到第 2／4／6 頁標題斷行與第 7 頁角色位置不協調，最後建立 v53。十一項原型契約全數通過；375px 為 `scrollWidth=clientWidth=375`、七頁均無自身 overflow，console 0 errors／0 warnings。最終截圖為 `.screenshots/page-polish-approved-desktop.png` 與 `.screenshots/page-polish-approved-mobile.png`。
- **目前候選狀態**：v48 保留長文基準、v50 保留第一個視覺化版本、v53 是逐頁細節完成的視覺化候選。三者皆為本機忽略原型，正式 Renderer、生成提示詞、SQLite 與正式站仍未修改。
- **逐頁精修完整測試**：第一次全套在系統同時存在大量瀏覽器程序時出現 6 個 Streamlit 啟動／Runtime 連鎖超時，其餘 `733 passed`；六個失敗案例隔離重跑為 `6 passed in 52.82s`。關閉額外預覽瀏覽器後重新跑完整套件，結果為 `739 passed, 16 deselected, 1 warning in 596.71s`；唯一 warning 是既有 Starlette／httpx 棄用提醒。
- **公司優先封面 v54**：依使用者確認的 A 方案，封面改為 Logo 在上、公司名稱最大、一句話介紹在下。公司名稱使用獨立的 `data-company-field="company"` 語意槽，`page.cover.section.0.text` 作可見副標、產業分類退為小標；舊 `page.cover.heading` 留在 DOM 但隱藏，避免破壞舊草稿又形成第二個主標。真實 Logo 使用 `object-fit: contain`，缺素材時顯示中性企業 Logo 佔位。
- **封面 TDD 與量測校準**：`cover-company-first-contract.py` 先在 v53 以缺少公司優先標記正確失敗。第一次以 `scrollHeight` 判斷文字裁切時，已知短字也固定多出約 3px，證明方法無法區分真溢位；改以實際文字行框數與最後一行邊界校準，並鎖住長名稱最多兩行、副標最多三行、公司名字級至少為副標兩倍、主體都在紙張內且不與角色重疊。
- **封面視覺 QA**：第一輪確認資訊方向正確，再把短公司名由 `7.2cqw` 提高至 `7.8cqw`，並讓正式 Logo 圖片自動移除佔位虛線與底色。第二輪 375px 量得公司名／副標字級比 `2.48×`，七頁均 `overflow:false`、`scrollWidth=clientWidth=375`，console 0 errors／0 warnings；十二項原型契約全部通過。最終截圖為 `.screenshots/company-first-cover-final-desktop.png` 與 `.screenshots/company-first-cover-final-mobile.png`。
- **目前候選狀態**：v48、v50、v53 均保留；v54 是公司辨識優先的最新視覺化候選。v54 仍是本機忽略原型，正式 Renderer、AI 生成提示詞、SQLite 與正式站尚未接線或修改。
- **公司優先封面完整測試**：隔離 worktree 開工基線為 `739 passed, 16 deselected, 1 warning in 196.08s`；完成後為 `739 passed, 16 deselected, 1 warning in 190.82s`；合回 `main` 後重跑為 `739 passed, 16 deselected, 1 warning in 216.06s`。唯一 warning 是既有 Starlette／httpx 棄用提醒。

## 2026-08-25 四套公司中立輪播模板原型

- **產品能力**：新增四套彼此獨立、各七頁的公司介紹輪播原型：粉彩手帳、Y2K 科技拼貼、奇幻世界觀、暖紙感 3D 資訊圖解。比較器可切換三家公司、七頁，以及逐套／同頁比較模式。
- **使用者體驗**：1280px 同頁比較會把四套排在同一列；375px 維持單欄 4:5 畫布，控制列可橫向滑動且整頁沒有水平溢位。鍵盤 focus、selected、hover、active、reduced-motion 與固定素材錯誤提示均有處理。
- **技術結構**：原型完全位於被忽略的 `.superpowers/prototypes/company-neutral-carousel/`，由 `build.py` 匯出三家公司壓力 fixture 並生成單一 `index.html`；正式 `daibu/cards/templates/`、layouts、SQLite 與現行 Streamlit 服務皆未修改。
- **資料流程**：公司 Logo 與七頁文字進入四套固定 renderer；背景、吉祥物姿勢、DOM 幾何、CSS 與固定圖像不隨公司改變。SUN、Billow AI Labs、Shiraz AI 僅是壓力測試資料，不存在固定模板材料裡。
- **設計理由**：四套使用不同的頁面幾何語言，而非同一骨架換皮；手帳用紙張／摺頁／書籤，Y2K 用視窗／終端／訊息框，奇幻用入口／道路／中繼站／橋／塔／山頂，3D 編輯風用紙帶／泡泡／積木／紙堆／結果卡。
- **固定 AI 素材**：奇幻世界母圖與奇幻／3D 七姿勢表各生成一次後固定重用；圖像不含文字、Logo、公司或產業物件。manifest 使用明確七格整數座標，三家公司切換不改 URL、場景裁切、sprite class 或 background position。
- **替代方案**：若使用者只喜歡各套中的部分頁型，可在下一輪組成第五套混合方向；本輪不先把未選定設計接入正式 Renderer，避免污染正式模板版本。
- **安全與成本**：沒有資料表、正式資料、外部 API key、付費模型或部署異動；固定點陣素材只在原型階段生成一次。素材 404 時在畫布外顯示錯誤並把預覽標記為無效，不默默留下空白。
- **測試證據**：中立掃描器先以五個已知禁用詞校準，再掃固定 HTML／CSS／SVG／manifest；原型為 `8` 項靜態契約、`37` 項瀏覽器契約，瀏覽器矩陣為 `4 × 3 × 7 × 2 = 168` 個狀態。`PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q` 為 `739 passed, 16 deselected, 1 warning in 196.42s`；唯一 warning 是既有 Starlette／httpx 棄用提醒。
- **視覺 QA**：第一輪不合格項目為 1280px 第四套掉到第二列、favicon 404、字型依賴裝置安裝；各自先補失敗契約再修正。第二輪八項檢查全部通過，console `0 errors`；唯一 warning 是單檔原型依規格使用 Tailwind CDN 的開發提示。最終截圖：`.screenshots/company-neutral-four-styles-round2-desktop.png`、`.screenshots/company-neutral-four-styles-round2-mobile.png`。
- **原型入口**：本機由 repo root 啟動 `python -m http.server 8765 --bind 127.0.0.1` 後，開啟 `http://127.0.0.1:8765/.superpowers/prototypes/company-neutral-carousel/index.html`。
- **剩餘限制**：此成果是選擇視覺方向用的隔離原型，不是正式貼文模板；使用者仍需選一套或指定混合方式，後續才會另案接入正式 Renderer 與模板版本生命週期。

## 2026-08-25 細線元件拖曳命中區修正

- **產品能力**：模板畫布中只有約 2px 高的分隔線、軸線與裝飾線，現在都有至少 24 CSS px 的透明拖曳命中區；線條外觀與正式產圖維持原尺寸。
- **根因與修正**：既有元素登錄與 X／Y 寫回都正常，問題是細線的實際可點範圍只有視覺高度，使用者幾乎無法命中。前端現在會依正式 DOM 尺寸，為所有 `graphic` 類細元素建立置中的透明 hit target，拖曳仍更新原本元素 ID，不建立另一份版面資料。
- **資料與安全**：透明命中區只存在於編輯器 overlay，不進入 Renderer、貼文圖片或 SQLite；點擊但未移動不會建立 history，也不會啟用儲存按鈕。沒有新依賴、schema、外部服務或付費操作。
- **TDD 證據**：新增真實 Chromium 迴歸測試，先重現 `.layout-hit-target[data-element-id="rule"]` 不存在，再修到命中區高度 `>= 24px`、大於約 2.21px 的實線，且拖曳後原線 X／Y 同步增加、屬性面板顯示「標題分隔線」。編輯器聚焦套件為 `19 passed in 80.75s`。
- **完整測試**：`PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q` → `739 passed, 16 deselected, 1 warning in 235.92s`；唯一 warning 為既有 Starlette／httpx deprecation。
- **視覺 QA**：兩輪 1280×800 與 375×812 截圖完成；桌面實拖時實線由約 `(550.07, 359.21)` 移至 `(581.15, 382.08)`，寬高不變，右側正確顯示「標題分隔線」。手機依產品規格維持唯讀，沒有顯示操作 overlay。最終截圖：`.screenshots/thin-rule-round2-desktop.png`、`.screenshots/thin-rule-round2-mobile.png`。
- **正式站驗收**：`origin/main` 已包含功能提交 `6615a81`；既有 `io.daibu.content-brain` 重啟後為 running、PID `48751`，health `ok`。由首頁進入設定後，正式橘線命中區為約 `359.64×24px`，實線仍為約 `359.65×2.21px`；拖動後實線由 `(550.07, 399.21)` 移至 `(581.15, 422.08)`，重設後精確回到原位且儲存鈕停用。模板版本操作前後皆為 2；375px 為 `scrollWidth=clientWidth=375`、唯讀提示可見、儲存按鈕為 0，console 0 errors／0 warnings。正式截圖：`.screenshots/thin-rule-production-moved.png`、`.screenshots/thin-rule-production-mobile.png`。
- **剩餘限制**：手機仍刻意不提供精準模板操作；24px 是桌面滑鼠命中區，不改變正式圖的視覺粗細。

## 2026-08-23 模板即時預覽與語意佔位修正

- **產品能力**：設定頁模板畫布現在會把拖曳、縮放、X／Y、寬高、字級與對齊同步套到真正的貼文元素；選取框不再自己移動而內容留在原地。復原、重做與 Escape 取消也同步更新內容。
- **使用者體驗**：七頁模板預覽改用「公司名稱」「系列名稱」「企業 Logo」「封面標題／頁面標題」等欄位角色，不再把 SUN 或其他壓力測試公司誤顯示成固定模板文字。預覽缺少 renderer hook 時會顯示錯誤並禁止儲存，避免存出畫面與數值不一致的版本。
- **技術結構與資料流**：語意 placeholder builder 產生七頁草稿 → 正式 Renderer 產出唯一預覽 DOM → 瀏覽器把 working layout 白名單屬性套到 `data-layout-id` 元素 → overlay 從實際 DOM 測量。儲存路徑、SQLite schema、版本生命週期與正式產圖預設皆未改。
- **設計理由與備援**：主方案共用正式 Renderer，可避免編輯器與產圖再度分岔；備援是每次操作回 Python 重繪，但延遲高且拖曳體驗差，未採用。公司名稱採語意 placeholder，而不是實際公司名，讓使用者知道此處會由每篇公司資料替換。
- **安全與成本**：只允許既有 registry 元素與樣式白名單，沒有任意 CSS／HTML、外部服務、LLM、付費操作或資料表變更。視覺 QA 使用正式庫副本且未按儲存，正式資料未寫入。
- **TDD 與瀏覽器證據**：先重現「選取框移動但實際元素 `actual_dx == 0`」、拖曳中內容不動、Escape 後內容未復原、缺 hook 仍可儲存，再逐片轉綠。真實 Chromium 驗證實際元素與選取框位移差 `<= 1 CSS px`，七頁均顯示語意 placeholder，沒有 SUN／Billow／Shiraz 殘留。
- **視覺 QA**：兩輪 1280×800 與 375×812 通過層次、留白、LINE Seed 字體、深藍／青／珊瑚三色、對齊、響應式、狀態與微動效；手機維持唯讀且 `scrollWidth=clientWidth=375`。最終截圖：`.screenshots/template-live-preview-round2-desktop.png`、`.screenshots/template-live-preview-round2-mobile.png`。
- **測試穩定化**：完整套件曾兩次抓到既有 build-story 靜態頁的 `file://` 載入會被遠端字型拖到 30 秒 timeout；改為等待本機 DOM，圖片案例另等內嵌圖片完成解碼。該檔 16 項通過，完整套件為 `724 passed, 16 deselected, 1 warning in 245.09s`；warning 仍是既有 Starlette／httpx 相依提醒。
- **主分支與正式站**：合併後主分支全套為 `724 passed, 16 deselected, 1 warning in 254.78s`，`origin/main` 與本機提交同為 `49a2247599c1a330e9109553865e9f9c8e4a7e3f`。既有 LaunchAgent 重啟後為 running、health `ok`、PID 66176，只監聽 `127.0.0.1:8501`。正式設定頁調整 X 後，實際標題位移 16.444px、選取框位移 16.453px，差 0.009px；操作前後模板版本數皆為 2，未寫正式資料。375px 為 `scrollWidth=clientWidth=375`，唯讀提示可見、儲存按鈕數為 0，console 0 errors／0 warnings。正式截圖：`.screenshots/template-live-preview-production-moved.png`、`.screenshots/template-live-preview-production-mobile.png`。
- **剩餘限制**：手機刻意只讀；模板仍不支援新增／刪除／旋轉、z-order、換品牌字型／色票或素材路徑。這些是既有產品邊界，不是本輪缺漏。
- **規格與計畫**：`docs/superpowers/specs/2026-08-23-template-editor-live-preview-placeholders-design.md`、`docs/superpowers/plans/2026-08-23-template-editor-live-preview-placeholders.md`。

## 本輪目標與驗收

- 日常工作區改成 1–7 頁導覽、目前頁欄位與同頁即時預覽；所有貼文內容文字含圖解節點可編輯，來源／引文／結構角色鎖定。
- 七頁未存內容切頁保留；只有「儲存全部變更」會用 Chromium 精準檢查後原子保存，過長、溢出或碰撞時不縮字、不截斷、不產圖。
- 設定頁新增受限制的 PPT 式系列模板管理：移動／縮放既有元素，文字可調字級、框寬與對齊，品牌字型／色票／元素結構鎖定。
- 模板每次保存建立不可變新版本；新草稿綁 active version，舊草稿維持原版本，只有手動升級才換版。
- v15.1 作為初始版面 v1 的視覺基準；正式搬遷必須保留既有七頁內容、來源、Logo、正文與狀態。

## 本輪狀態（2026-08-23：模板文字獨立層）

- **產品能力**：七頁每個可見的邏輯文字角色都成為可單獨選取的版面層，可獨立調整 X／Y、寬高、字級與對齊；背景色塊與文字分離。
- **根因修正**：字級直接套在承載文字的 `data-layout-id` 節點，不再依賴會被子層 CSS 覆蓋的父層繼承。
- **舊版相容**：schema v1 版面讀取時以純記憶體正規化為 schema v2；資料庫舊 `layout_json` 維持原樣，只有使用者儲存才建立新的 schema v2 版本。
- **快取安全**：模板編輯器 sessionStorage 加入 layout schema 與 registry 指紋，不會把舊 composite working copy 套到新獨立層。
- **真實互動 QA**：11 個 Playwright 瀏覽器流程全過，涵蓋拖曳、欄位移動、字級同步、兄弟層互不影響、復原／重做、Escape、上下限、儲存／啟用、schema v2 儲存重開、七頁每個文字層的實際計算字級，以及手機唯讀。
- **版面壓力 QA**：三家公司、三種 Logo 比例、共 21 頁的 Chromium 輸出驗證通過；QA 額外抓到並修正第 3、6 頁長補充文字框高度不足，沒有降低 overflow 驗證標準。
- **全套測試**：`PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q` → `738 passed, 16 deselected, 1 warning in 220.43s`；唯一 warning 是既有 Starlette/httpx deprecation。
- **main 合併後全套**：同一指令重跑為 `738 passed, 16 deselected, 1 warning in 242.49s`。
- **視覺 QA**：第一輪截圖未包含模板畫布，判定不合格並重做；最終桌機／手機畫布截圖為 `.screenshots/text-layers-round3-desktop.png`、`.screenshots/text-layers-round3-mobile.png`。手機 `scrollWidth=clientWidth=375`，儲存、選取層與屬性面板皆隱藏，維持唯讀。
- **安全與成本**：無新依賴、外部服務、任意 CSS／HTML／URL 輸入或資料表；所有元素與屬性仍由 registry 白名單控制。
- **狀態**：功能、全套測試、兩輪視覺 QA、main 合併、推送與正式站核心流程皆已驗收。
- **推送與正式服務**：`origin/main` 已更新；既有 `io.daibu.content-brain` 重啟後為 `state=running`、PID `77430`，只監聽 `127.0.0.1:8501`，health 回應 `ok`。
- **正式核心流程**：由首頁點進系統設定，模板編輯器無同步錯誤；第二頁 `facts-body` 字級由 `27.692` 改為 `30.692`，真實 DOM 精確增加 `3px`，重設後回到 `27.692` 且儲存鈕停用，未建立 QA 版本。手機 375px 無整頁橫向溢位，維持唯讀。
- **正式資料與錯誤**：`daibu.db` 為 `integrity_check=ok`、模板版本仍為 2；正式瀏覽器 console 0 errors／0 warnings，stderr 在本次重啟與操作後沒有新增內容。

---

## 前一輪狀態

- **產品能力**：日常工作區可逐頁修改七頁文字與 diagram；設定頁新增受限制的 PPT 式模板畫布，可選七頁與既有元素、拖曳、八向縮放、調整文字框位置／尺寸／字級／對齊、復原／重做／重設。每次儲存建立不可變新版，啟用與單篇舊草稿升級都是另外的明確操作。
- **使用者體驗**：切頁不丟未存內容，模板拖曳會依 8px 網格、安全線、中心線與其他元素吸附，guide 即時顯示；碰撞前橘色、碰撞時紅色。Escape 取消本次拖曳，欄位依元素最小值與畫布邊界限制。手機只顯示版本、七頁 rail 與貼文預覽，隱藏精確控制及新版儲存按鈕並明示改用桌面。
- **技術結構**：兩個 Streamlit Components v2 元件共用正式 Renderer。內容元件只回傳欄位白名單；模板元件只回傳登錄元素的 `x/y/w/h` 與文字的 `font_size/text_align`。Python 對全部輸入重跑 schema、三公司壓力案例與 Chromium，SQLite 只新增版本，不 update 舊 `layout_json`。
- **資料流程**：模板版本＋單頁正式 HTML → sessionStorage working copy／overlay 控制 → 儲存 → Python schema＋SUN／Billow／Shiraz 七頁驗證 → 建 vN（未啟用）→ 使用者確認後切 active pointer。新草稿用 active；舊草稿保留原版，手動升級前先用該篇內容驗證七頁，再只更新 binding 與 revision。
- **設計理由與備援**：工具介面延續核可的深藍／青／珊瑚橘科技編輯語言，控制框服務貼文而不另造卡片牆。受限制畫布避免任意 CSS、圖層與素材路徑破壞模板；備援是永遠可選回舊版本，舊貼文亦可維持原 binding。
- **安全與成本**：沒有新增 CDN、付費服務、LLM 呼叫或任意 HTML／CSS／JavaScript／URL／檔案路徑入口。正式 `daibu.db` 只透過 SQLite `.backup` 副本檢查，正式檔未寫入；新增版本與驗證都只用本機 SQLite／Chromium。
- **正式資料副本驗證**：正式庫基線為 ideas 23、carousel_pages 0、carousel_sources 0、brand_assets 0；逐欄 canonical JSON SHA-256 依序為 `006605efa926257747b74867050a0940257ecad8d3b89237ef7f358a1fe78484`、`0cc5ad572c159bc109ab2816840263977f82802842e5497b197fa341bccc0dad`、`5b50a1f3836660c4977c3aa409df13535cf0c3f8d36ab07cffc8d1b449dc29b6`、`10dd371a129ce285b87fc867f8c9c85b503a37ea7ad39d16e530f6b6515521ad`。backup、首次 migration 與第二次 migration 四組指紋完全相同，只新增三張預期資料表；正式庫沒有 carousel rows，因此 backfill 版本／設定／metadata 都為 0。
- **TDD 與跨公司驗收**：依序看見快取版本未納入、SUN 第 5 頁文字框 overflow、Billow 長名第 7 頁 overflow、Shiraz 長結果標題 overflow、桌機預覽過小等紅燈，再做最小修正。SUN、Billow AI Labs、Shiraz AI 搭配橫式／直式／方形 Logo，共 21 張 HTML 與 PNG 全數為 1080×1350，無非法碰撞、頁碼、來源或日期。
- **視覺 QA**：Phase C 第一輪抓到 Renderer 色票變數在 Shadow DOM 缺失而導致封面發白，以及手機仍露出儲存按鈕；第二輪已恢復正式貼文配色並切成真正唯讀。正式站最終證據為 `.screenshots/template-editor-production-desktop.png`、`.screenshots/template-editor-production-mobile.png`。層次、留白節奏、LINE Seed 字體、三色限制、對齊、375px 響應式、focus／disabled／error／empty 狀態與 120–150ms 微動效全數合格；`scrollWidth=clientWidth=375`，從首頁正常導覽 console 0 errors／0 warnings。
- **Phase B 測試證據**：真實瀏覽器三條流程通過：切頁保留 working copy 且 DB 未寫、hard limit 同時擋 save／產圖、合法 save 寫 DB 且留在原頁。AppTest 119 passed；全套首次為 `696 passed, 16 deselected`，只抓到移除舊表單後遺留的 `.carousel-page-heading` CSS，已刪除並以兩個聚焦測試轉綠；Phase C 收尾會再跑完整全套。
- **設計規格**：`docs/superpowers/specs/2026-08-20-七頁內容與系列模板編輯器-design.md`。
- **實作計畫 A**：`docs/superpowers/plans/2026-08-21-carousel-layout-foundation.md`。
- **實作計畫 B**：`docs/superpowers/plans/2026-08-21-carousel-content-editor.md`。
- **實作計畫 C**：`docs/superpowers/plans/2026-08-21-carousel-template-editor.md`。
- **Phase C 測試證據**：真實 Chromium 六條模板流程通過：拖曳不偷存、縮放＋undo／redo、Escape 取消、登錄最小尺寸限制、手機唯讀無 overflow、存 v2 維持 inactive 後明確啟用。v1／v2 × SUN／Billow AI Labs／Shiraz AI 共 42 張頁面無 overflow／非法碰撞，PNG 全為 1080×1350，無頁碼、來源列或日期列。
- **完整測試**：`PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q` 為 `718 passed, 16 deselected, 1 warning in 192.54s`；接續 `compileall` 與 `git diff --check` 均為 exit 0。唯一 warning 是既有 Starlette／httpx 相依棄用提醒。
- **資料副本證據**：以 `sqlite3 .backup` 複製正式庫；migration 前後 ideas 23 筆、其餘三個內容表 0 筆，四組 JSON SHA-256 完全相同。ideas 指紋為 `0fbb8c3d54f4b31920a22aa7f5cfe4591515017b2d276b2f60e72e1843b4b700`，空表為 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`；副本只新增預期模板表。
- **剩餘限制**：模板畫布刻意不支援新增／刪除／旋轉元素、z-order、換字型、改色票或素材路徑；手機不提供精確拖曳。正式庫目前沒有 carousel rows，因此正式資料副本只能驗證 migration 不改內容；完整存版／啟用／升級生命週期由隔離 SQLite 真實瀏覽器測試覆蓋。
- **部署與狀態**：Phase A、B、C 已合併 `main` 並推送至 `origin/main`，既有 LaunchAgent 已重啟，正式網址仍為 `http://127.0.0.1:8501`。健康檢查為 `ok`；正式設定頁顯示模板 v1、桌機畫布可見，375px 顯示唯讀說明且儲存按鈕隱藏，console 0 errors／0 warnings。

---

# 前一輪 — 七頁貼文模板 v15.1 逐頁細修

> 2026-08-20 更新。本輪保留三家公司內容資料與 v15 的頁面語法，依使用者指定恢復右側大型企業名稱封面，另設右上 Logo 區，並逐頁修正白洞、段距、碰撞、機器人比例、第 5 頁標題與「到」、第 6 頁主訊號色塊。正式產圖模板、Streamlit、SQLite 與內容資料沒有修改。

## 本輪目標與驗收

- 第 1 頁恢復 v12 已核可的右側大型直式描邊企業名稱；右上角另留正式 Logo 安全區，原型先以公司字標佔位。
- 第 2 頁深藍結論回到正常文流並延伸到畫面 85% 以下；第 3 頁三段內容舒展到畫面 82% 以下；第 4 頁警示帶與機器人天線至少保留 `1.5cqw`。
- 七頁呆一布相對 v15 至少縮小 10%，且完整留在畫布內。
- 第 5 頁維持左右 50/50 對比，左右標題放大並靠近中線，但與放大的雙色「到」至少保留 `2cqw`；機器人移到左側紙白區。
- 第 6 頁主訊號使用深藍底白字；SUN、Billow AI Labs、Shiraz AI 都要在 1280×800 與 375×812 通過。

## 本輪狀態

- **產品能力**：同一份三家公司資料可產生七頁 v15.1 原型；封面同時有大型企業名稱識別與獨立 Logo 安全區，其餘六頁維持 v15 的內容功能。
- **使用者體驗**：封面先用企業名稱與主題建立記憶點；第 2 頁深藍結論不再硬釘頁底或留下白洞，第 3 頁三段問題更舒展，第 4 頁天線不碰警示帶，第 5 頁清楚讀成「從節目搜尋／到／直接生成」，第 6 頁主訊號與機器人不再黏色。
- **技術結構**：localhost 仍讀 `.superpowers/brainstorm/31101-1787251453/content/multi-company-template-stress-v13.html` 與 `editorial-v15-contract.js`；版本標記升為 `v15.1`，只新增 `.cover-v151` 與範圍化 CSS／幾何契約。正式程式未變。
- **資料流程**：既有三家公司測試資料 → `renderCompany` → v15.1 七頁 DOM → 單欄預覽 → 三公司雙尺寸契約 → 逐頁與整頁截圖。沒有 LLM、外部 API、資料保存或正式發文。
- **設計理由與備援**：主方案恢復使用者較喜歡的名稱主導封面，再將正式 Logo 當成另一個品牌層級；這比把 Logo 與大型名稱二選一更完整。備援是只保留右上 Logo、拿掉大型名稱，成本較低但會失去封面辨識度，因此未採用。
- **安全與成本**：沒有新增套件、字型服務、生成圖片、付費操作、schema 或正式資料異動；使用者正在修改的兩份 HTML 與未追蹤個人檔案沒有被 stage 或覆寫。
- **TDD 證據**：依序看見 `v15.1 marker missing`、`approved cover word missing`、`page 3 mascot leaves the canvas`、`profile anchor leaves a white hole`、`problem stages are cramped`、`mechanism antenna touches caution band`、`result titles are too small`、`到 is too small`、`result mascot should move to the white side`、`primary signal blends into mascot`、`primary signal text lacks contrast`、`profile conclusion lacks vertical weight`、`problem story does not use enough vertical space`、`result connector crowds the titles`，再逐項做最小修正轉綠。
- **視覺 QA**：第一輪 1280×800／375×812 與七頁校稿抓到第 2、3 頁垂直張力不足及第 5 頁「到」太靠近標題；第 4 頁元素截圖疑似裁切，改用完整 viewport 校準後確認實際安全，沒有用壞測量去改正常畫面。修正後第二輪八項清單全數合格。最終證據為 `.screenshots/v15-1-round2-desktop.png`、`.screenshots/v15-1-round2-mobile.png`；逐頁證據為 `.screenshots/v15-1-page1.png` 至 `.screenshots/v15-1-page7.png`，第 2、3、5 頁複驗另有 `*-updated.png`。
- **視覺清單**：層次合格；區塊間距有長短節奏；使用 LINE Seed 而非系統預設；主色限制為深藍、青、珊瑚；左右基線一致；375px 無橫向溢位；公司切換有 pressed／focus 狀態；卡片 hover 微動效保留。靜態原型不涉及載入、錯誤或空資料狀態。
- **跨內容壓力測試**：桌機三家公司各 12 項、手機三家公司各 11 項，共 69 項契約，失敗 0；1280px 與 375px 都是 `scrollWidth = clientWidth`，console 0 errors／0 warnings。無 key root 回 HTTP 403，帶既有 key 的 localhost 回 HTTP 200，符合保護設定。
- **全套測試**：`PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q` 為 `617 passed, 16 deselected, 1 warning in 78.88s`；warning 是既有 Starlette／httpx 相依提醒。
- **剩餘限制**：右上 Logo 目前是公司字標佔位，取得正式 Logo 後才能替換；v15.1 仍是本機隔離視覺原型，不是正式貼文產圖模板，必須先由使用者確認再搬入正式流程。
- **狀態**：v15.1 逐頁細修、三公司雙尺寸契約、兩輪截圖與全套測試完成，等待使用者在 localhost 逐頁檢視。

---

# 前一輪 — 七頁貼文模板 v12 混合回退原型

> 2026-08-20 更新。本輪只調整瀏覽器中的三公司壓力測試原型；正式貼文模板、內容資料與 SQLite 都沒有修改。

## 本輪目標與驗收

- 保留 v11 已獲核可的首頁與最後一頁。
- 第 2–6 頁完整恢復 v10 的 DOM 與排版，不混入 v11 中間頁元素。
- SUN、Billow AI Labs、Shiraz AI 各七頁都要通過 1280px 與 375px 寬度驗證。
- 正式貼文模板、內容資料與 SQLite 維持原狀，先交付隔離原型供使用者比較。

## 本輪狀態

- **產品能力**：新增隔離的 v12 混合原型；第 1、7 頁沿用 v11，第 2–6 頁完整恢復 v10，可用同一套結構切換 SUN、Billow AI Labs 與 Shiraz AI。
- **使用者體驗**：首頁與收尾保留使用者較喜歡的新版構圖，中間五頁回到上一版已熟悉的閱讀節奏，不再承擔 v11 新構圖造成的線條、框線與資訊層級風險。
- **技術結構**：以 v10 複製建立 multi-company-template-stress-v12.html，只把 cover-v12 與 closing-v12 兩個區塊換成 v11；hybrid-v12-contract.js 鎖住頁面組成與溢位。v10、v11、正式 Streamlit 元件、產圖模板及 SQLite 均未修改。
- **資料流程**：三家公司測試資料 → renderCompany → v12 七頁 DOM → 混合版契約檢查 → 公司切換器。沒有外部 API、資料保存、資料庫寫入或正式發文。
- **設計理由**：依使用者逐頁比較結果做回退，而不是再次發明新風格；保留獲肯定的首尾辨識度，同時讓中段回到較穩定的內容結構。
- **替代方案**：直接修補 v11 中間頁仍可能遺留不滿意的結構；完全退回 v10 則會失去已核可的首頁與最後一頁。v12 混合版以最小變動精確對應使用者選擇。
- **安全與成本**：沒有新相依、字型服務、生成圖片、付費操作、schema 變更或正式資料異動；原型仍位於 .superpowers/ 並受 .gitignore 排除。
- **TDD 證據**：先看到 v12 marker missing，再補版本標記；接著依序看到 v11 cover missing 與 v11 closing missing，再移植首尾。視覺檢查發現 v10 的 nowrap 洩漏到新版封面後，先補上 v10 cover nowrap leaked 失敗契約，再以 cover-v12 範圍覆寫修正。
- **回退精確度**：以程式比對 v10 與 v12 的第 2–6 頁 render 片段，diff 為空；契約同時禁止 v11 中間頁選擇器出現在 v12。
- **視覺 QA**：完成三輪桌面 1280×800／手機 375×812 截圖；最終封面與第二頁證據為 .screenshots/hybrid-v12-verify-desktop.png、.screenshots/hybrid-v12-verify-mobile.png，最後一頁證據為 .screenshots/hybrid-v12-final-mobile.png。
- **跨內容壓力測試**：三家公司各七頁、兩種寬度共 42 個版面狀態均為 0 overflow；三個實際切換按鈕皆正確更新 aria-pressed，手機 scrollWidth=clientWidth=375，console 0 errors／0 warnings，帶 key 的 localhost 為 HTTP 200。
- **全套測試**：PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q 為 617 passed, 16 deselected, 1 warning in 90.44s；warning 是既有 Starlette/httpx 相依提醒。
- **剩餘限制**：目前是本機視覺原型，不是正式貼文模板；必須先由使用者確認 v12 的逐頁畫面，才會搬入正式產圖流程。
- **狀態**：v12 原型與驗證已完成，等待使用者視覺確認。

### 前一版 v11 紀錄

- **產品能力**：新增隔離的 v11 七頁原型，同一份公司資料可切換 SUN、Billow AI Labs、Shiraz AI；封面、定位、問題、機制、結果、訊號與收束各自使用不同閱讀構圖，不再是一組格子重複換字。
- **使用者體驗**：封面以大標、描邊公司字與橘色註記線形成科技編輯海報；第二頁改為貼齊的青色主論點＋右側兩段資訊；第三頁用逐步加重的問題鏈；第四頁用階梯整合 AI 與人工責任；第五頁讓大字「到」跨接雙色色面；第六頁改為三列 evidence ledger；第七頁用全寬深色問題區與底部橘色帶收束。
- **技術結構**：保留 v10 為只讀失敗基準，另建 `multi-company-template-stress-v11.html` 與 `editorial-v11-contract.js`。`renderCompany` 仍提供資料，v11 只替換七頁 DOM 與 CSS；正式 Streamlit 元件、產圖模板與 SQLite 均未修改。
- **資料流程**：三家公司測試資料 → `renderCompany` → v11 七頁語意 DOM → 瀏覽器契約檢查 → 公司切換器。沒有外部 API、資料保存、資料庫寫入或正式發文。
- **設計理由**：採科技編輯雜誌方向，以 LINE Seed、深藍、紙白、青色與珊瑚橘延續品牌；用不對稱欄位、橫線、註記與色面建立節奏，刻意排除圓角 SaaS 卡片、bento grid、橢圓流程、hashtag 方格、日期與來源。
- **替代方案**：保留 v10 卡片骨架的成本最低，但會延續「每頁長得一樣」與 AI 模板感；全頁都改成深色海報辨識度高，卻會犧牲內容閱讀與跨公司彈性。現行方案保留一個設計語言、讓七頁使用不同構圖，較適合作為可重複模板。
- **安全與成本**：沒有新相依、字型服務、生成圖片、付費操作或 schema 變更。v11 原型位於 `.superpowers/` 並受 `.gitignore` 排除；使用者核可前不搬入正式產圖流程。
- **TDD 證據**：逐頁先看見 `v11 marker missing`、`editorial cover structure missing`、`profile thesis missing`、`problem chain missing`、`mechanism steps missing`、`large transition word missing`、`evidence ledger missing`、`closing question missing` 等紅燈，再做最小 DOM／CSS 實作轉綠。後續新增標題碰撞與結尾占版契約，先重現桌面碰撞與問題區過小，再修成雙寬度通過。
- **視覺 QA**：完成六輪桌面 1280×800／手機 375×812 截圖檢查；實際抓到第二頁無效大白、第三／四頁上擠下空、第六頁標題撞線、第七頁問題區過小，逐項修正後再截。最終證據為 `.screenshots/editorial-v11-final2-desktop.png`、`.screenshots/editorial-v11-final2-mobile.png`。
- **跨內容壓力測試**：SUN、Billow AI Labs、Shiraz AI 各七頁，在 1280px 與 375px 共 42 個版面狀態皆為 0 overflow；三個實際切換按鈕皆更新 `aria-pressed` 並維持契約通過；手機 `scrollWidth=clientWidth=375`，console 0 errors／0 warnings，localhost HTTP 200。
- **全套測試**：`PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q` 為 `617 passed, 16 deselected, 1 warning in 94.98s`；warning 是既有 Starlette/httpx 相依提醒。
- **剩餘限制**：目前是本機視覺原型，不是正式貼文模板；下一步必須由使用者先確認 v11 的整體方向與個別頁面，再把核可結構搬入正式產圖流程。
- **狀態**：v11 原型與驗證完成，正式模板、正式內容與 SQLite 維持原狀，等待使用者視覺確認。

---

# 前一輪 — 僅限官網的官方 Logo 搜尋

> 2026-08-18 更新。產品負責人要求完全移除第三方 Logo API；系統現在只從已驗證官網尋找候選，找不到就手動上傳。

## 本輪目標與驗收

- 以公司名、題目、切角、正文與查證來源辨認正確官網。
- 依序檢查官網靜態素材與瀏覽器渲染後的動態素材，最多顯示三張候選。
- 候選必須由使用者人工確認才保存；拒絕不重搜，找不到就手動上傳。
- 不使用第三方 Logo API，不保留其 adapter、憑證、設定、測試或現行文件。
- 缺 Logo 只擋七張圖，不擋文字輪播草稿。

## 本輪狀態

- **產品能力**：Logo 搜尋會先解析官方網站，再從首頁、品牌頁、JSON-LD、圖片、內嵌 SVG、CSS 背景與動態渲染頁面找安全候選；工作台最多顯示三張。
- **使用者體驗**：候選卡顯示官方網域、官網來源、完整 Logo／品牌符號／網站圖示類型、判定理由與原始連結。只有「確認這是官方 Logo」會寫入；拒絕只移除該候選。找不到時仍可重搜或手動上傳，文字草稿按鈕保持可用。
- **技術結構**：`official_site` 負責身分與網域，`logo_discovery` 負責靜態素材，`logo_browser` 負責動態渲染，`logo_search` 只編排官方路徑，`assets.store_logo` 維持唯一正式寫入入口。
- **資料流程**：Idea 公司與內容脈絡＋查證來源 → 官方網站證據 → 官網靜態／動態素材 → session 候選 → 人工確認 → SQLite 品牌資產與本機 Logo 檔案。
- **設計理由**：短公司名容易撞到同名品牌；先確認網域再找素材，比直接猜圖片安全。產品負責人選擇硬移除第三方備援，避免未來誤開或把外部資料誤當官方來源。
- **替代方案**：曾考慮停用但保留 adapter，缺點是程式與憑證仍存在、未來可能被重新啟用；現行方案以手動上傳作為唯一備援，犧牲少量自動命中率換取更清楚的信任邊界。
- **安全與成本**：沒有第三方 Logo 憑證、設定或請求，沒有新依賴與費用。候選預覽不寫 DB；原檔連結顯示前會移除 query string；SVG／透明 PNG 仍走既有安全驗證。
- **TDD 證據**：官網空結果測試先得到舊第三方 stage 再轉成 `official_assets`；工作台先捕捉到仍傳憑證參數再移除；設定頁與 runtime 檔案存在測試先紅再刪除。搜尋編排 `4 passed`、工作台 `11 passed`、設定 `9 passed`、Logo／設定聚焦 `39 passed`、預覽與設定聚焦 `25 passed`。
- **真實邊界**：SUN 精確解析為 `sunapp.ai`，Moove 官網 Logo 通過本機安全驗證；合併執行為 `2 passed, 20 deselected in 1.04s`。一般官網單元為 `20 passed, 2 deselected in 0.13s`。
- **視覺 QA 第一輪**：1280×800 與 375×812 發現白色 SUN Logo 在淺色背景幾乎不可見；其餘層次、留白、字體、配色、對齊、狀態與響應式合格。
- **視覺 QA 最終輪**：加入左右淺／深雙背景預覽後，白色 SUN Logo 可清楚核對。手機 `scrollWidth=clientWidth=375`，console 0 errors／0 warnings；副本最終截圖為 `.screenshots/logo-official-only-final-desktop.png`、`.screenshots/logo-official-only-final-mobile.png`。
- **全套測試**：第一次為 `616 passed, 16 deselected, 1 warning`，另有一個既有 CSS 測試因全域字串比對誤判 Logo 卡片邊線；將測量範圍縮到輪播清單後，第二次為 `617 passed, 16 deselected, 1 warning in 74.00s`。warning 是既有 Starlette/httpx 相依提醒。
- **殘留掃描**：先以 `rg --version` 確認 ripgrep 15.2.0 可用，再掃 runtime 與刪除臨時計畫後的完整 active tree；兩次皆為退出碼 1、空輸出，代表移除的供應商名稱與環境變數沒有殘留。
- **main 與推送**：fast-forward 合併後以 `PYTHON_DOTENV_DISABLED=1` 重跑，結果為 `617 passed, 16 deselected, 1 warning in 70.23s`；compileall、`git diff --check` 與殘留掃描通過。本機與 `origin/main` 當時均為 `b48460305c2e048ef995ab2005926e0a3d846365`。
- **正式備份與資料安全**：重啟前建立 `/private/tmp/daibu-before-official-logo-20260818-134035.db`；備份與正式庫皆為 23 ideas、0 brand assets、6 idea sources、`integrity_check=ok`。唯讀畫面驗收後正式庫數量不變，沒有儲存候選。
- **正式服務與畫面**：既有 `io.daibu.content-brain` 已重啟，`state=running`、PID `39504`、只監聽 `127.0.0.1:8501`，HTTP 200。從首頁正常進入 SUN 輪播工作區，系統將官方網站解析為 `sunapp.ai`，顯示一張官網直接引用候選、原始 Logo 連結與人工確認閘門；畫面沒有舊第三方服務文字。
- **正式前端驗收**：1280×800 與 375×812 的候選區層次、留白、字體、配色、對齊、響應式、狀態與微動效全部合格；手機 `scrollWidth=clientWidth=375`，console 0 errors／0 warnings。正式細節截圖為 `.screenshots/logo-official-only-production-desktop-detail.png`、`.screenshots/logo-official-only-production-mobile-detail.png`。伺服器 stderr 最後修改時間仍為 2026-08-13 12:45:16，本輪沒有新增 server exception。
- **剩餘限制**：Canvas、封閉資源或反爬嚴格的官網仍可能無法自動擷取；品牌身分與最終 Logo 選擇仍需使用者判斷。
- **狀態**：功能、真實官網契約、資料庫副本、兩輪桌機／手機 QA、main 複驗、推送與既有 localhost 正式服務皆已完成。

---

# 前一輪 — AI 新創選題多樣性

> 2026-08-13 17:00 更新。使用者核可每批五則、AI 基礎建設最多一則、企業／產業應用與其他單一類別最多兩則、至少三類，並允許最多檢查四十家公司。

## 本輪目標與驗收

- AI 新創介紹每次產生 5 則；一般系列不改。
- 公司依核心產品與主要客戶分成六個主類別；每批 AI 基礎建設最多 1、任何其他單一類別最多 2、至少 3 類。
- 先看 15 家，不足再擴到 25、最多 40；每次只分類新增加的公司。
- 40 家仍無解、分類失敗、資格不足或模型回傳不完整時，新增 ideas 必須是 0。
- 五則必須一次成功寫入；中途資料庫錯誤不可留下半批。

## 本輪狀態

- **產品能力**：新增六類公司分類與硬性配額選擇器。分類依公司核心產品／客戶，不依貼文角度；可行組合中優先選類別數較多者。
- **來源取捨**：保留 YC Launches、YC Companies、a16z Speedrun 與 TechCrunch Startups；YC 與 a16z 目錄改成交錯取樣，避免前 40 家被單一目錄佔滿。TechCrunch 仍只做一家具時效新聞的補強，不主導整批。
- **漸進分類**：來源一次取得最多 40 家，Gemma 分類呼叫依序只送 15、10、15 家；每階段有可見進度。Gemma 可恢復錯誤仍沿用既有 GoogleTaskRouter，自動改用 Gemini 3.5 Flash-Lite。
- **資格補位**：先從已分類池選五家，再沿用現有 YC 官方快速判定與資格快取；不合格／unknown 公司會被排除並從同一池補位。分類本身不新增 Tavily 搜尋。
- **輸出契約**：模型只能替選定的五家公司寫題。程式核對剛好五則、公司一一對應、題目不重複，以及網址／逐字引文屬於該公司素材；任一不符整批拒絕。
- **原子寫入**：新增 `db.add_ideas_atomic`，以 SQLite savepoint 保證五筆全成或全退。用第三筆觸發器故障的測試證明前兩筆也會回復。
- **預設與搬遷**：新資料庫的 AI 新創系列為 5 則；既有 `company_profile` 系列只搬遷一次到 5，一般系列原數量不變。沒有新增 schema。
- **API 卡住修正**：副本真實流程第一次發現一般文字／分類請求沒有把既有 45 秒 timeout 傳入 Google SDK，畫面會無限卡住。依紅→綠補測試後，`generate_text` 現在和輪播一樣有 timeout；Gemma 超時後仍可走 Gemini 備援。
- **TDD 證據**：逐一看見分類解析、配額、15／25／40、資格補位、零寫入、原子 rollback、數量搬遷、錯誤文案與文字 timeout 的紅燈，再做最小實作轉綠。相關聚焦測試為 `238 passed`；`tests/test_llm.py` 為 `57 passed`。
- **真實 Gemma 契約**：六家公司描述回傳六個允許類別且各一類，`1 passed in 20.99s`。
- **全套測試**：timeout 修正後功能分支為 `592 passed, 15 deselected, 1 warning in 57.53s`；15 個略過項需外部服務，唯一 warning 是既有 Starlette/httpx 提醒。
- **副本校準**：SQLite `.backup` 建立 `/private/tmp/daibu-diversity-qa.ElOtSy/daibu.db`。正式與副本起始皆為 18 ideas、16 筆資格、`integrity_check=ok`；ideas 全欄位 JSON SHA-256 都是 `b427d57b51bd51c85b387ff2aeaff18915a65e90dd7061ae3746a1af0bc86563`。
- **副本真實產生**：8502 只點擊一次完成後，副本 ideas 由 18 增至 23、資格由 16 增至 22；新增 Hammock、August、Shiraz AI、Click、Pennant，恰好五家且公司不重複。正式庫仍為 18、`integrity_check=ok`、指紋仍為 `b427…6563`。
- **使用者結果**：真實新增批次涵蓋消費／金融、機器人、企業研究與公司治理等方向，沒有 AI 基礎建設集中問題；畫面顯示「再產生 5 則」與候選（15）。
- **視覺 QA 第一輪**：淺色 1280×800、375×812；層次、留白、字體、配色、對齊、響應式、狀態與動效均合格，手機 `scrollWidth=clientWidth=375`，console 0 errors／0 warnings。不合格項目：無。
- **視覺 QA 第二輪**：深色 1280×800、375×812；同八項維持合格，手機無水平溢出，console 0 errors／0 warnings。最終截圖：`.screenshots/startup-diversity-round2-desktop.png`、`.screenshots/startup-diversity-round2-mobile.png`。
- **安全與成本**：無新依賴、付費服務、API key 或資料表。最壞三次分類＋一次寫題；資格查核成本沿用既有規則。分類與題目錯誤不顯示原始 provider detail。
- **剩餘限制**：分類依目錄短描述，跨領域公司仍可能與人的判斷不同；分類目前不持久化，也沒有人工覆寫。Gemma 與 Gemini 同屬 Google，無法處理 Google 整體故障。
- **main 全套測試**：合併後以 `PYTHON_DOTENV_DISABLED=1` 重跑，結果為 `592 passed, 15 deselected, 1 warning in 59.17s`。
- **推送**：`origin/main` 與本機 `main` 均為 `6fb2a07e136266a0b3f3552ace13429e64c1093e`。
- **正式備份**：更新前建立 `backups/daibu-before-startup-diversity-20260813-1705.db`；備份與正式庫均為 18 ideas、16 筆資格、`integrity_check=ok`，系列數量為 3。
- **正式搬遷**：重啟 `io.daibu.content-brain` 後，第一次實際開頁才執行 `init_schema`；只把 `company_profile.n_ideas` 更新為 5 並寫入一次性 key。正式 ideas 仍為 18、資格仍為 16、`integrity_check=ok`，ideas 指紋仍為 `b427d57b51bd51c85b387ff2aeaff18915a65e90dd7061ae3746a1af0bc86563`。
- **正式服務與畫面**：LaunchAgent `state=running`，新 PID `46304`，只監聽 `127.0.0.1:8501`；stderr mtime 重啟前後相同，沒有新 server error。從首頁正常導覽到內容製作，顯示「再產生 5 則」；1280px 與 375px 都無水平溢出，console 0 errors／0 warnings。未在正式資料庫按產生按鈕。
- **狀態**：功能、真實模型、資料副本、真實五則流程、兩輪明暗與桌機／手機 QA、main 全測、推送、正式搬遷與正式 localhost 均已驗收。

---

# 前一輪 — Gemma 選題與 Gemini 備援

> 2026-08-13 14:00 更新。正式系統原本使用 `gemini-3.1-flash-lite`；12:45 的失敗是 Gemini 503 暫時繁忙，不是 429 額度耗盡。本輪依使用者核可，拆分高頻選題與格式敏感任務。

## 本輪目標與驗收

- 選題與必要公司資格查核優先使用 `gemma-4-26b-a4b-it`。
- Gemma 遇額度、逾時、503，或選題連續兩次格式失敗時，自動改用 `gemini-3.5-flash-lite`。
- 350–500 字正文與七頁輪播固定使用 Gemini 3.5 Flash-Lite。
- 不新增付費服務或 Groq key；不修改正式 ideas 做 QA。

## 本輪狀態

- **模型可用性**：Google Models API 實查目前 key 可呼叫 `gemma-4-26b-a4b-it`、`gemma-4-31b-it`、`gemini-3.1-flash-lite` 與 `gemini-3.5-flash-lite`；採用較適合高頻的 Gemma 4 26B。
- **任務路由**：新增 `GoogleTaskRouter`。`generate_ideas` 走 Gemma 並在可恢復失敗時切 Gemini；資格查核使用獨立 `generate_research_text`；一般 `generate_text` 與 `generate_carousel_text` 直接走 Gemini，避免正文被意外換模。
- **設定資料流**：新增 `llm_idea_model`／`LLM_IDEA_MODEL`，既有 `llm_model`／`LLM_MODEL` 改代表正文、備援與輪播模型。Groq 明確選擇仍維持原本行為。
- **TDD**：逐一看見缺少路由器、503 未切換、資格仍走一般文字、Gemini 預設仍為 3.1、設定頁未拆欄位與標籤不精確的紅燈，再做最小修正轉綠。
- **真實 Gemma 契約**：直接指定 Gemma、不允許備援，產出一則可解析、公司名為 Feldy 且標題含繁體中文的候選，`1 passed in 20.79s`。
- **真實雙模型契約**：Gemma 候選與 Gemini 3.5 七頁輪播同跑，`2 passed in 43.36s`；輪播七頁皆有 sections 並成功存回 SQLite 測試庫。
- **副本資料安全**：以 SQLite `.backup` 從正式絕對路徑建立 `/private/tmp/daibu-gemma-routing-qa.iG2HzU/daibu.db`；來源與副本起始均為 12 ideas、`integrity_check=ok`，ideas JSON SHA-256 均為 `405c705c707590ce3a9802392864ba7f9a87697b0b5a5e9fee5bc55a8595c9da`。
- **一次完整產生**：8502 僅點擊一次，候選由 4 增為 7，副本 ideas 由 12 增為 15；新增 Parasma、Billow AI Labs、Almanac。正式庫仍為 12，指紋仍為 `405c…9da`；副本 `integrity_check=ok`，browser console 0 errors／0 warnings。
- **視覺 QA**：設定頁完成多輪 1280×800 與 375×812。第一輪抓到任務說明不完整後補上正文／資格分工；直接重新整理中文子路徑會產生既有 `_stcore` 相對路徑 404，最終改由首頁正常導覽。最終兩尺寸模型值正確、手機 `scrollWidth=clientWidth=375`、console 0 errors／0 warnings。截圖：`.screenshots/gemma-routing-final-desktop.png`、`.screenshots/gemma-routing-final-mobile.png`。
- **全套測試**：功能分支為 `560 passed, 14 deselected, 1 warning in 66.83s`；14 個略過項目需真實外部服務，唯一 warning 是既有 Starlette/httpx 提醒。
- **main 全套測試**：先確認未隔離測試會被正式 `.env` 重新注入 key，另有一次既有 AppTest 3 秒逾時；用 `PYTHON_DOTENV_DISABLED=1` 讓每個案例只使用自己注入的測試環境後，結果為 `560 passed, 14 deselected, 1 warning in 63.23s`。
- **安全與自審**：compileall、`git diff --check` 通過；秘密掃描先以合成 AIza key 校準後掃 production diff，沒有 Google、Groq 或 Tavily key。因本輪禁止子代理，依 review checklist 自審，未發現 Critical／Important 問題。
- **正式設定備份**：切換前建立 `backups/daibu-before-gemma-routing-20260813-140254.db`，正式庫與備份均為 `integrity_check=ok`、12 ideas、13 筆資格。
- **正式模型設定**：只更新三列為 `llm_provider=gemini`、`llm_idea_model=gemma-4-26b-a4b-it`、`llm_model=gemini-3.5-flash-lite`；與備份逐列比對，ideas 差異 0、資格差異 0。
- **正式服務**：管理命令再次遇到既有 `launchctl` 卸載後立即載入的時序問題；確認服務已卸載、plist `OK`、8501 無占用後，只對 `io.daibu.content-brain` bootstrap＋kickstart。最終 LaunchAgent `running`、health `ok`，只監聽 `127.0.0.1:8501`，stderr 最後修改時間仍為 12:45:16，沒有新增 server error。
- **正式使用者視角**：從首頁正常導覽到設定頁，正式畫面顯示 Gemma 4 26B 與 Gemini 3.5 Flash-Lite，1280×800 與 375×812 都無水平溢出，console 0 errors／0 warnings；截圖為 `.screenshots/gemma-routing-production-desktop.png`、`.screenshots/gemma-routing-production-mobile.png`。再進內容製作，候選（4）與 Risklytics 正常出現，未點擊正式產生按鈕。
- **剩餘限制**：Gemma 與 Gemini 共用 Google API，只能分散模型別配額／容量，不能處理 Google 整體故障；跨平台備援仍需日後設定 Groq key。
- **狀態**：程式、真實模型契約、資料副本、完整候選流程、main 全套測試、正式設定、推送、正式服務與正式畫面皆已驗收。

---

# 前一輪 — YC 公司身分資格修正

> 2026-08-13 12:50 更新。11:56 的「沒有符合資格」不是來源或 API 失效，而是裸公司名搜尋把 YC Almanac 認成 Almanac Realty Investors，並遺失 YC 已知的官方網域、成立年與 batch。

## 本輪目標與驗收

- 資格查核必須接收完整 `CompanyLead`，不可只傳公司名稱。
- 成立、上市與收購證據若無法對上官方網域或 YC 公司身分，不得淘汰公司；證據不足仍為 unknown，不自動放行。
- 依使用者核可，YC 官方頁的 `Active`＋官方網站＋十年內成立年／batch 可直接判定 eligible；`Public`／`Acquired` 直接判定 ineligible。
- Almanac、Feldy、Marengo 的受污染資格紀錄要在備份後精確修正；不得修改任何既有 idea。

## 本輪狀態

- **根因證據**：11:55:59 新增 Almanac=`ineligible/acquired`、Feldy／Marengo=`unknown`。Almanac 唯一證據是 LinkedIn 的 Almanac Realty Investors 收購紀錄；實際 YC Almanac 為 Summer 2026、Active，官方網站 `usealmanac.com`。
- **身分資料流**：selection 現在把 discovery 的 YC profile、官方網址、成立年、batch、狀態與來源名稱完整交給資格查核；legacy backfill 仍相容純字串。
- **同名防護**：有已知官方身分時，外部成立／上市／收購證據必須對上官方網域、YC profile 或 launch 身分；否則捨棄該證據並保持 unknown。官方網域上的真實 public 證據仍會判 ineligible。
- **YC 專屬規則**：只有 `source_name=YC Launches`、profile 為 `ycombinator.com`、狀態 `active`、有官方網站，而且成立年或 batch 年在十年內才直接 eligible。batch 年只保存成 `recent_batch` 證據，不冒充成立年。YC `public/acquired` 直接保存不合格紀錄。
- **成本**：符合上述條件的 YC 公司資格查核為 Tavily 0 次、資格 Gemini 0 次；非 YC 或身分不足者仍沿用每家公司一次 Tavily＋整批一次免費 LLM。
- **TDD**：逐一看見完整身分輸入、YC 年份證據、同名收購、同名年份、selection 身分傳遞、YC Active 直通與 YC public/acquired 直擋的紅燈，再做最小修正。聚焦資格／selection 為 `42 passed`。
- **副本資料安全**：用 SQLite Backup API 建立 `/private/tmp/daibu-company-identity-qa-019ffbe2-v2.db`。清除副本三筆前後均為 12 ideas，ideas JSON SHA-256 都是 `f75cfde255d25b6917fb6020d39fff2792ddfa8cb40baa41c0184d113a1bbf33`；其餘十筆資格 JSON SHA-256 都是 `2144bc6ccd918ea930cb170731c089b1a727b2f8c920a899fc2599b465a824d6`。
- **副本真實身分**：直接讀當下 YC Launches＋YC Companies 後，Almanac、Feldy、Marengo 都是 eligible/private_independent；Almanac 用 Summer 2026 batch，Feldy=2024、Marengo=2026，每家兩筆 YC profile 證據，且測試替身保證未呼叫 Tavily／Gemini。
- **一次真實產生**：8502 只點擊一次。資格已通過，但題目 Gemini 回 `LLMUnavailableError/ServerError`；畫面精確顯示「Gemini 暫時繁忙」，ideas 仍為 12，未重試。
- **視覺 QA**：兩輪各一張 1280×800 與 375×812。第一輪錯誤狀態層次、留白、字體、配色、對齊、響應式、狀態與動效合格，但直接開中文子路徑留下兩個既有 Streamlit 初始化 404；第二輪從首頁正常導覽後，兩尺寸 `scrollWidth=clientWidth`、候選（4）存在、console 0 errors／0 warnings。最終：`.screenshots/company-identity-round2-desktop.png`、`.screenshots/company-identity-round2-mobile.png`。
- **功能分支全套**：`551 passed, 13 deselected, 1 warning in 70.64s`；13 個略過項目需要真實外部服務，唯一 warning 是既有 Starlette／httpx 提醒。
- **合併 main 後全套**：`551 passed, 13 deselected, 1 warning in 64.84s`，exit code 0；唯一 warning 仍是既有 Starlette／httpx 提醒。
- **安全與自審**：compileall、`git diff --check` 通過；秘密掃描先用合成 AIza 字串校準，再掃 production diff，無 Gemini／Groq／Tavily key。依無子代理規則完成逐段自審，未發現 Critical／Important 問題。
- **正式備份**：`backups/daibu-before-company-identity-20260813-123742.db` 為 `integrity_check=ok`、12 ideas、13 筆資格，ideas JSON SHA-256=`f75cfde255d25b6917fb6020d39fff2792ddfa8cb40baa41c0184d113a1bbf33`。
- **正式 metadata 修正**：只覆寫 Almanac、Feldy、Marengo 三筆；現在三家都是 `eligible/private_independent`，Feldy=2024、Marengo=2026，Almanac 的成立年維持 null 並保存 Summer 2026 batch。修正過程 Tavily 0 次、Gemini 0 次。
- **正式資料複驗**：仍為 12 ideas、13 筆資格、`integrity_check=ok`；ideas 指紋仍為 `f75c…f33`，其餘十筆資格指紋仍為 `2144bc6ccd918ea930cb170731c089b1a727b2f8c920a899fc2599b465a824d6`。
- **正式服務**：管理命令再次遇到既有 `launchctl` 卸載後立即載入的時序問題；確認 plist `OK`、服務未載入與 8501 無占用後，只對 `io.daibu.content-brain` bootstrap＋kickstart。最終 `state=running`、健康檢查 `ok`，只監聽 `127.0.0.1:8501`。
- **正式使用者視角**：從首頁正常導覽到 `http://127.0.0.1:8501/選題`，顯示候選（4）與 Risklytics；1280px、375px 都無水平溢出，console 0 errors／0 warnings。正式截圖：`.screenshots/company-identity-production-desktop.png`、`.screenshots/company-identity-production-mobile.png`。
- **正式 log**：stderr 最後修改時間仍為 11:55:59，本輪重啟與唯讀畫面驗收沒有新增 server error。
- **狀態**：程式、資料副本、正式 metadata、main 全測、正式服務與正式畫面皆已驗收並推送。

## 前一輪：候選產生錯誤診斷

> 2026-08-13 11:34 更新。正式畫面再次出現泛用失敗訊息；根因不是資料遺失，而是多種已知外部錯誤沒有完整接到前台，且未知錯誤沒有留下安全診斷紀錄。

## 本輪目標與驗收

- Gemini 免費額度、超時、503 繁忙與回覆格式錯誤必須顯示不同的白話原因。
- 公司資格查核裡的 Gemini 錯誤不得被包成模糊的資格失敗；非 Gemini 的資格查核失敗仍需指出正確階段。
- 未知錯誤維持安全泛用文案，但 log 至少留下外層與根因的「類型」，不可記錄錯誤原文、API key、完整 prompt 或下載內容。
- 每種失敗都不得新增 idea 或不完整的資格快取；不得用重複點擊正式 API 來製造錯誤。

## 本輪狀態

- **QA 漏洞**：上一輪只驗證來源失敗、公司重複、資格不符與 Gemini 503；`LLMQuotaError`、`LLMTimeoutError`、`LLMResponseError` 與 `CompanyEligibilityVerificationError` 都會落入同一個泛用訊息。
- **11:34 證據邊界**：失敗後正式庫仍為 12 筆 ideas、10 筆資格紀錄，最新寫入仍是 11:29 的成功批次，證明 11:34 沒有半成品。但舊版 catch 沒寫 log，因此不能誠實斷言唯一根因是額度、超時、格式或 Tavily／資格服務。
- **錯誤保真**：資格查核現在會讓 Gemini 額度、超時與 503 原樣往前傳；其他資格查核錯誤才包成 `CompanyEligibilityVerificationError`。
- **前台文案**：已補 Gemini 額度、超時、模型格式與資格查核四個分支；原始錯誤文字不會顯示。
- **安全診斷**：所有候選產生錯誤會記錄 `error_type` 與 `cause_type`，不記 `str(error)` 或 traceback，避免第三方訊息意外含秘密或完整內容。
- **TDD**：八個回歸切片都逐一看見紅燈再做最小修正轉綠；模型、資格管線與選題頁整合為 `174 passed in 30.47s`。
- **功能分支全套**：`540 passed, 13 deselected, 1 warning in 59.38s`；13 個略過項目需真實外部服務，唯一 warning 是既有 Starlette／httpx 相依提醒。
- **合併 main 後全套**：`540 passed, 13 deselected, 1 warning in 54.55s`，exit code 0；唯一 warning 仍是既有 Starlette／httpx 相依提醒。
- **資料安全**：資格查核的三個 Gemini 錯誤測試都斷言 ideas 與資格快取為空；本輪沒有再次點擊正式產生按鈕。
- **真實邊界（零 API 呼叫）**：在正式資料的暫存副本把 provider 設成受控無效值，從 8502 真實點擊「再產生 3 則」。前台顯示安全泛用訊息，server 只記錄 `generation_failed error_type=ValueError cause_type=none`，沒有記錄錯誤原文或無效設定值；副本仍為 12 筆 ideas、10 筆資格紀錄，證明錯誤跨過 Streamlit 邊界後也不會半套寫入。
- **視覺驗收**：正式資料的 SQLite 副本在 8502 完成兩輪桌機／手機檢查。第一輪桌機抓到骨架載入未結束，判定狀態不合格；第二輪改以候選內容出現為條件，1280×800 與 375×812 都顯示 4 筆候選，手機 `scrollWidth=clientWidth=375`，console 0 errors／0 warnings。最終證據：`.screenshots/generation-errors-round2-desktop.png`、`.screenshots/generation-errors-round2-mobile.png`。
- **UI 檢視**：

  | Before | After | Why |
  |---|---|---|
  | 額度、超時、格式與資格錯誤都顯示泛用訊息 | 每類有自己的白話訊息 | 使用者不用猜來源或資格規則 |
  | 資格查核把 Gemini 錯誤包掉 | 額度／超時／繁忙保留到前台 | 不丟失真正失敗原因 |
  | 未知錯誤沒有 log | 只記錄外層與根因型別 | 可診斷，同時避免秘密外洩 |

- **正式服務**：管理命令再次遇到既有 `launchctl` 卸載後立即載入的時序問題；確認 plist 為 `OK`、舊服務確實未載入後，只對精確標籤 `io.daibu.content-brain` 執行 bootstrap＋kickstart。最終 `state=running`、健康檢查回 `ok`，且只監聽 `127.0.0.1:8501`。
- **正式資料複驗**：重啟前後都是 12 筆 ideas、10 筆資格紀錄；ideas 全 11 欄依 id 排序後的 SHA-256 都是 `86983e7be4f3f91b9eaca5f5f88e68bc385e78d56854ccc87efb7de82523a746`，本輪沒有修改正式內容。
- **正式使用者視角**：`http://127.0.0.1:8501/選題` 顯示 4 則候選與 Risklytics；1280px 與 375px 的 `scrollWidth` 都等於 viewport，browser console 0 errors／0 warnings。最終截圖：`.screenshots/generation-errors-production-desktop.png`、`.screenshots/generation-errors-production-mobile.png`。
- **狀態**：本輪程式、main 全測、受控錯誤邊界、正式服務、正式資料與正式畫面皆已驗收。

## 前一輪：AI 新創來源重整

> 2026-08-13 更新。「AI 新創介紹」已改用公司目錄找新公司、用新聞補時效性，最後才用公開證據查資格。

## 本輪目標與驗收

- 從 YC Launches 與 a16z Speedrun 發現當期 AI 新創，再用 YC Companies 補公司年份與狀態。
- TechCrunch Startups 只會補在已知公司上，不會因為一篇新聞就擅自創建公司候選。
- 歷史公司在查詳情與新聞前先排除；上市、被收購、超過十年或證據不足仍由現有 Tavily＋Gemini 資格守門擋下。
- 所有舊題目、正文、狀態、輪播圖與資格快取保留，移轉只改本系列今後的來源綁定。

## 本輪狀態

1. **產品能力**：一次點擊會從 YC Launches 與 Speedrun 找當期 AI 公司，用 YC Companies 補身分，再最多搭一則 TechCrunch 近期新聞。
2. **使用者體驗**：操作仍是「開始／再產生 3 則」；來源無法取得、公司都重複、資格不符與 Gemini 繁忙會顯示不同說明，不再全部誤報成資格失敗。
3. **技術區塊**：公司目錄 adapter 負責讀公開網頁；discovery 負責排重、初步狀態過濾與新聞配對；免費 LLM 負責整理候選；現有資格守門負責證據查核；SQLite 保存題目與快取。
4. **資料流**：公司目錄 → 歷史／狀態初濾 → 近期新聞 → 題目 LLM → Tavily 證據／整批資格 LLM → 只寫入合格候選。
5. **設計理由**：「這是哪家公司」、「現在為什麼值得寫」、「它是否符合系列資格」是三個不同問題，分開證據才不會把 API 繁忙誤當成資格過嚴。
6. **替代方案**：RSS-only 最省事，但容易只看到新聞熱度而非新公司；directory-only 公司身分比較穩，但缺少「為什麼是現在」。採用目錄＋新聞＋資格證據的三層組合。
7. **安全與成本**：只讀公開目錄，沒有新付費服務或新金鑰；每個未查公司最多一次 Tavily、每批最多一次資格 LLM，不重試湊滿三則。紀錄不含 API key、完整 prompt 或整頁下載內容。
8. **測試證據**：每個切片都先看見失敗測試再實作轉綠。最終聚焦套件 `209 passed, 5 deselected in 36.56s`；狀態修正後分支全套為 `532 passed, 13 deselected, 1 warning in 77.20s`，合併 main 後同套件為 `532 passed, 13 deselected, 1 warning in 108.00s`。YC Launches、YC Companies、Speedrun 與 TechCrunch 真實契約合計 `5 passed, 7 deselected in 2.51s`。
9. **剩餘限制**：公開網頁格式未來可能改版；目前沒有排程自動更新，也沒有處理公司別名；免費 Gemini 仍可能暂時繁忙。

- **舊來源處理**：Y Combinator Blog 保留、啟用，但不再綁在「AI 新創介紹」；舊 a16z RSS 保留成停用記錄且解除綁定；其他系列與來源不變。
- **副本真實流程**：以 SQLite Backup API 從正式庫建立 `/private/tmp/daibu-startup-source-acceptance-019ffbe2.db`。產生前後都是 10 筆 ideas，全欄位 SHA-256 同為 `b4908c2ec754419927b83bbe5a7efaebbcda4dcb9add57de9f5538f1fd31d9c8`。
- **這次實測結果**：四個來源綁定正確，又找不到新候選的根因是「Gemini 暂時繁忙」，不是資格過嚴或目錄來源無法使用。失敗後原候選與題目指紋不變。
- **狀態回歸**：視覺驗收發現失敗後仍殘留「呆一布正在讀資料」。回歸測試先紅後綠，現在等待中只用 spinner，失敗後只留復原說明與精確原因；選題頁 `103 passed in 31.49s`。
- **視覺驗收**：依規則完成三輪，每輪各一張 1280×800 與 375×812。最終四個新來源清楚勾選、舊 a16z 清楚停用，手機 `scrollWidth=clientWidth=375`，console 0 errors／0 warnings。最終證據：`.screenshots/startup-sources-round3-desktop.png`、`.screenshots/startup-sources-round3-mobile.png`。
- **UI 檢視**：

  | Before | After | Why |
  |---|---|---|
  | 失敗後同時顯示「正在讀資料」與失敗原因 | 等待時只有載入提示，結束後只顯示成功或實際失敗階段 | 避免互相矛盾的狀態讓人誤判根因 |
  | 公司目錄無專屬抓取類型 | 來源編輯器有「公司目錄」，且只接受核可的三個網址 | 不讓畫面假裝任意目錄都會解析 |

- **正式資料導入**：導入前用 SQLite Backup API 建立 `backups/daibu-before-startup-sources-20260813-1130.db`；備份與正式庫均為 `integrity_check=ok`、10 筆 ideas、7 筆資格紀錄，ideas 指紋同為 `b4908c2ec754419927b83bbe5a7efaebbcda4dcb9add57de9f5538f1fd31d9c8`。移轉後該指紋仍不變，`config.startup_source_strategy_v1=1`，四個新來源精確綁定，YC Blog 與舊 a16z 皆無綁定。
- **正式一次核心流程**：只點擊一次「再產生 3 則」，成功新增 Dipole Labs 與 Risklytics，兩家均為 2026 年成立、`eligible/private_independent`，來源都是 YC Launches 的可點擊 HTTPS 頁面。正式庫現為 12 筆 ideas、10 筆資格紀錄，舊 10 筆與備份逐欄指紋仍完全相同。
- **正式 localhost 驗收**：第一次服務 install 再次遇到既有 `launchctl` 時序問題；確認 plist 完整、舊服務已離開後，以精確標籤 `io.daibu.content-brain` bootstrap＋kickstart 恢復。最終 `state=running`、健康檢查成功、只監聽 `127.0.0.1:8501`；畫面顯示「候選（4）」與「候選整理好了」，1280px 與 375px 皆無水平溢出，browser console 0 errors／0 warnings。正式最終截圖：`.screenshots/startup-sources-production-desktop.png`、`.screenshots/startup-sources-production-mobile.png`。stderr 最後修改時間為 09:16，本次 11:27 重啟與真實流程未寫入新錯誤。

## 前一輪：新創公司資格查核

> 2026-08-10 更新。公司介紹候選現在必須以可追溯的公開證據確認成立不超過十年、未上市、未被收購，且仍為私人獨立公司。

## 本輪目標與驗收

- Cloudflare 等上市／已收購／超過十年的公司不得進入或留在可見候選。
- 每個沒查過的公司最多搜尋一次，整批公司只呼叫一次免費 LLM；已有資格快取的不重查。
- LLM 提供的網址與逐字引文必須實際出現在 Tavily 結果，否則判定 unknown 並排除。
- 舊候選只新增公司資格 metadata，不刪除或修改任何 `ideas` 欄位。

## 本輪狀態

- **根因**：舊流程只確認候選公司與素材網址／引文一致，沒有查成立年份、上市或收購狀態，因此 2009 年成立且 2019 年上市的 Cloudflare 仍可進入候選。
- **架構**：新增獨立 `company_eligibility` 表，保存 `eligible / ineligible / unknown`、成立年、所有權狀態、理由、原始證據 URL／逐字引文與查核時間；不與 `ideas` 做破壞性綁定。
- **資料流**：產生公司候選 → 排除歷史／同批重複 → 讀資格快取 → 每家未知公司 Tavily 一次 → 整批 Gemini 一次 → 程式核對 URL 與 quote → 先快取全部判定 → 只寫入 eligible 候選。
- **防誤判**：十年邊界可通過；十一年以上、已上市或已收購有證據即不合格；網址錯、引文不存在、缺少私人公司證據或證據矛盾一律 unknown，不讓模型自行放行。
- **舊資料回填**：`python -m daibu.company_eligibility backfill --db <path>` 只查尚未有快取的公司；重跑時不再呼叫 Tavily／LLM。
- **副本演練**：先用已知 10 筆 ideas 校準完整資料指紋。副本回填前後 SHA-256 均為 `bd13bc29e909606f08e315f86a87d5a2c64467258a409683dbe3011369fcb4d2`，10 筆與全部欄位不變。
- **真實邊界**：以實際 Tavily＋Gemini 查 Cloudflare、Moove、Railway；Cloudflare=`ineligible/public/2009`，Moove 與 Railway=`eligible/private_independent/2020`，三者各保存兩筆匹配證據。
- **API 成本**：每個新公司一次 Tavily、每批一次 Gemini。單家公司搜尋失敗只讓該公司 unknown，不重試湊滿三則，也不把原始錯誤或 API key 顯示給使用者。
- **TDD**：依垂直切片逐一看見 schema、證據驗證、上市／收購、矛盾、批次呼叫、快取、顯示過濾、回填與 idempotency 測試先失敗再通過；CLI 副本演練另抓到入口位置造成的 `NameError`，修正後同流程成功查核三家公司。
- **測試**：功能分支全套 `508 passed, 14 deselected, 1 warning in 94.16s`；14 個預設略過項目是需外部服務的契約測試，唯一 warning 是既有相依套件提示。
- **合併 main 後全套**：`508 passed, 14 deselected, 1 warning in 75.19s`，exit code 0；`origin/main` 與本機 `main` 均包含本輪提交。
- **視覺驗收**：副本在 1280×800 與 375×812 各跑兩輪；候選為 2、Moove／Railway 可見、Cloudflare 不可見，375px 水平 overflow 為 0。最終證據：`.screenshots/startup-eligibility-round2-desktop.png`、`.screenshots/startup-eligibility-round2-mobile.png`。
- **正式資料回填**：先用 SQLite `.backup` 建立 `backups/daibu-before-startup-eligibility-20260810-1330.db`；備份與正式庫均為 10 筆且 ideas 指紋同為 `bd13bc29e909606f08e315f86a87d5a2c64467258a409683dbe3011369fcb4d2`。回填後仍為同一指紋，只新增 Cloudflare／Moove／Railway 三筆資格紀錄。
- **正式 localhost 驗收**：重啟時再次遇到既有 `bootout`／`bootstrap` 時序問題；確認服務未載入後以精確標籤 `io.daibu.content-brain` 執行 bootstrap＋kickstart，最終 `loaded=yes`、`health=yes`、只監聽 `127.0.0.1:8501`。正式頁顯示「候選（2）」、Moove／Railway 可見、Cloudflare 不可見，1280px 無橫向溢出，browser console 0 errors／warnings。
- **限制**：公開網頁日後可能更新，目前快取沒有自動過期；公司後續上市或被收購時需重新查核。副本的第一次中文子路徑載入曾有既有 Streamlit `_stcore/health`／`host-config` 404，但正式 8501 最終驗收為 0 console errors／warnings。

## 前一輪：公司介紹候選排重與舊資料相容

> 2026-08-10 更新。修復公司介紹系列混入舊通用題目，以及「再產生」重複推薦已出現公司的問題。

## 本輪目標與驗收

- 公司介紹系列中，同一家公司整個系列只介紹一次，所有狀態都算已出現。
- 同一批 AI 結果也不能出現同公司或同題目。
- 舊的空白公司候選與後來的同公司重複項不顯示，但不刪除、不改狀態。
- 「比較」候選的介面語意改成「瀏覽／查看」。
- 找不到足夠的新公司時寧可少產，不重試免費 LLM 湊數。

## 本輪狀態

- **資料校準**：先用畫面已知的「候選（10）」校準 SQLite 查詢；`daibu.db` 同系列確實有 10 筆候選。其中 6 筆建立於公司限制上線前，`company` 為空白；4 筆有公司，但 Railway 有 2 筆。
- **根因一**：產生候選只排除同系列「已淘汰」標題，候選、採用、已發與同公司不同標題都不在排除名單。
- **根因二**：2026-07-31 才加入公司候選驗證；2026-07-25 的六筆舊通用題目仍留在資料庫，介面用「比較｜標題」替代空白公司，造成仍在產比較題的錯覺。
- **排重名冊**：SQLite 現在會提供同系列所有狀態的歷史題目與非空白公司，依 `created_at, id` 排序。
- **三層保護**：歷史公司／題目先交給 Gemini／Groq 避開；程式收到結果後再強制過濾歷史重複；同批較後出現的公司／題目也會被擋下，未通過者不寫入。
- **名稱規則**：公司與題目比對會去除頭尾空白並忽略英文大小寫，不做模糊比對，避免不同公司被誤傷。
- **舊資料相容**：公司介紹系列只顯示有公司名稱且第一次出現的資料；空白公司與後來重複項保留在 SQLite。一般系列維持原行為。
- **真實資料結果**：以 `daibu.db` 的暫存副本開啟選題頁，候選由 10 則變成 3 則，只顯示 Moove、第一次出現的 Railway、Cloudflare；六則通用題目與後來的 Railway 不顯示。
- **介面文案**：「一次比較／比較清單／逐則比較／先比較／比較｜」改成「一次查看／候選清單／逐則查看／先瀏覽／查看｜」。公司候選按鈕維持「公司｜在做什麼」。
- **TDD**：每個資料庫、prompt、歷史公司排重、歷史題目與同批排重、全重複錯誤、舊資料顯示、介面文案切片都先看見單一測試失敗，再做最小修正轉綠。
- **集中測試**：`PYTHON_DOTENV_DISABLED=1 ... pytest -q tests/test_db.py tests/test_llm.py tests/test_selection.py tests/test_app_smoke.py` 為 `192 passed in 26.24s`。停用 dotenv 是為了讓既有「金鑰尚未設定」測試不被本機真實 `.env` 影響。
- **真實 Gemini 契約**：`pytest -q -m contract tests/test_llm_contract.py::test_real_llm_returns_parsable_ideas` 為 `1 passed in 4.29s`；真實回應仍能解析為公司候選欄位。
- **功能分支全套**：`PYTHON_DOTENV_DISABLED=1 pytest -q` 為 `489 passed, 13 deselected, 1 warning in 54.05s`。13 個預設略過項目需要外部服務；唯一 warning 是既有 Starlette／httpx 棄用提示。
- **合併 main 後全套**：同一指令為 `489 passed, 13 deselected, 1 warning in 52.10s`，確認合併結果沒有引入差異。
- **視覺驗收第一輪**：桌機與手機的層次、留白、字體、配色、對齊、響應式、狀態與動效全數合格，沒有新增 CSS 修正。
- **視覺驗收第二輪**：重新載入後結果穩定。375px 與 1280px 的 `scrollWidth` 都等於 viewport；候選標題為 3，三家公司齊全，舊通用題不可見，`比較｜` 為 0，browser console 0 errors／warnings。最終截圖：`.screenshots/dedup-round2-desktop.png`、`.screenshots/dedup-round2-mobile.png`。
- **正式 localhost 驗收**：推送後重啟 `io.daibu.content-brain`。管理命令第一次在 `bootout` 後立刻 `bootstrap` 遇到 macOS 時序失敗；確認 plist 完整且服務未載入後，精確執行同一標籤的 `launchctl bootstrap` 與 `kickstart`，最終 `loaded=yes`、`health=yes`、只監聽 `127.0.0.1:8501`。
- **使用者畫面驗收**：實際開啟 `http://127.0.0.1:8501/選題`，頁面標題正確，顯示「候選（3）」與 Moove／Railway／Cloudflare；Railway 按鈕只有 1 個，`比較｜` 為 0，舊通用題不可見，1280px 無橫向溢出，browser console 0 errors／warnings。
- **資料保留複驗**：正式畫面驗收後直接查 SQLite，仍是 10 筆候選、6 筆空白公司，Cloudflare 1／Moove 1／Railway 2。數字來自 `ideas` 表按 `status` 與 `LOWER(TRIM(company))` 分組，證明本輪只改顯示與未來寫入規則，沒有刪除舊資料。
- **成本與限制**：沒有新依賴或付費服務，也不自動重試湊滿三則。精準比對無法自動合併 `Cloudflare` 與 `Cloudflare, Inc.` 這類別名；後續若要做別名需另有人工確認設計。

## 前一輪：macOS 登入後自動保持開啟

> 2026-08-10 更新。修復 `localhost:8501` 因手動 Streamlit 程序結束而拒絕連線，改由 macOS LaunchAgent 自動啟動與恢復。

## 本輪目標與驗收

- 使用者登入這台 Mac 後，工具自動在 `http://localhost:8501` 啟動，不需開 Terminal。
- Streamlit 程序意外停止後，由 macOS `launchd` 自動重開。
- 服務只綁 `127.0.0.1:8501`，不開放區域網路或公開網路。
- plist、啟動命令與紀錄不得含 API key；既有資料庫與使用者文件不得被修改。

## 本輪狀態

- **根因**：失敗時 `lsof` 確認 8501 沒有監聽程序；瀏覽器網址存在，但提供頁面的 Streamlit 已經結束。
- **服務**：已安裝使用者層級 LaunchAgent `io.daibu.content-brain`，設定在 `/Users/cengweiting/Library/LaunchAgents/io.daibu.content-brain.plist`。使用 `RunAtLoad=true`、`KeepAlive=true`、`ThrottleInterval=10`。
- **啟動鏈**：macOS `launchd` → 專案 `.venv/bin/streamlit` → `server.py` → `127.0.0.1:8501`。工作目錄固定為 `/Users/cengweiting/Developer/daibu-content-brain`。
- **管理命令**：新增 `.venv/bin/python -m daibu.local_service install|status|uninstall`。`uninstall` 只移除背景服務與 plist，保留 `.env`、資料庫、Logo 與紀錄。
- **秘密檔**：原本 `.env` 不存在；安裝時由 `.env.example` 建立空白 `.env`，權限實測為 `600`。沒有代填或顯示秘密，因此首頁目前會提醒尚未設定 Gemini key。
- **安全校準**：先用已知含 key 名稱的 `.env.example` 確認掃描方法有效，再掃 plist、stdout 與 stderr；三處都沒有 Gemini、Groq 或 Tavily API key 名稱。
- **第一次啟動**：安裝前健康檢查明確連線失敗；安裝後第 1 次輪詢即回應 `ok`。`launchctl` 顯示 `state=running`，`lsof` 顯示只監聽 `127.0.0.1:8501`。
- **自動恢復**：精確驗證 8501 舊 PID `14386` 的命令屬於本專案後送出 `TERM`；第 2 次輪詢出現新 PID `14439` 並恢復 `health=ok`，沒有用廣泛程序名稱終止其他程序。
- **瀏覽器驗收**：實際開啟首頁，標題為「呆一布 內容工作站」，既有「AI 新創介紹」系列與 9 則候選正常顯示；browser console 的 error／warning 均為 0。
- **TDD**：新增 10 個本機服務測試，逐一看見預期失敗後完成最小實作。涵蓋 plist、安全綁定位址、安裝前檢查、`.env` 建立與保護、launchctl 邊界、健康狀態、外來程序占用、無資料損失移除與白話錯誤訊息。
- **功能分支全套**：`481 passed, 13 deselected, 1 warning in 75.96s`。
- **合併 main 後全套**：`481 passed, 13 deselected, 1 warning in 85.44s`。13 個預設略過項目需外部服務；唯一 warning 是既有 Starlette／httpx 棄用提示。
- **紀錄**：`/Users/cengweiting/Library/Logs/DaibuContentBrain/stdout.log` 與 `stderr.log`。
- **成本與限制**：使用 macOS 內建服務，沒有訂閱費。Mac 關機、登出或睡眠時 localhost 仍不可用；若要 24 小時與他人共用，需另做雲端部署。

## 下一個使用者操作

在本機把 Gemini 與 Tavily key 填入 `.env`，再重啟背景服務。API key 不可貼進聊天；一次只引導一個本機操作。

## 前一輪：建造故事 HTML 改版

> 2026-08-06 更新。使用者回饋舊版「內容不對、看起來不好看」，經 grill-me 逐題對齊後重寫。未修改產品程式碼。

### 目標與驗收

依 `docs/superpowers/specs/2026-08-06-建造故事改版-design.md` 重寫建造故事 HTML：從八章的方法論教材，改成用一個真實功能貫穿全篇的四章教學；視覺從「只用品牌最淡幾階」改成編輯式雜誌骨架，把深色階拉回來當結構色。

### 交付狀態

- **十個拍板決策**：見設計文件第 3 節。關鍵三項是「不引用任何對話原文」、「主線用七張輪播圖產生器」、「工具定位寫成通用架構＋目前一個系列」。
- **章節**：八章砍到四章——做出來／系統／不寫歪／照著做。起點、分工、時間軸被主線吸收。
- **現場感素材**：嵌入七張 Railway 輪播成品（實測全部 1080×1350）與一組 `ia-refactor` 修前／修後對照。
- **素材驗證**：`carousel-redesign` 的 round1/round2 差異細到縮圖看不出來，不採用；`.screenshots/task10`–`task23` 共 13 個資料夾的 round1/round2 其實是明暗模式或裝置變體，不是修前／修後。判斷方法是比對兩個資料夾的檔名交集。
- **組裝方式**：改成 `docs/build-story/template.html` ＋ `build.py`。圖片以 base64 內嵌，分享後不會失效。產出檔開頭有註記，要改請動 template 後重跑 `python3 docs/build-story/build.py`。來源截圖在 `.screenshots/` 與 `.playwright-cli/`，兩者都被 gitignore，所以壓好的素材必須留在 `docs/build-story/assets/`。
- **測試**：新增 8 個、更新 2 個既有斷言（它們斷言的是被 spec 明確替換掉的舊八章結構）。建造故事測試 `13 passed`。
- **功能分支全測**：`466 passed, 13 deselected, 1 warning in 108.55s`。
- **合併 main 後全測**：`466 passed, 13 deselected, 1 warning in 102.70s`。13 個略過項是需要外部服務的契約測試；唯一 warning 是既有的 Starlette／httpx 棄用提示。
- **視覺驗收第一輪**：五項不合格——桌機右側大片死空間、窄文字欄與滿版元素對不齊、章節節奏不足、手機七張成品排 3 欄每張只剩 90px、主標把「呆一布」拆成兩行。
- **視覺驗收第二輪**：內容置中、圖片突出文字欄、章節間距 118px、手機成品改 2 欄、品牌名加 `.keep` 不換行。修完後八項檢查全過。過程中測試抓到 1280px 有 8px 橫向溢出，根因是 `.compare` 自己的 `margin` 簡寫寫在媒體查詢之後把負邊界蓋掉（媒體查詢不提高優先權）；已把突出規則移到基本規則之後。
- **產品程式與資料**：未修改 Streamlit、資料表、AI 指令或真實資料庫；本輪沒有呼叫 Tavily／Gemini。
- **抽 partial 的錯誤與修正**：從舊 HTML 抽評論工具時整個 `<script>` 都拿了，但裡面有兩個 IIFE，第一個是舊版的 journey／進度條／目次腳本。產出檔因此同時載入新舊兩套 journey 邏輯，載入與每次點擊都丟 TypeError（舊腳本找 `#reading-progress` 得到 null；舊鍵名 `sources`／`idea`／`cards` 與新版 `source`／`ideas`／`pages` 對不上）。既有測試沒抓到，因為新的 handler 先註冊先跑完。已只保留評論工具那一個 IIFE，並補上 `test_page_loads_and_interacts_without_console_errors`——先在未重建的產出檔上看到紅燈，重建後轉綠。
- **色彩 token 重整**：`--deep` 原本同時當標題文字色與實心區塊底色，深色主題下會變成淺字配淺底。已抽出 `--fill-strong`／`--on-fill-strong`／`--warn-*`／`--ok-*`。淺色模式的計算值不變，測試維持通過。
- **最終全套**：`467 passed, 13 deselected, 1 warning in 105.03s`。
- **已推送**：`origin/main` 已包含 `7e8f61f`。
- **舊正式站未更新**：`https://daibu-vibe-coding-story.workspace-249035.chatgpt.site` 仍服務舊的八章版本（已實際抓取確認，目次仍是八節）。該網域屬於 Codex 雲端工作區，這個 repo 沒有任何部署設定驅動它，本機無法重新部署。
- **新發佈位置**：`https://claude.ai/code/artifact/f9b4ff4f-1aee-4829-bde2-4ff04d9440d1`（Artifact，預設私人，要分享得從頁面的分享選單開啟）。由 `docs/build-story/build_artifact.py` 產生：拿掉 Tailwind CDN 與 Google Fonts（Artifact 沙箱擋外部連線），字型改成 Songti TC／PingFang TC 系統堆疊，並補上深色主題。實測 console 錯誤 0、外部請求 0、圖片全部載入、淺色與深色都無橫向捲動。

## 後續（同日）

- **文案人性化**（`afac739`）：依 humanizer-zh 清單過一遍正文。破折號 9 處減到 0、粗體 11 處減到 2、兩句對仗式格言的拉引句換成具體的話、拆掉 Red／Green／Refactor 的三段式排比。
- **修好內容系列的死路**（`aaf963e`）：選題頁可以刪系列，而 `seeds.load` 被 `seeds_loaded` 旗標擋住只跑一次。實測確認刪光後重開 App 系列不會回來，空狀態卻叫使用者去設定頁新增，而設定頁沒有這個功能。現在零個系列時才顯示「新增內容系列」表單當救援出口；有系列時維持隱藏，不牴觸 2026-08-01 單一系列收斂的決定。三處空狀態文案一併修正。

## 第二次改版（2026-08-07）

使用者回饋兩件事：「我作為一個完全不了解這個系統的人完全看不懂」、「我也不算是 vibe coding，比較偏 prompt engineer」。逐句讀過之後確認問題是**每一段都是結論，沒有前因後果**——例如「原本規劃的七個頁型裡有『文組生用途』和『多少錢』，在動工前被改掉」，讀者不知道七個頁型是什麼、為什麼那兩個不對。

- **範圍改成整個工具**，不再只講輪播圖那一個功能。
- **結構重排**：先看成品（七張圖移到最前面）→ 用起來是什麼樣子 → 開發方式 → 怎麼一步步做出來的 → 怎麼確認沒寫歪。
- **第三章改寫成七組「問題 → 解法」**，每組都交代當時的情況、發現什麼、怎麼解、結果。全部出自 `docs/specs/` 與 `docs/superpowers/specs/` 的背景段落。
- **新增第二章「開發方式：誰決定什麼」**：人說清楚要解決什麼 → Claude 追問並寫規格與計畫 → Codex 照計畫先寫測試再實作 → 人親手操作驗收。每輪留下規格、計畫、交接單三份檔案。
- **定位改掉**：不再用「Vibe Coding」。標題改成「我沒寫程式，怎麼做出呆一布內容工作站」，檔名一併改為 `docs/2026-08-07-呆一布內容工作站是怎麼做出來的.html`。
- **使用者刪掉兩條**：「圖片生成服務付費」與「系列太多要收斂」，理由是那不算問題。
- **補了三個名詞的白話定義**（內容系列、候選、採用），因為後面一直用到。
- 全套 `471 passed`。整頁 8598px。

## 舊建造故事交付的下一步

1. 舊網址的連結若已發給組員，等 Codex 額度恢復後重新部署原網址，兩個版本才不會並存。**刪除舊站需要在 Codex／ChatGPT 的介面上操作**，本機沒有任何憑證或設定可以碰到 `workspace-249035.chatgpt.site`。

## 前一輪：自動文案與官方 Logo 修復

> 2026-08-05 更新。這一輪修復「AI 文案產生後變空白」與「找不到新創公司官方 Logo」兩條真實使用流程。

### 目標與驗收

- 在現有 Streamlit 工作台中，AI 文案產生後要立刻顯示，且頁面重跑後不能被舊的空白編輯器內容蓋掉。
- 官方網站若把 Logo 寫成頁面內嵌 SVG，系統仍要能安全擷取、預覽，並維持「使用者確認後才保存」的產品規則。
- 搜尋備援不得把名稱只是部分相似的其他公司誤認為官方網域。
- 依 TDD 補回歸測試，完成真實 API／官網邊界驗證、兩輪桌機／手機視覺驗收與全套測試。

### 狀態

- **文案根因與修復**：Streamlit 的文字框會保留舊的瀏覽器 session 值；Gemini 已把新文案寫入 SQLite 後，舊空白值仍可能在下一次頁面重跑時覆蓋它。新增 `sync_body_editor`，資料庫正文比目前 session 更新時先同步編輯器；使用者正在打字時則保留使用者內容。
- **Logo 根因與修復**：Moove 官網的導覽 Logo 是頁面內嵌 `<svg>`，舊版只會找 `<img src>`。現在能解析安全的內嵌 SVG，移除非允許標籤／屬性並沿用既有 SVG 安全驗證，再以瀏覽器可顯示的 data URL 預覽。
- **搜尋備援**：第一次品牌搜尋沒有結果時才追加一次「公司名＋official website」查詢；網域判定改為完整 label 相符，因此 `moovecars.com` 不會再因包含 `moove` 字串而通過。
- **真實流程證據**：在實際 8501 工作台重新產生 Moove 文案，取得 492 字，來源重載後文字仍保留；Logo 候選來自 `https://www.moove.io`，頁面無應用程式錯誤或新增 console 錯誤。候選尚未保存，等待使用者肉眼確認。
- **安全與成本**：錯誤的 `moovecars.com` 候選沒有寫入資料庫；所有 Logo 仍須使用者確認才保存。只有第一次搜尋為空時才多用一次 Tavily 免費額度。
- **TDD／契約測試**：新增內嵌 SVG 擷取、空搜尋備援、相似網域拒絕、Moove 官網真實契約、正文 session 同步與 SVG data URL 預覽測試；均先看見失敗再以最小修正通過。
- **相關測試**：Logo 單元測試 `8 passed, 1 deselected`；Moove 真實官網契約 `1 passed`；相關頁面測試 `4 passed`；Python 編譯檢查通過。
- **全套測試**：最終乾淨環境 `458 passed, 13 deselected, 1 warning in 62.57s`。13 個預設略過項目是需外部服務的契約測試；唯一 warning 是既有 Starlette／httpx 棄用提示。
- **視覺驗收**：1280×800 與 375×812 各做兩輪；最終 Logo 候選卡、來源、確認／拒絕操作在桌機與手機都沒有破版，375px 的水平 overflow 為 0。最終證據：`.screenshots/logo-fix-round2-desktop.png`、`.screenshots/logo-fix-round2-mobile.png`；第一輪：`.screenshots/logo-fix-round1-desktop.png`、`.screenshots/logo-fix-round1-mobile.png`。
- **服務狀態**：本機工具維持在 `http://localhost:8501`。此專案目前沒有 production 部署流程，因此本輪不另建正式站。
- **剩餘限制**：設定頁輸入的 Tavily／Gemini key 只存在目前 Streamlit 程序；重啟工具後仍需重填。永久保存涉及秘密管理方式，未在本次功能修復中擅自改動。

### 下一步

1. 使用者在 Moove 候選卡上確認圖樣確實是官方 Logo 後，點「確認是官方 Logo」；確認前系統不會保存或拿去出圖。
2. 若要解決「重啟後 API key 消失」，另開一輪選擇安全的本機秘密保存方式，不把 key 寫進 Git。

## 前一輪：社團建造故事 HTML

> 同為 2026-08-05 交付。製作給幾乎不寫程式、主要使用 Vibe Coding 的社團組員閱讀的建造故事 HTML；未修改產品程式碼。

### 目標與驗收

依 `docs/superpowers/specs/2026-08-05-社團建造故事-html-design.md` 製作一份可獨立閱讀的繁體中文單頁 HTML，說明工具為什麼做、如何拆解、AI 與人的分工、系統資料流、TDD、真實迭代與可複製的 Vibe Coding 建造方式。

成品需沿用呆一布品牌，在 1280×800 與 375×812 各完成至少兩輪截圖自檢；不碰真實資料庫、不呼叫外部 API、不修改產品功能。

### 交付狀態

- **設計**：使用者已確認建造故事式互動網頁方向；正式規格位於 `docs/superpowers/specs/2026-08-05-社團建造故事-html-design.md`。
- **執行方式**：使用者選擇 inline；依 `docs/superpowers/plans/2026-08-05-社團建造故事-html.md` 以五個垂直 TDD 切片完成。
- **HTML 成品**：`docs/2026-08-07-呆一布內容工作站是怎麼做出來的.html`。包含八個主章節、一分鐘摘要、十個術語的漸進解釋、七步內容旅程、七階段時間軸、五張踩坑卡與八步建造公式。
- **閱讀互動**：桌機／手機章節導覽、閱讀進度、可鍵盤操作的七步內容旅程、原生技術補充、減少動態、列印版與全頁段落評論均完成。
- **內容現況**：守門線、來源分層、常青／時效分類只出現在「後來移除」的歷史脈絡；沒有寫成現有功能。
- **安全邊界**：HTML 不讀資料庫、不呼叫產品 API、不含 API key、本機絕對路徑或外連資產路徑；吉祥物與 favicon 都已內嵌。
- **HTML 測試**：`5 passed in 4.65s`。另以本機 HTTP 真實操作確認 AI 正文步驟切換成功、375px overflow 為 0、瀏覽器 console 為 0 errors；Tailwind CDN 有一則既有的 production 使用提醒。
- **功能分支全測**：`454 passed, 12 deselected, 1 warning in 69.48s`；唯一 warning 是既有 Starlette／httpx 棄用提示。
- **合併 main 後全測**：`454 passed, 12 deselected, 1 warning in 65.68s`；同一個既有棄用提示，無新增失敗。
- **視覺驗收第一輪**：主標字級被 Tailwind 基礎樣式覆蓋、桌機首屏留白過長、手機主標層級不足；已提高 selector specificity、重調字級與首屏高度並補 favicon。
- **視覺驗收第二輪**：層次、留白、字體、配色、對齊、響應式、狀態與動效全數通過。最終證據：`.screenshots/build-story-round2-desktop.png`、`.screenshots/build-story-round2-mobile.png`；第一輪證據：`.screenshots/build-story-round1-desktop.png`、`.screenshots/build-story-round1-mobile.png`。
- **產品程式與資料**：未修改 Streamlit、資料表、AI 指令或真實資料庫；本輪沒有呼叫 Tavily／Gemini。
- **公開分享網址**：`https://daibu-vibe-coding-story.workspace-249035.chatgpt.site`，只發佈這一份建造故事，不公開 private GitHub repo 的其他文件。
- **正式站驗證**：公開網址會進入 `/story`；在 375×812 實測主標正確、AI 正文步驟切換為選取狀態、內容同步更新、overflow 為 0、console 為 0 errors。唯一 warning 是 Tailwind CDN 的 production 提醒。

## 前一輪 Demo 影片交付紀錄

- **成片**：`artifacts/demo-video/edit/final.mp4`，115.4 秒、1280×720、30fps、H.264、yuv420p、無音訊、4.7 MB。SHA-256：`8c687b587baf5fea87ff79f7b7ddf9dab9fecbc736e9d7ba45415dbda15dc16c`。
- **正文畫面修正**：使用者發現第一個案例雖顯示 478 字，影片中的 textarea 卻是空白。資料庫正文完整，根因是錄製片段沒有拍到瀏覽器已繪製的文字。已只替換 36.2–45.2 秒，現在先顯示 Warp 正文開頭，再輕微捲動；沒有重跑 Tavily／Gemini。
- **真實流程**：搜尋新增 Warp idea 16；AI 初稿 478 字、查證來源 3 筆。系統找到 Warp 官網 Logo 候選，但未確認、未儲存、未拿去出圖。
- **透明備援**：影片以轉場明說 Warp Logo 等待確認，後段接已驗證的 BillionToOne idea 15，完成七頁草稿、七張圖、預覽與 ZIP 下載。
- **報告提綱**：`docs/2026-08-01-社團報告提綱.md`，可講 3–5 分鐘；另含只剩 3 分鐘與現場 API 失敗時的說法。
- **驗收證據**：`artifacts/demo-video/edit/verify/boundaries.png`、`samples.png`。正文可視回歸檢查由修正前 0.0000 升至 0.1481 並通過；3,462 幀可完整解碼、無黑格，總長與後半段時間軸未變。
- **技術驗證**：完整解碼成功；ZIP 內 7 張 PNG 均通過完整性檢查；文字產物沒有 Tavily／Gemini key；影片與字幕皆未經過設定頁。
- **資料安全**：8502 實際使用 `/private/tmp/daibu-workstation-redesign.db`。真實 `daibu.db` 錄製前後 mtime 都是 `1785650884`，未變。
- **測試**：正文修正後 `449 passed, 12 deselected, 1 warning in 43.78s`。產品程式碼未變；唯一 warning 是既有 Starlette/httpx 棄用提示。
- **已知非阻擋訊息**：Playwright console 有兩個 multipage-relative `_stcore/health`／`host-config` 404；錄影流程與畫面未受影響。

## 舊交付的分享方式

1. 把公開網址傳給社團組員，會後可直接用手機或桌機閱讀。
2. 若收到段落評論，整理後再決定是否改版；本輪成品與正式站已完成。

## 最容易踩的坑

- 現有規格與初版文件同時存在；描述現況時要以 `STATUS.md`、最新規格與實際程式為準，不能把已移除的守門線、來源分層或常青／時效分類寫成現有功能。
- 成品給非工程背景組員自讀。專有名詞第一次出現必須先講使用畫面與生活比喻，再放精準定義；主文不可變成檔案路徑導覽。
- 分享後不能依賴作者電腦的絕對路徑。吉祥物與必要 SVG 要內嵌，外部相依失效時仍須保留完整文字內容。
- 前端完成前要跑兩輪 1280×800 與 375×812 截圖自檢；只看 HTML 原始碼或指令 exit 0 不算視覺驗收。
