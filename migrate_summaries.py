#!/usr/bin/env python3
"""
Migration script to update the thread_analyses table with separate op_summary and responses_summary fields
"""

import sqlite3
import logging
import os
from datetime import datetime
from openai import OpenAI
import json
import time
import random
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not OPENAI_API_KEY:
    logging.error("OPENAI_API_KEY not found in environment variables")
    exit(1)

def migrate_summaries():
    """Migrate existing single summary to dual summaries"""
    
    # Check if analysis.db exists
    if not os.path.exists('analysis.db'):
        logging.error("analysis.db not found")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect('analysis.db')
        conn.row_factory = sqlite3.Row
        
        # First, check if we need to alter the table structure
        cursor = conn.execute("PRAGMA table_info(thread_analyses)")
        columns = [column['name'] for column in cursor.fetchall()]
        
        # Check if the new columns already exist
        if 'op_summary' in columns and 'responses_summary' in columns:
            logging.info("Database schema already updated with op_summary and responses_summary")
        else:
            # Add new columns
            logging.info("Adding new columns to the schema")
            conn.execute("ALTER TABLE thread_analyses ADD COLUMN op_summary TEXT")
            conn.execute("ALTER TABLE thread_analyses ADD COLUMN responses_summary TEXT")
            conn.commit()
        
        # Get all analyses that have a summary but no op_summary/responses_summary
        cursor = conn.execute("""
            SELECT thread_id, summary FROM thread_analyses 
            WHERE (op_summary IS NULL OR responses_summary IS NULL) AND summary IS NOT NULL
        """)
        analyses = cursor.fetchall()
        
        if not analyses:
            logging.info("No analyses found that need migration")
            return True
        
        logging.info(f"Found {len(analyses)} analyses to migrate")
        
        # Connect to reddit.db to get the original posts and comments
        reddit_conn = sqlite3.connect('reddit.db')
        reddit_conn.row_factory = sqlite3.Row
        
        migrated_count = 0
        
        for analysis in analyses:
            thread_id = analysis['thread_id']
            current_summary = analysis['summary']
            
            # Fetch the original post and comments
            post = reddit_conn.execute("""
                SELECT * FROM reddit_posts WHERE id = ?
            """, (thread_id,)).fetchone()
            
            if not post:
                logging.warning(f"Could not find post {thread_id} in reddit.db")
                continue
            
            # Try to split the existing summary
            try:
                # If there are existing op_summary or responses_summary, skip
                existing = conn.execute("""
                    SELECT op_summary, responses_summary FROM thread_analyses WHERE thread_id = ?
                """, (thread_id,)).fetchone()
                
                if existing and existing['op_summary'] and existing['responses_summary']:
                    logging.info(f"Thread {thread_id} already has both summaries, skipping")
                    continue
                
                # Try to use OpenAI to split the summary
                logging.info(f"Splitting summary for thread {thread_id}")
                
                # Simple splitting logic - call OpenAI to split the summary
                split_result = split_summary_with_openai(thread_id, current_summary, dict(post))
                
                if split_result:
                    op_summary, responses_summary = split_result
                    
                    # Update the database
                    conn.execute("""
                        UPDATE thread_analyses 
                        SET op_summary = ?, responses_summary = ? 
                        WHERE thread_id = ?
                    """, (op_summary, responses_summary, thread_id))
                    conn.commit()
                    
                    migrated_count += 1
                    logging.info(f"Successfully migrated thread {thread_id}")
                else:
                    # If splitting failed, use the entire summary as op_summary
                    conn.execute("""
                        UPDATE thread_analyses 
                        SET op_summary = ?, responses_summary = ? 
                        WHERE thread_id = ?
                    """, (current_summary, "No response summary available", thread_id))
                    conn.commit()
                    logging.warning(f"Used current summary as op_summary for {thread_id}")
                    migrated_count += 1
                
                # Add a small delay to avoid rate limits
                time.sleep(random.uniform(0.5, 1.0))
                
            except Exception as e:
                logging.error(f"Error migrating thread {thread_id}: {str(e)}")
                continue
        
        logging.info(f"Migration complete. Migrated {migrated_count} out of {len(analyses)} analyses")
        
        # Close connections
        conn.close()
        reddit_conn.close()
        
        return True
        
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        return False

def split_summary_with_openai(thread_id, current_summary, post):
    """Use OpenAI to split the existing summary into op_summary and responses_summary"""
    try:
        # Format the prompt
        prompt = f"""Given the following information about a Reddit thread about healthcare insurance denials:

Thread ID: {thread_id}
Title: {post.get('title', 'Unknown')}
Original Post: {post.get('selftext', 'Unknown')}
Current Summary: {current_summary}

Please split this summary into two parts:
1. A summary of what the original poster was asking or needed (1-2 sentences)
2. A summary of the key community responses/advice (1-2 sentences)

Format your response as a valid JSON object with these two fields:
{{
  "op_summary": "1-2 sentence summary of what OP was asking",
  "responses_summary": "1-2 sentence summary of key advice/responses"
}}
"""

        # Call OpenAI API
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes Reddit threads."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        # Parse the response - add null check
        content = response.choices[0].message.content
        if content is None:
            logging.warning(f"Received empty response from OpenAI for thread {thread_id}")
            return None
            
        content = content.strip()
        
        # Ensure it's valid JSON
        if not (content.startswith('{') and content.endswith('}')):
            logging.warning(f"Response is not properly formatted JSON: {content}")
            return None
            
        try:
            result = json.loads(content)
            
            if 'op_summary' not in result or 'responses_summary' not in result:
                logging.warning(f"Missing required fields in response: {content}")
                return None
                
            return result['op_summary'], result['responses_summary']
            
        except json.JSONDecodeError as e:
            logging.warning(f"Failed to parse JSON response: {str(e)}")
            return None
            
    except Exception as e:
        logging.error(f"Error calling OpenAI for thread {thread_id}: {str(e)}")
        return None

if __name__ == "__main__":
    logging.info("Starting summary migration")
    success = migrate_summaries()
    if success:
        logging.info("Migration completed successfully")
    else:
        logging.error("Migration failed") 