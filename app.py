"""
Flask 新闻聚合器 — 多源 RSS 抓取 + Web 展示
"""

from flask import Flask, render_template
from fetcher import fetch_all, RSS_SOURCES

app = Flask(__name__)


@app.route("/")
def index():
    """首页：抓取并展示所有新闻"""
    try:
        articles = fetch_all(max_per_source=20)
    except Exception as e:
        articles = []
        print(f"[!] 抓取出错: {e}")

    return render_template(
        "index.html",
        articles=articles,
        sources=RSS_SOURCES,
    )


@app.route("/health")
def health():
    """健康检查端点（Render 用）"""
    return "OK", 200


# ── 入口 ────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
