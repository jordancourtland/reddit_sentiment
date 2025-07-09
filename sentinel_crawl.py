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
from config_manager import ConfigManager
import logging
from requests.auth import HTTPBasicAuth

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize configuration
config_manager = ConfigManager('config_patient_journey.json')

# Get configuration values
SUBREDDITS = config_manager.get_subreddits()
KEYWORDS = config_manager.get_keywords()
CRAWL_CONFIG = config_manager.get_crawl_config()

# Reddit API credentials
CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
UA = os.getenv('REDDIT_USER_AGENT', 'PatientJourneyBot/1.0')

# Fix the None subscript issue
print(f"Credentials loaded - Client ID: {CLIENT_ID[:5] if CLIENT_ID else 'None'}... (truncated)")
print(f"User Agent: {UA}")

DB_PATH       = "reddit.db"

print(f"Using subreddits: {SUBREDDITS}")
print(f"Using keywords: {KEYWORDS[:5]}... (showing first 5)")

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
    keyword_tag text,
    collection_run text default 'patient_journey_1'
);

create table if not exists reddit_comments (
    id text primary key,
    post_id text,
    parent_id text,
    author text,
    body text,
    created_utc integer,
    score integer,
    FOREIGN KEY (post_id) REFERENCES reddit_posts (id)
);

