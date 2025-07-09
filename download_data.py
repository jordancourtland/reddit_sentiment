#!/usr/bin/env python3
"""
Script to download database files from cloud storage on app startup
"""

import os
import requests
import sqlite3
from pathlib import Path

def download_database_files():
    """Download database files if they don't exist locally."""
    
    # Database file paths
    reddit_db_path = "reddit.db"
    analysis_db_path = "analysis.db"
    
    # Cloud storage URLs (you'll need to replace these with your actual URLs)
    # For Google Drive: Get shareable links and replace with direct download URLs
    # For Dropbox: Get shareable links
    REDDIT_DB_URL = os.getenv('REDDIT_DB_URL', '')
    ANALYSIS_DB_URL = os.getenv('ANALYSIS_DB_URL', '')
    
    # Download reddit.db if it doesn't exist
    if not os.path.exists(reddit_db_path) and REDDIT_DB_URL:
        print("Downloading reddit.db...")
        try:
            response = requests.get(REDDIT_DB_URL, stream=True)
            response.raise_for_status()
            
            with open(reddit_db_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("✅ reddit.db downloaded successfully")
        except Exception as e:
            print(f"❌ Failed to download reddit.db: {e}")
    
    # Download analysis.db if it doesn't exist
    if not os.path.exists(analysis_db_path) and ANALYSIS_DB_URL:
        print("Downloading analysis.db...")
        try:
            response = requests.get(ANALYSIS_DB_URL, stream=True)
            response.raise_for_status()
            
            with open(analysis_db_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("✅ analysis.db downloaded successfully")
        except Exception as e:
            print(f"❌ Failed to download analysis.db: {e}")
    
    # Check if databases exist and are valid
    for db_path in [reddit_db_path, analysis_db_path]:
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                conn.close()
                print(f"✅ {db_path} is valid")
            except Exception as e:
                print(f"❌ {db_path} is corrupted: {e}")
        else:
            print(f"⚠️ {db_path} not found")

if __name__ == "__main__":
    download_database_files() 