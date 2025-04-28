"""
Content Aggregator - Simple RSS Feed Reader
Initial implementation focusing on basic functionality
"""

import json
import os
import feedparser
from datetime import datetime
from flask import Flask, render_template, jsonify

app = Flask(__name__, 
            template_folder='frontend/web/templates',
            static_folder='frontend/web/static')

def load_config():
    """Load configuration from sources.json"""
    config_path = os.path.join('config', 'sources.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading configuration: {e}")
        return {"rss_feeds": []}

def fetch_rss_content(feeds):
    """Fetch content from RSS feeds"""
    all_entries = []
    
    for feed in feeds:
        try:
            parsed_feed = feedparser.parse(feed['url'])
            
            for entry in parsed_feed.entries:
                # Create a standardized entry format
                processed_entry = {
                    'id': entry.get('id', entry.get('link', '')),
                    'title': entry.get('title', 'No title'),
                    'summary': entry.get('summary', entry.get('description', 'No description')),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', datetime.now().isoformat()),
                    'source': feed['name'],
                    'category': feed.get('category', 'uncategorized')
                }
                all_entries.append(processed_entry)
                
        except Exception as e:
            print(f"Error fetching feed {feed['name']}: {e}")
    
    # Sort entries by publication date (newest first)
    # This is a simple approach and might need refinement based on date formats
    all_entries.sort(key=lambda x: x['published'], reverse=True)
    
    return all_entries

@app.route('/')
def index():
    """Main page - display all content"""
    config = load_config()
    entries = fetch_rss_content(config.get('rss_feeds', []))
    
    # Group entries by category
    categories = {}
    for entry in entries:
        category = entry['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(entry)
    
    return render_template('index.html', 
                          entries=entries, 
                          categories=categories)

@app.route('/api/entries')
def api_entries():
    """API endpoint to get all entries as JSON"""
    config = load_config()
    entries = fetch_rss_content(config.get('rss_feeds', []))
    return jsonify(entries)

if __name__ == '__main__':
    # Create necessary directories if they don't exist
    os.makedirs('frontend/web/templates', exist_ok=True)
    os.makedirs('frontend/web/static', exist_ok=True)
    
    # Check if template exists, if not create a basic one
    template_path = os.path.join('frontend', 'web', 'templates', 'index.html')
    if not os.path.exists(template_path):
        with open(template_path, 'w') as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Content Aggregator</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background-color: #333; color: white; padding: 10px 20px; margin-bottom: 20px; }
        .entry { background-color: white; margin-bottom: 15px; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .entry h3 { margin-top: 0; }
        .entry-meta { color: #666; font-size: 0.9em; margin-bottom: 10px; }
        .category-section { margin-bottom: 30px; }
        .category-header { background-color: #eee; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Content Aggregator</h1>
        <p>Your personalized content feed</p>
    </div>
    
    <div class="container">
        {% for category, category_entries in categories.items() %}
            <div class="category-section">
                <div class="category-header">
                    <h2>{{ category|capitalize }}</h2>
                </div>
                
                {% for entry in category_entries %}
                    <div class="entry">
                        <h3><a href="{{ entry.link }}" target="_blank">{{ entry.title }}</a></h3>
                        <div class="entry-meta">
                            <span>Source: {{ entry.source }}</span> | 
                            <span>Published: {{ entry.published }}</span>
                        </div>
                        <div class="entry-summary">
                            {{ entry.summary|safe }}
                        </div>
                    </div>
                {% endfor %}
            </div>
        {% endfor %}
        
        {% if not categories %}
            <p>No content available. Please check your feed configuration.</p>
        {% endif %}
    </div>
</body>
</html>""")
    
    # Create a basic CSS file
    css_path = os.path.join('frontend', 'web', 'static', 'style.css')
    if not os.path.exists(css_path):
        with open(css_path, 'w') as f:
            f.write("""/* Basic styles will be added here */""")
    
    print("Starting Content Aggregator...")
    app.run(debug=True)
