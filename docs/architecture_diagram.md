# Content Aggregator Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                          Content Sources                                    │
│                                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │          │   │          │   │          │   │          │   │          │  │
│  │  RSS     │   │  GitHub  │   │ LinkedIn │   │ YouTube  │   │  Other   │  │
│  │  Feeds   │   │  Repos   │   │ Profiles │   │ Channels │   │ Sources  │  │
│  │          │   │          │   │          │   │          │   │          │  │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘  │
│       │              │              │              │              │        │
└───────┼──────────────┼──────────────┼──────────────┼──────────────┼────────┘
        │              │              │              │              │
        ▼              ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                          Content Fetchers                                   │
│                                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │          │   │          │   │          │   │          │   │          │  │
│  │   RSS    │   │  GitHub  │   │ LinkedIn │   │ YouTube  │   │  Other   │  │
│  │ Fetcher  │   │ Fetcher  │   │ Fetcher  │   │ Fetcher  │   │ Fetchers │  │
│  │          │   │          │   │          │   │          │   │          │  │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘  │
│       │              │              │              │              │        │
└───────┼──────────────┼──────────────┼──────────────┼──────────────┼────────┘
        │              │              │              │              │
        └──────────────┼──────────────┼──────────────┼──────────────┘
                       │              │              │
                       ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                          Content Aggregator                                 │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  • Combines content from all sources                                 │  │
│  │  • Standardizes content format                                       │  │
│  │  • Filters content by category, date, etc.                           │  │
│  │  • Deduplicates content                                              │  │
│  │  • Performs content analysis (sentiment, relevance, etc.)            │  │
│  │  • Saves/loads content from JSON files                               │  │
│  │                                                                      │  │
│  └───────────────────────────────┬──────────────────────────────────────┘  │
│                                  │                                         │
└──────────────────────────────────┼─────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                          Content Delivery                                   │
│                                                                             │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────────────────┐  │
│  │              │      │              │      │                          │  │
│  │  Web         │      │  Email       │      │  AWS Lambda              │  │
│  │  Interface   │      │  Digest      │      │  (Scheduled Execution)   │  │
│  │              │      │              │      │                          │  │
│  └──────┬───────┘      └──────┬───────┘      └───────────┬──────────────┘  │
│         │                     │                          │                 │
└─────────┼─────────────────────┼──────────────────────────┼─────────────────┘
          │                     │                          │
          ▼                     ▼                          ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────────────┐
│                     │ │                     │ │                             │
│  Users              │ │  Email              │ │  AWS Services               │
│  (Web Browsers)     │ │  Subscribers        │ │  (S3, EventBridge, SNS)     │
│                     │ │                     │ │                             │
└─────────────────────┘ └─────────────────────┘ └─────────────────────────────┘
```

## Component Details

### Content Sources
- **RSS Feeds**: AWS blogs, Google Alerts, tech news sites
- **GitHub Repositories**: Amazon Q repositories, other AI coding assistant repos
- **LinkedIn Profiles**: Key people and organizations in the AI assistant space
- **YouTube Channels**: AWS channels, AI coding assistant tutorials and reviews
- **Other Sources**: Future expansion for additional content sources

### Content Fetchers
- **RSS Fetcher**: Parses RSS feeds using feedparser
- **GitHub Fetcher**: Uses GitHub API to fetch repository activities
- **LinkedIn Fetcher**: Scrapes LinkedIn profiles for relevant posts
- **YouTube Fetcher**: Uses YouTube Data API to fetch videos from channels
- **Other Fetchers**: Extensible design for adding more content sources

### Content Aggregator
- Central component that combines and processes content from all sources
- Standardizes content format across different sources
- Provides filtering capabilities (by category, date, search terms)
- Implements content deduplication and relevance scoring
- Saves processed content to JSON files for persistence

### Content Delivery
- **Web Interface**: Flask-based web application for browsing content
- **Email Digest**: Generates and sends email digests to subscribers
- **AWS Lambda**: Scheduled execution for automated content aggregation

### User Interfaces
- **Web Interface**: Responsive design for desktop and mobile browsers
- **Email Templates**: HTML email templates for digest delivery
- **CLI**: Command-line interface for local testing and management

### AWS Infrastructure
- **S3**: Hosts static website for subscription form
- **Lambda**: Runs scheduled content aggregation and email sending
- **EventBridge**: Schedules Lambda function execution
- **SNS**: Manages email subscriptions and delivery
- **API Gateway**: Provides REST API for subscription management

## Data Flow

1. **Content Acquisition**:
   - Fetchers retrieve content from various sources
   - Content is normalized into a standard format

2. **Content Processing**:
   - Aggregator combines content from all sources
   - Content is filtered, deduplicated, and enhanced

3. **Content Storage**:
   - Processed content is saved to JSON files
   - Files are stored locally or in S3 for Lambda execution

4. **Content Delivery**:
   - Web interface displays content with filtering options
   - Email digest generator creates and sends digests to subscribers
   - Lambda function automates the entire process on a schedule

5. **User Interaction**:
   - Users view content via web interface
   - Users subscribe/unsubscribe via subscription form
   - Users receive email digests based on preferences

## Subscription System Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  S3 Static Site │────▶│  API Gateway    │────▶│ Lambda Function │
│  (Subscription  │     │  (REST API)     │     │ (Subscription   │
│   Form)         │     │                 │     │  Handler)       │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │                 │
                                                │  Amazon SNS     │
                                                │  Topic          │
                                                │                 │
                                                └────────┬────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │                 │
                                                │  Email          │
                                                │  Subscribers    │
                                                │                 │
                                                └─────────────────┘
```
