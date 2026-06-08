"""
多源 RSS 抓取模块
从多个 RSS 源抓取新闻，合并后按时间排序
"""

import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen
from urllib.error import URLError
from datetime import datetime, timezone
from typing import List, Dict
import re


# ── RSS 源配置 ──────────────────────────────────────────────
RSS_SOURCES = [
    {
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage",
        "color": "#ff6600",
    },
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "color": "#0a9e01",
    },
    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "color": "#ff4e00",
    },
]


def _safe_text(element, tag: str) -> str:
    """安全提取子元素文本"""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return ""


def _strip_html(text: str) -> str:
    """去除 HTML 标签，保留纯文本"""
    return re.sub(r"<[^>]+>", "", text)


def _parse_date(raw: str) -> datetime:
    """
    解析多种常见日期格式，返回 UTC datetime
    常见格式：RFC 2822 (RSS)、ISO 8601 (Atom)
    """
    if not raw:
        return datetime.min.replace(tzinfo=timezone.utc)

    # RFC 2822 / RFC 822
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(raw)
    except (ValueError, TypeError):
        pass

    # ISO 8601 (Atom)
    for fmt in [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
    ]:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return datetime.min.replace(tzinfo=timezone.utc)


def fetch_feed(source: Dict) -> List[Dict]:
    """
    抓取单个 RSS 源
    返回文章列表，每篇文章是一个 dict
    """
    req = Request(
        source["url"],
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; RSS-Reader/1.0)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
        },
    )

    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except URLError as e:
        print(f"[!] 抓取失败 {source['name']}: {e}")
        return []
    except Exception as e:
        print(f"[!] 解析失败 {source['name']}: {e}")
        return []

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"[!] XML 解析错误 {source['name']}: {e}")
        return []

    articles = []

    # ── RSS 2.0 格式 ──
    for item in root.iter("item"):
        title = _safe_text(item, "title")
        link = _safe_text(item, "link")
        desc = _strip_html(_safe_text(item, "description"))
        pub_date = _parse_date(_safe_text(item, "pubDate"))
        creator = _safe_text(item, "{http://purl.org/dc/elements/1.1/}creator")

        if not title or not link:
            continue

        articles.append({
            "title": title,
            "link": link,
            "description": desc[:300] if desc else "",
            "published": pub_date,
            "source": source["name"],
            "source_color": source["color"],
            "author": creator,
        })

    # ── Atom 格式 ──
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        title = title_el.text.strip() if title_el is not None and title_el.text else ""

        link_el = entry.find("atom:link", ns)
        link = link_el.get("href", "") if link_el is not None else ""

        summary_el = entry.find("atom:summary", ns)
        desc = _strip_html(summary_el.text.strip()) if summary_el is not None and summary_el.text else ""

        updated_el = entry.find("atom:updated", ns)
        pub_date = _parse_date(updated_el.text) if updated_el is not None and updated_el.text else datetime.min.replace(tzinfo=timezone.utc)

        author_el = entry.find("atom:author/atom:name", ns)
        author = author_el.text.strip() if author_el is not None and author_el.text else ""

        if not title or not link:
            continue

        articles.append({
            "title": title,
            "link": link,
            "description": desc[:300] if desc else "",
            "published": pub_date,
            "source": source["name"],
            "source_color": source["color"],
            "author": author,
        })

    return articles


def fetch_all(max_per_source: int = 20) -> List[Dict]:
    """
    抓取所有 RSS 源，合并后按时间倒序排列
    """
    all_articles = []

    for source in RSS_SOURCES:
        print(f"[*] 正在抓取 {source['name']}...")
        articles = fetch_feed(source)
        all_articles.extend(articles[:max_per_source])
        print(f"    获取到 {len(articles[:max_per_source])} 篇")

    # 按发布时间倒序
    all_articles.sort(key=lambda a: a["published"], reverse=True)

    return all_articles


# ── CLI 入口 ────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  多源 RSS 新闻抓取器")
    print("=" * 60)
    print()

    articles = fetch_all(max_per_source=20)

    print(f"\n共抓取 {len(articles)} 篇文章\n")

    for i, a in enumerate(articles, 1):
        source_tag = f"[{a['source']}]"
        time_str = (
            a["published"].strftime("%Y-%m-%d %H:%M")
            if a["published"].year > 2000
            else "----"
        )
        print(f"{i:2d}. {source_tag} {a['title']}")
        print(f"    {a['link']}")
        print(f"    {time_str}")
        if a["description"]:
            print(f"    {a['description'][:120]}...")
        print()
