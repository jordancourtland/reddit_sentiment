#!/usr/bin/env python3
"""
Script to download database files from cloud storage on app startup
"""

import os
import requests
import sqlite3
from pathlib import Path

def download_database_files():
    """Download database files from cloud storage if they don't exist locally."""
    
    # Database file paths
    reddit_db_path = "reddit.db"
    analysis_db_path = "analysis.db"
    
    # Cloud storage URLs
    REDDIT_DB_URL = os.getenv('REDDIT_DB_URL', '')
    ANALYSIS_DB_URL = os.getenv('ANALYSIS_DB_URL', '')
    
    # Download reddit.db if it doesn't exist
    if not os.path.exists(reddit_db_path) and REDDIT_DB_URL:
        print("Downloading reddit.db...")
        try:
            response = requests.get(REDDIT_DB_URL, stream=True)
            response.raise_for_status()
            
            # Check if we got an HTML response (error page)
            if 'text/html' in response.headers.get('content-type', ''):
                print(f"❌ Got HTML response instead of database file")
                print(f"URL: {REDDIT_DB_URL}")
                print(f"Content-Type: {response.headers.get('content-type')}")
                return
            
            with open(reddit_db_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Check file size
            file_size = os.path.getsize(reddit_db_path)
            print(f"✅ reddit.db downloaded successfully ({file_size} bytes)")
            
            # Verify it's a valid SQLite database
            if file_size < 1000:  # Too small to be a real database
                print(f"❌ Downloaded file is too small ({file_size} bytes) - likely an error page")
                os.remove(reddit_db_path)
                return
                
        except Exception as e:
            print(f"❌ Failed to download reddit.db: {e}")
            print(f"URL: {REDDIT_DB_URL}")
    
    # Download analysis.db if it doesn't exist
    if not os.path.exists(analysis_db_path) and ANALYSIS_DB_URL:
        print("Downloading analysis.db...")
        try:
            response = requests.get(ANALYSIS_DB_URL, stream=True)
            response.raise_for_status()
            
            # Check if we got an HTML response (error page)
            if 'text/html' in response.headers.get('content-type', ''):
                print(f"❌ Got HTML response instead of database file")
                print(f"URL: {ANALYSIS_DB_URL}")
                print(f"Content-Type: {response.headers.get('content-type')}")
                return
            
            with open(analysis_db_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Check file size
            file_size = os.path.getsize(analysis_db_path)
            print(f"✅ analysis.db downloaded successfully ({file_size} bytes)")
            
            # Verify it's a valid SQLite database
            if file_size < 1000:  # Too small to be a real database
                print(f"❌ Downloaded file is too small ({file_size} bytes) - likely an error page")
                os.remove(analysis_db_path)
                return
                
        except Exception as e:
            print(f"❌ Failed to download analysis.db: {e}")
            print(f"URL: {ANALYSIS_DB_URL}")
    
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