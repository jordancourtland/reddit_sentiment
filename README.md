# RedditScraper

A web application that crawls Reddit posts about healthcare insurance denials and analyzes them using AI to extract insights and help patterns.

## Quick Setup

### Prerequisites
- Python 3.9+
- Reddit API credentials
- OpenAI API key

### Installation Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd RedditScraper
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
Create a `.env` file in the root directory:
```env
# Reddit API credentials
client_id=your_reddit_client_id
client_secret=your_reddit_client_secret
user_agent=your_app_name/1.0 by /u/your_reddit_username

# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# Server configuration (optional)
PORT=10000
```

5. **Initialize databases**
```bash
python -c "from analysis_db import init_db; init_db()"
```

## Usage Commands

### To crawl Reddit posts
```bash
python sentinel_crawl.py
```
This will:
- Search subreddits: r/healthinsurance, r/medicalbill
- Look for keywords: "claim denied", "coverage denied", "appeal medical claim", etc.
- Store posts and comments in `reddit.db`
- Update existing threads with new comments

### To analyze collected posts
```bash
python run_analysis.py
```
This will:
- Process unanalyzed Reddit threads
- Use GPT-4 to extract insights
- Calculate persona fit scores
- Store results in `analysis.db`
- Handle rate limiting automatically

### To run the web interface
```bash
python app.py
```
Then open `http://localhost:5000` in your browser to:
- View all analyzed posts
- Search and filter results
- Sort by date, score, or comments
- View detailed thread comments
- See analysis statistics

### To run continuous operations

For production, you might want to run these in separate terminals:

```bash
# Terminal 1: Web server
python app.py

# Terminal 2: Crawling (runs once then exits)
python sentinel_crawl.py

# Terminal 3: Analysis (runs once then exits)
python run_analysis.py
```

## Customizing Search Parameters

### To change which subreddits to search
Edit `sentinel_crawl.py` and modify the `SUBREDDITS` list (around line 10):
```python
SUBREDDITS = ["healthinsurance", "medicalbill"]  # Default
# Change to:
SUBREDDITS = ["insurance", "legaladvice", "personalfinance"]  # Example
```

### To change search keywords
Edit `sentinel_crawl.py` and modify the `KEYWORDS` list (around line 11):
```python
KEYWORDS = ["claim denied", "coverage denied", "appeal medical claim", "denied claim"]  # Default
# Change to:
KEYWORDS = ["insurance dispute", "claim rejected", "pre-authorization denied"]  # Example
```

### To adjust crawling behavior
In `sentinel_crawl.py`, you can also modify:
- `POSTS_PER_KEYWORD` (line 13) - Number of posts to fetch per keyword (default: 100)
- Time range for searches - Currently searches last 30 days
- Sort order - Currently sorts by relevance

### To customize AI analysis prompts
Edit `thread_analyzer.py` to modify:
- Analysis prompts in the `analyze_thread()` function
- Persona fit criteria
- Information extraction categories

## Exporting Data to Plaintext

### Export Reddit posts to CSV
```bash
# Export all posts with basic information
sqlite3 -header -csv reddit.db "SELECT id, title, author, score, num_comments, created_utc, url FROM reddit_posts;" > posts.csv

# Export posts with full text
sqlite3 -header -csv reddit.db "SELECT * FROM reddit_posts;" > posts_full.csv
```

### Export comments to text file
```bash
# Export all comments for a specific post
sqlite3 reddit.db "SELECT author, body FROM reddit_comments WHERE post_id='POST_ID';" > comments.txt

# Export all comments with post titles
sqlite3 -header -csv reddit.db "SELECT p.title, c.author, c.body, c.score FROM reddit_comments c JOIN reddit_posts p ON c.post_id = p.id;" > all_comments.csv
```

### Export analysis results
```bash
# Export analysis summaries
sqlite3 -header -csv analysis.db "SELECT * FROM thread_analyses;" > analysis_results.csv

# Export high-persona-fit posts (score >= 7)
sqlite3 -header -csv analysis.db "SELECT thread_id, persona_fit_score, op_question_summary, community_response_summary FROM thread_analyses WHERE persona_fit_score >= 7;" > high_fit_posts.csv
```

### Create a combined report
```bash
# Join Reddit posts with their analysis
sqlite3 -header -csv reddit.db "ATTACH 'analysis.db' AS analysis; SELECT p.title, p.url, p.score, a.persona_fit_score, a.op_question_summary FROM reddit_posts p LEFT JOIN analysis.thread_analyses a ON p.id = a.thread_id;" > combined_report.csv
```

## Project Structure

- `sentinel_crawl.py` - Reddit crawler
- `thread_analyzer.py` - AI analysis engine
- `app.py` - Flask web server
- `analysis_db.py` - Analysis database manager
- `run_analysis.py` - Batch analysis runner
- `templates/index.html` - Web interface
- `reddit.db` - Reddit posts database
- `analysis.db` - Analysis results database

## Features

- Automated Reddit crawling for insurance denial posts
- AI-powered analysis using GPT-4
- Web dashboard with search and filtering
- Persona fit scoring (1-10 scale)
- Thread comment viewing
- Statistics tracking
- Duplicate detection and update handling

## Database Management

### To check database contents
```bash
# View Reddit posts
sqlite3 reddit.db "SELECT COUNT(*) FROM reddit_posts;"

# View analysis results
sqlite3 analysis.db "SELECT COUNT(*) FROM thread_analyses;"

# Check crawl state
sqlite3 reddit.db "SELECT * FROM crawl_state;"
```

### To reset databases (warning: deletes all data)
```bash
rm reddit.db analysis.db
python -c "from analysis_db import init_db; init_db()"
```