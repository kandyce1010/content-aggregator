# Content Aggregator Setup Guide

This guide will walk you through setting up and configuring the Content Aggregator tool.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Google Developer account (for YouTube API)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/content-aggregator.git
   cd content-aggregator
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration

### API Keys

1. **YouTube API Key**:
   - Go to [Google Developer Console](https://console.developers.google.com/)
   - Create a new project
   - Enable the YouTube Data API v3
   - Create an API key
   - Add the key to `config/settings.py`

### Content Sources

Configure your content sources in `config/sources.json`:

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
  ],
  "youtube_channels": [
    {
      "name": "AWS Events",
      "channel_id": "UCdoadna9HFHsxXWhafhNvKw",
      "category": "cloud"
    }
  ],
  "linkedin_profiles": [
    {
      "name": "AWS",
      "url": "https://www.linkedin.com/company/amazon-web-services/",
      "category": "cloud"
    }
  ]
}
```

### Database Setup

The application uses SQLite by default. The database will be created automatically when you first run the application.

If you want to use a different database:

1. Update the database URI in `config/settings.py`
2. Install the appropriate database driver

## Running the Application

### Web Interface

Start the web server:
```
python app.py
```

Access the web interface at `http://localhost:5000`

### Scheduled Updates

Configure the update schedule in `scheduler.py` and run:
```
python scheduler.py
```

This will fetch new content according to your schedule.

## Email Digest Configuration

To enable email digests:

1. Configure email settings in `config/settings.py`:
   ```python
   EMAIL_CONFIG = {
       'smtp_server': 'smtp.gmail.com',
       'smtp_port': 587,
       'username': 'your-email@gmail.com',
       'password': 'your-app-password',  # Use app password for Gmail
       'from_email': 'your-email@gmail.com',
       'to_email': 'recipient@example.com'
   }
   ```

2. Run the digest generator:
   ```
   python -m frontend.email_digest.generator
   ```

## Troubleshooting

### RSS Feed Issues
- Ensure the feed URL is correct and accessible
- Some feeds may require user agent headers

### YouTube API Issues
- Check your API quota usage in Google Developer Console
- Ensure your API key has the correct permissions

### LinkedIn Scraping Issues
- LinkedIn may block scraping attempts
- Consider using a rotating proxy service
- Adjust scraping frequency to avoid rate limiting