create table if not exists crawl_state (
    subreddit text,
    keyword_tag text,
    last_checkpoint integer default 0,
    primary key (subreddit, keyword_tag)
);
"""

# Initialize database and fix schema
def init_database():
    con = sqlite3.connect(DB_PATH)
    con.executescript(ddl)
    con.commit()
    
    # Check if url column exists
    cursor = con.execute("PRAGMA table_info(reddit_posts)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'url' not in columns:
        print("Adding missing 'url' column to reddit_posts table...")
        con.execute("ALTER TABLE reddit_posts ADD COLUMN url TEXT")
        con.commit()
        print("Successfully added 'url' column!")
    
    if 'keyword_tag' not in columns:
        print("Adding missing 'keyword_tag' column to reddit_posts table...")
        con.execute("ALTER TABLE reddit_posts ADD COLUMN keyword_tag TEXT")
        con.commit()
        print("Successfully added 'keyword_tag' column!")
    
    con.close()

# Initialize database
init_database()

# --------------------------------- auth helper ---------------------------------

def get_token():
    if not CLIENT_ID or not CLIENT_SECRET or not UA:
        raise ValueError("Missing Reddit API credentials. Please check your .env file.")
    
    # Use HTTPBasicAuth from requests.auth
    auth = HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
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
    total=CRAWL_CONFIG.get("max_retries", 3),  # number of retries
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
        r = session.get(url, headers=hdrs, params=params, timeout=CRAWL_CONFIG.get("timeout", 30))
        r.raise_for_status()
        return r.json(), r.headers
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Subreddit not found (404): {url}")
            return None
        else:
            print(f"HTTP Error {e.response.status_code} fetching {url}: {str(e)}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {str(e)}")
        return None

def check_subreddit_exists(subreddit):
    """Check if a subreddit exists and is accessible."""
    url = f"https://oauth.reddit.com/r/{subreddit}/about"
    result = api_get(url)
    if result is None:
        return False
    json_data, _ = result
    return json_data is not None and "data" in json_data

# --------------------------------- crawler core ---------------------------------

def get_db_connection():
    return sqlite3.connect('reddit.db')

def last_checkpoint(sub, kw):
    con = get_db_connection()
    try:
        cur = con.execute(
            "select last_checkpoint from crawl_state where subreddit=? and keyword_tag=?",
            (sub, kw)
        ).fetchone()
        return cur[0] if cur else 0
    finally:
        con.close()

def save_checkpoint(sub, kw, ts):
    con = get_db_connection()
    try:
        con.execute("""
            insert into crawl_state (subreddit, keyword_tag, last_checkpoint)
            values (?,?,?)
            on conflict (subreddit, keyword_tag) do update set last_checkpoint=excluded.last_checkpoint
        """, (sub, kw, ts))
        con.commit()
    finally:
        con.close()

def store_post(p, kw):
    con = get_db_connection()
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
    finally:
        con.close()

def store_comment(c, post_id):
    con = get_db_connection()
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
    finally:
        con.close()

def fetch_comments_tree(post_id):
    url = f"https://oauth.reddit.com/comments/{post_id}"
    params = {
        "limit": CRAWL_CONFIG.get("comments_limit", 200),  # Reduced from 500
        "depth": CRAWL_CONFIG.get("comments_depth", 5),     # Reduced from 10
    }
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
        if tree and len(tree) > 1 and tree[1] and "data" in tree[1] and "children" in tree[1]["data"]:
            for child in tree[1]["data"]["children"]:
                walk(child)
    except (IndexError, KeyError) as e:
        print(f"Error processing comments for post {post_id}: {str(e)}")
    
    return flat

def crawl_once():
    # Track which combinations we've processed in this session
    processed_combinations = set()
    
    # First, prioritize unprocessed combinations
    unprocessed_combinations = []
    recently_processed_combinations = []
    old_combinations = []
    
    for sub in SUBREDDITS:
        for kw in KEYWORDS:
            combination = f"{sub}_{kw}"
            last_ts = last_checkpoint(sub, kw)
            
            if last_ts == 0:
                # Never processed
                unprocessed_combinations.append((sub, kw))
            elif (time.time() - last_ts) < 24 * 3600:
                # Processed within last 24 hours
                recently_processed_combinations.append((sub, kw))
            else:
                # Processed more than 24 hours ago
                old_combinations.append((sub, kw))
    
    print(f"Found {len(unprocessed_combinations)} unprocessed combinations")
    print(f"Found {len(recently_processed_combinations)} recently processed combinations (skipping)")
    print(f"Found {len(old_combinations)} old combinations (will re-process if needed)")
    print()
    
    # Process unprocessed combinations first
    combinations_to_process = unprocessed_combinations + old_combinations
    
    for sub, kw in combinations_to_process:
        combination = f"{sub}_{kw}"
        
        # Skip if we've already processed this combination in this session
        if combination in processed_combinations:
            continue
            
        print(f"\nSearching r/{sub} for '{kw}'")
        
        # Check if subreddit exists before proceeding
        if not check_subreddit_exists(sub):
            print(f"Subreddit r/{sub} does not exist or is not accessible. Skipping...")
            # Save a checkpoint to avoid checking again
            current_time = int(time.time())
            save_checkpoint(sub, kw, current_time)
            processed_combinations.add(combination)
            continue
            
        last_ts = last_checkpoint(sub, kw)
        
        # Skip if we've processed this recently (within last 24 hours)
        if last_ts > 0:
            hours_since_last = (time.time() - last_ts) / 3600
            print(f"Last checkpoint for r/{sub} '{kw}': {hours_since_last:.1f} hours ago")
            if hours_since_last < 24:
                print(f"Skipping r/{sub} for '{kw}' - processed {hours_since_last:.1f} hours ago")
                continue
            else:
                print(f"Processing r/{sub} for '{kw}' - last processed {hours_since_last:.1f} hours ago")
        else:
            print(f"First time processing r/{sub} for '{kw}'")
        
        query = kw.replace(" ", "+")
        params = {
            "q": query,
            "sort": CRAWL_CONFIG.get("sort_by", "new"),
            "limit": CRAWL_CONFIG.get("posts_per_search", 25),
            "restrict_sr": "true",
            "t": CRAWL_CONFIG.get("search_timeframe", "all")
        }
        url = f"https://oauth.reddit.com/r/{sub}/search"
        print(f"Making API request to {url} with query: {query}")
        
        result = api_get(url, params=params)
        if result is None:
            print(f"Failed to fetch posts for r/{sub} with keyword '{kw}'")
            time.sleep(5)
            continue
            
        json_page, hdrs = result
        if json_page is None or "data" not in json_page or "children" not in json_page["data"]:
            print(f"Invalid response format for r/{sub} with keyword '{kw}'")
            continue
            
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
                    
                    # Fix the type comparison issue
                    created_utc = int(p["data"]["created_utc"])
                    last_ts = max(last_ts, created_utc)
                    time.sleep(2.0)
            except Exception as e:
                print(f"Error processing post {p['data'].get('id', 'unknown')}: {str(e)}")
                time.sleep(1.0)
                continue
        
        # Save checkpoint with current time (not post timestamp)
        current_time = int(time.time())
        save_checkpoint(sub, kw, current_time)
        
        # Mark this combination as processed
        processed_combinations.add(combination)
        time.sleep(3.0)

def update_post_metadata(post_id, post_data):
    """Update the metadata for a post with the latest data from Reddit."""
    try:
        con = get_db_connection()
        con.execute("""
            UPDATE reddit_posts SET
                score = ?,
                num_comments = ?
            WHERE id = ?
        """, (
            post_data["score"],
            post_data["num_comments"],
            post_id
        ))
        con.commit()
        return True
    except Exception as e:
        print(f"Error updating metadata for post {post_id}: {str(e)}")
        return False

def update_all_threads_with_new_comments():
    """Update any thread with new comments by checking Reddit first."""
    
    # Get ALL threads from database
    con = get_db_connection()
    posts = con.execute("""
        SELECT p.id, COUNT(c.id) as stored_comments 
        FROM reddit_posts p
        LEFT JOIN reddit_comments c ON p.id = c.post_id
        GROUP BY p.id
    """).fetchall()
    
    updated_count = 0
    
    for post_id, stored_comments in posts:
        # Make API call to get current thread info
        url = f"https://oauth.reddit.com/comments/{post_id}/.json"
        result = api_get(url, {"limit": 1})
        
        if result is None:
            continue
            
        json_data, _ = result
        
        # Get current comment count from API response
        try:
            if json_data and len(json_data) > 0 and json_data[0] and "data" in json_data[0]:
                children = json_data[0]["data"].get("children", [])
                if children and len(children) > 0 and children[0] and "data" in children[0]:
                    current_num_comments = children[0]["data"].get("num_comments", 0)
                    
                    # If there are more comments on Reddit than in our DB
                    if current_num_comments > stored_comments:
                        print(f"Thread {post_id} has {current_num_comments} comments but we only have {stored_comments}. Updating...")
                        
                        # Update the post metadata first
                        update_post_metadata(post_id, children[0]["data"])
                        
                        # Then fetch all comments
                        comments = fetch_comments_tree(post_id)
                        for c in comments:
                            store_comment(c, post_id)
                        
                        updated_count += 1
                        
                        # Add a longer delay to avoid rate limiting
                        time.sleep(2.0)
        except (IndexError, KeyError) as e:
            print(f"Error processing thread metadata for {post_id}: {str(e)}")
            continue
            
    print(f"Updated {updated_count} threads with new comments")
    return updated_count

# Fix the reddit_comments table schema
def fix_database_schema():
    con = sqlite3.connect('reddit.db')
    
    # Check reddit_posts table
    cursor = con.execute("PRAGMA table_info(reddit_posts)")
    post_columns = [column[1] for column in cursor.fetchall()]
    
    if 'url' not in post_columns:
        print("Adding missing 'url' column to reddit_posts table...")
        con.execute("ALTER TABLE reddit_posts ADD COLUMN url TEXT")
        print("Successfully added 'url' column!")
    
    if 'keyword_tag' not in post_columns:
        print("Adding missing 'keyword_tag' column to reddit_posts table...")
        con.execute("ALTER TABLE reddit_posts ADD COLUMN keyword_tag TEXT")
        print("Successfully added 'keyword_tag' column!")
    
    # Check reddit_comments table
    cursor = con.execute("PRAGMA table_info(reddit_comments)")
    comment_columns = [column[1] for column in cursor.fetchall()]
    
    if 'parent_id' not in comment_columns:
        print("Adding missing 'parent_id' column to reddit_comments table...")
        con.execute("ALTER TABLE reddit_comments ADD COLUMN parent_id TEXT")
        print("Successfully added 'parent_id' column!")
    
    con.commit()
    con.close()
    print("Database schema fixed!")

# Run the fix
fix_database_schema()

if __name__ == "__main__":
    import sys
    
    # Check for command line arguments
    start_subreddit = None
    if len(sys.argv) > 1:
        start_subreddit = sys.argv[1].lower()
        print(f"Starting crawl from subreddit: {start_subreddit}")
    
    try:
        # Use filtered subreddits if starting from a specific subreddit
        subreddits_to_crawl = SUBREDDITS
        if start_subreddit:
            # Filter subreddits to start from the specified one
            try:
                start_index = next(i for i, sub in enumerate(SUBREDDITS) if sub.lower() == start_subreddit)
                subreddits_to_crawl = SUBREDDITS[start_index:]
                print(f"Filtered subreddits: {subreddits_to_crawl}")
            except StopIteration:
                print(f"Subreddit '{start_subreddit}' not found in config. Using all subreddits.")
        
        # Temporarily replace SUBREDDITS for this run
        original_subreddits = SUBREDDITS
        SUBREDDITS = subreddits_to_crawl
        
        crawl_once()
        print("Checking for new comments in existing threads...")
        update_all_threads_with_new_comments()
        print("done – db updated:", datetime.now(timezone.utc))
        
        # Restore original subreddits
        SUBREDDITS = original_subreddits
    except Exception as e:
        print(f"Fatal error: {str(e)}")