# Getting Started with Content Aggregator

This guide will help you get started with the Content Aggregator project, focusing on the simplest initial implementation.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Basic knowledge of command line operations

## Initial Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/content-aggregator.git
   cd content-aggregator
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install basic dependencies**
   ```bash
   pip install flask feedparser requests beautifulsoup4
   pip freeze > requirements.txt
   ```

## First Run: RSS Feed Reader

The simplest version of the application is an RSS feed reader that:
1. Reads from configured RSS feeds
2. Displays the content in a basic web interface

### Steps:

1. **Configure your RSS feeds**
   
   Edit `config/sources.json` to include your desired RSS feeds:
   ```json
   {
     "rss_feeds": [
       {
         "name": "AWS Blog",
         "url": "https://aws.amazon.com/blogs/aws/feed/",
         "category": "cloud"
       },
       {
         "name": "TechCrunch",
         "url": "https://techcrunch.com/feed/",
         "category": "tech_news"
       }
     ]
   }
   ```

2. **Run the basic application**
   ```bash
   python app.py
   ```

3. **Access the web interface**
   
   Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## Next Steps

After getting the basic RSS reader working, you can:

1. **Add more RSS feeds** in the configuration file
2. **Implement YouTube integration** following the implementation plan
3. **Set up the database** to store content persistently
4. **Add LinkedIn scraping** for profile updates

Refer to the [Implementation Plan](implementation_plan.md) for a detailed roadmap of future enhancements.

## Troubleshooting

### Common Issues:

- **RSS Feed Not Loading**: Verify the feed URL is correct and accessible
- **Application Crashes**: Check the console output for error messages
- **Empty Results**: Ensure the RSS feeds are active and have recent content

If you encounter persistent issues, check the logs in the console output or create an issue in the project repository.
