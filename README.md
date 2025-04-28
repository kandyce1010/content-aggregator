# Content Aggregator

A hybrid content aggregation tool that delivers daily email digests with new posts from blogs, YouTube channels, LinkedIn, and GitHub repositories across various topics of interest.

## Features

- **Multi-source aggregation**: Collect content from blogs (RSS), YouTube channels, LinkedIn posts, and GitHub repositories
- **Regular updates**: Scheduled daily email digests
- **Content categorization**: Automatically categorize content by topic
- **AWS Integration**: Uses AWS SNS for email delivery and EventBridge for scheduling
- **Customizable**: Configure your own content sources and categories

## Content Sources

### RSS Feeds
- AWS Blog, TechCrunch, Hacker News, Python Blog, CSS-Tricks, and more

### YouTube Channels
- AWS Events, Google Developers, TechWorld with Nana, and more

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

### Search-based Content
- **Medium**: Integration with Medium search for "Amazon Q Developer" content
- **Dev.to**: Integration with Dev.to search for "Amazon Q Developer" content

## Architecture

```
Content Aggregator
├── Backend (Python)
│   ├── Content Fetchers
│   │   ├── RSS Parser
│   │   ├── YouTube API Client
│   │   ├── Web Scraper (for LinkedIn)
│   │   └── GitHub API Client
│   ├── Content Processor
│   │   ├── Deduplication
│   │   ├── Categorization
│   │   └── Storage
│   └── Email Digest
│       ├── Digest Generator
│       └── Email Sender (AWS SNS)
└── AWS Integration
    ├── SNS (Email Delivery)
    └── EventBridge (Scheduling)
```

## Project Structure

```
content-aggregator/
├── backend/
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── rss_fetcher.py
│   │   ├── youtube_fetcher.py
│   │   ├── linkedin_fetcher.py
│   │   └── github_fetcher.py
│   ├── processor/
│   │   ├── __init__.py
│   │   ├── deduplicator.py
│   │   └── categorizer.py
│   ├── email_digest/
│   │   ├── __init__.py
│   │   ├── digest_generator.py
│   │   ├── email_sender.py
│   │   └── templates/
│   │       └── email_template.html
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── config/
│   ├── sources.json
│   └── aws_config.json
├── data/
│   └── README.md
├── docs/
│   ├── implementation_plan.md
│   ├── getting_started.md
│   └── setup_guide.md
├── cli.py
├── send_digest.py
├── requirements.txt
└── README.md
```

## Setup and Installation

See [Setup Guide](docs/setup_guide.md) for detailed instructions.

## Usage

1. Configure your content sources in `config/sources.json`
2. Configure AWS settings in `config/aws_config.json`
3. Run the CLI tool to test content fetching: `python cli.py rss`
4. Send a test digest: `python send_digest.py --email your.email@example.com`
5. Deploy to AWS for scheduled daily digests

## Technologies Used

- **Python**: Core backend language
- **AWS SNS**: Email delivery
- **AWS EventBridge**: Scheduled execution
- **AWS Lambda**: Serverless execution (future)
- **feedparser**: RSS feed parsing
- **YouTube Data API**: YouTube content fetching
- **Beautiful Soup**: Web scraping for LinkedIn
- **GitHub API**: Repository activity monitoring
- **Jinja2**: Email template rendering
- **boto3**: AWS SDK for Python
