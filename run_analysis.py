import os
import time
import random
from analysis_db import AnalysisDB
from thread_analyzer import ThreadAnalyzer
import logging
from typing import Dict, List
import json
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more verbose output
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analysis.log'),
        logging.StreamHandler()
    ]
)

# Load environment variables
logging.debug("Loading environment variables...")
load_dotenv()
logging.debug(f"Environment variables loaded. OPENAI_API_KEY exists: {bool(os.getenv('OPENAI_API_KEY'))}")

class AnalysisProcess:
    def __init__(self, openai_api_key: str, batch_size: int = 20, delay_between_batches: int = 15):
        logging.debug(f"Initializing AnalysisProcess with API key length: {len(openai_api_key) if openai_api_key else 0}")
        self.db = AnalysisDB()
        self.analyzer = ThreadAnalyzer(openai_api_key)
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        self.max_retries = 5  # Increased retries
        self.base_retry_delay = 5  # Start with 5 seconds
        
        # Rate limit handling
        self.max_rate_limit_wait = 300  # Maximum wait time for rate limits (5 minutes)

    def process_batch(self) -> Dict:
        """Process a batch of unanalyzed threads."""
        stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }

        # Get unanalyzed threads
        threads = self.db.get_unanalyzed_threads(self.batch_size)
        logging.info(f"Processing batch of {len(threads)} threads")
        
        if not threads:
            logging.info("No more threads to analyze!")
            return stats

        for thread in threads:
            retries = 0
            while retries <= self.max_retries:
                try:
                    # Add a small delay before each API call to reduce rate limit likelihood
                    time.sleep(random.uniform(1.0, 3.0))
                    
                    # Analyze the thread
                    analysis = self.analyzer.analyze_thread(thread)
                    
                    if analysis:
                        # Log the full analysis for debugging
                        logging.debug(f"Analysis for thread {thread['id']}: {json.dumps(analysis, indent=2)}")
                        
                        validation_result = self.analyzer.validate_analysis(analysis)
                        if validation_result:
                            # Store the analysis
                            self.db.store_analysis(thread['id'], analysis)
                            stats['successful'] += 1
                            logging.info(f"Successfully analyzed thread {thread['id']}")
                            break  # Break out of retry loop on success
                        else:
                            if retries == self.max_retries:
                                stats['failed'] += 1
                                error_msg = f"Invalid analysis for thread {thread['id']} - validation failed"
                                stats['errors'].append(error_msg)
                                logging.error(f"{error_msg} after {retries} retries")
                            else:
                                retries += 1
                                retry_delay = self.base_retry_delay * (2 ** retries) + random.uniform(0, 1)
                                logging.warning(f"Invalid analysis for thread {thread['id']}, retrying in {retry_delay:.2f}s (attempt {retries}/{self.max_retries})")
                                time.sleep(retry_delay)
                    else:
                        if retries == self.max_retries:
                            stats['failed'] += 1
                            error_msg = f"No analysis returned for thread {thread['id']}"
                            stats['errors'].append(error_msg)
                            logging.error(f"{error_msg} after {retries} retries")
                        else:
                            retries += 1
                            retry_delay = self.base_retry_delay * (2 ** retries) + random.uniform(0, 1)
                            logging.warning(f"No analysis returned for thread {thread['id']}, retrying in {retry_delay:.2f}s (attempt {retries}/{self.max_retries})")
                            time.sleep(retry_delay)
                
                except Exception as e:
                    error_message = str(e)
                    if "rate_limit" in error_message.lower():
                        # Improved rate limit handling
                        if retries < self.max_retries:
                            retries += 1
                            
                            # Try to extract wait time from error message
                            try:
                                wait_time = float(error_message.split("try again in ")[1].split("s")[0])
                                # Add 10% buffer plus jitter to the suggested wait time
                                wait_time = min(self.max_rate_limit_wait, 
                                               wait_time * 1.1 + random.uniform(1, 5))
                            except (IndexError, ValueError):
                                # If we can't extract the wait time, use exponential backoff
                                wait_time = min(self.max_rate_limit_wait,
                                               self.base_retry_delay * (4 ** retries) + random.uniform(1, 10))
                                
                            logging.warning(f"Rate limit exceeded for thread {thread['id']}, waiting {wait_time:.2f}s before retry (attempt {retries}/{self.max_retries})")
                            time.sleep(wait_time)
                        else:
                            stats['failed'] += 1
                            stats['errors'].append(f"Rate limit exceeded for thread {thread['id']} after {retries} retries")
                            logging.error(f"Rate limit exceeded for thread {thread['id']} after {retries} retries")
                            
                            # Give OpenAI API a break if we've hit multiple rate limits
                            cooldown = 60
                            logging.info(f"Taking a {cooldown}s cooldown to respect API rate limits")
                            time.sleep(cooldown)
                            break
                    else:
                        if retries < self.max_retries:
                            retries += 1
                            retry_delay = self.base_retry_delay * (2 ** retries) + random.uniform(0, 1)
                            logging.warning(f"Error processing thread {thread['id']}: {error_message}, retrying in {retry_delay:.2f}s (attempt {retries}/{self.max_retries})")
                            time.sleep(retry_delay)
                        else:
                            stats['failed'] += 1
                            stats['errors'].append(f"Error processing thread {thread['id']}: {error_message}")
                            logging.error(f"Error processing thread {thread['id']}: {error_message} after {retries} retries")
                            break
            
            stats['processed'] += 1

        return stats

    def process_all_threads(self):
        """Process all threads in the database until no more are left to analyze."""
        logging.info("Starting analysis of all unanalyzed threads")
        
        total_stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        batch_num = 1
        
        while True:
            logging.info(f"Processing batch #{batch_num}")
            
            # Process a batch
            stats = self.process_batch()
            
            # Update total stats
            total_stats['processed'] += stats['processed']
            total_stats['successful'] += stats['successful']
            total_stats['failed'] += stats['failed']
            total_stats['errors'].extend(stats['errors'])
            
            # Log batch statistics
            logging.info(f"Batch #{batch_num} completed: {json.dumps(stats, indent=2)}")
            
            # Get overall statistics
            db_stats = self.db.get_analysis_stats()
            logging.info(f"Overall statistics: {json.dumps(db_stats, indent=2)}")
            
            # If no threads were processed in this batch, we're done
            if stats['processed'] == 0:
                logging.info("All threads have been analyzed! Process complete.")
                break
                
            # Otherwise wait before next batch
            logging.info(f"Waiting {self.delay_between_batches} seconds before next batch")
            time.sleep(self.delay_between_batches)
            
            batch_num += 1
        
        return total_stats

def main():
    # Get OpenAI API key from environment
    api_key = os.getenv('OPENAI_API_KEY')
    logging.debug(f"API key from environment: {'*' * len(api_key) if api_key else 'None'}")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Create analysis process
    process = AnalysisProcess(api_key, batch_size=20, delay_between_batches=15)
    
    try:
        # Process all threads
        logging.info("Starting to process all threads in the database...")
        total_stats = process.process_all_threads()
        
        # Log final statistics
        logging.info(f"Process completed. Final statistics: {json.dumps(total_stats, indent=2)}")
        
    except KeyboardInterrupt:
        logging.info("Process stopped by user.")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
    
    logging.info("Analysis process exiting.")

if __name__ == "__main__":
    main() 