#!/usr/bin/env python3
"""
Telegram Bot — 個人投資研究日誌

- 接收 Telegram 訊息，呼叫 OpenAI 回答
- 自動產生 HTML 並發布到 GitHub Pages
"""

import os
import re
import json
import base64
import logging
from datetime import datetime

import requests as http_requests
import markdown
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

load_dotenv()

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_OWNER = os.environ["GITHUB_OWNER"]
GITHUB_REPO = os.environ["GITHUB_REPO"]
PAGES_BASE = f"https://{GITHUB_OWNER}.github.io/{GITHUB_REPO}"

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)

ai = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "你是一個投資研究與知識整理助理。請用繁體中文回答。"
    "回答時請結構清晰，善用標題、段落和列表，提供具體數據和邏輯推演。"
    "在需要時標註資料來源的不確定性。"
)

# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------

def ask(question: str, model: str = "gpt-4o-mini") -> str:
    resp = ai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        max_tokens=4096,
    )
    return resp.choices[0].message.content


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

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
  <a class="back" href="index.html">&larr; 回到日誌首頁</a>
  <h1>{title}</h1>
  <div class="meta">{date}</div>
  <div class="question">{question}</div>
  <div class="answer">{answer_html}</div>
</article>
</body>
</html>"""


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


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# GitHub publishing
# ---------------------------------------------------------------------------

def _gh_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def _gh_url(path: str) -> str:
    return f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"


def push_file(path: str, content: str, commit_msg: str):
    r = http_requests.get(_gh_url(path), headers=_gh_headers(), timeout=15)
    sha = r.json().get("sha") if r.status_code == 200 else None

    payload = {
        "message": commit_msg,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
    }
    if sha:
        payload["sha"] = sha

    r = http_requests.put(_gh_url(path), headers=_gh_headers(), json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def update_manifest(title: str, filename: str, date: str, category: str = "日誌"):
    r = http_requests.get(_gh_url("articles.json"), headers=_gh_headers(), timeout=15)
    if r.status_code == 200:
        data = r.json()
        articles = json.loads(base64.b64decode(data["content"]).decode("utf-8"))
        sha = data["sha"]
    else:
        articles = []
        sha = None

    articles.insert(0, {
        "title": title,
        "filename": filename,
        "date": date,
        "category": category,
    })

    payload = {
        "message": f"Update manifest: {title}",
        "content": base64.b64encode(
            json.dumps(articles, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("ascii"),
    }
    if sha:
        payload["sha"] = sha

    r = http_requests.put(
        _gh_url("articles.json"), headers=_gh_headers(), json=payload, timeout=30
    )
    r.raise_for_status()


def publish(title: str, question: str, answer: str) -> str:
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M")
    safe = _sanitize(question)
    filename = f"journal/{date_str}-{time_str}-{safe}.html"

    html = build_html(title, now.strftime("%Y-%m-%d %H:%M"), question, answer)
    push_file(filename, html, f"Add: {title}")
    update_manifest(title, filename, date_str)

    return f"{PAGES_BASE}/{filename}"


def _sanitize(text: str) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff-]", "", text)
    return text[:40] or "untitled"


# ---------------------------------------------------------------------------
# Telegram handlers
# ---------------------------------------------------------------------------

HELP_TEXT = (
    "我是你的投資研究助理。\n\n"
    "直接傳訊息問我問題，我會：\n"
    "1. 回答你的問題\n"
    "2. 自動儲存為精美 HTML 日誌\n"
    "3. 附上日誌連結讓你隨時回顧\n\n"
    "指令：\n"
    "/deep — 使用 GPT-4o 深度回答（較慢、較貴、更強）\n"
    "/help — 顯示這則說明"
)


async def cmd_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


async def cmd_deep(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = " ".join(ctx.args) if ctx.args else ""
    if not text:
        await update.message.reply_text("用法：/deep 你的問題")
        return
    await _answer(update, text, model="gpt-4o")


async def handle_message(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    await _answer(update, update.message.text, model="gpt-4o-mini")


async def _answer(update: Update, question: str, model: str):
    thinking = await update.message.reply_text("思考中 ...")

    try:
        answer = ask(question, model=model)
    except Exception as e:
        log.error("AI error: %s", e)
        await thinking.edit_text("AI 回覆失敗，請稍後再試。")
        return

    # Telegram 4096 char limit
    if len(answer) <= 4096:
        await thinking.edit_text(answer)
    else:
        await thinking.edit_text(answer[:4096])
        for i in range(4096, len(answer), 4096):
            await update.message.reply_text(answer[i : i + 4096])

    try:
        title = question if len(question) <= 60 else question[:57] + "..."
        url = publish(title, question, answer)
        await update.message.reply_text(f"日誌已儲存：\n{url}")
    except Exception as e:
        log.error("Publish error: %s", e)
        await update.message.reply_text("回答已送出，但儲存到 GitHub 時出錯。")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("deep", cmd_deep))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("Bot is running …")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
