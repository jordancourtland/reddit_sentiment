import sqlite3
import json
from datetime import datetime
import os
import logging

class AnalysisDB:
    def __init__(self, analysis_db_path='analysis.db', reddit_db_path='reddit.db'):
        self.analysis_db_path = analysis_db_path
        self.reddit_db_path = reddit_db_path
        self._init_db()

    def _init_db(self):
        """Initialize the analysis database with required tables."""
        try:
            with sqlite3.connect(self.analysis_db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS thread_analyses (
                        thread_id TEXT PRIMARY KEY,
                        analysis_timestamp DATETIME,
                        op_summary TEXT,
                        responses_summary TEXT,
                        persona_fit FLOAT,
                        confidence FLOAT,
                        fit_explanation TEXT,
                        denial_type TEXT,
                        themes TEXT,
                        outcome TEXT,
                        options_suggested TEXT
                    )
                ''')
                conn.commit()
            logging.info(f"Analysis database initialized at {self.analysis_db_path}")
        except Exception as e:
            logging.error(f"Error initializing database: {str(e)}")
            raise

    def get_unanalyzed_threads(self, limit=10):
        """Get threads that haven't been analyzed yet."""
        try:
            # Check if both databases exist
            if not os.path.exists(self.reddit_db_path):
                logging.error(f"Reddit database not found at {self.reddit_db_path}")
                return []
                
            if not os.path.exists(self.analysis_db_path):
                logging.error(f"Analysis database not found at {self.analysis_db_path}")
                return []
            
            # Connect to both databases
            with sqlite3.connect(self.reddit_db_path) as reddit_conn, \
                 sqlite3.connect(self.analysis_db_path) as analysis_conn:
                
                reddit_conn.row_factory = sqlite3.Row
                analysis_conn.row_factory = sqlite3.Row
                
                # Get analyzed thread IDs
                analyzed_ids = set(row['thread_id'] for row in analysis_conn.execute('SELECT thread_id FROM thread_analyses'))
                logging.info(f"Found {len(analyzed_ids)} already analyzed threads")
                
                # First, let's check how many total posts we have
                try:
                    total_posts = reddit_conn.execute('SELECT COUNT(*) FROM reddit_posts').fetchone()[0]
                    logging.info(f"Total posts in reddit.db: {total_posts}")
                except sqlite3.OperationalError as e:
                    logging.error(f"Error counting posts: {str(e)}")
                    return []
                
                # Get unanalyzed threads from reddit database
                try:
                    if analyzed_ids:
                        query = '''
                            SELECT p.*, 
                                   GROUP_CONCAT(c.body) as comments,
                                   GROUP_CONCAT(c.created_utc) as comment_timestamps
                            FROM reddit_posts p
                            LEFT JOIN reddit_comments c ON p.id = c.post_id
                            WHERE p.id NOT IN ({})
                            GROUP BY p.id
                            LIMIT ?
                        '''.format(','.join('?' * len(analyzed_ids)))
                        params = list(analyzed_ids) + [limit]
                    else:
                        query = '''
                            SELECT p.*, 
                                   GROUP_CONCAT(c.body) as comments,
                                   GROUP_CONCAT(c.created_utc) as comment_timestamps
                            FROM reddit_posts p
                            LEFT JOIN reddit_comments c ON p.id = c.post_id
                            GROUP BY p.id
                            LIMIT ?
                        '''
                        params = [limit]
                    
                    logging.debug(f"Query: {query}")
                    logging.debug(f"Parameters: {params}")
                    
                    cursor = reddit_conn.execute(query, params)
                    results = []
                    for row in cursor.fetchall():
                        thread = dict(row)
                        # Format comments with timestamps if available
                        if thread.get('comments'):
                            comments = thread['comments'].split(',')
                            timestamps = thread['comment_timestamps'].split(',') if thread.get('comment_timestamps') else []
                            formatted_comments = []
                            for i, comment in enumerate(comments):
                                timestamp = timestamps[i] if i < len(timestamps) else ''
                                if timestamp:
                                    formatted_comments.append(f"[{datetime.fromtimestamp(int(timestamp)).isoformat()}] {comment}")
                                else:
                                    formatted_comments.append(comment)
                            thread['comments'] = '\n'.join(formatted_comments)
                        else:
                            thread['comments'] = ''
                        results.append(thread)
                    
                    logging.info(f"Found {len(results)} unanalyzed threads")
                    return results
                except sqlite3.OperationalError as e:
                    logging.error(f"Error executing query: {str(e)}")
                    return []
        except Exception as e:
            logging.error(f"Unexpected error in get_unanalyzed_threads: {str(e)}")
            return []

    def store_analysis(self, thread_id, analysis_result):
        """Store the analysis results for a thread."""
        try:
            with sqlite3.connect(self.analysis_db_path) as conn:
                # Log what we're storing
                logging.debug(f"Storing analysis for thread {thread_id}")
                
                conn.execute('''
                    INSERT OR REPLACE INTO thread_analyses (
                        thread_id,
                        analysis_timestamp,
                        op_summary,
                        responses_summary,
                        persona_fit,
                        confidence,
                        fit_explanation,
                        denial_type,
                        themes,
                        outcome,
                        options_suggested
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    thread_id,
                    datetime.now().isoformat(),
                    analysis_result['op_summary'],
                    analysis_result['responses_summary'],
                    analysis_result['persona_fit'],
                    analysis_result['confidence'],
                    analysis_result['fit_explanation'],
                    analysis_result['denial_type'],
                    json.dumps(analysis_result['themes']),
                    analysis_result['outcome'],
                    json.dumps(analysis_result['options_suggested'])
                ))
                conn.commit()
                logging.info(f"Successfully stored analysis for thread {thread_id}")
                return True
        except Exception as e:
            logging.error(f"Error storing analysis for thread {thread_id}: {str(e)}")
            return False

    def get_analysis(self, thread_id):
        """Get the analysis results for a specific thread."""
        try:
            with sqlite3.connect(self.analysis_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT * FROM thread_analyses WHERE thread_id = ?
                ''', (thread_id,))
                row = cursor.fetchone()
                if row:
                    result = dict(row)
                    result['themes'] = json.loads(result['themes'])
                    result['options_suggested'] = json.loads(result['options_suggested'])
                    return result
                return None
        except Exception as e:
            logging.error(f"Error retrieving analysis for thread {thread_id}: {str(e)}")
            return None

    def get_analysis_stats(self):
        """Get statistics about the analysis process."""
        try:
            with sqlite3.connect(self.analysis_db_path) as conn:
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_analyzed,
                        COALESCE(AVG(persona_fit), 0) as avg_persona_fit,
                        COALESCE(AVG(confidence), 0) as avg_confidence
                    FROM thread_analyses
                ''')
                row = cursor.fetchone()
                if row:
                    return {
                        'total_analyzed': row[0],
                        'avg_persona_fit': row[1] or 0,
                        'avg_confidence': row[2] or 0
                    }
                return {
                    'total_analyzed': 0,
                    'avg_persona_fit': 0,
                    'avg_confidence': 0
                }
        except Exception as e:
            logging.error(f"Error getting analysis stats: {str(e)}")
            return {
                'total_analyzed': 0,
                'avg_persona_fit': 0,
                'avg_confidence': 0,
                'error': str(e)
            }

    def get_analyzed_threads(self, limit=50):
        """Get threads that have been analyzed, with their analysis results."""
        try:
            # Check if both databases exist
            if not os.path.exists(self.reddit_db_path):
                logging.error(f"Reddit database not found at {self.reddit_db_path}")
                return []
                
            if not os.path.exists(self.analysis_db_path):
                logging.error(f"Analysis database not found at {self.analysis_db_path}")
                return []
            
            # Connect to both databases
            with sqlite3.connect(self.reddit_db_path) as reddit_conn, \
                 sqlite3.connect(self.analysis_db_path) as analysis_conn:
                
                reddit_conn.row_factory = sqlite3.Row
                analysis_conn.row_factory = sqlite3.Row
                
                # Get analyzed threads with their analysis results
                query = '''
                    SELECT 
                        a.thread_id,
                        a.analysis_timestamp,
                        a.op_summary,
                        a.responses_summary,
                        a.persona_fit,
                        a.confidence,
                        a.fit_explanation,
                        a.denial_type,
                        a.themes,
                        a.outcome,
                        a.options_suggested,
                        p.title,
                        p.subreddit,
                        p.created_utc,
                        p.score,
                        p.num_comments,
                        p.selftext
                    FROM thread_analyses a
                    LEFT JOIN reddit_posts p ON a.thread_id = p.id
                    ORDER BY a.analysis_timestamp DESC
                    LIMIT ?
                '''
                
                cursor = analysis_conn.execute(query, (limit,))
                results = []
                for row in cursor.fetchall():
                    thread = dict(row)
                    # Parse JSON fields
                    thread['themes'] = json.loads(thread['themes'])
                    thread['options_suggested'] = json.loads(thread['options_suggested'])
                    results.append(thread)
                
                logging.info(f"Retrieved {len(results)} analyzed threads")
                return results
                
        except Exception as e:
            logging.error(f"Error getting analyzed threads: {str(e)}")
            return [] 