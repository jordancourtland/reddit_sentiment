import google.generativeai as genai
import json
from typing import Dict, List, Optional
import os
import time
import random
from datetime import datetime
import logging

# This fixed version uses OpenAI v0.28.0
class ThreadAnalyzer:
    def __init__(self, api_key: str):
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        self.system_prompt = """You are a patient experience and sentiment analysis expert specializing in healthcare treatment journeys, with particular focus on insurance denials and patient experience touchpoints. Your task is to analyze Reddit threads about patient experiences and provide structured insights focused on patient sentiment, journey phases, and denial experiences.

PATIENT EXPERIENCE PHASES TO IDENTIFY:

1. Symptom Awareness
   - Symptom Onset
   - Initial Consultation

2. Symptom Diagnosis  
   - Preliminary Assessment
   - Diagnostic Testing
   - Receive Diagnosis

3. Treatment Decision
   - Planning Treatment Options
   - Qualification for Treatment
   - Determine Insurance Coverage + Finances
   - Treatment Enrollment

4. Insurance & Financial Support
   - Start Insurance Review
   - Wait for Prior Authorization
   - Resolve Delays & Denials
   - Learn about Savings Programs
   - Enroll in Savings & Support Programs
   - Confirm Approval

5. Treatment Onboarding (Induction)
   - Onboard to Program Services
   - Confirm Delivery Details

6. Initial Treatment
   - Receive or Confirm Medication Delivery
   - Receive any necessary training for application & handling
   - Receive first dose

7. Maintaining Treatment
   - Evaluate Outcome
   - Setup Treatment Routine

8. Ongoing Treatment
   - Monitor Progress
   - Monitor Claims & Transactions
   - Attend Check-ins
   - Provide Feedback

PATIENT TOUCHPOINTS TO IDENTIFY:
- At Home
- SEO / SEM
- Treatment / Company Website
- Phone
- Telehealth
- Doctor's Office
- Patient Portal / App
- Nurse Guide
- Other

PLAYERS TO IDENTIFY:
- HCP: Doctor
- HCP: Nurse
- HCP: Bio-Coordinator
- HCP: Staff
- Insurer
- Pharmaceutical Company
- Caregiver

DENIAL CATEGORIES (MANDATORY - EVERY DENIAL MUST BE CATEGORIZED):
- Medical Necessity: "not medically necessary", "experimental", "investigational", "not covered for this diagnosis"
- Prior Authorization: "requires prior auth", "pre-authorization needed", "not pre-approved", "authorization required"
- Formulary: "not on formulary", "step therapy required", "tier restrictions", "not in drug formulary"
- Coordination of Benefits: "primary vs secondary", "coordination issues", "other insurance primary"
- Network: "out of network", "provider not covered", "out of network provider"
- Documentation: "missing documentation", "incomplete forms", "missing medical records"
- Coverage Limits: "exceeded coverage limits", "annual limit reached", "lifetime maximum"
- Timing: "too early for refill", "outside coverage period", "expired authorization"
- Eligibility: "not eligible for coverage", "coverage terminated", "enrollment issues"

IMPORTANT: If a denial is mentioned, you MUST categorize it into one of the above specific categories. Do NOT use "None", "Other", or "Unclear" for denial categories. If the denial doesn't clearly fit the above categories, choose the closest match and explain why in the denial_specifics.

RESOLUTION TIMEFRAMES:
- immediate: Resolved same day
- 1-7_days: Resolved within a week
- 1-4_weeks: Resolved within a month
- 1-3_months: Resolved within 3 months
- ongoing: Still being resolved

ANALYSIS REQUIREMENTS:

1. Identify which patient phase(s) the post relates to
2. Identify specific patient actions mentioned
3. Identify touchpoints and players involved
4. Analyze sentiment (positive/negative/neutral) with confidence
5. Rate overall experience (1-10 scale)
6. Identify pain points and positive aspects
7. Focus on emotional and practical aspects of the patient journey
8. Assess persona fit for healthcare patient experience analysis
9. Identify denial types and categories if applicable (MANDATORY categorization)
10. Determine outcome and suggested options

Your response MUST match this exact JSON structure:
{
  "op_summary": "Brief summary of what the patient was experiencing/asking",
  "responses_summary": "Brief summary of community responses and advice",
  "patient_phase": "Primary phase (Symptom Awareness|Symptom Diagnosis|Treatment Decision|Insurance & Financial Support|Treatment Onboarding|Initial Treatment|Maintaining Treatment|Ongoing Treatment)",
  "patient_actions": ["action1", "action2", "action3"],
  "touchpoints": ["touchpoint1", "touchpoint2"],
  "players": ["player1", "player2"],
  "phase_sentiments": {"phase_name": 0.7, "phase_name2": 0.3},
  "sentiment_score": 0.7,
  "sentiment_explanation": "Explanation of sentiment analysis",
  "experience_rating": 7.5,
  "experience_explanation": "Explanation of experience rating",
  "pain_points": ["pain_point1", "pain_point2"],
  "positive_aspects": ["positive1", "positive2"],
  "confidence": 0.8,
  "themes": ["theme1", "theme2", "theme3"],
  "treatment_mentions": ["treatment1", "treatment2"],
  "support_program_mentions": ["program1", "program2"],
  "persona_fit": 0.8,
  "fit_explanation": "Explanation of how well this post fits the patient experience persona",
  "denial_type": "Complete|Partial|None|Unclear",
  "denial_category": "Medical Necessity|Prior Authorization|Formulary|Coordination of Benefits|Network|Documentation|Coverage Limits|Timing|Eligibility",
  "denial_specifics": ["specific_reason1", "specific_reason2"],
  "denial_resolution": "Resolved|Ongoing|Unresolved|Appealed|Escalated",
  "resolution_timeframe": "immediate|1-7_days|1-4_weeks|1-3_months|ongoing",
  "outcome": "Resolved|Ongoing|Unresolved|Unclear",
  "options_suggested": ["option1", "option2", "option3"]
}

SENTIMENT SCORING (0.0-1.0):
- 0.0-0.3: Very negative experience
- 0.4-0.6: Neutral/mixed experience  
- 0.7-1.0: Positive experience

EXPERIENCE RATING (1-10):
- 1-3: Poor experience
- 4-6: Mixed experience
- 7-10: Good experience

PERSONA FIT (0.0-1.0):
- 0.0-0.3: Not relevant to patient experience
- 0.4-0.6: Somewhat relevant
- 0.7-1.0: Highly relevant to patient experience

DENIAL CATEGORIZATION RULES:
- If ANY denial is mentioned, you MUST categorize it into one of the 9 specific categories
- Do NOT use "None", "Other", or "Unclear" for denial_category
- If multiple denials, categorize the primary one
- If unclear which category, choose the closest match and explain in denial_specifics

IMPORTANT: Focus on patient sentiment, emotional journey, and practical experience aspects. Identify specific treatments, support programs, patient actions, touchpoints, and players mentioned. For denials, capture both the specific reason and the broader category. Return ONLY valid JSON - no additional text or explanations."""

    def analyze_thread(self, thread: Dict) -> Optional[Dict]:
        """Analyze a Reddit thread using Gemini."""
        try:
            formatted_thread = self._format_thread_for_analysis(thread)
            
            # Add a delay to respect rate limits
            time.sleep(random.uniform(1.0, 2.0))
            
            # Create the prompt
            prompt = f"{self.system_prompt}\n\nAnalyze this patient experience thread and provide structured insights:\n\n{formatted_thread}"
            
            # Call Gemini API
            response = self.model.generate_content(prompt)
            
            # Get the response text
            content = response.text
            logging.debug(f"Raw Gemini response for thread {thread.get('id', 'unknown')}: {content}")
            
            # Add null check before calling strip()
            if content is None:
                logging.error(f"Received empty response from Gemini for thread {thread.get('id', 'unknown')}")
                return None
            
            # Extract JSON from response
            try:
                # Find JSON in the response
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx != 0:
                    json_str = content[start_idx:end_idx]
                    analysis = json.loads(json_str)
                else:
                    logging.error("No JSON found in response")
                    return None
                    
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON response: {str(e)}\nContent: {content}")
                return None
            
            # Validate the analysis structure with safe type checking
            required_fields = [
                'op_summary', 'responses_summary', 'patient_phase', 'patient_actions',
                'touchpoints', 'players', 'phase_sentiments', 'sentiment_score', 
                'sentiment_explanation', 'experience_rating', 'experience_explanation', 
                'pain_points', 'positive_aspects', 'confidence', 'themes', 
                'treatment_mentions', 'support_program_mentions', 'persona_fit', 
                'fit_explanation', 'denial_type', 'denial_category', 'denial_specifics',
                'denial_resolution', 'resolution_timeframe', 'outcome', 'options_suggested'
            ]
            
            for field in required_fields:
                if field not in analysis:
                    logging.error(f"Missing required field in analysis: {field}")
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate numeric fields with safe type checking
            numeric_fields = ['sentiment_score', 'experience_rating', 'confidence', 'persona_fit']
            for field in numeric_fields:
                if not isinstance(analysis.get(field), (int, float)) or analysis[field] is None:
                    logging.error(f"Invalid {field} value: {analysis.get(field)}")
                    raise ValueError(f"{field} must be a number")
            
            # Validate ranges
            if not 0 <= analysis['sentiment_score'] <= 1:
                raise ValueError("sentiment_score must be between 0 and 1")
            if not 1 <= analysis['experience_rating'] <= 10:
                raise ValueError("experience_rating must be between 1 and 10")
            if not 0 <= analysis['confidence'] <= 1:
                raise ValueError("confidence must be between 0 and 1")
            if not 0 <= analysis['persona_fit'] <= 1:
                raise ValueError("persona_fit must be between 0 and 1")
            
            # Validate denial category (must be one of the specific categories)
            valid_denial_categories = [
                'Medical Necessity', 'Prior Authorization', 'Formulary', 
                'Coordination of Benefits', 'Network', 'Documentation',
                'Coverage Limits', 'Timing', 'Eligibility'
            ]
            
            if analysis.get('denial_type') in ['Complete', 'Partial'] and analysis.get('denial_category'):
                if analysis['denial_category'] not in valid_denial_categories:
                    logging.warning(f"Invalid denial category: {analysis['denial_category']}, using closest match")
                    # Try to map to closest category
                    if 'necessity' in analysis['denial_category'].lower():
                        analysis['denial_category'] = 'Medical Necessity'
                    elif 'auth' in analysis['denial_category'].lower():
                        analysis['denial_category'] = 'Prior Authorization'
                    elif 'formulary' in analysis['denial_category'].lower():
                        analysis['denial_category'] = 'Formulary'
                    elif 'network' in analysis['denial_category'].lower():
                        analysis['denial_category'] = 'Network'
                    elif 'document' in analysis['denial_category'].lower():
                        analysis['denial_category'] = 'Documentation'
                    elif 'coordination' in analysis['denial_category'].lower():
                        analysis['denial_category'] = 'Coordination of Benefits'
                    elif 'limit' in analysis['denial_category'].lower():
                        analysis['denial_category'] = 'Coverage Limits'
                    elif 'timing' in analysis['denial_category'].lower():
                        analysis['denial_category'] = 'Timing'
                    elif 'eligibility' in analysis['denial_category'].lower():
                        analysis['denial_category'] = 'Eligibility'
                    else:
                        analysis['denial_category'] = 'Medical Necessity'  # Default fallback
            
            return analysis
            
        except Exception as e:
            logging.error(f"Error analyzing thread {thread.get('id', 'unknown')}: {str(e)}")
            return None

    def _format_thread_for_analysis(self, thread: Dict) -> str:
        """Format a thread for analysis."""
        try:
            # Format the original post
            op_text = f"Original Post:\nTitle: {thread.get('title', 'No title')}\n"
            op_text += f"Subreddit: r/{thread.get('subreddit', 'unknown')}\n"
            op_text += f"Content: {thread.get('selftext', 'No content')}\n"
            
            # Add comments if available
            comments_text = ""
            if 'comments' in thread and thread['comments']:
                comments_text = "\nCommunity Responses:\n"
                for comment in thread['comments'][:5]:  # Limit to first 5 comments
                    comments_text += f"- {comment.get('body', 'No content')}\n"
            
            return op_text + comments_text
            
        except Exception as e:
            logging.error(f"Error formatting thread: {str(e)}")
            return str(thread)

    def validate_analysis(self, analysis: Dict) -> bool:
        """Validate that the analysis contains all required fields."""
        try:
            required_fields = [
                'op_summary', 'responses_summary', 'patient_phase', 'patient_actions',
                'touchpoints', 'players', 'phase_sentiments', 'sentiment_score', 
                'sentiment_explanation', 'experience_rating', 'experience_explanation', 
                'pain_points', 'positive_aspects', 'confidence', 'themes', 
                'treatment_mentions', 'support_program_mentions', 'persona_fit', 
                'fit_explanation', 'denial_type', 'denial_category', 'denial_specifics',
                'denial_resolution', 'resolution_timeframe', 'outcome', 'options_suggested'
            ]
            
            for field in required_fields:
                if field not in analysis:
                    logging.error(f"Missing required field: {field}")
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f"Error validating analysis: {str(e)}")
            return False 