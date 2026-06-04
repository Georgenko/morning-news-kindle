import argparse
import datetime
import os
import smtplib
import textwrap
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import feedparser
import requests
from bs4 import BeautifulSoup
from ebooklib import epub

# How many articles to pull per feed
MAX_ARTICLES_PER_FEED = 10

# Request timeout in seconds
TIMEOUT = 15

# Output directory (same folder as the script by default)
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Kindle email settings — fill these in or set as env vars
KINDLE_EMAIL   = os.getenv("KINDLE_EMAIL", "")
SENDER_EMAIL   = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")        # use an App Password for Gmail
SMTP_SERVER    = "smtp.gmail.com"
SMTP_PORT      = 587

FEEDS = [
    # ── Bulgarian ──────────────────────────────
   {
       "name": "БТА",
       "url": "https://www.bta.bg/bg/rss/free",
       "lang": "bg",
   },
    {
        "name": "Mediapool",
        "url": "https://mediapool.bg/rss",
        "lang": "bg",
    },
    {
        "name": "Capital.bg",
        "url": "https://www.capital.bg/rss/",
        "lang": "bg",
    },

    # ── English ────────────────────────────────
    # {
    #     "name": "BBC News",
    #     "url": "http://feeds.bbci.co.uk/news/rss.xml",
    #     "lang": "en",
    # },
#    {
#        "name": "AP News",
#        "url": "https://rsshub.app/apnews/topics/apf-topnews",  # Reuters killed their RSS; AP is a solid replacement
#        "lang": "en",
#    },
#     {
#         "name": "The Guardian",
#         "url": "https://www.theguardian.com/world/rss",
#         "lang": "en",
#     },
#     {
#         "name": "Ars Technica",
#         "url": "https://feeds.arstechnica.com/arstechnica/index",
#         "lang": "en",
#     },
]


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; MorningNewsBot/1.0; "
        "+https://github.com/yourname/morning-news)"
    )
}


def fetch_feed(feed_cfg: dict) -> list[dict]:
    """Parse an RSS/Atom feed and return a list of article dicts."""
    print(f"  Fetching {feed_cfg['name']} …")
    try:
        parsed = feedparser.parse(
            feed_cfg["url"],
            request_headers=HEADERS,
            # feedparser follows redirects by itself
        )
    except Exception as exc:
        print(f"    ⚠  Could not parse feed: {exc}")
        return []

    articles = []
    for entry in parsed.entries[:MAX_ARTICLES_PER_FEED]:
        title   = getattr(entry, "title", "Untitled")
        link    = getattr(entry, "link",  "")
        summary = getattr(entry, "summary", "")
        # Some feeds put HTML in summary — strip it
        summary = BeautifulSoup(summary, "lxml").get_text(" ", strip=True)

        body = fetch_article_body(link) or summary or "(No content)"

        articles.append(
            {
                "title":   title,
                "link":    link,
                "summary": summary,
                "body":    body,
                "source":  feed_cfg["name"],
                "lang":    feed_cfg["lang"],
            }
        )

    print(f"    ✓ {len(articles)} articles")
    return articles


def fetch_article_body(url: str) -> str:
    """Best-effort full-text extraction from an article URL."""
    if not url:
        return ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        # Remove clutter
        for tag in soup(["script", "style", "nav", "footer",
                          "header", "aside", "figure", "form"]):
            tag.decompose()

        # Try common article containers in order of preference
        for selector in [
            "article",
            "[class*='article-body']",
            "[class*='article-content']",
            "[class*='entry-content']",
            "[class*='post-content']",
            "main",
        ]:
            container = soup.select_one(selector)
            if container:
                text = container.get_text(" ", strip=True)
                if len(text) > 200:
                    return text[:8000]   # cap so EPUB chapters stay readable

        # Fallback: largest <p> block cluster
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = " ".join(p for p in paragraphs if len(p) > 60)
        return text[:8000] if text else ""

    except Exception:
        return ""


def article_to_html(article: dict) -> str:
    """Render one article as an EPUB-friendly HTML chapter."""
    body_html = ""
    for para in textwrap.wrap(article["body"], width=120):
        body_html += f"<p>{para}</p>\n"

    return f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{article['lang']}">
