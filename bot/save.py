#!/usr/bin/env python3
"""
save.py — 將一組問答（Q&A）存成 HTML 並發布到 GitHub Pages 日誌。

- 產生的 HTML 樣式與 bot.py 一致
- 檔案寫入 docs/journal/，並更新 docs/articles.json（filename 不含 docs/ 前綴）
- 預設會 git add / commit / push（用 --no-push 可略過）

用法：
  python3 bot/save.py --question "問題" --answer "答案(Markdown)" --category "投資研究"
  python3 bot/save.py                # 互動模式：依提示貼上內容，輸入單獨一行 END 結束答案
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime

import markdown

# --- 路徑設定 ---------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_DIR = "docs"                      # GitHub Pages 從 main 分支的 /docs 發布
JOURNAL_SUBDIR = "journal"             # filename 內用的相對路徑（不含 docs/）
ARTICLES_JSON = os.path.join(ROOT, SITE_DIR, "articles.json")
JOURNAL_DIR = os.path.join(ROOT, SITE_DIR, JOURNAL_SUBDIR)

VALID_CATEGORIES = ["投資研究", "總經研究", "書籍筆記", "交易策略", "日誌"]

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title>
<style>
:root {{
  --bg:#f4f5f7;--surface:#fff;--text:#1a1a2e;--muted:#6b7280;
  --border:#e5e7eb;--accent:#2563eb;--accent-soft:#dbeafe;
  --code-bg:#1e293b;--code-fg:#e2e8f0;
  --shadow:0 1px 3px rgba(0,0,0,.06);
}}
@media(prefers-color-scheme:dark){{:root{{
  --bg:#0f172a;--surface:#1e293b;--text:#f1f5f9;--muted:#94a3b8;
  --border:#334155;--accent:#60a5fa;--accent-soft:#1e3a5f;
  --code-bg:#0f172a;--code-fg:#e2e8f0;
  --shadow:0 1px 3px rgba(0,0,0,.3);
}}}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans TC",sans-serif;
  background:var(--bg);color:var(--text);line-height:1.7}}
article{{max-width:720px;margin:0 auto;padding:1.5rem 1rem 3rem}}
h1{{font-size:1.5rem;font-weight:700;margin-bottom:.25rem;line-height:1.3}}
.meta{{color:var(--muted);font-size:.8125rem;margin-bottom:1.5rem;
  padding-bottom:1rem;border-bottom:1px solid var(--border)}}
.question{{background:var(--accent-soft);border-left:4px solid var(--accent);
  padding:.75rem 1rem;border-radius:0 8px 8px 0;margin-bottom:1.5rem;font-weight:500}}
.answer h2,.answer h3{{margin-top:1.5rem;margin-bottom:.5rem}}
.answer h2{{font-size:1.25rem}} .answer h3{{font-size:1.0625rem}}
.answer p{{margin-bottom:.75rem}}
.answer ul,.answer ol{{margin:0 0 .75rem 1.25rem}}
.answer li{{margin-bottom:.25rem}}
.answer table{{width:100%;border-collapse:collapse;margin:1rem 0;font-size:.875rem}}
.answer th,.answer td{{border:1px solid var(--border);padding:.5rem .75rem;text-align:left}}
.answer th{{background:var(--accent-soft);font-weight:600}}
.answer code{{background:var(--code-bg);color:var(--code-fg);padding:.15em .35em;
  border-radius:4px;font-size:.875em}}
.answer pre{{background:var(--code-bg);color:var(--code-fg);padding:1rem;
  border-radius:8px;overflow-x:auto;margin:1rem 0}}
.answer pre code{{background:none;padding:0}}
.answer blockquote{{border-left:3px solid var(--accent);padding:.5rem 1rem;
  margin:1rem 0;color:var(--muted)}}
.back{{display:inline-block;margin-bottom:1rem;color:var(--accent);
  text-decoration:none;font-size:.875rem}}
.back:hover{{text-decoration:underline}}
@media(min-width:640px){{article{{padding:2rem 1.5rem 4rem}}h1{{font-size:1.75rem}}}}
</style>
</head>
<body>
<article>
  <a class="back" href="../index.html">&larr; 回到日誌首頁</a>
  <h1>{title}</h1>
  <div class="meta">{date}</div>
  <div class="question">{question}</div>
  <div class="answer">{answer_html}</div>
</article>
</body>
</html>"""


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _sanitize(text: str, maxlen: int = 40) -> str:
    """把問題轉成適合當檔名的字串。"""
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
    return text[:maxlen] or "untitled"


