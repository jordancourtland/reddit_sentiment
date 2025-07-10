#!/usr/bin/env python3
"""
Script to download database files from cloud storage on app startup
"""

import os
import requests
import sqlite3
import hashlib
from pathlib import Path
import time

def validate_sqlite_database(file_path):
    """Validate that a file is a proper SQLite database."""
    try:
        # Try to open and query the database
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        
        # Check if we can read the schema
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        conn.close()
        
        if not tables:
            print(f"⚠️ {file_path} has no tables - may be corrupted")
            return False
            
        print(f"✅ {file_path} validated successfully ({len(tables)} tables found)")
        return True
        
    except Exception as e:
        print(f"❌ {file_path} validation failed: {e}")
        return False

def download_file_with_retry(url, file_path, max_retries=3):
    """Download a file with retry logic and validation."""
    for attempt in range(max_retries):
        try:
            print(f"Downloading {file_path} (attempt {attempt + 1}/{max_retries})...")
            
            # Use a larger chunk size for better performance
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type:
                print(f"❌ Got HTML response instead of database file")
                print(f"Content-Type: {content_type}")
                return False
            
            # Get expected file size
            content_length = response.headers.get('content-length')
            if content_length:
                expected_size = int(content_length)
                print(f"Expected file size: {expected_size} bytes")
            
            # Download with progress tracking
            downloaded_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=65536):  # Larger chunks
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
            
            # Verify file size
            actual_size = os.path.getsize(file_path)
            print(f"✅ Downloaded {file_path} ({actual_size} bytes)")
            
            # Validate the database
            if validate_sqlite_database(file_path):
                return True
            else:
                print(f"❌ Database validation failed for {file_path}")
                os.remove(file_path)
                return False
                
        except Exception as e:
            print(f"❌ Download attempt {attempt + 1} failed: {e}")
            if os.path.exists(file_path):
                os.remove(file_path)
            
            if attempt < max_retries - 1:
                print(f"Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print(f"❌ All download attempts failed for {file_path}")
                return False
    
    return False

def download_database_files():
    """Download database files from cloud storage if they don't exist locally."""
    
    # Database file paths
    reddit_db_path = "reddit.db"
    analysis_db_path = "analysis.db"
    
    # Cloud storage URLs
    REDDIT_DB_URL = os.getenv('REDDIT_DB_URL', '')
    ANALYSIS_DB_URL = os.getenv('ANALYSIS_DB_URL', '')
    
    print("=== Database Download Process ===")
    
    # Download reddit.db if it doesn't exist
    if not os.path.exists(reddit_db_path) and REDDIT_DB_URL:
        if not download_file_with_retry(REDDIT_DB_URL, reddit_db_path):
            print(f"❌ Failed to download reddit.db from {REDDIT_DB_URL}")
    elif os.path.exists(reddit_db_path):
        print(f"📁 reddit.db already exists, validating...")
        if not validate_sqlite_database(reddit_db_path):
            print(f"❌ Existing reddit.db is corrupted, removing...")
            os.remove(reddit_db_path)
            if REDDIT_DB_URL:
                download_file_with_retry(REDDIT_DB_URL, reddit_db_path)
    
    # Download analysis.db if it doesn't exist
    if not os.path.exists(analysis_db_path) and ANALYSIS_DB_URL:
        if not download_file_with_retry(ANALYSIS_DB_URL, analysis_db_path):
            print(f"❌ Failed to download analysis.db from {ANALYSIS_DB_URL}")
    elif os.path.exists(analysis_db_path):
        print(f"📁 analysis.db already exists, validating...")
        if not validate_sqlite_database(analysis_db_path):
            print(f"❌ Existing analysis.db is corrupted, removing...")
            os.remove(analysis_db_path)
            if ANALYSIS_DB_URL:
                download_file_with_retry(ANALYSIS_DB_URL, analysis_db_path)
    
    # Final validation check
    print("=== Final Database Status ===")
    for db_path in [reddit_db_path, analysis_db_path]:
        if os.path.exists(db_path):
            if validate_sqlite_database(db_path):
                print(f"✅ {db_path} is ready for use")
            else:
                print(f"❌ {db_path} is corrupted and unusable")
        else:
            print(f"⚠️ {db_path} not found")

if __name__ == "__main__":
    download_database_files() 