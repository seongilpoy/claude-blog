import json
import os

import requests
from bs4 import BeautifulSoup

BLOG_URL = "https://claude.com/blog"
BASE_URL = "https://claude.com"
STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "last_posts.json")


def is_blog_post_url(url):
    """Filter out category pages, PDFs, and non-post URLs."""
    if not url.startswith(BASE_URL + "/blog/"):
        return False
    if "/blog/category/" in url:
        return False
    return True


def fetch_posts():
    """Scrape blog posts from claude.com/blog."""
    resp = requests.get(BLOG_URL, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    seen = set()
    posts = []

    for item in soup.select("div.w-dyn-item"):
        link = item.find("a", href=True)
        title_el = item.select_one("h2.card_blog_title") or item.find("h2")
        time_el = item.find("time")

        if not link or not title_el:
            continue

        href = link["href"]
        url = href if href.startswith("http") else BASE_URL + href

        if not is_blog_post_url(url):
            continue
        if url in seen:
            continue
        seen.add(url)

        posts.append({
            "title": title_el.get_text(strip=True),
            "url": url,
            "date": time_el.get_text(strip=True) if time_el else "",
        })

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
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📢 Claude Blog 새 글",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*<{post['url']}|{post['title']}>*\n📅 {post['date']}",
                },
            },
        ],
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
    new_posts = [p for p in posts if p["url"] not in seen_urls]

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
