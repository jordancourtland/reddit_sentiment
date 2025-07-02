from flask import Flask, render_template, jsonify, request, send_file
import sqlite3
from datetime import datetime
import json
import csv
import os
from analysis_db import AnalysisDB

# Create Flask app
app = Flask(__name__)

# Initialize database
db = AnalysisDB()

@app.route('/')
def index():
    """Main page showing analysis results."""
    return render_template('index.html')

@app.route('/api/threads')
def get_threads():
    """API endpoint to get analyzed threads."""
    try:
        threads = db.get_analyzed_threads()
        return jsonify(threads)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """API endpoint to get analysis statistics."""
    try:
        stats = db.get_analysis_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True) 