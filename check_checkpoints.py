#!/usr/bin/env python3
"""
Quick script to check checkpoint status
"""

import sqlite3
import time
from datetime import datetime

def check_checkpoints():
    con = sqlite3.connect('reddit.db')
    
    print("=== CURRENT CHECKPOINT STATUS ===")
    
    cursor = con.execute("""
        SELECT subreddit, keyword_tag, last_checkpoint 
        FROM crawl_state 
        ORDER BY last_checkpoint DESC
    """)
    
    checkpoints = cursor.fetchall()
    
    if not checkpoints:
        print("No checkpoints found in database")
        return
    
    current_time = time.time()
    
    for sub, kw, checkpoint in checkpoints:
        if checkpoint > 0:
            hours_ago = (current_time - checkpoint) / 3600
            date_str = datetime.fromtimestamp(checkpoint).strftime('%Y-%m-%d %H:%M:%S')
            print(f"r/{sub} - '{kw}' - {hours_ago:.1f} hours ago ({date_str})")
        else:
            print(f"r/{sub} - '{kw}' - No checkpoint")
    
    print(f"\nTotal checkpoints: {len(checkpoints)}")
    
    # Show recent ones (last 24 hours)
    recent = [cp for cp in checkpoints if cp[2] > 0 and (current_time - cp[2]) < 24*3600]
    print(f"Recent checkpoints (last 24h): {len(recent)}")
    
    con.close()

if __name__ == "__main__":
    check_checkpoints() 