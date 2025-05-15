#!/usr/bin/env python3
"""
stand-alone crawler: reddit api → sqlite
"""

import os, time, requests, sqlite3, json
from datetime import datetime, timezone
from urllib.parse import urlencode
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()
CLIENT_ID     = os.environ.get("client_id")
CLIENT_SECRET = os.environ.get("client_secret")
UA            = os.environ.get("user_agent")

print(f"Credentials loaded - Client ID: {CLIENT_ID[:5]}... (truncated)")
print(f"User Agent: {UA}")

DB_PATH       = "reddit.db"

SUBREDDITS    = ["healthinsurance", "medicalbill"]
KEYWORDS      = ["claim denied", "coverage denied", "appeal medical claim", "denied claim"]

# --------------------------------- database init ---------------------------------

ddl = """
create table if not exists reddit_posts (
    id text primary key,
    subreddit text,
    created_utc integer,
    title text,
    selftext text,
    url text,
    score integer,
    num_comments integer,
    keyword_tag text
);

create table if not exists reddit_comments (
    id text primary key,
    post_id text,
    parent_id text,
    author text,
    body text,
    created_utc integer,
    score integer
);

create table if not exists crawl_state (
    subreddit text,
    keyword_tag text,
    last_epoch integer default 0,
    primary key (subreddit, keyword_tag)
);
"""
con = sqlite3.connect(DB_PATH)
con.executescript(ddl)
con.commit()

# --------------------------------- auth helper ---------------------------------

def get_token():
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    res  = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        data={"grant_type": "client_credentials"},
        headers={"user-agent": UA},
        auth=auth, timeout=30
    )
    res.raise_for_status()
    j = res.json()
    return j["access_token"], time.time() + j["expires_in"]

token, token_expiry = get_token()
print("Successfully obtained Reddit API token")

# Set up retry strategy
retry_strategy = Retry(
    total=3,  # number of retries
    backoff_factor=1,  # wait 1, 2, 4 seconds between retries
    status_forcelist=[429, 500, 502, 503, 504]  # HTTP status codes to retry on
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("https://", adapter)
session.mount("http://", adapter)

def api_get(url, params=None):
    global token, token_expiry
    if time.time() > token_expiry - 60:
        token, token_expiry = get_token()
    hdrs = {"authorization": f"bearer {token}", "user-agent": UA}
    try:
        r = session.get(url, headers=hdrs, params=params, timeout=30)
        r.raise_for_status()
        return r.json(), r.headers
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {str(e)}")
        return None, None

# --------------------------------- crawler core ---------------------------------

def last_checkpoint(sub, kw):
    cur = con.execute(
        "select last_epoch from crawl_state where subreddit=? and keyword_tag=?",
        (sub, kw)
    ).fetchone()
    return cur[0] if cur else 0

def save_checkpoint(sub, kw, ts):
    con.execute("""
        insert into crawl_state (subreddit, keyword_tag, last_epoch)
        values (?,?,?)
        on conflict (subreddit, keyword_tag) do update set last_epoch=excluded.last_epoch
    """, (sub, kw, ts))
    con.commit()

def store_post(p, kw):
    try:
        con.execute("""
            insert into reddit_posts (id, subreddit, created_utc, title, selftext, url,
                                    score, num_comments, keyword_tag)
            values (?,?,?,?,?,?,?, ?,?)
            on conflict(id) do nothing
        """, (
            p["data"]["id"],
            p["data"]["subreddit"].lower(),
            int(p["data"]["created_utc"]),
            p["data"].get("title"),
            p["data"].get("selftext"),
            p["data"]["url"],
            p["data"]["score"],
            p["data"]["num_comments"],
            kw
        ))
        con.commit()
        return True
    except Exception as e:
        print(f"Error storing post {p['data'].get('id', 'unknown')}: {str(e)}")
        return False

def store_comment(c, post_id):
    try:
        con.execute("""
            insert into reddit_comments (id, post_id, parent_id, author, body,
                                        created_utc, score)
            values (?,?,?,?,?,?,?)
            on conflict(id) do nothing
        """, (
            c["data"]["id"],
            post_id,
            c["data"]["parent_id"],
            c["data"].get("author"),
            c["data"].get("body"),
            int(c["data"]["created_utc"]),
            c["data"]["score"]
        ))
        con.commit()
        return True
    except Exception as e:
        print(f"Error storing comment {c['data'].get('id', 'unknown')}: {str(e)}")
        return False

def fetch_comments_tree(post_id):
    url = f"https://oauth.reddit.com/comments/{post_id}"
    params = {"limit": 500, "depth": 10}
    result = api_get(url, params=params)
    if result is None:
        return []
    
    tree, _ = result
    flat = []

    def walk(node):
        if isinstance(node, list):
            for n in node:
                walk(n)
            return
        if not isinstance(node, dict):
            return
        kind = node.get("kind")
        if kind == "t1":
            flat.append(node)
            replies = node["data"].get("replies", {})
            if isinstance(replies, dict):
                for reply in replies.get("data", {}).get("children", []):
                    walk(reply)

    try:
        for child in tree[1]["data"]["children"]:
            walk(child)
    except (IndexError, KeyError) as e:
        print(f"Error processing comments for post {post_id}: {str(e)}")
    
    return flat

def crawl_once():
    for sub in SUBREDDITS:
        for kw in KEYWORDS:
            print(f"\nSearching r/{sub} for '{kw}'")
            last_ts = last_checkpoint(sub, kw)
            query = kw.replace(" ", "+")
            params = {
                "q": query,
                "sort": "new",
                "limit": 100,
                "restrict_sr": "true",
                "t": "all"
            }
            url = f"https://oauth.reddit.com/r/{sub}/search"
            print(f"Making API request to {url} with query: {query}")
            
            result = api_get(url, params=params)
            if result is None:
                print(f"Failed to fetch posts for r/{sub} with keyword '{kw}'")
                continue
                
            json_page, hdrs = result
            posts = json_page["data"]["children"]
            print(f"Found {len(posts)} posts")

            for p in posts:
                try:
                    print(f"Processing post: {p['data'].get('title', '')[:50]}...")
                    if store_post(p, kw):
                        comments = fetch_comments_tree(p["data"]["id"])
                        print(f"Found {len(comments)} comments")
                        for c in comments:
                            store_comment(c, p["data"]["id"])
                        last_ts = max(last_ts, int(p["data"]["created_utc"]))
                        save_checkpoint(sub, kw, last_ts)  # Save checkpoint after each successful post
                        time.sleep(0.3)  # stay < 100 req/min
                except Exception as e:
                    print(f"Error processing post {p['data'].get('id', 'unknown')}: {str(e)}")
                    continue

if __name__ == "__main__":
    try:
        crawl_once()
        print("done – db updated:", datetime.now(timezone.utc))
    except Exception as e:
        print(f"Fatal error: {str(e)}")
    finally:
        con.close()  # Ensure the database connection is closed