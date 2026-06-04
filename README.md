# Fetch morning news and send to Kindle

Fetches the latest news via RSS, scrapes the text, packages everything into an EPUB, and sends it to your Kindle via email (could be configured for other e-ink devices).

---

## The idea
I wanted to:
1) Read for the first hour or so in the morning as opposed to reaching for the phone
2) Read the latest news

That's why I thought I could send the news to my Kindle.
The e-reader screen does not have the negative effect on your body like the phone.
Also, the phone always makes you open other apps unvoluntarily.

---

## Usage

### Prerequisites - Python virtual env
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Create EPUB with latest news
```
python news-to-epub.py
```
An `morning_news_YYYY-MM-DD.epub` file will appear in the same folder.

### Send to Kindle via mail

#### Prerequisites
1. Find your Kindle email - https://www.amazon.com/sendtokindle/email
2. Create Gmail App Password - https://support.google.com/mail/answer/185833?hl=en
3. Add the Gmail email to the "Approved Personal Document E-mail List", located at the Kindle Preferences page from step 1.

#### Set environment variables
```
export KINDLE_EMAIL="yourname@kindle.com"
export SENDER_EMAIL="you@gmail.com"
export SENDER_PASSWORD="your-gmail-app-password"
```

Then run with `--send`:

```
python news-to-epub.py --send
```

---

## Automate with cron (e.g. every morning at 8 AM)

```
crontab -e
```

Add this line:

```
0 8 * * * cd /path/to/this/folder && python news-to-epub.py --send
```

---

## Customizing news sources

Edit the `FEEDS` list in `news-to-epub.py`. Each entry is a dict:

```
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
├── news-to-epub.py   # main script
└── README.md
```

EPUBs are saved alongside the script by default.
Change `OUTPUT_DIR` in the script to use a different folder.