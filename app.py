from flask import Flask, render_template, jsonify
import sqlite3
from datetime import datetime
import traceback

app = Flask(__name__)

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
        conn = get_db_connection()
        cursor = conn.execute('''
            SELECT 
                id,
                subreddit,
                datetime(created_utc, 'unixepoch') as created_at,
                title,
                selftext,
                url,
                score,
                num_comments,
                keyword_tag
            FROM reddit_posts
            ORDER BY created_utc DESC
        ''')
        
        # Debug: Print raw results
        posts = cursor.fetchall()
        print(f"Raw SQL results: {len(posts)} posts found")
        if len(posts) > 0:
            print("First post raw data:", dict(posts[0]))
        
        # Convert to list of dicts
        posts_list = [dict(post) for post in posts]
        print(f"Converted to list: {len(posts_list)} posts")
        if len(posts_list) > 0:
            print("First post converted:", posts_list[0])
        
        conn.close()
        return jsonify(posts_list)
    except Exception as e:
        print(f"Error in get_posts: {str(e)}")
        print("Traceback:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/comments/<post_id>')
def get_comments(post_id):
    try:
        conn = get_db_connection()
        comments = conn.execute('''
            SELECT 
                id,
                post_id,
                parent_id,
                author,
                body,
                datetime(created_utc, 'unixepoch') as created_at,
                score
            FROM reddit_comments
            WHERE post_id = ?
            ORDER BY created_utc DESC
        ''', (post_id,)).fetchall()
        conn.close()
        
        return jsonify([dict(comment) for comment in comments])
    except Exception as e:
        print(f"Error in get_comments: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001) 