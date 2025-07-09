#!/usr/bin/env python3
"""
Script to download database files from cloud storage on app startup
"""

import os
import requests
import sqlite3
from pathlib import Path

def download_database_files():
    """Download analysis.db from cloud storage if it doesn't exist locally."""
    
    # Database file path
    analysis_db_path = "analysis.db"
    
    # Cloud storage URL for analysis.db
    ANALYSIS_DB_URL = os.getenv('ANALYSIS_DB_URL', '')
    
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
    
    # Check if analysis.db exists and is valid
    if os.path.exists(analysis_db_path):
        try:
            conn = sqlite3.connect(analysis_db_path)
            conn.close()
            print("✅ analysis.db is valid")
        except Exception as e:
            print(f"❌ analysis.db is corrupted: {e}")
    else:
        print("⚠️ analysis.db not found")

if __name__ == "__main__":
    download_database_files() 