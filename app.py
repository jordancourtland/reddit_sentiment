from flask import Flask, render_template, jsonify
import sqlite3
from datetime import datetime
import json
from analysis_db import AnalysisDB
import os

app = Flask(__name__)
analysis_db = AnalysisDB()

def get_db_connection():
    try:
        conn = sqlite3.connect('reddit.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/posts')
def get_posts():
    try:
        # Connect to the reddit.db database
        conn = get_db_connection()
        print("Connected to reddit.db")
        
        # Get all posts from reddit.db
        posts = conn.execute('''
            SELECT * FROM reddit_posts
            ORDER BY created_utc DESC
        ''').fetchall()
        
        posts_list = [dict(post) for post in posts]
        print(f"Found {len(posts_list)} posts in reddit.db")
        
        # If we have posts, try to enrich them with analysis data
        if posts_list:
            try:
                # Create a connection to analysis.db
                with sqlite3.connect('analysis.db') as analysis_conn:
                    analysis_conn.row_factory = sqlite3.Row
                    for post in posts_list:
                        # Look up analysis for this post
                        analysis = analysis_conn.execute('''
                            SELECT * FROM thread_analyses 
                            WHERE thread_id = ?
                        ''', (post['id'],)).fetchone()
                        
                        if analysis:
                            analysis_dict = dict(analysis)
                            # Add analysis data to post
                            post['op_summary'] = analysis_dict.get('op_summary')
                            post['responses_summary'] = analysis_dict.get('responses_summary')
                            post['persona_fit'] = analysis_dict.get('persona_fit')
                            post['confidence'] = analysis_dict.get('confidence')
                            post['fit_explanation'] = analysis_dict.get('fit_explanation')
                            post['denial_type'] = analysis_dict.get('denial_type')
                            # Parse JSON fields
                            if analysis_dict.get('themes'):
                                post['themes'] = json.loads(analysis_dict.get('themes'))
                            else:
                                post['themes'] = []
                            post['outcome'] = analysis_dict.get('outcome')
                            if analysis_dict.get('options_suggested'):
                                post['options_suggested'] = json.loads(analysis_dict.get('options_suggested'))
                            else:
                                post['options_suggested'] = []
                        else:
                            # Add empty analysis fields
                            post['op_summary'] = None
                            post['responses_summary'] = None
                            post['persona_fit'] = None
                            post['confidence'] = None
                            post['fit_explanation'] = None
                            post['denial_type'] = None
                            post['themes'] = []
                            post['outcome'] = None
                            post['options_suggested'] = []
            except Exception as e:
                print(f"Error enriching posts with analysis data: {str(e)}")
                # Continue without analysis data
                
        return jsonify(posts_list)
    except Exception as e:
        print(f"Error in get_posts: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/comments/<post_id>')
def get_comments(post_id):
    try:
        conn = get_db_connection()
        
        # Fetch the original post first
        post = conn.execute('''
            SELECT * FROM reddit_posts 
            WHERE id = ?
        ''', (post_id,)).fetchone()
        
        # Fetch all comments for this post
        comments = conn.execute('''
            SELECT * FROM reddit_comments 
            WHERE post_id = ? 
            ORDER BY created_utc ASC
        ''', (post_id,)).fetchall()
        
        # Return both the post and comments
        response = {
            'post': dict(post) if post else None,
            'comments': [dict(comment) for comment in comments]
        }
        
        return jsonify(response)
    except Exception as e:
        print(f"Error in get_comments: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/stats')
def get_stats():
    try:
        # Get analysis statistics
        analysis_stats = analysis_db.get_analysis_stats()
        
        # Get post statistics
        conn = get_db_connection()
        post_stats = conn.execute('''
            SELECT 
                COUNT(*) as total_posts,
                COUNT(DISTINCT subreddit) as total_subreddits,
                AVG(score) as avg_score,
                AVG(num_comments) as avg_comments
            FROM reddit_posts
        ''').fetchone()
        
        stats = {
            'analysis': analysis_stats,
            'posts': dict(post_stats)
        }
        
        return jsonify(stats)
    except Exception as e:
        print(f"Error in get_stats: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True) 