def build_html(title: str, date: str, question: str, answer_md: str) -> str:
    answer_html = markdown.markdown(
        answer_md, extensions=["tables", "fenced_code", "nl2br"]
    )
    return HTML_TEMPLATE.format(
        title=_esc(title),
        date=_esc(date),
        question=_esc(question),
        answer_html=answer_html,
    )


def update_manifest(title: str, filename: str, date: str, category: str):
    if os.path.exists(ARTICLES_JSON):
        with open(ARTICLES_JSON, encoding="utf-8") as f:
            articles = json.load(f)
    else:
        articles = []

    articles.insert(0, {
        "title": title,
        "filename": filename,      # 相對於 docs/，不含 docs/ 前綴
        "date": date,
        "category": category,
    })

    with open(ARTICLES_JSON, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _pages_base() -> str:
    """由 git remote 推導 GitHub Pages 網址（不需 token）。"""
    try:
        url = subprocess.check_output(
            ["git", "-C", ROOT, "remote", "get-url", "origin"],
            text=True,
        ).strip()
        m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", url)
        if m:
            owner, repo = m.group(1), m.group(2)
            return f"https://{owner.lower()}.github.io/{repo}"
    except Exception:
        pass
    return ""


def git_push(paths, message):
    subprocess.run(["git", "-C", ROOT, "add", *paths], check=True)
    subprocess.run(["git", "-C", ROOT, "commit", "-m", message], check=True)
    subprocess.run(["git", "-C", ROOT, "push", "origin", "main"], check=True)


def _read_multiline(prompt: str) -> str:
    print(prompt + "（貼上內容，最後單獨一行輸入 END 結束）:")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def main():
    ap = argparse.ArgumentParser(description="將問答存成 HTML 並發布到 docs/ 日誌")
    ap.add_argument("--question", "-q", help="問題")
    ap.add_argument("--answer", "-a", help="答案（Markdown）")
    ap.add_argument("--category", "-c", default="日誌",
                    help=f"分類：{' / '.join(VALID_CATEGORIES)}（預設：日誌）")
    ap.add_argument("--title", "-t", help="標題（預設取問題）")
    ap.add_argument("--no-push", action="store_true", help="只在本地產生，不 commit/push")
    args = ap.parse_args()

    question = args.question
    answer = args.answer
    category = args.category

    if not question or not answer:
        print("== 互動模式 ==")
        if not question:
            question = input("問題: ").strip()
        if not answer:
            answer = _read_multiline("答案")
        cat_in = input(f"分類 [{'/'.join(VALID_CATEGORIES)}]（預設 日誌）: ").strip()
        if cat_in:
            category = cat_in

    if not question or not answer:
        print("❌ 問題與答案皆不可為空", file=sys.stderr)
        sys.exit(1)

    if category not in VALID_CATEGORIES:
        print(f"⚠️  分類「{category}」不在建議清單，仍照用：{VALID_CATEGORIES}")

    title = args.title or (question if len(question) <= 60 else question[:57] + "…")

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M")
    safe = _sanitize(question)
    rel_filename = f"{JOURNAL_SUBDIR}/{date_str}-{time_str}-{safe}.html"   # docs/ 相對
    out_path = os.path.join(ROOT, SITE_DIR, rel_filename)

    os.makedirs(JOURNAL_DIR, exist_ok=True)
    html = build_html(title, now.strftime("%Y-%m-%d %H:%M"), question, answer)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    update_manifest(title, rel_filename, date_str, category)

    print(f"✅ 已產生：{os.path.relpath(out_path, ROOT)}")
    print(f"✅ 已更新：{os.path.relpath(ARTICLES_JSON, ROOT)}（分類：{category}）")

    base = _pages_base()
    if base:
        print(f"🔗 頁面連結（部署後）：{base}/{rel_filename}")

    if args.no_push:
        print("ℹ️  已略過 git push（--no-push）。稍後可執行 ./scripts/push.sh 發布。")
        return

    try:
        git_push([out_path, ARTICLES_JSON], f"Add journal: {title}")
        print("🚀 已推上 GitHub，GitHub Pages 約 1–2 分鐘後更新。")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  git 發布失敗（{e}）。可手動執行 ./scripts/push.sh。", file=sys.stderr)


if __name__ == "__main__":
    main()