<head>
  <title>{article['title']}</title>
  <style>
    body  {{ font-family: serif; margin: 2em; line-height: 1.6; }}
    h1    {{ font-size: 1.4em; margin-bottom: 0.3em; }}
    .meta {{ font-size: 0.8em; color: #555; margin-bottom: 1.2em; }}
    p     {{ margin: 0.6em 0; }}
    a     {{ color: #1a6fbf; }}
  </style>
</head>
<body>
  <h1>{article['title']}</h1>
  <p class="meta">Source: {article['source']} &nbsp;|&nbsp;
     <a href="{article['link']}">Read online ↗</a></p>
  {body_html}
</body>
</html>"""


def build_epub(all_articles: list[dict], date_str: str) -> str:
    """Assemble an EPUB from all fetched articles and return the file path."""

    book = epub.EpubBook()
    book.set_identifier(f"morning-news-{date_str}")
    book.set_title(f"Morning News — {date_str}")
    book.set_language("en")
    book.add_author("Morning News Bot")

    # ── Table of contents & spine ──────────────────────
    toc     = []
    spine   = ["nav"]
    chapters = []

    # Group by language section
    sections = {
        "bg": ("Bulgarian News", [a for a in all_articles if a["lang"] == "bg"]),
        "en": ("English News",   [a for a in all_articles if a["lang"] == "en"]),
    }

    for lang_code, (section_title, articles) in sections.items():
        if not articles:
            continue

        sec_items = []
        for idx, article in enumerate(articles):
            file_name = f"{lang_code}_{idx:03d}.xhtml"
            chap = epub.EpubHtml(
                title=article["title"],
                file_name=file_name,
                lang=lang_code,
            )
            chap.set_content(article_to_html(article).encode("utf-8"))
            book.add_item(chap)
            chapters.append(chap)
            spine.append(chap)
            sec_items.append(chap)

        toc.append((epub.Section(section_title), sec_items))

    book.toc = toc
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Basic CSS
    css = epub.EpubItem(
        uid="style",
        file_name="style/main.css",
        media_type="text/css",
        content=b"body { font-family: serif; }",
    )
    book.add_item(css)

    out_path = os.path.join(OUTPUT_DIR, f"morning_news_{date_str}.epub")
    epub.write_epub(out_path, book)
    return out_path


def send_to_kindle(epub_path: str) -> None:
    """Email the EPUB to your Kindle address."""
    if not SENDER_PASSWORD:
        print("\n⚠  SENDER_PASSWORD not set — skipping email.")
        print("   Set it via:  export SENDER_PASSWORD='your-app-password'")
        return

    msg = MIMEMultipart()
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = KINDLE_EMAIL
    msg["Subject"] = "convert"        # Amazon's magic word to convert & deliver

    msg.attach(MIMEText("Morning news digest — delivered by MorningNewsBot."))

    with open(epub_path, "rb") as f:
        part = MIMEBase("application", "epub+zip")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f'attachment; filename="{os.path.basename(epub_path)}"',
    )
    msg.attach(part)

    print(f"\n📧 Sending to {KINDLE_EMAIL} …")
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, KINDLE_EMAIL, msg.as_string())
    print("   ✓ Sent!")


def main():
    parser = argparse.ArgumentParser(description="Build a morning news EPUB.")
    parser.add_argument(
        "--send", action="store_true",
        help="Email the EPUB to your Kindle after building."
    )
    args = parser.parse_args()

    today = datetime.date.today().isoformat()
    print(f"\n📰 Morning News — {today}\n")

    all_articles: list[dict] = []

    print("── Bulgarian sources ──")
    for feed in (f for f in FEEDS if f["lang"] == "bg"):
        all_articles.extend(fetch_feed(feed))

    print("\n── English sources ──")
    for feed in (f for f in FEEDS if f["lang"] == "en"):
        all_articles.extend(fetch_feed(feed))

    if not all_articles:
        print("\n✗ No articles fetched. Check your internet connection or feed URLs.")
        return

    # Drop articles with no usable content (empty body crashes ebooklib)
    all_articles = [a for a in all_articles if a.get("body", "").strip()]
    print(f"\n📚 Building EPUB with {len(all_articles)} articles …")
    epub_path = build_epub(all_articles, today)
    print(f"   ✓ Saved → {epub_path}")

    if args.send:
        send_to_kindle(epub_path)

    print("\nDone! ☕\n")


if __name__ == "__main__":
    main()
