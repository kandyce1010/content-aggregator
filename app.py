"""
Content Aggregator - Web Interface
Displays content from multiple sources including RSS feeds, GitHub, LinkedIn, and YouTube
"""

import json
import os
import sys
from datetime import datetime
from flask import Flask, render_template, jsonify, request

# Add the parent directory to sys.path to allow importing from backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.aggregator import ContentAggregator

app = Flask(__name__, 
            template_folder='frontend/web/templates',
            static_folder='frontend/web/static')

# Initialize the content aggregator
aggregator = ContentAggregator()

@app.route('/')
def index():
    """Main page - display all content"""
    # Get filter parameters
    category = request.args.get('category')
    days = request.args.get('days', 7, type=int)
    search_query = request.args.get('search')
    
    # Get the latest content file or fetch new content
    latest_file = aggregator.get_latest_content_file()
    
    if latest_file:
        entries = aggregator.load_content(latest_file)
    else:
        entries = aggregator.fetch_all_content()
        aggregator.save_content(entries)
    
    # Apply filters
    if category:
        entries = aggregator.filter_content_by_category(entries, category)
    
    entries = aggregator.filter_content_by_date(entries, days)
    
    if search_query:
        entries = aggregator.search_content(entries, search_query)
    
    # Group entries by category
    categories = {}
    for entry in entries:
        entry_category = entry.get('category', 'Uncategorized')
        if entry_category not in categories:
            categories[entry_category] = []
        categories[entry_category].append(entry)
    
    # Get all available categories for the filter dropdown
    all_categories = set()
    for entry in entries:
        all_categories.add(entry.get('category', 'Uncategorized'))
    
    return render_template('index.html', 
                          entries=entries, 
                          categories=categories,
                          all_categories=sorted(all_categories),
                          selected_category=category,
                          days=days,
                          search_query=search_query)

@app.route('/refresh')
def refresh():
    """Refresh content from all sources"""
    entries = aggregator.fetch_all_content()
    aggregator.save_content(entries)
    return jsonify({"status": "success", "message": f"Fetched {len(entries)} items"})

@app.route('/api/entries')
def api_entries():
    """API endpoint to get all entries as JSON"""
    # Get filter parameters
    category = request.args.get('category')
    days = request.args.get('days', 7, type=int)
    search_query = request.args.get('search')
    
    # Get the latest content file or fetch new content
    latest_file = aggregator.get_latest_content_file()
    
    if latest_file:
        entries = aggregator.load_content(latest_file)
    else:
        entries = aggregator.fetch_all_content()
        aggregator.save_content(entries)
    
    # Apply filters
    if category:
        entries = aggregator.filter_content_by_category(entries, category)
    
    entries = aggregator.filter_content_by_date(entries, days)
    
    if search_query:
        entries = aggregator.search_content(entries, search_query)
    
    return jsonify(entries)

@app.route('/api/categories')
def api_categories():
    """API endpoint to get all available categories"""
    latest_file = aggregator.get_latest_content_file()
    
    if latest_file:
        entries = aggregator.load_content(latest_file)
    else:
        entries = aggregator.fetch_all_content()
        aggregator.save_content(entries)
    
    categories = set()
    for entry in entries:
        categories.add(entry.get('category', 'Uncategorized'))
    
    return jsonify(sorted(list(categories)))

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
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <div class="header">
        <h1>Content Aggregator</h1>
        <p>Your personalized content feed</p>
    </div>
    
    <div class="filters">
        <form action="/" method="get">
            <div class="filter-group">
                <label for="category">Category:</label>
                <select name="category" id="category">
                    <option value="">All Categories</option>
                    {% for cat in all_categories %}
                        <option value="{{ cat }}" {% if cat == selected_category %}selected{% endif %}>{{ cat }}</option>
                    {% endfor %}
                </select>
            </div>
            
            <div class="filter-group">
                <label for="days">Time Period:</label>
                <select name="days" id="days">
                    <option value="1" {% if days == 1 %}selected{% endif %}>Last 24 hours</option>
                    <option value="7" {% if days == 7 %}selected{% endif %}>Last 7 days</option>
                    <option value="30" {% if days == 30 %}selected{% endif %}>Last 30 days</option>
                    <option value="90" {% if days == 90 %}selected{% endif %}>Last 90 days</option>
                </select>
            </div>
            
            <div class="filter-group">
                <label for="search">Search:</label>
                <input type="text" name="search" id="search" value="{{ search_query or '' }}">
            </div>
            
            <button type="submit">Apply Filters</button>
            <a href="/" class="reset-button">Reset</a>
        </form>
        
        <button id="refresh-button" onclick="refreshContent()">Refresh Content</button>
    </div>
    
    <div class="container">
        {% for category, category_entries in categories.items() %}
            <div class="category-section">
                <div class="category-header">
                    <h2>{{ category }}</h2>
                </div>
                
                <div class="entries-grid">
                    {% for entry in category_entries %}
                        <div class="entry {% if 'YouTube' in entry.source %}entry-youtube{% endif %}">
                            <h3><a href="{{ entry.link }}" target="_blank">{{ entry.title }}</a></h3>
                            <div class="entry-meta">
                                <span>Source: {{ entry.source }}</span> | 
                                <span>Published: {{ entry.published }}</span>
                            </div>
                            
                            {% if 'YouTube' in entry.source and entry.thumbnail %}
                                <div class="entry-thumbnail">
                                    <a href="{{ entry.link }}" target="_blank">
                                        <img src="{{ entry.thumbnail }}" alt="{{ entry.title }}">
                                    </a>
                                </div>
                            {% endif %}
                            
                            <div class="entry-summary">
                                {{ entry.summary|truncate(200)|safe }}
                            </div>
                            
                            {% if 'YouTube' in entry.source and entry.views %}
                                <div class="entry-stats">
                                    <span>{{ entry.views }} views</span>
                                    {% if entry.likes %} | <span>{{ entry.likes }} likes</span>{% endif %}
                                </div>
                            {% endif %}
                        </div>
                    {% endfor %}
                </div>
            </div>
        {% endfor %}
        
        {% if not categories %}
            <p>No content available. Please check your feed configuration or try different filters.</p>
        {% endif %}
    </div>
    
    <script>
        function refreshContent() {
            document.getElementById('refresh-button').disabled = true;
            document.getElementById('refresh-button').textContent = 'Refreshing...';
            
            fetch('/refresh')
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    location.reload();
                })
                .catch(error => {
                    alert('Error refreshing content: ' + error);
                    document.getElementById('refresh-button').disabled = false;
                    document.getElementById('refresh-button').textContent = 'Refresh Content';
                });
        }
    </script>
