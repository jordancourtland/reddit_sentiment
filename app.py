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
    """Main page showing posts with analysis."""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page with charts and analytics."""
    return render_template('dashboard.html')

@app.route('/api/threads')
def get_threads():
    """API endpoint to get all threads with optional analysis data, pagination, search, and filtering."""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        offset = (page - 1) * per_page
        # Filters
        search = request.args.get('search', '').strip()
        subreddit = request.args.get('subreddit', '').strip()
        patient_phase = request.args.get('patient_phase', '').strip()
        denial_category = request.args.get('denial_category', '').strip()
        outcome = request.args.get('outcome', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        # Build SQL query for reddit_posts only
        base_query = '''
            SELECT id, title, subreddit, created_utc, score, num_comments, 
                   selftext, keyword_tag, url
            FROM reddit_posts
            WHERE 1=1
        '''
        params = []
        if search:
            base_query += ' AND (title LIKE ? OR selftext LIKE ?)' 
            params.extend([f'%{search}%', f'%{search}%'])
        if subreddit:
            base_query += ' AND subreddit = ?'
            params.append(subreddit)
        if date_from:
            base_query += ' AND created_utc >= ?'
            from datetime import datetime
            dt_from = int(datetime.strptime(date_from, '%Y-%m-%d').timestamp())
            params.append(dt_from)
        if date_to:
            base_query += ' AND created_utc <= ?'
            from datetime import datetime, timedelta
            dt_to = int((datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)).timestamp())
            params.append(dt_to)
        # Get total count (for pagination)
        count_query = 'SELECT COUNT(*) FROM (' + base_query + ') as sub'
        reddit_con = sqlite3.connect('reddit.db')
        reddit_con.row_factory = sqlite3.Row
        total_posts = reddit_con.execute(count_query, params).fetchone()[0]
        # Add ordering and pagination
        base_query += ' ORDER BY created_utc DESC LIMIT ? OFFSET ?'
        params.extend([per_page, offset])
        posts = [dict(row) for row in reddit_con.execute(base_query, params).fetchall()]
        reddit_con.close()
        # Get analysis data for each post from analysis.db
        analysis_con = sqlite3.connect('analysis.db')
        analysis_con.row_factory = sqlite3.Row
        filtered_posts = []
        for post in posts:
            analysis = analysis_con.execute('''
                SELECT persona_fit, confidence, denial_type, denial_category, 
                       themes, outcome, op_summary, responses_summary, patient_phase,
                       touchpoints, players, sentiment_score, experience_rating,
                       pain_points, positive_aspects, treatment_mentions, 
                       support_program_mentions, keyword_tag
                FROM thread_analyses WHERE thread_id = ?
            ''', (post['id'],)).fetchone()
            if analysis:
                post.update(dict(analysis))
            else:
                # Add null values for unanalyzed posts
                post.update({
                    'persona_fit': None,
                    'confidence': None,
                    'denial_type': None,
                    'denial_category': None,
                    'themes': None,
                    'outcome': None,
                    'op_summary': None,
                    'responses_summary': None,
                    'patient_phase': None,
                    'touchpoints': None,
                    'players': None,
                    'sentiment_score': None,
                    'experience_rating': None,
                    'pain_points': None,
                    'positive_aspects': None,
                    'treatment_mentions': None,
                    'support_program_mentions': None,
                    'keyword_tag': None
                })
            # Apply analysis filters after merging
            if (
                (not patient_phase or (post['patient_phase'] == patient_phase)) and
                (not denial_category or (post['denial_category'] == denial_category)) and
                (not outcome or (post['outcome'] == outcome))
            ):
                filtered_posts.append(post)
        analysis_con.close()
        return jsonify({
            "threads": filtered_posts,
            "total_posts": total_posts,
            "page": page,
            "per_page": per_page
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """API endpoint to get analysis statistics."""
    try:
        stats = db.get_analysis_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics')
def get_analytics():
    """API endpoint for dashboard analytics."""
    try:
        # Connect to databases
        reddit_con = sqlite3.connect('reddit.db')
        analysis_con = sqlite3.connect('analysis.db')
        
        # Basic stats
        total_posts = reddit_con.execute('SELECT COUNT(*) FROM reddit_posts').fetchone()[0]
        total_analyzed = analysis_con.execute('SELECT COUNT(*) FROM thread_analyses').fetchone()[0]
        
        # Denial type distribution (handle null values)
        denial_types_result = analysis_con.execute('''
            SELECT 
                COALESCE(denial_type, 'Unknown') as denial_type, 
                COUNT(*) as count 
            FROM thread_analyses 
            GROUP BY COALESCE(denial_type, 'Unknown')
            ORDER BY count DESC
        ''').fetchall()
        
        denial_types = []
        for row in denial_types_result:
            denial_types.append({
                'denial_type': row[0],
                'count': row[1]
            })
        
        # Subreddit distribution
        subreddits_result = reddit_con.execute('''
            SELECT subreddit, COUNT(*) as count 
            FROM reddit_posts 
            GROUP BY subreddit 
            ORDER BY count DESC 
            LIMIT 10
        ''').fetchall()
        
        subreddits = []
        for row in subreddits_result:
            subreddits.append({
                'subreddit': row[0],
                'count': row[1]
            })
        
        # Average scores
        avg_scores_result = reddit_con.execute('''
            SELECT AVG(score) as avg_score, AVG(num_comments) as avg_comments 
            FROM reddit_posts
        ''').fetchone()
        
        avg_score = avg_scores_result[0] if avg_scores_result[0] is not None else 0
        avg_comments = avg_scores_result[1] if avg_scores_result[1] is not None else 0
        
        reddit_con.close()
        analysis_con.close()
        
        return jsonify({
            'total_posts': total_posts,
            'total_analyzed': total_analyzed,
            'denial_types': denial_types,
            'subreddits': subreddits,
            'avg_score': avg_score,
            'avg_comments': avg_comments
        })
    except Exception as e:
        print(f"Analytics error: {str(e)}")  # Debug print
        return jsonify({'error': str(e)}), 500

@app.route('/api/patient-analytics')
def get_patient_analytics():
    """API endpoint for patient experience analytics."""
    try:
        analysis_con = sqlite3.connect('analysis.db')
        
        # Check if new columns exist
        cursor = analysis_con.execute("PRAGMA table_info(thread_analyses)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Patient phase distribution (only if column exists)
        phase_distribution = []
        if 'patient_phase' in columns:
            phase_rows = analysis_con.execute('''
                SELECT patient_phase, COUNT(*) as count 
                FROM thread_analyses 
                WHERE patient_phase IS NOT NULL 
                GROUP BY patient_phase 
                ORDER BY 
                    CASE patient_phase
                        WHEN 'Symptom Onset' THEN 1
                        WHEN 'Assessment & Diagnosis' THEN 2
                        WHEN 'Treatment Options' THEN 3
                        WHEN 'Pretreatment & Prescription' THEN 4
                        WHEN 'Insurance & Financial Support Determination' THEN 5
                        WHEN 'Enrollment' THEN 6
                        WHEN 'Initial Treatment' THEN 7
                        WHEN 'Maintaining Treatment' THEN 8
                        WHEN 'Ongoing Treatment' THEN 9
                        ELSE 10
                    END
            ''').fetchall()
            
            # Convert rows to dictionaries properly
            for row in phase_rows:
                phase_distribution.append({
                    'patient_phase': row[0],
                    'count': row[1]
                })
        
        # Phase sentiment aggregation
        phase_sentiment = []
        if 'patient_phase' in columns and 'sentiment_score' in columns:
            phase_sentiment_rows = analysis_con.execute('''
                SELECT patient_phase, AVG(sentiment_score) as avg_sentiment, COUNT(*) as count
                FROM thread_analyses
                WHERE patient_phase IS NOT NULL AND sentiment_score IS NOT NULL
                GROUP BY patient_phase
                ORDER BY 
                    CASE patient_phase
                        WHEN 'Symptom Onset' THEN 1
                        WHEN 'Assessment & Diagnosis' THEN 2
                        WHEN 'Treatment Options' THEN 3
                        WHEN 'Pretreatment & Prescription' THEN 4
                        WHEN 'Insurance & Financial Support Determination' THEN 5
                        WHEN 'Enrollment' THEN 6
                        WHEN 'Initial Treatment' THEN 7
                        WHEN 'Maintaining Treatment' THEN 8
                        WHEN 'Ongoing Treatment' THEN 9
                        ELSE 10
                    END
            ''').fetchall()
            phase_sentiment = [
                {'patient_phase': row[0], 'avg_sentiment': row[1], 'count': row[2]} for row in phase_sentiment_rows
            ]
        
        # Touchpoint effectiveness (only if columns exist)
        touchpoint_effectiveness = {}
        if 'touchpoints' in columns and 'sentiment_score' in columns:
            touchpoint_data = analysis_con.execute('''
                SELECT touchpoints, sentiment_score, COUNT(*) as count
                FROM thread_analyses 
                WHERE touchpoints IS NOT NULL AND sentiment_score IS NOT NULL
            ''').fetchall()
            
            # Process touchpoint data
            for row in touchpoint_data:
                try:
                    touchpoints = json.loads(row[0])
                    sentiment = row[1]
                    count = row[2]
                    
                    for touchpoint in touchpoints:
                        if touchpoint not in touchpoint_effectiveness:
                            touchpoint_effectiveness[touchpoint] = {'total_sentiment': 0, 'count': 0}
                        touchpoint_effectiveness[touchpoint]['total_sentiment'] += sentiment
                        touchpoint_effectiveness[touchpoint]['count'] += count
                except:
                    continue
            
            # Calculate average sentiment per touchpoint
            for touchpoint in touchpoint_effectiveness:
                if touchpoint_effectiveness[touchpoint]['count'] > 0:
                    touchpoint_effectiveness[touchpoint]['avg_sentiment'] = (
                        touchpoint_effectiveness[touchpoint]['total_sentiment'] / 
                        touchpoint_effectiveness[touchpoint]['count']
                    )
        
        # Player performance (only if columns exist)
        player_performance = {}
        if 'players' in columns and 'sentiment_score' in columns:
            player_data = analysis_con.execute('''
                SELECT players, sentiment_score, COUNT(*) as count
                FROM thread_analyses 
                WHERE players IS NOT NULL AND sentiment_score IS NOT NULL
            ''').fetchall()
            
            # Process player data
            for row in player_data:
                try:
                    players = json.loads(row[0])
                    sentiment = row[1]
                    count = row[2]
                    
                    for player in players:
                        if player not in player_performance:
                            player_performance[player] = {'total_sentiment': 0, 'count': 0}
                        player_performance[player]['total_sentiment'] += sentiment
                        player_performance[player]['count'] += count
                except:
                    continue
            
            # Calculate average sentiment per player
            for player in player_performance:
                if player_performance[player]['count'] > 0:
                    player_performance[player]['avg_sentiment'] = (
                        player_performance[player]['total_sentiment'] / 
                        player_performance[player]['count']
                    )
        
        # Denial analysis by phase (only if columns exist)
        denial_by_phase = []
        if 'patient_phase' in columns and 'denial_category' in columns:
            denial_rows = analysis_con.execute('''
                SELECT patient_phase, denial_category, COUNT(*) as count
                FROM thread_analyses 
                WHERE patient_phase IS NOT NULL 
                    AND denial_category IS NOT NULL
                    AND denial_category NOT IN ('None', 'N/A', 'Null')
                GROUP BY patient_phase, denial_category
                ORDER BY 
                    CASE patient_phase
                        WHEN 'Symptom Onset' THEN 1
                        WHEN 'Assessment & Diagnosis' THEN 2
                        WHEN 'Treatment Options' THEN 3
                        WHEN 'Pretreatment & Prescription' THEN 4
                        WHEN 'Insurance & Financial Support Determination' THEN 5
                        WHEN 'Enrollment' THEN 6
                        WHEN 'Initial Treatment' THEN 7
                        WHEN 'Maintaining Treatment' THEN 8
                        WHEN 'Ongoing Treatment' THEN 9
                        ELSE 10
                    END,
                    count DESC
            ''').fetchall()
            
            # Convert rows to dictionaries properly
            for row in denial_rows:
                denial_by_phase.append({
                    'patient_phase': row[0],
                    'denial_category': row[1],
                    'count': row[2]
                })
        
        # Resolution analysis (only if columns exist)
        resolution_data = []
        if 'denial_resolution' in columns:
            resolution_rows = analysis_con.execute('''
                SELECT denial_resolution, resolution_timeframe, COUNT(*) as count
                FROM thread_analyses 
                WHERE denial_resolution IS NOT NULL
                    AND denial_resolution NOT IN ('None', 'N/A', 'Null')
                GROUP BY denial_resolution, resolution_timeframe
            ''').fetchall()
            
            # Convert rows to dictionaries properly
            for row in resolution_rows:
                resolution_data.append({
                    'denial_resolution': row[0],
                    'resolution_timeframe': row[1],
                    'count': row[2]
                })
        
        analysis_con.close()
        
        return jsonify({
            'phase_distribution': phase_distribution,
            'phase_sentiment': phase_sentiment,
            'touchpoint_effectiveness': touchpoint_effectiveness,
            'player_performance': player_performance,
            'denial_by_phase': denial_by_phase,
            'resolution_data': resolution_data
        })
        
    except Exception as e:
        print(f"Patient analytics error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/all')
def export_all():
    """Export all analyzed threads."""
    try:
        # Create exports directory
        os.makedirs('exports', exist_ok=True)
        
        # Connect to databases
        reddit_con = sqlite3.connect('reddit.db')
        analysis_con = sqlite3.connect('analysis.db')
        
        # Get all analyzed threads with basic data
        query = '''
            SELECT 
                ta.thread_id,
                ta.persona_fit,
                ta.confidence,
                ta.denial_type,
                ta.themes,
                ta.outcome,
                ta.op_summary,
                ta.responses_summary,
                p.title,
                p.subreddit,
                p.created_utc,
                p.score,
                p.num_comments,
                p.selftext
            FROM thread_analyses ta
            LEFT JOIN reddit.db.reddit_posts p ON ta.thread_id = p.id
            ORDER BY ta.analysis_timestamp DESC
        '''
        
        # Try the complex query first, fallback to simple query
        try:
            threads = analysis_con.execute(query).fetchall()
        except:
            # Fallback: get analysis data only
            threads = analysis_con.execute('SELECT * FROM thread_analyses').fetchall()
        
        if not threads:
            return jsonify({'error': 'No analyzed threads found'}), 404
        
        # Export as CSV
        csv_file = os.path.join('exports', 'analyzed_threads.csv')
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if threads:
                # Get column names
                columns = [description[0] for description in analysis_con.execute('SELECT * FROM thread_analyses LIMIT 1').description]
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(threads)
        
        # Export summary
        summary_file = os.path.join('exports', 'analysis_summary.txt')
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"Reddit Sentiment Analysis Export\n")
            f.write(f"Export Date: {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total Threads Analyzed: {len(threads)}\n\n")
            
            # Calculate basic stats
            denial_types = {}
            for thread in threads:
                denial_type = thread[3] if len(thread) > 3 else 'Unknown'  # denial_type column
                denial_types[denial_type] = denial_types.get(denial_type, 0) + 1
            
            f.write("Denial Type Distribution:\n")
            for denial_type, count in denial_types.items():
                f.write(f"  {denial_type}: {count}\n")
        
        reddit_con.close()
        analysis_con.close()
        
        return jsonify({
            'message': f'Export completed successfully. {len(threads)} threads exported to exports/ directory.',
            'files_created': ['analyzed_threads.csv', 'analysis_summary.txt']
        })
        
    except Exception as e:
        print(f"Export error: {str(e)}")  # Debug print
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@app.route('/api/runs')
def get_runs():
    """Get all collection runs."""
    try:
        runs = db.get_collection_runs()
        return jsonify(runs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/threads/run/<run_id>')
def get_threads_by_run(run_id):
    """Get threads from a specific collection run."""
    try:
        threads = db.get_threads_by_run(run_id)
        return jsonify(threads)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/denial-categories')
def get_denial_categories():
    """API endpoint to get denial categories."""
    try:
        analysis_con = sqlite3.connect('analysis.db')
        cursor = analysis_con.execute("PRAGMA table_info(thread_analyses)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'denial_category' in columns:
            categories = analysis_con.execute('''
                SELECT denial_category, COUNT(*) as count 
                FROM thread_analyses 
                WHERE denial_category IS NOT NULL 
                GROUP BY denial_category 
                ORDER BY count DESC
            ''').fetchall()
            
            result = [{'category': row[0], 'count': row[1]} for row in categories]
        else:
            result = []
        
        analysis_con.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/touchpoint-analytics')
def get_touchpoint_analytics():
    """API endpoint for touchpoint analytics."""
    try:
        analysis_con = sqlite3.connect('analysis.db')
        
        # Touchpoint frequency distribution
        touchpoint_freq = analysis_con.execute('''
            SELECT 
                json_extract(touchpoints, '$[0]') as touchpoint,
                COUNT(*) as count
            FROM thread_analyses 
            WHERE touchpoints IS NOT NULL 
                AND json_extract(touchpoints, '$[0]') IS NOT NULL
                AND json_extract(touchpoints, '$[0]') != 'Null'
            GROUP BY touchpoint
            ORDER BY count DESC
        ''').fetchall()
        
        # Get all touchpoints from arrays
        all_touchpoints = analysis_con.execute('''
            SELECT touchpoints, sentiment_score, patient_phase, outcome, denial_category
            FROM thread_analyses 
            WHERE touchpoints IS NOT NULL
        ''').fetchall()
        
        # Process touchpoint data manually
        touchpoint_sentiment_data = []
        touchpoint_phase_data = []
        touchpoint_outcome_data = []
        touchpoint_denial_data = []
        
        for row in all_touchpoints:
            try:
                touchpoints = json.loads(row[0]) if row[0] else []
                sentiment_score = row[1]
                patient_phase = row[2]
                outcome = row[3]
                denial_category = row[4]
                
                for touchpoint in touchpoints:
                    if touchpoint and touchpoint != 'Null':
                        if sentiment_score is not None:
                            touchpoint_sentiment_data.append({
                                'touchpoint': touchpoint,
                                'sentiment_score': sentiment_score,
                                'count': 1
                            })
                        if patient_phase is not None:
                            touchpoint_phase_data.append({
                                'touchpoint': touchpoint,
                                'phase': patient_phase,
                                'count': 1
                            })
                        if outcome is not None:
                            touchpoint_outcome_data.append({
                                'touchpoint': touchpoint,
                                'outcome': outcome,
                                'count': 1
                            })
                        if denial_category is not None:
                            touchpoint_denial_data.append({
                                'touchpoint': touchpoint,
                                'denial_category': denial_category,
                                'count': 1
                            })
            except json.JSONDecodeError:
                continue
        
        analysis_con.close()
        
        return jsonify({
            'frequency': [{'touchpoint': row[0], 'count': row[1]} for row in touchpoint_freq],
            'sentiment': touchpoint_sentiment_data,
            'phase_heatmap': touchpoint_phase_data,
            'outcome': touchpoint_outcome_data,
            'denial': touchpoint_denial_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/player-analytics')
def get_player_analytics():
    """API endpoint for player analytics."""
    try:
        analysis_con = sqlite3.connect('analysis.db')
        
        # Player frequency distribution
        player_freq = analysis_con.execute('''
            SELECT 
                json_extract(players, '$[0]') as player,
                COUNT(*) as count
            FROM thread_analyses 
            WHERE players IS NOT NULL 
                AND json_extract(players, '$[0]') IS NOT NULL
                AND json_extract(players, '$[0]') != 'Null'
            GROUP BY player
            ORDER BY count DESC
        ''').fetchall()
        
        # Get all players from arrays
        all_players = analysis_con.execute('''
            SELECT players, sentiment_score, patient_phase, outcome, denial_category
            FROM thread_analyses 
            WHERE players IS NOT NULL
        ''').fetchall()
        
        # Process player data manually
        player_sentiment_data = []
        player_phase_data = []
        player_outcome_data = []
        player_denial_data = []
        
        for row in all_players:
            try:
                players = json.loads(row[0]) if row[0] else []
                sentiment_score = row[1]
                patient_phase = row[2]
                outcome = row[3]
                denial_category = row[4]
                
                for player in players:
                    if player and player != 'Null':
                        if sentiment_score is not None:
                            player_sentiment_data.append({
                                'player': player,
                                'sentiment_score': sentiment_score,
                                'count': 1
                            })
                        if patient_phase is not None:
                            player_phase_data.append({
                                'player': player,
                                'phase': patient_phase,
                                'count': 1
                            })
                        if outcome is not None:
                            player_outcome_data.append({
                                'player': player,
                                'outcome': outcome,
                                'count': 1
                            })
                        if denial_category is not None:
                            player_denial_data.append({
                                'player': player,
                                'denial_category': denial_category,
                                'count': 1
                            })
            except json.JSONDecodeError:
                continue
        
        analysis_con.close()
        
        return jsonify({
            'frequency': [{'player': row[0], 'count': row[1]} for row in player_freq],
            'sentiment': player_sentiment_data,
            'phase_heatmap': player_phase_data,
            'outcome': player_outcome_data,
            'denial': player_denial_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/correlation-matrix')
def get_correlation_matrix():
    """API endpoint for correlation analysis."""
    try:
        analysis_con = sqlite3.connect('analysis.db')
        
        # Get all relevant data for correlation analysis
        correlations = analysis_con.execute('''
            SELECT 
                sentiment_score,
                experience_rating,
                outcome,
                denial_category,
                patient_phase,
                touchpoints,
                players
            FROM thread_analyses 
            WHERE sentiment_score IS NOT NULL 
                OR experience_rating IS NOT NULL 
                OR outcome IS NOT NULL
        ''').fetchall()
        
        analysis_con.close()
        
        # Process correlations (simplified for now)
        correlation_data = {
            'sentiment_vs_experience': [],
            'sentiment_vs_outcome': [],
            'experience_vs_outcome': []
        }
        
        for row in correlations:
            if row[0] is not None and row[1] is not None:  # sentiment vs experience
                correlation_data['sentiment_vs_experience'].append({
                    'sentiment': row[0],
                    'experience': row[1]
                })
        
        return jsonify(correlation_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/treatment-decision-factors')
def get_treatment_decision_factors():
    """API endpoint for treatment decision factors analysis."""
    try:
        analysis_con = sqlite3.connect('analysis.db')
        
        # Get treatment-related posts with sentiment
        treatment_data = analysis_con.execute('''
            SELECT 
                themes,
                sentiment_score,
                patient_phase,
                outcome,
                denial_category,
                touchpoints,
                players
            FROM thread_analyses 
            WHERE themes LIKE '%treatment%' 
                OR themes LIKE '%medication%' 
                OR themes LIKE '%biologic%'
        ''').fetchall()
        
        # Process treatment factors
        decision_factors = {
            'cost_considerations': [],
            'effectiveness_concerns': [],
            'side_effects': [],
            'convenience': [],
            'doctor_recommendation': [],
            'insurance_coverage': []
        }
        
        for row in treatment_data:
            themes = row[0] if row[0] else ''
            sentiment = row[1] if row[1] else 0
            
            # Categorize themes into decision factors
            if 'cost' in themes.lower() or 'price' in themes.lower():
                decision_factors['cost_considerations'].append(sentiment)
            if 'effective' in themes.lower() or 'work' in themes.lower():
                decision_factors['effectiveness_concerns'].append(sentiment)
            if 'side effect' in themes.lower() or 'adverse' in themes.lower():
                decision_factors['side_effects'].append(sentiment)
            if 'convenient' in themes.lower() or 'easy' in themes.lower():
                decision_factors['convenience'].append(sentiment)
            if 'doctor' in themes.lower() or 'physician' in themes.lower():
                decision_factors['doctor_recommendation'].append(sentiment)
            if 'insurance' in themes.lower() or 'coverage' in themes.lower():
                decision_factors['insurance_coverage'].append(sentiment)
        
        # Calculate average sentiment for each factor
        factor_sentiments = {}
        for factor, sentiments in decision_factors.items():
            if sentiments:
                factor_sentiments[factor] = sum(sentiments) / len(sentiments)
            else:
                factor_sentiments[factor] = 0
        
        analysis_con.close()
        return jsonify(factor_sentiments)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/patient-confidence-by-phase')
def get_patient_confidence_by_phase():
    """API endpoint for patient confidence analysis by phase."""
    try:
        analysis_con = sqlite3.connect('analysis.db')
        
        # Get confidence scores by patient phase
        confidence_data = analysis_con.execute('''
            SELECT 
                patient_phase,
                confidence,
                sentiment_score,
                experience_rating,
                COUNT(*) as count
            FROM thread_analyses 
            WHERE patient_phase IS NOT NULL 
                AND confidence IS NOT NULL
            GROUP BY patient_phase
            ORDER BY 
                CASE patient_phase
                    WHEN 'Symptom Onset' THEN 1
                    WHEN 'Assessment & Diagnosis' THEN 2
                    WHEN 'Treatment Options' THEN 3
                    WHEN 'Pretreatment & Prescription' THEN 4
                    WHEN 'Insurance & Financial Support Determination' THEN 5
                    WHEN 'Enrollment' THEN 6
                    WHEN 'Initial Treatment' THEN 7
                    WHEN 'Maintaining Treatment' THEN 8
                    WHEN 'Ongoing Treatment' THEN 9
                    ELSE 10
                END
        ''').fetchall()
        
        analysis_con.close()
        
        phases = []
        confidence_scores = []
        sentiment_scores = []
        experience_scores = []
        counts = []
        
        for row in confidence_data:
            phases.append(row[0])
            confidence_scores.append(row[1])
            sentiment_scores.append(row[2] if row[2] else 0)
            experience_scores.append(row[3] if row[3] else 0)
            counts.append(row[4])
        
        return jsonify({
            'phases': phases,
            'confidence_scores': confidence_scores,
            'sentiment_scores': sentiment_scores,
            'experience_scores': experience_scores,
            'counts': counts
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/denial-timeline-analysis')
def get_denial_timeline_analysis():
    """API endpoint for denial timeline analysis."""
    try:
        analysis_con = sqlite3.connect('analysis.db')
        
        # Get denial events by patient phase
        denial_timeline = analysis_con.execute('''
            SELECT 
                patient_phase,
                denial_category,
                denial_type,
                COUNT(*) as denial_count,
                AVG(sentiment_score) as avg_sentiment
            FROM thread_analyses 
            WHERE denial_category IS NOT NULL 
                AND patient_phase IS NOT NULL
                AND denial_category NOT IN ('None', 'N/A', 'Null')
            GROUP BY patient_phase, denial_category
            ORDER BY 
                CASE patient_phase
                    WHEN 'Symptom Onset' THEN 1
                    WHEN 'Assessment & Diagnosis' THEN 2
                    WHEN 'Treatment Options' THEN 3
                    WHEN 'Pretreatment & Prescription' THEN 4
                    WHEN 'Insurance & Financial Support Determination' THEN 5
                    WHEN 'Enrollment' THEN 6
                    WHEN 'Initial Treatment' THEN 7
                    WHEN 'Maintaining Treatment' THEN 8
                    WHEN 'Ongoing Treatment' THEN 9
                    ELSE 10
                END
        ''').fetchall()
        
        analysis_con.close()
        
        timeline_data = []
        for row in denial_timeline:
            timeline_data.append({
                'phase': row[0],
                'denial_category': row[1],
                'denial_type': row[2],
                'denial_count': row[3],
                'avg_sentiment': row[4] if row[4] else 0
            })
        
        return jsonify(timeline_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/denial-reason-breakdown')
def get_denial_reason_breakdown():
    """API endpoint for detailed denial reason breakdown."""
    try:
        analysis_con = sqlite3.connect('analysis.db')
        
        # Get detailed denial reasons
        denial_reasons = analysis_con.execute('''
            SELECT 
                denial_category,
                denial_type,
                themes,
                outcome,
                COUNT(*) as count,
                AVG(sentiment_score) as avg_sentiment
            FROM thread_analyses 
            WHERE denial_category IS NOT NULL
                AND denial_category NOT IN ('None', 'N/A', 'Null')
            GROUP BY denial_category, denial_type
            ORDER BY count DESC
        ''').fetchall()
        
        analysis_con.close()
        
        breakdown_data = []
        for row in denial_reasons:
            breakdown_data.append({
                'category': row[0],
                'type': row[1],
                'themes': row[2],
                'outcome': row[3],
                'count': row[4],
                'avg_sentiment': row[5] if row[5] else 0
            })
        
        return jsonify(breakdown_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/insurance-company-performance')
def get_insurance_company_performance():
    """API endpoint for insurance company performance analysis."""
    try:
        analysis_con = sqlite3.connect('analysis.db')
        
        # Extract insurance companies from themes and players
        insurance_data = analysis_con.execute('''
            SELECT 
                themes,
                players,
                denial_category,
                sentiment_score,
                outcome
            FROM thread_analyses 
            WHERE themes LIKE '%insurance%' 
                OR players LIKE '%insurer%'
        ''').fetchall()
        
        # Process insurance company mentions
        insurance_companies = {}
        
        for row in insurance_data:
            themes = row[0] if row[0] else ''
            players = row[1] if row[1] else ''
            denial_category = row[2]
            sentiment = row[3] if row[3] else 0
            outcome = row[3]
            
            # Extract insurance company names (simplified)
            companies = []
            if 'blue cross' in themes.lower() or 'bluecross' in themes.lower():
                companies.append('Blue Cross Blue Shield')
            if 'aetna' in themes.lower():
                companies.append('Aetna')
            if 'cigna' in themes.lower():
                companies.append('Cigna')
            if 'united' in themes.lower() and 'health' in themes.lower():
                companies.append('UnitedHealth')
            if 'kaiser' in themes.lower():
                companies.append('Kaiser Permanente')
            if 'humana' in themes.lower():
                companies.append('Humana')
            
            for company in companies:
                if company not in insurance_companies:
                    insurance_companies[company] = {
                        'denial_count': 0,
                        'approval_count': 0,
                        'total_sentiment': 0,
                        'sentiment_count': 0
                    }
                
                if denial_category:
                    insurance_companies[company]['denial_count'] += 1
                else:
                    insurance_companies[company]['approval_count'] += 1
                
                if sentiment != 0:
                    insurance_companies[company]['total_sentiment'] += sentiment
                    insurance_companies[company]['sentiment_count'] += 1
        
        # Calculate metrics
        performance_data = []
        for company, data in insurance_companies.items():
            total_claims = data['denial_count'] + data['approval_count']
            denial_rate = (data['denial_count'] / total_claims * 100) if total_claims > 0 else 0
            avg_sentiment = (data['total_sentiment'] / data['sentiment_count']) if data['sentiment_count'] > 0 else 0
            
            performance_data.append({
                'company': company,
                'denial_rate': denial_rate,
                'avg_sentiment': avg_sentiment,
                'total_claims': total_claims,
                'denial_count': data['denial_count'],
                'approval_count': data['approval_count']
            })
        
        analysis_con.close()
        return jsonify(performance_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/denial-impact-on-treatment')
def get_denial_impact_on_treatment():
    """API endpoint for denial impact on treatment analysis."""
    try:
        analysis_con = sqlite3.connect('analysis.db')
        
        # Get posts with denials and their treatment outcomes
        impact_data = analysis_con.execute('''
            SELECT 
                denial_category,
                outcome,
                patient_phase,
                sentiment_score,
                experience_rating,
                themes,
                COUNT(*) as count
            FROM thread_analyses 
            WHERE denial_category IS NOT NULL
                AND denial_category NOT IN ('None', 'N/A', 'Null')
            GROUP BY denial_category, outcome
        ''').fetchall()
        
        analysis_con.close()
        
        impact_analysis = []
        for row in impact_data:
            impact_analysis.append({
                'denial_category': row[0],
                'outcome': row[1],
                'patient_phase': row[2],
                'avg_sentiment': row[3] if row[3] else 0,
                'avg_experience': row[4] if row[4] else 0,
                'themes': row[5],
                'count': row[6]
            })
        
        return jsonify(impact_analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/touchpoint-effectiveness-matrix')
def get_touchpoint_effectiveness_matrix():
    """API endpoint for touchpoint effectiveness matrix."""
    try:
        analysis_con = sqlite3.connect('analysis.db')
        
        # Get touchpoint data with sentiment and frequency
        touchpoint_data = analysis_con.execute('''
            SELECT 
                touchpoints,
                sentiment_score,
                outcome,
                COUNT(*) as frequency
            FROM thread_analyses 
            WHERE touchpoints IS NOT NULL
            GROUP BY touchpoints
        ''').fetchall()
        
        analysis_con.close()
        
        # Process touchpoint effectiveness
        effectiveness_matrix = []
        
        for row in touchpoint_data:
            try:
                touchpoints = json.loads(row[0]) if row[0] else []
                avg_sentiment = row[1] if row[1] else 0
                outcome = row[2]
                frequency = row[3]
                
                for touchpoint in touchpoints:
                    effectiveness_matrix.append({
                        'touchpoint': touchpoint,
                        'frequency': frequency,
                        'sentiment_score': avg_sentiment,
                        'effectiveness_score': (avg_sentiment + 1) * frequency / 2,  # Combined score
                        'outcome': outcome
                    })
            except json.JSONDecodeError:
                continue
        
        return jsonify(effectiveness_matrix)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/player-interaction-network')
def get_player_interaction_network():
    """API endpoint for player interaction network analysis."""
    try:
        analysis_con = sqlite3.connect('analysis.db')
        
        # Get player co-occurrence data
        player_data = analysis_con.execute('''
            SELECT 
                players,
                touchpoints,
                sentiment_score,
                COUNT(*) as interaction_count
            FROM thread_analyses 
            WHERE players IS NOT NULL
        ''').fetchall()
        
        analysis_con.close()
        
        # Build interaction network
        interactions = {}
        player_sentiments = {}
        
        for row in player_data:
            try:
                players = json.loads(row[0]) if row[0] else []
                touchpoints = json.loads(row[1]) if row[1] else []
                sentiment = row[2] if row[2] else 0
                interaction_count = row[3]
                
                # Track player interactions
                for i, player1 in enumerate(players):
                    if player1 not in player_sentiments:
                        player_sentiments[player1] = {'total_sentiment': 0, 'count': 0}
                    
                    player_sentiments[player1]['total_sentiment'] += sentiment
                    player_sentiments[player1]['count'] += 1
                    
                    for j, player2 in enumerate(players[i+1:], i+1):
                        interaction_key = f"{player1}-{player2}"
                        if interaction_key not in interactions:
                            interactions[interaction_key] = {
                                'source': player1,
                                'target': player2,
                                'weight': 0,
                                'sentiment': 0,
                                'count': 0
                            }
                        
                        interactions[interaction_key]['weight'] += interaction_count
                        interactions[interaction_key]['sentiment'] += sentiment
                        interactions[interaction_key]['count'] += 1
                        
            except json.JSONDecodeError:
                continue
        
        # Calculate average sentiments
        for player, data in player_sentiments.items():
            if data['count'] > 0:
                data['avg_sentiment'] = data['total_sentiment'] / data['count']
            else:
                data['avg_sentiment'] = 0
        
        for interaction in interactions.values():
            if interaction['count'] > 0:
                interaction['avg_sentiment'] = interaction['sentiment'] / interaction['count']
            else:
                interaction['avg_sentiment'] = 0
        
        return jsonify({
            'nodes': [{'id': player, 'sentiment': data['avg_sentiment'], 'count': data['count']} 
                     for player, data in player_sentiments.items()],
            'edges': [{'source': edge['source'], 'target': edge['target'], 
                      'weight': edge['weight'], 'sentiment': edge['avg_sentiment']} 
                     for edge in interactions.values()]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/touchpoint-journey-mapping')
def get_touchpoint_journey_mapping():
    """API endpoint for touchpoint journey mapping."""
    try:
        analysis_con = sqlite3.connect('analysis.db')
        
        # Get touchpoint sequence by patient phase
        journey_data = analysis_con.execute('''
            SELECT 
                patient_phase,
                touchpoints,
                sentiment_score,
                COUNT(*) as frequency
            FROM thread_analyses 
            WHERE touchpoints IS NOT NULL 
                AND patient_phase IS NOT NULL
            GROUP BY patient_phase, touchpoints
            ORDER BY 
                CASE patient_phase
                    WHEN 'Symptom Onset' THEN 1
                    WHEN 'Assessment & Diagnosis' THEN 2
                    WHEN 'Treatment Options' THEN 3
                    WHEN 'Pretreatment & Prescription' THEN 4
                    WHEN 'Insurance & Financial Support Determination' THEN 5
                    WHEN 'Enrollment' THEN 6
                    WHEN 'Initial Treatment' THEN 7
                    WHEN 'Maintaining Treatment' THEN 8
                    WHEN 'Ongoing Treatment' THEN 9
                    ELSE 10
                END
        ''').fetchall()
        
        analysis_con.close()
        
        # Build journey mapping
        journey_mapping = {}
        
        for row in journey_data:
            phase = row[0]
            try:
                touchpoints = json.loads(row[1]) if row[1] else []
                avg_sentiment = row[2] if row[2] else 0
                frequency = row[3]
                
                if phase not in journey_mapping:
                    journey_mapping[phase] = []
                
                for touchpoint in touchpoints:
                    journey_mapping[phase].append({
                        'touchpoint': touchpoint,
                        'frequency': frequency,
                        'sentiment': avg_sentiment
                    })
                    
            except json.JSONDecodeError:
                continue
        
        return jsonify(journey_mapping)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Download database files on startup
try:
    from download_data import download_database_files
    download_database_files()
except ImportError:
    print("download_data.py not found, skipping database download")

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True) 