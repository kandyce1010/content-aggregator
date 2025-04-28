# Content Aggregator

A hybrid content aggregation tool that keeps you updated with new posts from blogs, YouTube channels, and LinkedIn across various topics of interest.

## Features

- **Multi-source aggregation**: Collect content from blogs (RSS), YouTube channels, and LinkedIn posts
- **Regular updates**: Scheduled fetching of new content
- **Unified interface**: View all content in one place
- **Content categorization**: Automatically categorize content by topic
- **Filtering**: Filter content by source, date, topic, and read/unread status
- **Notifications**: Email digests of new content

## TODO: Additional Sources to Integrate

### LinkedIn Profiles
- [Swaminathan Sivasubramanian](https://www.linkedin.com/in/swaminathansivasubramanian/) - VP of Database, Analytics, and ML Services at AWS
- [Jeff Barr](https://www.linkedin.com/in/jeffbarr/) - Chief Evangelist at AWS
- [Brian Beach](https://www.linkedin.com/in/brianjbeach/) - Senior Developer Advocate at AWS

### GitHub Repositories
- [amazon-q-developer-cli](https://github.com/aws/amazon-q-developer-cli) - CLI tool for Amazon Q Developer
- [aws-toolkit-vscode](https://github.com/aws/aws-toolkit-vscode) - VS Code extension for Amazon Q
- [mynah-ui](https://github.com/aws/mynah-ui) - The chat interface of Amazon Q Developer for IDEs
- [amazon-q-eclipse](https://github.com/aws/amazon-q-eclipse) - Eclipse plugin for Amazon Q
- [amazon-q-connectjs](https://github.com/aws/amazon-q-connectjs) - JavaScript library for Amazon Q Connect

### Additional Platforms
- **Medium**: Integration with Medium search for "Amazon Q Developer" content
- **Dev.to**: Integration with Dev.to search for "Amazon Q Developer" content

## Architecture

```
Content Aggregator
├── Backend (Python)
│   ├── Content Fetchers
│   │   ├── RSS Parser
│   │   ├── YouTube API Client
│   │   └── Web Scraper (for LinkedIn)
│   ├── Content Processor
│   │   ├── Deduplication
│   │   ├── Categorization
│   │   └── Storage
│   └── API Server
└── Frontend
    ├── Web Interface (Flask/React)
    └── Email Digest Generator
```

## Project Structure

```
content-aggregator/
├── backend/
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── rss_fetcher.py
│   │   ├── youtube_fetcher.py
│   │   └── linkedin_fetcher.py
│   ├── processor/
│   │   ├── __init__.py
│   │   ├── deduplicator.py
│   │   └── categorizer.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── storage/
│   │   ├── __init__.py
│   │   └── db_manager.py
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── frontend/
│   ├── web/
│   │   ├── static/
│   │   └── templates/
│   └── email_digest/
│       └── template.html
├── config/
│   ├── sources.json
│   └── settings.py
├── docs/
│   └── setup_guide.md
├── app.py
├── scheduler.py
├── requirements.txt
└── README.md
```

## Setup and Installation

See [Setup Guide](docs/setup_guide.md) for detailed instructions.

## Usage

1. Configure your content sources in `config/sources.json`
2. Run the application: `python app.py`
3. Access the web interface at `http://localhost:5000`
4. Configure scheduled updates in `scheduler.py`

## Technologies Used

- **Python**: Core backend language
- **Flask**: Web server and API
- **SQLite/SQLAlchemy**: Content storage
- **feedparser**: RSS feed parsing
- **YouTube Data API**: YouTube content fetching
- **Beautiful Soup**: Web scraping for LinkedIn
- **NLTK/spaCy**: Content categorization
- **APScheduler**: Scheduled content updates
- **HTML/CSS/JavaScript**: Frontend web interface
