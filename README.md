# AI_Agent — 個人投資研究與知識庫

這個 repo 是個人用的「投資研究 + 閱讀知識庫 + 逐字稿庫」，並搭配一個發布到 GitHub Pages 的網頁前台。以下說明各資料夾用途，方便日後維護與讓 AI 正確歸檔。

## 目錄總覽

| 路徑 | 用途 | 是否需要索引/README |
|------|------|------|
| `knowledge/` | **閱讀知識庫**：書籍與摘要型筆記，依主題分 15 類子資料夾（約 112 篇 md） | ✅ 有 `README.md` + `books_index.md` |
| `transcript/` | **逐字稿庫**：法說／訪談／會議／股東信，依「產業/公司/類型/年份」歸檔（約 473 篇 md），是回答問題時的**引用來源** | ✅ 有 `README.md` |
| `books/` | 單一書籍的**拆章全文**（目前為 Perez《技術革命與金融資本》） | 有 `index.md` |
| `docs/` | **網頁發布系統（GitHub Pages 唯一來源）**：`index.html` + `manage.html` + `articles.json` + 所有研究／書籍筆記 HTML（23 篇），日誌型問答放 `docs/journal/` | 由 `articles.json` 索引 |
| `_sources/` | **原始素材**（PDF / TXT / EPUB 等）：年報、書籍原文、逐字稿原檔，整理成 md 後留底用 | 不需要 |
| `bot/` | Telegram bot（`bot.py`）：收訊息→呼叫 OpenAI→產生 HTML→發布到 GitHub Pages | 不需要 |
| `viewer/` | 本機 md/txt 瀏覽器（Vite + Express `server.js`），根目錄為上層專案 | 不需要 |
| `scripts/` | 發布輔助腳本：`push.sh`（commit+push）、`delete.sh`（刪文章） | 不需要 |
| `prompts/` | 可重複使用的提示詞草稿 | 不需要 |
| `japanese-n3/` | **獨立主題**：日文 N3 學習（與投資無關，僅共用此 repo） | 不需要 |

## 發布系統（GitHub Pages）

- **單一來源：`docs/`**。原本「根目錄」與「`investment-research/`」兩套已整併進 `docs/`（重複檔保留較新、含深色主題的版本），`articles.json` 也合成單一份（23 篇）。
- Repo：`LukCabbage/journal`；GitHub Pages 需設定為 **`main` 分支的 `/docs` 資料夾**。
- `docs/articles.json` 內 `filename` **不含 `docs/` 前綴**（因為 `/docs` 即網站根）。`bot.py` 與 `scripts/*.sh` 皆已改為讀寫 `docs/`。

## 歸檔規則（給 AI 用）

- **逐字稿** → `transcript/產業/公司/類型/年份/`（見 `transcript/README.md` 與 `.cursor/rules/youtube-transcript-workflow.mdc`）
- **書籍筆記** → `knowledge/<分類>/`，並更新 `knowledge/books_index.md`
- **投資研究／日誌 HTML** → `docs/`（日誌放 `docs/journal/`），並更新 `docs/articles.json`（見 `.cursor/rules/investment-research-html.mdc`）
- **原始素材** → `_sources/`

## 常用指令

```bash
# 發布（commit + push 到 GitHub Pages）
./scripts/push.sh

# 刪除日誌文章（依 id）
./scripts/delete.sh <id1> [id2] ...

# 啟動本機瀏覽器（viewer）
cd viewer && ./start.sh
```
