"""
Configuration manager for the Reddit sentiment analysis project
"""

import os
import json
from typing import Dict, List, Optional
from dotenv import load_dotenv

class ConfigManager:
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager."""
        load_dotenv()
        self.config_file = config_file
        self.custom_config = {}
        
        # Only load custom config if config_file is provided and exists
        if config_file is not None and os.path.exists(config_file):
            self.load_custom_config(config_file)
    
    def load_custom_config(self, config_file: str):
        """Load custom configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                self.custom_config = json.load(f)
            print(f"✅ Loaded custom configuration from {config_file}")
        except Exception as e:
            print(f"Error loading custom config: {e}")
    
    def get_subreddits(self, category: Optional[str] = None) -> List[str]:
        """Get subreddits to crawl."""
        # Prioritize JSON configuration over old config
        if self.custom_config and 'subreddits' in self.custom_config:
            if category and category in self.custom_config['subreddits']:
                return self.custom_config['subreddits'][category]
            elif isinstance(self.custom_config['subreddits'], list):
                return self.custom_config['subreddits']
        
        # Fallback to old config if JSON not available
        from config import SUBREDDITS
        return SUBREDDITS
    
    def get_keywords(self, category: str = "all") -> List[str]:
        """Get keywords to search for."""
        # Prioritize JSON configuration over old config
        if self.custom_config and 'keywords' in self.custom_config:
            if category in self.custom_config['keywords']:
                return self.custom_config['keywords'][category]
            elif isinstance(self.custom_config['keywords'], list):
                return self.custom_config['keywords']
        
        # Fallback to old config if JSON not available
        from config import KEYWORD_CATEGORIES, ALL_KEYWORDS
        return KEYWORD_CATEGORIES.get(category, ALL_KEYWORDS)
    
    def get_crawl_config(self) -> Dict:
        """Get crawling configuration."""
        # Start with default config
        from config import CRAWL_CONFIG
        base_config = CRAWL_CONFIG.copy()
        
        # Override with JSON config if available
        if self.custom_config and 'crawl_config' in self.custom_config:
            base_config.update(self.custom_config['crawl_config'])
        
        return base_config
    
    def get_analysis_config(self) -> Dict:
        """Get analysis configuration."""
        # Start with default config
        from config import ANALYSIS_CONFIG
        base_config = ANALYSIS_CONFIG.copy()
        
        # Override with JSON config if available
        if self.custom_config and 'analysis_config' in self.custom_config:
            base_config.update(self.custom_config['analysis_config'])
        
        return base_config
    
    def get_export_config(self) -> Dict:
        """Get export configuration."""
        # Start with default config
        from config import EXPORT_CONFIG
        base_config = EXPORT_CONFIG.copy()
        
        # Override with JSON config if available
        if self.custom_config and 'export_config' in self.custom_config:
            base_config.update(self.custom_config['export_config'])
        
        return base_config
    
    def get_reddit_credentials(self) -> Dict:
        """Get Reddit API credentials."""
        return {
            "client_id": os.getenv("REDDIT_CLIENT_ID"),
            "client_secret": os.getenv("REDDIT_CLIENT_SECRET"),
            "user_agent": os.getenv("REDDIT_USER_AGENT")
        }
    
    def validate_config(self) -> bool:
        """Validate configuration."""
        credentials = self.get_reddit_credentials()
        if not all(credentials.values()):
            print("❌ Missing Reddit API credentials in .env file")
            return False
        
        subreddits = self.get_subreddits()
        if not subreddits:
            print("❌ No subreddits configured")
            return False
        
        keywords = self.get_keywords()
        if not keywords:
            print("❌ No keywords configured")
            return False
        
        print("✅ Configuration validated successfully")
        return True
    
    def print_config_summary(self):
        """Print a summary of current configuration."""
        print("\n" + "="*60)
        print("CONFIGURATION SUMMARY")
        print("="*60)
        
        subreddits = self.get_subreddits()
        print(f"📁 Subreddits: {len(subreddits)}")
        for sub in subreddits[:5]:  # Show first 5
            print(f"   - r/{sub}")
        if len(subreddits) > 5:
            print(f"   ... and {len(subreddits) - 5} more")
        
        keywords = self.get_keywords()
        print(f"\n🔍 Keywords: {len(keywords)}")
        for kw in keywords[:5]:  # Show first 5
            print(f"   - '{kw}'")
        if len(keywords) > 5:
            print(f"   ... and {len(keywords) - 5} more")
        
        crawl_config = self.get_crawl_config()
        print(f"\n🕷️ Crawl Settings:")
        print(f"   - Posts per search: {crawl_config['posts_per_search']}")
        print(f"   - Comments limit: {crawl_config['comments_limit']}")
        print(f"   - Delay between requests: {crawl_config.get('delay_between_requests', 'N/A')}s")
        
        analysis_config = self.get_analysis_config()
        print(f"\n🤖 Analysis Settings:")
        print(f"   - Batch size: {analysis_config['batch_size']}")
        print(f"   - Delay between batches: {analysis_config['delay_between_batches']}s")
        print(f"   - Confidence threshold: {analysis_config['confidence_threshold']}")
        
        print("="*60 + "\n") 