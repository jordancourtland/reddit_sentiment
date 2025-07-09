import os
import time
import random
import logging
from dotenv import load_dotenv
from thread_analyzer import ThreadAnalyzer
from analysis_db import AnalysisDB
import sqlite3

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analysis.log'),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

def analyze_threads(batch_size=10, max_threads=None, delay_between_batches=20):
    """Main function to analyze threads with patient experience framework."""
    
    # Get API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print('Error: GEMINI_API_KEY not found in environment variables')
        return
    
    # Initialize analyzer and database
    analyzer = ThreadAnalyzer(api_key)
    db = AnalysisDB()
    
    # Get unanalyzed threads (simpler approach)
    reddit_con = sqlite3.connect('reddit.db')
    analysis_con = sqlite3.connect('analysis.db')
    
    # Get all analyzed thread IDs
    analyzed_ids = analysis_con.execute('SELECT thread_id FROM thread_analyses').fetchall()
    analyzed_ids = [row[0] for row in analyzed_ids]
    
    # Get all posts
    all_posts = reddit_con.execute('''
        SELECT id, title, subreddit, created_utc, score, num_comments, 
               selftext, keyword_tag
        FROM reddit_posts
        ORDER BY created_utc DESC
    ''').fetchall()
    
    # Filter out already analyzed posts
    unanalyzed_threads = []
    for post in all_posts:
        if post[0] not in analyzed_ids:
            unanalyzed_threads.append(post)
            if max_threads and len(unanalyzed_threads) >= max_threads:
                break
    
    reddit_con.close()
    analysis_con.close()
    
    print(f"Found {len(unanalyzed_threads)} unanalyzed threads")
    
    if not unanalyzed_threads:
        print("No unanalyzed threads found!")
        return
    
    # Process threads in batches
    successful = 0
    failed = 0
    batch_num = 1
    
    for i, thread in enumerate(unanalyzed_threads, 1):
        thread_dict = {
            'id': thread[0],
            'title': thread[1],
            'subreddit': thread[2],
            'created_utc': thread[3],
            'score': thread[4],
            'num_comments': thread[5],
            'selftext': thread[6],
            'keyword_tag': thread[7]
        }
        
        print(f"\nAnalyzing thread {i}/{len(unanalyzed_threads)}: {thread_dict['title'][:60]}...")
        print(f"  Subreddit: r/{thread_dict['subreddit']}")
        print(f"  Score: {thread_dict['score']}, Comments: {thread_dict['num_comments']}")
        
        try:
            # Add delay to respect rate limits
            time.sleep(random.uniform(2.0, 4.0))
            
            # Analyze with patient experience framework
            analysis = analyzer.analyze_thread(thread_dict)
            
            if analysis:
                # Store the analysis
                success = db.store_analysis(thread_dict['id'], analysis)
                if success:
                    successful += 1
                    print(f"  ✅ Successfully analyzed")
                    print(f"     Patient Phase: {analysis.get('patient_phase')}")
                    print(f"     Denial Category: {analysis.get('denial_category')}")
                    print(f"     Touchpoints: {analysis.get('touchpoints', [])}")
                    print(f"     Players: {analysis.get('players', [])}")
                    print(f"     Sentiment: {analysis.get('sentiment_score', 0):.2f}")
                else:
                    failed += 1
                    print(f"  ❌ Failed to store analysis")
            else:
                failed += 1
                print(f"  ❌ Failed to analyze thread")
                
        except Exception as e:
            failed += 1
            print(f"  ❌ Error: {str(e)}")
        
        # Progress update and batch handling
        if i % batch_size == 0:
            print(f"\n--- Batch {batch_num} Complete: {i}/{len(unanalyzed_threads)} threads processed ---")
            print(f"Successful: {successful}, Failed: {failed}")
            
            if i < len(unanalyzed_threads):
                print(f"Waiting {delay_between_batches} seconds before next batch...")
                time.sleep(delay_between_batches)
            
            batch_num += 1
    
    print(f"\n=== Analysis Complete ===")
    print(f"Total processed: {len(unanalyzed_threads)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(successful/len(unanalyzed_threads)*100):.1f}%")

if __name__ == "__main__":
    # Analyze 2000 threads with patient experience framework
    analyze_threads(batch_size=10, max_threads=2000, delay_between_batches=20) 