</body>
</html>""")
    
    # Create a CSS file with improved styling
    css_path = os.path.join('frontend', 'web', 'static', 'style.css')
    if not os.path.exists(css_path):
        with open(css_path, 'w') as f:
            f.write("""/* Content Aggregator Styles */

body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #f5f5f5;
    color: #333;
}

.header {
    background-color: #2c3e50;
    color: white;
    padding: 20px;
    text-align: center;
    margin-bottom: 20px;
}

.header h1 {
    margin: 0;
    font-size: 2em;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

.filters {
    background-color: #ecf0f1;
    padding: 15px;
    margin-bottom: 20px;
    border-radius: 5px;
    max-width: 1200px;
    margin: 0 auto 20px;
}

.filters form {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 15px;
}

.filter-group {
    display: flex;
    flex-direction: column;
    min-width: 150px;
}

.filter-group label {
    margin-bottom: 5px;
    font-weight: bold;
}

.filter-group select,
.filter-group input {
    padding: 8px;
    border: 1px solid #ccc;
    border-radius: 4px;
}

button, .reset-button {
    background-color: #3498db;
    color: white;
    border: none;
    padding: 10px 15px;
    border-radius: 4px;
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
    font-size: 14px;
}

button:hover, .reset-button:hover {
    background-color: #2980b9;
}

.reset-button {
    background-color: #95a5a6;
}

.reset-button:hover {
    background-color: #7f8c8d;
}

#refresh-button {
    margin-left: auto;
    background-color: #27ae60;
}

#refresh-button:hover {
    background-color: #2ecc71;
}

.category-section {
    margin-bottom: 30px;
}

.category-header {
    background-color: #34495e;
    color: white;
    padding: 10px 15px;
    border-radius: 5px;
    margin-bottom: 15px;
}

.category-header h2 {
    margin: 0;
    font-size: 1.5em;
}

.entries-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
}

.entry {
    background-color: white;
    border-radius: 5px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    padding: 15px;
    transition: transform 0.2s;
}

.entry:hover {
    transform: translateY(-5px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
}

.entry h3 {
    margin-top: 0;
    font-size: 1.2em;
}

.entry h3 a {
    color: #2c3e50;
    text-decoration: none;
}

.entry h3 a:hover {
    color: #3498db;
}

.entry-meta {
    color: #7f8c8d;
    font-size: 0.9em;
    margin-bottom: 10px;
}

.entry-summary {
    font-size: 0.95em;
    line-height: 1.5;
}

.entry-youtube {
    grid-column: span 2;
}

.entry-thumbnail {
    margin: 10px 0;
    text-align: center;
}

.entry-thumbnail img {
    max-width: 100%;
    height: auto;
    border-radius: 5px;
}

.entry-stats {
    margin-top: 10px;
    font-size: 0.9em;
    color: #7f8c8d;
}

@media (max-width: 768px) {
    .entries-grid {
        grid-template-columns: 1fr;
    }
    
    .entry-youtube {
        grid-column: span 1;
    }
    
    .filters form {
        flex-direction: column;
        align-items: stretch;
    }
    
    .filter-group {
        width: 100%;
    }
    
    #refresh-button {
        margin-top: 15px;
        width: 100%;
    }
}""")
    
    print("Starting Content Aggregator Web Interface...")
    app.run(debug=True)
