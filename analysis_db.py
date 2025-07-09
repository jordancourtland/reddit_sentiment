import sqlite3
import json
from datetime import datetime
import os
import logging
import csv
from typing import Dict

# New configuration for autoimmune conditions
AUTOIMMUNE_CONFIG = {
    "primary_conditions": [
        "ulcerative_colitis", "plaque_psoriasis", 
        "psoriatic_arthritis", "crohns_disease"
    ],
    "secondary_conditions": [
        "rheumatoid_arthritis", "ankylosing_spondylitis",
        "multiple_sclerosis", "lupus", "atopic_dermatitis",
        "hidradenitis_suppurativa", "uveitis", "inflammatory_bowel_disease"
    ],
    "subreddits": {
        "condition_specific": [
            "UlcerativeColitis", "CrohnsDisease", "Psoriasis",
            "PsoriaticArthritis", "RheumatoidArthritis", "MultipleSclerosis",
            "Lupus", "Dermatology", "IBD", "Autoimmune",
            "HidradenitisSuppurativa", "Uveitis", "Eczema"
        ],
        "treatment_specific": [
            "Humira", "Stelara", "Cosentyx", "Tremfya", "Skyrizi",
            "Rinvoq", "Otezla", "Taltz", "Entyvio", "Remicade",
            "Simponi", "Cimzia", "Orencia", "Actemra", "Xeljanz",
            "Rituxan", "Ocrevus", "Kesimpta", "Tysabri", "Aubagio"
        ]
    },
    "keywords": {
        "symptoms": [
            "flare", "symptoms", "pain", "inflammation", "rash",
            "joint pain", "fatigue", "diarrhea", "constipation",
            "abdominal pain", "skin lesions", "swelling"
        ],
        "diagnosis": [
            "diagnosis", "diagnosed", "test results", "biopsy",
            "colonoscopy", "endoscopy", "blood work", "imaging"
        ],
        "treatment": [
            "treatment", "medication", "injection", "biologic",
            "infusion", "therapy", "dose", "regimen"
        ],
        "insurance": [
            "insurance", "prior authorization", "denial", "approval",
            "coverage", "copay", "deductible", "out of pocket"
        ],
        "pharmacy": [
            "pharmacy", "prescription", "delivery", "refill",
            "specialty pharmacy", "mail order", "pickup"
        ],
        "adherence": [
            "adherence", "compliance", "missed dose", "routine",
            "schedule", "reminder", "tracking"
        ],
        "digital_experience": [
            "app", "portal", "website", "online", "digital",
            "patient portal", "mobile app", "tracking app",
            "support program", "nurse line", "patient services"
        ]
    },
    "digital_experience_keywords": {
        "humira_complete": ["Humira Complete", "Humira app", "Humira portal"],
        "stelara_connect": ["Stelara Connect", "Stelara app", "Stelara portal"],
        "cosentyx_connect": ["Cosentyx Connect", "Cosentyx app"],
        "tremfya_connect": ["Tremfya Connect", "Tremfya app"],
        "skyrizi_connect": ["Skyrizi Connect", "Skyrizi app"],
        "rinvoq_connect": ["Rinvoq Connect", "Rinvoq app"],
        "otezla_connect": ["Otezla Connect", "Otezla app"],
        "taltz_connect": ["Taltz Connect", "Taltz app"],
        "entyvio_connect": ["Entyvio Connect", "Entyvio app"],
        "remicade_connect": ["Remicade Connect", "Remicade app"],
        "simponi_connect": ["Simponi Connect", "Simponi app"],
        "cimzia_connect": ["Cimzia Connect", "Cimzia app"],
        "orencia_connect": ["Orencia Connect", "Orencia app"],
        "actemra_connect": ["Actemra Connect", "Actemra app"],
        "xeljanz_connect": ["Xeljanz Connect", "Xeljanz app"],
        "rituxan_connect": ["Rituxan Connect", "Rituxan app"],
        "ocrevus_connect": ["Ocrevus Connect", "Ocrevus app"],
        "kesimpta_connect": ["Kesimpta Connect", "Kesimpta app"],
        "tysabri_connect": ["Tysabri Connect", "Tysabri app"],
        "aubagio_connect": ["Aubagio Connect", "Aubagio app"]
    },
    "pharma_companies": {
        "abbvie": ["Humira", "Rinvoq", "Skyrizi"],
        "janssen": ["Stelara", "Tremfya", "Remicade", "Simponi"],
        "novartis": ["Cosentyx", "Entyvio", "Xeljanz"],
        "amgen": ["Otezla", "Enbrel"],
        "eli_lilly": ["Taltz", "Olumiant"],
        "bristol_myers_squibb": ["Orencia", "Otezla"],
        "roche": ["Actemra", "Rituxan"],
        "biogen": ["Tysabri", "Aubagio"],
        "genentech": ["Ocrevus", "Actemra"],
        "novartis": ["Kesimpta", "Cosentyx"]
    },
    "digital_programs": {
        "humira_complete": {
            "company": "AbbVie",
            "features": ["dose tracking", "nurse support", "financial assistance", "delivery coordination"],
            "keywords": ["Humira Complete", "Complete app", "Humira nurse", "Humira support"]
        },
        "stelara_connect": {
            "company": "Janssen",
            "features": ["patient portal", "nurse support", "financial assistance", "dose reminders"],
            "keywords": ["Stelara Connect", "Connect portal", "Stelara nurse", "Stelara support"]
        },
        "cosentyx_connect": {
            "company": "Novartis",
            "features": ["dose tracking", "nurse support", "financial assistance"],
            "keywords": ["Cosentyx Connect", "Cosentyx app", "Cosentyx nurse"]
        },
        "tremfya_connect": {
            "company": "Janssen",
            "features": ["patient portal", "nurse support", "financial assistance"],
            "keywords": ["Tremfya Connect", "Tremfya portal", "Tremfya nurse"]
        },
        "skyrizi_connect": {
            "company": "AbbVie",
            "features": ["dose tracking", "nurse support", "financial assistance"],
            "keywords": ["Skyrizi Connect", "Skyrizi app", "Skyrizi nurse"]
        },
        "rinvoq_connect": {
            "company": "AbbVie",
            "features": ["patient portal", "nurse support", "financial assistance"],
            "keywords": ["Rinvoq Connect", "Rinvoq portal", "Rinvoq nurse"]
        },
        "otezla_connect": {
            "company": "Amgen",
            "features": ["dose tracking", "nurse support", "financial assistance"],
            "keywords": ["Otezla Connect", "Otezla app", "Otezla nurse"]
        },
        "taltz_connect": {
            "company": "Eli Lilly",
            "features": ["patient portal", "nurse support", "financial assistance"],
            "keywords": ["Taltz Connect", "Taltz portal", "Taltz nurse"]
        },
        "entyvio_connect": {
            "company": "Takeda",
            "features": ["infusion coordination", "nurse support", "financial assistance"],
            "keywords": ["Entyvio Connect", "Entyvio portal", "Entyvio nurse"]
        },
        "remicade_connect": {
            "company": "Janssen",
            "features": ["infusion coordination", "nurse support", "financial assistance"],
            "keywords": ["Remicade Connect", "Remicade portal", "Remicade nurse"]
        }
    }
}

