#!/usr/bin/env python3
"""
Schema migration script to add missing columns to thread_analyses table.
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_schema():
    """Add missing columns to thread_analyses table."""
    try:
        with sqlite3.connect('analysis.db') as conn:
            # Get current columns
            cursor = conn.execute("PRAGMA table_info(thread_analyses)")
            existing_columns = [column[1] for column in cursor.fetchall()]
            logger.info(f"Existing columns: {existing_columns}")
            
            # Define required columns
            required_columns = {
                'patient_phase': 'TEXT',
                'sentiment_score': 'FLOAT',
                'denial_category': 'TEXT',
                'denial_specifics': 'TEXT',
                'denial_resolution': 'TEXT',
                'resolution_timeframe': 'TEXT',
                'sentiment_explanation': 'TEXT',
                'experience_rating': 'FLOAT',
                'experience_explanation': 'TEXT',
                'pain_points': 'TEXT',
                'positive_aspects': 'TEXT',
                'treatment_mentions': 'TEXT',
                'support_program_mentions': 'TEXT',
                'patient_actions': 'TEXT',
                'keyword_tag': 'TEXT'
            }
            
            # Add missing columns
            for column_name, column_type in required_columns.items():
                if column_name not in existing_columns:
                    logger.info(f"Adding column: {column_name} {column_type}")
                    conn.execute(f"ALTER TABLE thread_analyses ADD COLUMN {column_name} {column_type}")
                else:
                    logger.info(f"Column {column_name} already exists")
            
            conn.commit()
            logger.info("Schema migration completed successfully")
            
    except Exception as e:
        logger.error(f"Error during schema migration: {str(e)}")
        raise

if __name__ == "__main__":
    migrate_schema() 