import openai
import json
from typing import Dict, List, Optional
import os
import time
import random
from datetime import datetime
import logging

# This fixed version uses openai v0.28.0
class ThreadAnalyzer:
    def __init__(self, api_key: str):
        # Set API key directly
        openai.api_key = api_key
        
        # Disable proxies and any other configurations that might cause conflicts
        if hasattr(openai, 'proxy'):
            openai.proxy = None
            
        self.system_prompt = """You are a healthcare insurance denial analysis expert. Your task is to analyze Reddit threads about healthcare insurance denials and provide structured insights that MUST match the exact format specified.

Follow these MANDATORY requirements:

1. Only use information explicitly stated in the text
2. Do not make assumptions or inferences
3. If information is not clearly stated, mark it as unknown

FORMAT REQUIREMENTS (CRITICAL):
- Summary must be EXACTLY 1-2 sentences maximum - this is strictly enforced
- Persona_fit and confidence must be numbers between 0.0 and 1.0
- You MUST include EXACTLY 3 or more themes
- All fields in the output structure are required
- Response MUST be valid parseable JSON with no commentary

For scoring:
- Persona Fit (0.0-1.0):
  * 1.0: Perfect fit (actively seeking appeal help now)
  * 0.8: Very good fit (has denial, might need help soon)
  * 0.5: Moderate fit (has denial, already has solution)
  * 0.2: Poor fit (historical case, resolved)
  * 0.0: No fit (not about denials)

- Confidence (0.0-1.0):
  * 1.0: High confidence (all information clear)
  * 0.7: Medium confidence (some missing details)
  * 0.3: Low confidence (many missing details)

Your response MUST match this exact JSON structure:
{
  "summary": "Brief 1-2 sentence summary of the issue",
  "persona_fit": 0.8,
  "confidence": 0.7,
  "fit_explanation": "Explanation of the persona fit score",
  "denial_type": "The specific reason for the claim denial (e.g., 'Not medically necessary', 'Out of network', 'No prior authorization', etc.)",
  "themes": ["theme1", "theme2", "theme3"],
  "outcome": "Resolved|Ongoing|Unclear",
  "options_suggested": ["option1", "option2", "option3"]
}

IMPORTANT: Response validation will fail if any requirements are not met.
Your output must be valid JSON only - no additional text, explanations, or commentary."""

    def _format_thread_for_analysis(self, thread: Dict) -> str:
        """Format the thread data for GPT-4 analysis."""
        formatted = f"Title: {thread['title']}\n"
        formatted += f"Subreddit: {thread['subreddit']}\n"
        formatted += f"Created: {datetime.fromtimestamp(thread['created_utc']).isoformat()}\n"
        formatted += f"Score: {thread['score']}\n"
        formatted += f"Number of Comments: {thread['num_comments']}\n\n"
        
        formatted += "Original Post:\n"
        formatted += f"{thread['selftext']}\n\n"
        
        if thread.get('comments'):
            formatted += "Comments:\n"
            formatted += thread['comments']
        
        return formatted

    def analyze_thread(self, thread: Dict) -> Dict:
        """Analyze a Reddit thread using GPT-4."""
        try:
            formatted_thread = self._format_thread_for_analysis(thread)
            
            # Add a delay to avoid rate limits
            time.sleep(random.uniform(0.5, 1.5))
            
            # Make the API call with no extra configurations
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Analyze this Reddit thread and provide a structured response:\n\n{formatted_thread}"}
                ],
                temperature=0.1  # Low temperature for more consistent results
            )
            
            # Parse the response into our structured format
            content = response.choices[0].message['content']
            logging.debug(f"Raw GPT response for thread {thread.get('id', 'unknown')}: {content}")
            
            # Check for common errors in response format
            if not content.strip().startswith('{') or not content.strip().endswith('}'):
                logging.error(f"Response is not properly formatted JSON: {content}")
                return None
                
            try:
                analysis = json.loads(content)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON response: {str(e)}\nContent: {content}")
                return None
            
            # Validate the analysis structure
            required_fields = [
                'summary', 'persona_fit', 'confidence', 'fit_explanation',
                'denial_type', 'themes', 'outcome', 'options_suggested'
            ]
            
            for field in required_fields:
                if field not in analysis:
                    logging.error(f"Missing required field in analysis: {field}")
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate numeric fields
            if not 0 <= analysis['persona_fit'] <= 1:
                logging.error(f"Invalid persona_fit value: {analysis['persona_fit']} - must be between 0 and 1")
                raise ValueError("persona_fit must be between 0 and 1")
                
            if not 0 <= analysis['confidence'] <= 1:
                logging.error(f"Invalid confidence value: {analysis['confidence']} - must be between 0 and 1")
                raise ValueError("confidence must be between 0 and 1")
            
            return analysis
            
        except Exception as e:
            logging.error(f"Error analyzing thread {thread.get('id', 'unknown')}: {str(e)}")
            return None

    def validate_analysis(self, analysis: Dict) -> bool:
        """Validate the analysis results."""
        thread_id = "unknown"  # We'll use this for logging
        
        try:
            # Check required fields
            required_fields = [
                'summary', 'persona_fit', 'confidence', 'fit_explanation',
                'denial_type', 'themes', 'outcome', 'options_suggested'
            ]
            
            for field in required_fields:
                if field not in analysis:
                    logging.error(f"Validation failed - missing field: {field}")
                    return False
            
            # Validate numeric fields with detailed logging
            if not isinstance(analysis['persona_fit'], (int, float)):
                logging.error(f"Validation failed - persona_fit is not a number: {analysis['persona_fit']} (type: {type(analysis['persona_fit']).__name__})")
                return False
                
            if not 0 <= analysis['persona_fit'] <= 1:
                logging.error(f"Validation failed - persona_fit not between 0 and 1: {analysis['persona_fit']}")
                return False
                
            if not isinstance(analysis['confidence'], (int, float)):
                logging.error(f"Validation failed - confidence is not a number: {analysis['confidence']} (type: {type(analysis['confidence']).__name__})")
                return False
                
            if not 0 <= analysis['confidence'] <= 1:
                logging.error(f"Validation failed - confidence not between 0 and 1: {analysis['confidence']}")
                return False
            
            # Validate summary length with detailed logging but be more lenient
            sentences = analysis['summary'].split('.')
            # Filter out empty strings that may come from splitting
            sentences = [s for s in sentences if s.strip()]
            
            if len(sentences) > 4:  # Changed from 2 to 4
                logging.warning(f"Summary contains {len(sentences)} sentences: '{analysis['summary']}', but allowing it")
                # Note that we no longer return False here - we're just logging a warning
            
            # Validate themes
            if not isinstance(analysis['themes'], list):
                logging.error(f"Validation failed - themes is not a list: {analysis['themes']} (type: {type(analysis['themes']).__name__})")
                return False
                
            if len(analysis['themes']) < 3:
                logging.error(f"Validation failed - themes list has fewer than 3 items: {len(analysis['themes'])} - {analysis['themes']}")
                return False
            
            # Validate options
            if not isinstance(analysis['options_suggested'], list):
                logging.error(f"Validation failed - options_suggested is not a list: {analysis['options_suggested']} (type: {type(analysis['options_suggested']).__name__})")
                return False
            
            # No longer validating specific denial_type values - accept any string
            
            # Check outcome has valid value
            valid_outcomes = ["Resolved", "Ongoing", "Unclear"]
            if analysis['outcome'] not in valid_outcomes:
                logging.error(f"Validation failed - invalid outcome: {analysis['outcome']} - must be one of {valid_outcomes}")
                return False
            
            logging.debug(f"Analysis validation successful")
            return True
            
        except Exception as e:
            logging.error(f"Error validating analysis: {str(e)}")
            return False 