class AnalysisDB:
    def __init__(self, analysis_db_path='analysis.db', reddit_db_path='reddit.db'):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.analysis_db_path = os.path.join(base_dir, analysis_db_path)
        self.reddit_db_path = os.path.join(base_dir, reddit_db_path)
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
                        denial_category TEXT,
                        denial_specifics TEXT,
                        denial_resolution TEXT,
                        resolution_timeframe TEXT,
                        themes TEXT,
                        outcome TEXT,
                        options_suggested TEXT,
                        patient_phase TEXT,
                        patient_actions TEXT,
                        touchpoints TEXT,
                        players TEXT,
                        phase_sentiments TEXT,
                        sentiment_score FLOAT,
                        sentiment_explanation TEXT,
                        experience_rating FLOAT,
                        experience_explanation TEXT,
                        pain_points TEXT,
                        positive_aspects TEXT,
                        treatment_mentions TEXT,
                        support_program_mentions TEXT,
                        touchpoint_effectiveness TEXT,
                        player_interactions TEXT,
                        keyword_tag TEXT
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

    def store_analysis(self, thread_id: str, analysis_result: Dict) -> bool:
        """Store analysis results with enhanced patient experience and denial fields."""
        try:
            with sqlite3.connect(self.analysis_db_path) as conn:
                # Convert lists to JSON strings for storage
                patient_actions = json.dumps(analysis_result.get('patient_actions', []))
                touchpoints = json.dumps(analysis_result.get('touchpoints', []))
                players = json.dumps(analysis_result.get('players', []))
                phase_sentiments = json.dumps(analysis_result.get('phase_sentiments', {}))
                themes = json.dumps(analysis_result.get('themes', []))
                treatment_mentions = json.dumps(analysis_result.get('treatment_mentions', []))
                support_program_mentions = json.dumps(analysis_result.get('support_program_mentions', []))
                pain_points = json.dumps(analysis_result.get('pain_points', []))
                positive_aspects = json.dumps(analysis_result.get('positive_aspects', []))
                denial_specifics = json.dumps(analysis_result.get('denial_specifics', []))
                options_suggested = json.dumps(analysis_result.get('options_suggested', []))
                
                conn.execute('''
                    INSERT OR REPLACE INTO thread_analyses (
                        thread_id, analysis_timestamp, op_summary, responses_summary,
                        persona_fit, confidence, fit_explanation, denial_type,
                        themes, outcome, options_suggested, patient_phase,
                        patient_actions, touchpoints, players, phase_sentiments,
                        denial_category, denial_specifics, denial_resolution,
                        resolution_timeframe, sentiment_score, sentiment_explanation,
                        experience_rating, experience_explanation, pain_points,
                        positive_aspects, treatment_mentions, support_program_mentions
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    thread_id,
                    datetime.now().isoformat(),
                    analysis_result.get('op_summary'),
                    analysis_result.get('responses_summary'),
                    analysis_result.get('persona_fit'),
                    analysis_result.get('confidence'),
                    analysis_result.get('fit_explanation'),
                    analysis_result.get('denial_type'),
                    themes,
                    analysis_result.get('outcome'),
                    options_suggested,
                    analysis_result.get('patient_phase'),
                    patient_actions,
                    touchpoints,
                    players,
                    phase_sentiments,
                    analysis_result.get('denial_category'),
                    denial_specifics,
                    analysis_result.get('denial_resolution'),
                    analysis_result.get('resolution_timeframe'),
                    analysis_result.get('sentiment_score'),
                    analysis_result.get('sentiment_explanation'),
                    analysis_result.get('experience_rating'),
                    analysis_result.get('experience_explanation'),
                    pain_points,
                    positive_aspects,
                    treatment_mentions,
                    support_program_mentions
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
                    result['patient_phases'] = json.loads(result['patient_phases'])
                    result['touchpoints'] = json.loads(result['touchpoints'])
                    result['players'] = json.loads(result['players'])
                    result['phase_sentiments'] = json.loads(result['phase_sentiments'])
                    result['touchpoint_effectiveness'] = json.loads(result['touchpoint_effectiveness'])
                    result['player_interactions'] = json.loads(result['player_interactions'])
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

            with sqlite3.connect(self.analysis_db_path) as conn:
                conn.row_factory = sqlite3.Row
                conn.execute(f"ATTACH DATABASE '{self.reddit_db_path}' AS redditdb")
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
                        a.patient_phases,
                        a.touchpoints,
                        a.players,
                        a.phase_sentiments,
                        a.touchpoint_effectiveness,
                        a.player_interactions,
                        p.title,
                        p.subreddit,
                        p.created_utc,
                        p.score,
                        p.num_comments,
                        p.selftext
                    FROM thread_analyses a
                    LEFT JOIN redditdb.reddit_posts p ON a.thread_id = p.id
                    ORDER BY a.analysis_timestamp DESC
                    LIMIT ?
                '''
                cursor = conn.execute(query, (limit,))
                results = []
                for row in cursor.fetchall():
                    thread = dict(row)
                    # Parse JSON fields
                    thread['themes'] = json.loads(thread['themes'])
                    thread['options_suggested'] = json.loads(thread['options_suggested'])
                    thread['patient_phases'] = json.loads(thread['patient_phases'])
                    thread['touchpoints'] = json.loads(thread['touchpoints'])
                    thread['players'] = json.loads(thread['players'])
                    thread['phase_sentiments'] = json.loads(thread['phase_sentiments'])
                    thread['touchpoint_effectiveness'] = json.loads(thread['touchpoint_effectiveness'])
                    thread['player_interactions'] = json.loads(thread['player_interactions'])
                    results.append(thread)
                logging.info(f"Retrieved {len(results)} analyzed threads")
                return results

        except Exception as e:
            logging.error(f"Error getting analyzed threads: {str(e)}")
            return []

    def export_all_threads(self, output_dir='exports'):
        """Export all analyzed threads to plaintext and CSV files."""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Get all analyzed threads
            threads = self.get_analyzed_threads(limit=1000)  # Get all threads
            
            if not threads:
                logging.warning("No threads to export")
                return False
            
            # Export as plaintext
            self._export_threads_plaintext_simple(threads, output_dir)
            
            # Export as CSV
            self._export_threads_csv_simple(threads, output_dir)
            
            # Export summary statistics
            self._export_summary_simple(threads, output_dir)
            
            logging.info(f"Successfully exported {len(threads)} threads to {output_dir}")
            return True
            
        except Exception as e:
            logging.error(f"Error exporting data: {str(e)}")
            return False

    def _export_threads_plaintext_simple(self, threads, output_dir):
        """Export threads as plaintext files using current schema."""
        # Export all threads in one file
        all_threads_file = os.path.join(output_dir, "all_analyzed_threads.txt")
        with open(all_threads_file, 'w', encoding='utf-8') as f:
            f.write(f"Reddit Sentiment Analysis Export\n")
            f.write(f"Export Date: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, thread in enumerate(threads, 1):
                f.write(f"THREAD {i}\n")
                f.write(f"ID: {thread['thread_id']}\n")
                f.write(f"Title: {thread.get('title', 'N/A')}\n")
                f.write(f"Subreddit: {thread.get('subreddit', 'N/A')}\n")
                f.write(f"Created: {thread.get('created_utc', 'N/A')}\n")
                f.write(f"Persona Fit: {thread.get('persona_fit', 'N/A')}\n")
                f.write(f"Confidence: {thread.get('confidence', 'N/A')}\n")
                f.write(f"Denial Type: {thread.get('denial_type', 'N/A')}\n")
                f.write(f"Outcome: {thread.get('outcome', 'N/A')}\n")
                f.write(f"OP Summary: {thread.get('op_summary', 'N/A')}\n")
                f.write(f"Responses Summary: {thread.get('responses_summary', 'N/A')}\n")
                
                # Safely handle JSON fields
                themes = thread.get('themes', '[]')
                if isinstance(themes, str):
                    try:
                        themes_list = json.loads(themes)
                        themes_str = ', '.join(themes_list)
                    except:
                        themes_str = themes
                else:
                    themes_str = ', '.join(themes) if themes else 'N/A'
                
                options = thread.get('options_suggested', '[]')
                if isinstance(options, str):
                    try:
                        options_list = json.loads(options)
                        options_str = ', '.join(options_list)
                    except:
                        options_str = options
                else:
                    options_str = ', '.join(options) if options else 'N/A'
                
                f.write(f"Themes: {themes_str}\n")
                f.write(f"Options Suggested: {options_str}\n")
                f.write(f"Fit Explanation: {thread.get('fit_explanation', 'N/A')}\n")
                f.write("-" * 80 + "\n\n")
        
        # Export individual thread files
        threads_dir = os.path.join(output_dir, "individual_threads")
        os.makedirs(threads_dir, exist_ok=True)
        
        for thread in threads:
            thread_file = os.path.join(threads_dir, f"thread_{thread['thread_id']}.txt")
            with open(thread_file, 'w', encoding='utf-8') as f:
                f.write(f"Thread ID: {thread['thread_id']}\n")
                f.write(f"Title: {thread.get('title', 'N/A')}\n")
                f.write(f"Subreddit: {thread.get('subreddit', 'N/A')}\n")
                f.write(f"Created: {thread.get('created_utc', 'N/A')}\n")
                f.write(f"Persona Fit: {thread.get('persona_fit', 'N/A')}\n")
                f.write(f"Confidence: {thread.get('confidence', 'N/A')}\n")
                f.write(f"Denial Type: {thread.get('denial_type', 'N/A')}\n")
                f.write(f"Outcome: {thread.get('outcome', 'N/A')}\n")
                f.write(f"OP Summary: {thread.get('op_summary', 'N/A')}\n")
                f.write(f"Responses Summary: {thread.get('responses_summary', 'N/A')}\n")
                
                # Safely handle JSON fields
                themes = thread.get('themes', '[]')
                if isinstance(themes, str):
                    try:
                        themes_list = json.loads(themes)
                        themes_str = ', '.join(themes_list)
                    except:
                        themes_str = themes
                else:
                    themes_str = ', '.join(themes) if themes else 'N/A'
                
                options = thread.get('options_suggested', '[]')
                if isinstance(options, str):
                    try:
                        options_list = json.loads(options)
                        options_str = ', '.join(options_list)
                    except:
                        options_str = options
                else:
                    options_str = ', '.join(options) if options else 'N/A'
                
                f.write(f"Themes: {themes_str}\n")
                f.write(f"Options Suggested: {options_str}\n")
                f.write(f"Fit Explanation: {thread.get('fit_explanation', 'N/A')}\n")
                f.write(f"Original Post: {thread.get('selftext', 'N/A')}\n")

    def _export_threads_csv_simple(self, threads, output_dir):
        """Export threads as CSV file using current schema."""
        csv_file = os.path.join(output_dir, "analyzed_threads.csv")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if threads:
                # Flatten JSON fields for CSV
                flattened_threads = []
                for thread in threads:
                    flat_thread = thread.copy()
                    
                    # Safely handle JSON fields
                    themes = thread.get('themes', '[]')
                    if isinstance(themes, str):
                        try:
                            themes_list = json.loads(themes)
                            flat_thread['themes'] = ', '.join(themes_list)
                        except:
                            flat_thread['themes'] = themes
                    else:
                        flat_thread['themes'] = ', '.join(themes) if themes else ''
                    
                    options = thread.get('options_suggested', '[]')
                    if isinstance(options, str):
                        try:
                            options_list = json.loads(options)
                            flat_thread['options_suggested'] = ', '.join(options_list)
                        except:
                            flat_thread['options_suggested'] = options
                    else:
                        flat_thread['options_suggested'] = ', '.join(options) if options else ''
                    
                    flattened_threads.append(flat_thread)
                
                writer = csv.DictWriter(f, fieldnames=flattened_threads[0].keys())
                writer.writeheader()
                writer.writerows(flattened_threads)

    def _export_summary_simple(self, threads, output_dir):
        """Export summary statistics using current schema."""
        summary_file = os.path.join(output_dir, "analysis_summary.txt")
        
        # Calculate statistics
        total_threads = len(threads)
        denial_types = {}
        outcomes = {}
        subreddits = {}
        persona_fits = []
        confidences = []
        
        for thread in threads:
            denial_type = thread.get('denial_type', 'Unknown')
            denial_types[denial_type] = denial_types.get(denial_type, 0) + 1
            
            outcome = thread.get('outcome', 'Unknown')
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
            
            subreddit = thread.get('subreddit', 'Unknown')
            subreddits[subreddit] = subreddits.get(subreddit, 0) + 1
            
            if thread.get('persona_fit'):
                persona_fits.append(thread['persona_fit'])
            if thread.get('confidence'):
                confidences.append(thread['confidence'])
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"Reddit Sentiment Analysis Summary\n")
            f.write(f"Export Date: {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Total Threads Analyzed: {total_threads}\n\n")
            
            if persona_fits:
                avg_persona_fit = sum(persona_fits) / len(persona_fits)
                f.write(f"Average Persona Fit: {avg_persona_fit:.2f}\n")
            
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                f.write(f"Average Confidence: {avg_confidence:.2f}\n\n")
            
            f.write("Denial Types Distribution:\n")
            for denial_type, count in denial_types.items():
                percentage = (count / total_threads) * 100 if total_threads > 0 else 0
                f.write(f"  {denial_type}: {count} ({percentage:.1f}%)\n")
            
            f.write("\nOutcomes Distribution:\n")
            for outcome, count in outcomes.items():
                percentage = (count / total_threads) * 100 if total_threads > 0 else 0
                f.write(f"  {outcome}: {count} ({percentage:.1f}%)\n")
            
            f.write("\nSubreddit Distribution:\n")
            for subreddit, count in subreddits.items():
                percentage = (count / total_threads) * 100 if total_threads > 0 else 0
                f.write(f"  r/{subreddit}: {count} ({percentage:.1f}%)\n")

    def get_collection_runs(self):
        """Get all collection runs - simplified version."""
        # Since we don't have collection runs, return a simple structure
        return [{'run_id': 'all', 'start_time': 'N/A', 'end_time': 'N/A', 'status': 'completed'}]

    def get_threads_by_run(self, run_id):
        """Get threads from specific collection run."""
        return self.get_analyzed_threads(limit=1000) 

    def get_analytics_by_run(self, run_id):
        """Get analytics for specific collection run."""
        # Implementation needed
        pass
