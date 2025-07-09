#!/usr/bin/env python3
"""
Crawl Manager - Helper script to manage the Reddit crawler
"""

import sqlite3
import json
from datetime import datetime, timedelta
import subprocess
import sys

def get_crawl_progress():
    """Show current crawl progress and checkpoint status"""
    con = sqlite3.connect('reddit.db')
    
    # Get all subreddits and keywords from config
    with open('config_patient_journey.json', 'r') as f:
        config = json.load(f)
    
    subreddits = config['subreddits']
    keywords = config['keywords']
    
    print("=== CRAWL PROGRESS REPORT ===")
    print(f"Total subreddits: {len(subreddits)}")
    print(f"Total keywords: {len(keywords)}")
    print(f"Total combinations: {len(subreddits) * len(keywords)}")
    print()
    
    # Check checkpoint status
    cursor = con.execute("""
        SELECT subreddit, keyword_tag, last_checkpoint 
        FROM crawl_state 
        ORDER BY subreddit, keyword_tag
    """)
    
    checkpoints = cursor.fetchall()
    processed_combinations = len(checkpoints)
    total_combinations = len(subreddits) * len(keywords)
    
    print(f"Processed combinations: {processed_combinations}/{total_combinations}")
    print(f"Progress: {(processed_combinations/total_combinations)*100:.1f}%")
    print()
    
    # Show recent activity
    print("=== RECENT ACTIVITY (last 24 hours) ===")
    recent_checkpoints = []
    for sub, kw, checkpoint in checkpoints:
        if checkpoint > 0:
            hours_ago = (datetime.now().timestamp() - checkpoint) / 3600
            if hours_ago < 24:
                recent_checkpoints.append((sub, kw, hours_ago))
    
    if recent_checkpoints:
        for sub, kw, hours in sorted(recent_checkpoints, key=lambda x: x[2]):
            print(f"r/{sub} - '{kw}' ({hours:.1f} hours ago)")
    else:
        print("No recent activity")
    
    print()
    
    # Show next subreddits to process
    print("=== REMAINING SUBREDDITS TO PROCESS ===")
    processed_subs = set()
    for sub, kw, checkpoint in checkpoints:
        if checkpoint > 0:
            processed_subs.add(sub)
    
    unprocessed_subs = [sub for sub in subreddits if sub not in processed_subs]
    if unprocessed_subs:
        print(f"Subreddits not yet started ({len(unprocessed_subs)} total):")
        for i, sub in enumerate(unprocessed_subs, 1):
            print(f"  {i:2d}. r/{sub}")
    else:
        print("All subreddits have been started")
    
    con.close()

def start_crawl_from_subreddit(subreddit):
    """Start crawling from a specific subreddit"""
    print(f"Starting crawl from r/{subreddit}...")
    try:
        subprocess.run([sys.executable, 'sentinel_crawl.py', subreddit], check=True)
        print("Crawl completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Crawl failed with error: {e}")
    except KeyboardInterrupt:
        print("Crawl interrupted by user")

def show_help():
    """Show help information"""
    print("""
Crawl Manager - Reddit Crawler Management Tool

Usage:
  python crawl_manager.py [command] [options]

Commands:
  progress          Show current crawl progress and status
  start <subreddit> Start crawling from a specific subreddit
  help             Show this help message

Examples:
  python crawl_manager.py progress
  python crawl_manager.py start Psoriasis
  python crawl_manager.py start MultipleSclerosis
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "progress":
        get_crawl_progress()
    elif command == "start":
        if len(sys.argv) < 3:
            print("Error: Please specify a subreddit to start from")
            print("Example: python crawl_manager.py start Psoriasis")
            sys.exit(1)
        subreddit = sys.argv[2]
        start_crawl_from_subreddit(subreddit)
    elif command == "help":
        show_help()
    else:
        print(f"Unknown command: {command}")
        show_help()
        sys.exit(1) 