# 📰 Morning News → Kindle

Fetches Bulgarian and English news via RSS, scrapes full article text,
and packages everything into an EPUB you can read on your Kindle.

---

## Quick start

```bash
# 1. Install dependencies
pip install requests beautifulsoup4 ebooklib feedparser lxml

# 2. Run it
python news_to_epub.py
```

An `morning_news_YYYY-MM-DD.epub` file will appear in the same folder.

---

## Send to Kindle automatically

Amazon lets you email documents to your Kindle.

### One-time setup
1. Go to **Manage Your Content and Devices** → **Preferences** → **Personal Document Settings**
2. Note your `@kindle.com` address
3. Add your sender Gmail address to the **Approved Personal Document E-mail List**
4. Create a Gmail **App Password** (Google Account → Security → 2-Step Verification → App Passwords)

### Configure the script
Set environment variables (don't hard-code passwords in source!):

```bash
export KINDLE_EMAIL="yourname@kindle.com"
export SENDER_EMAIL="you@gmail.com"
export SENDER_PASSWORD="your-gmail-app-password"
```

Then run with `--send`:

```bash
python news_to_epub.py --send
```

---

## Automate with cron (runs every morning at 6 AM)

```bash
crontab -e
```

Add this line:

```
0 6 * * * cd /path/to/this/folder && python news_to_epub.py --send
```

Or on Windows, use **Task Scheduler**.

---

## Customizing news sources

Edit the `FEEDS` list in `news_to_epub.py`. Each entry is a dict:

```python
{
    "name": "My Source",
    "url":  "https://example.com/rss.xml",
    "lang": "bg",   # or "en"
}
```

Any RSS or Atom feed works. Good Bulgarian sources to consider:
- **Actualno**: `https://www.actualno.com/rss.xml`
- **Klassa**: `https://klassa.bg/rss`
- **24 Chasa**: `https://www.24chasa.bg/rss`

---

## Project structure

```
morning_news/
├── news_to_epub.py   # main script
└── README.md
```

EPUBs are saved alongside the script by default.
Change `OUTPUT_DIR` in the script to use a different folder.

---

## Dependencies

| Package | Purpose |
|---|---|
| `feedparser` | Parse RSS/Atom feeds |
| `requests` | HTTP requests |
| `beautifulsoup4` | HTML scraping & cleanup |
| `lxml` | Fast HTML/XML parser (used by BS4) |
| `ebooklib` | Build EPUB files |

All are installable with `pip` and have permissive licenses.

---

"""
morning\_news.py — Fetch Bulgarian & English news and pack them into an EPUB
for reading on Kindle.

Usage:
    python news_to_epub.py                 # builds today's digest
    python news_to_epub.py --send          # also emails it to your Kindle

Dependencies:
    pip install requests beautifulsoup4 ebooklib feedparser lxml
"""
