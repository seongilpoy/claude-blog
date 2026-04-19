import json
import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

BLOG_URL = "https://claude.com/blog"
BASE_URL = "https://claude.com"
STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "last_posts.json")

DATE_PATTERN = re.compile(
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}"
)


def is_blog_post_url(url):
    """Filter out category pages, PDFs, and non-post URLs."""
    if not url.startswith(BASE_URL + "/blog/"):
        return False
    if "/blog/category/" in url:
        return False
    return True


def slug_to_title(slug):
    """Convert URL slug to readable title."""
    return slug.replace("-", " ").title()


def find_date(element):
    """Find a date string inside an element's text."""
    for div in element.find_all("div"):
        text = div.get_text(strip=True)
        m = DATE_PATTERN.search(text)
        if m:
            return m.group()
    return ""


def fetch_posts():
    """Scrape blog posts from claude.com/blog."""
    resp = requests.get(BLOG_URL, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    seen = set()
    posts = []

    for item in soup.select("div.w-dyn-item"):
        link = item.find("a", href=True)
        if not link:
            continue

        href = link["href"]
        url = href if href.startswith("http") else BASE_URL + href

        if not is_blog_post_url(url):
            continue
        if url in seen:
            continue
        seen.add(url)

        # Try h2 title first, then link text, then slug
        title_el = item.select_one("h2.card_blog_title") or item.find("h2")
        if title_el:
            title = title_el.get_text(strip=True)
        else:
            link_text = link.get_text(strip=True)
            if link_text:
                title = link_text
            else:
                slug = url.rstrip("/").split("/")[-1]
                title = slug_to_title(slug)

        date = find_date(item)

        posts.append({"title": title, "url": url, "date": date})

    return posts


def load_seen_urls():
    """Load previously seen post URLs from state file."""
    if not os.path.exists(STATE_FILE):
        return set()
    with open(STATE_FILE) as f:
        data = json.load(f)
    return set(data.get("seen_urls", []))


def save_seen_urls(urls):
    """Save seen post URLs to state file."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump({"seen_urls": sorted(urls)}, f, indent=2)


def send_slack_notification(post, webhook_url):
    """Send a Slack message for a new blog post."""
    payload = {
        "text": f"{post['date']} - <{post['url']}|{post['title']}>",
    }
    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()


def main():
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")

    posts = fetch_posts()
    if not posts:
        print("No posts found on the blog page.")
        return

    seen_urls = load_seen_urls()

    # Optional: filter by month (e.g. FILTER_MONTH="Apr 2026")
    filter_month = os.environ.get("FILTER_MONTH", "")
    if filter_month:
        parts = filter_month.lower().split()
        posts = [p for p in posts if all(part in p["date"].lower() for part in parts)]

    new_posts = [p for p in posts if p["url"] not in seen_urls]

    # Sort oldest first so the most recent post is sent last
    def parse_date(d):
        for fmt in ("%B %d, %Y", "%b %d, %Y"):
            try:
                return datetime.strptime(d, fmt)
            except ValueError:
                continue
        return datetime.min

    new_posts.sort(key=lambda p: parse_date(p["date"]))

    if not new_posts:
        print(f"No new posts. ({len(posts)} posts checked)")
        return

    print(f"Found {len(new_posts)} new post(s)!")

    for post in new_posts:
        print(f"  - {post['title']} ({post['url']})")
        if webhook_url:
            send_slack_notification(post, webhook_url)
            print(f"    → Slack notification sent")
        else:
            print(f"    → SLACK_WEBHOOK_URL not set, skipping notification")

    # Update state with all current post URLs
    all_urls = seen_urls | {p["url"] for p in posts}
    save_seen_urls(all_urls)
    print("State file updated.")


if __name__ == "__main__":
    main()
