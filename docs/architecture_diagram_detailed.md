# Content Aggregator - Detailed Architecture

## System Components and Data Flow

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                                                                       │
│                                                           CONTENT SOURCES                                                                             │
│                                                                                                                                                       │
│  ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐           │
│  │                       │   │                       │   │                       │   │                       │   │                       │           │
│  │   RSS Feeds           │   │   GitHub              │   │   LinkedIn            │   │   YouTube             │   │   Other Sources       │           │
│  │   - AWS Blogs         │   │   - amazon-q-dev-cli  │   │   - AWS Profiles      │   │   - AWS Events        │   │   - Medium           │           │
│  │   - Google Alerts     │   │   - aws-toolkit-vscode│   │   - AI Companies      │   │   - AWS Tech Talks    │   │   - Dev.to           │           │
│  │   - Tech News         │   │   - mynah-ui          │   │   - Industry Leaders  │   │   - Amazon Web Svcs   │   │   - Twitter/X        │           │
│  │                       │   │                       │   │                       │   │                       │   │                       │           │
│  └───────────┬───────────┘   └───────────┬───────────┘   └───────────┬───────────┘   └───────────┬───────────┘   └───────────┬───────────┘           │
│              │                           │                           │                           │                           │                       │
└──────────────┼───────────────────────────┼───────────────────────────┼───────────────────────────┼───────────────────────────┼───────────────────────┘
               │                           │                           │                           │                           │
               │                           │                           │                           │                           │
               ▼                           ▼                           ▼                           ▼                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                                                                      │
│                                                           BACKEND FETCHERS                                                                            │
│                                                                                                                                                      │
│  ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐          │
│  │                       │   │                       │   │                       │   │                       │   │                       │          │
│  │   RSSFetcher          │   │   GitHubFetcher       │   │   LinkedInFetcher     │   │   YouTubeFetcher      │   │   OtherFetchers       │          │
│  │   - fetch_all_feeds() │   │   - fetch_all_repos() │   │   - fetch_profiles()  │   │   - fetch_channels()  │   │   - fetch_content()   │          │
│  │   - parse_feed()      │   │   - get_activities()  │   │   - parse_posts()     │   │   - get_videos()      │   │   - parse_data()      │          │
│  │                       │   │                       │   │                       │   │                       │   │                       │          │
│  └───────────┬───────────┘   └───────────┬───────────┘   └───────────┬───────────┘   └───────────┬───────────┘   └───────────┬───────────┘          │
│              │                           │                           │                           │                           │                      │
└──────────────┼───────────────────────────┼───────────────────────────┼───────────────────────────┼───────────────────────────┼──────────────────────┘
               │                           │                           │                           │                           │
               └───────────────────────────┼───────────────────────────┼───────────────────────────┼───────────────────────────┘
                                           │                           │                           │
                                           ▼                           ▼                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                                                                      │
│                                                       CONTENT AGGREGATOR                                                                             │
│                                                                                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐          │
│  │                                                                                                                                        │          │
│  │  ContentAggregator                                                                                                                     │          │
│  │                                                                                                                                        │          │
│  │  ┌─────────────────────────────┐   ┌─────────────────────────────┐   ┌─────────────────────────────┐   ┌─────────────────────────────┐│          │
│  │  │                             │   │                             │   │                             │   │                             ││          │
│  │  │  Content Collection         │   │  Content Processing         │   │  Content Storage            │   │  Content Filtering          ││          │
│  │  │  - fetch_all_content()      │   │  - deduplicate_content()    │   │  - save_content()           │   │  - filter_by_category()     ││          │
│  │  │  - fetch_rss_content()      │   │  - analyze_sentiment()      │   │  - load_content()           │   │  - filter_by_date()         ││          │
│  │  │  - fetch_github_content()   │   │  - summarize_content()      │   │  - get_latest_content()     │   │  - search_content()         ││          │
│  │  │  - fetch_linkedin_content() │   │  - score_relevance()        │   │                             │   │                             ││          │
│  │  │  - fetch_youtube_content()  │   │                             │   │                             │   │                             ││          │
│  │  │                             │   │                             │   │                             │   │                             ││          │
│  │  └─────────────────────────────┘   └─────────────────────────────┘   └─────────────────────────────┘   └─────────────────────────────┘│          │
│  │                                                                                                                                        │          │
│  └────────────────────────────────────────────────────────────┬───────────────────────────────────────────────────────────────────────────┘          │
│                                                               │                                                                                      │
└───────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┘
                                                                │
                                                                │
                                                                ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                                                                      │
│                                                       DELIVERY MECHANISMS                                                                            │
│                                                                                                                                                      │
│  ┌───────────────────────────────────────┐            ┌───────────────────────────────────────┐            ┌───────────────────────────────────────┐ │
│  │                                       │            │                                       │            │                                       │ │
│  │  Web Interface (Flask)                │            │  Email Digest Generator               │            │  AWS Lambda Function                  │ │
│  │  - app.py                             │            │  - send_digest.py                     │            │  - lambda_function.py                 │ │
│  │  - Templates & Static Files           │            │  - HTML Email Templates               │            │  - Scheduled via EventBridge          │ │
│  │  - Content Filtering UI               │            │  - Subscriber Management              │            │  - S3 for Content Storage            │ │
│  │                                       │            │                                       │            │                                       │ │
│  └─────────────────┬─────────────────────┘            └─────────────────┬─────────────────────┘            └─────────────────┬─────────────────────┘ │
│                    │                                                    │                                                    │                       │
└────────────────────┼────────────────────────────────────────────────────┼────────────────────────────────────────────────────┼───────────────────────┘
                     │                                                    │                                                    │
                     ▼                                                    ▼                                                    ▼
┌─────────────────────────────────────┐                  ┌─────────────────────────────────────┐                  ┌─────────────────────────────────────┐
│                                     │                  │                                     │                  │                                     │
│  Users (Web Browsers)               │                  │  Email Subscribers                  │                  │  AWS Services                       │
│  - View Content                     │                  │  - Receive Daily/Weekly Digests     │                  │  - S3                              │
│  - Filter by Category/Date          │                  │  - Manage Subscription Preferences  │                  │  - EventBridge                     │
│  - Search Content                   │                  │  - Click Through to Content         │                  │  - SNS                             │
│                                     │                  │                                     │                  │  - API Gateway                     │
└─────────────────────────────────────┘                  └─────────────────────────────────────┘                  └─────────────────────────────────────┘
```

## Subscription System Architecture

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                                                                       │
│                                                     SUBSCRIPTION SYSTEM                                                                               │
│                                                                                                                                                       │
│  ┌───────────────────────┐                 ┌───────────────────────┐                 ┌───────────────────────┐                 ┌───────────────────────┐
│  │                       │                 │                       │                 │                       │                 │                       │
│  │  S3 Static Website    │                 │  API Gateway          │                 │  Lambda Function      │                 │  SNS Topic            │
│  │  - Subscription Form  │ ───Request────▶ │  - REST API           │ ───Request────▶ │  - Process Request    │ ───Subscribe──▶ │  - Manage            │
│  │  - HTML/CSS/JS        │ ◀───Response─── │  - CORS Enabled       │ ◀───Response─── │  - Validate Email     │ ◀───Confirm──── │    Subscriptions     │
│  │  - Success/Error UI   │                 │  - API Key Auth       │                 │  - Error Handling     │                 │  - Send Emails        │
│  │                       │                 │                       │                 │                       │                 │                       │
│  └───────────────────────┘                 └───────────────────────┘                 └───────────────────────┘                 └──────────┬────────────┘
│                                                                                                                                          │            │
│                                                                                                                                          │            │
│                                                                                                                                          ▼            │
│                                                                                                                           ┌───────────────────────────┐│
│                                                                                                                           │                          ││
│                                                                                                                           │  Email Subscribers       ││
│                                                                                                                           │  - Confirmation Emails   ││
│                                                                                                                           │  - Content Digests       ││
│                                                                                                                           │  - Unsubscribe Links     ││
│                                                                                                                           │                          ││
│                                                                                                                           └──────────────────────────┘│
│                                                                                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## AWS Lambda Deployment Architecture

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                                                                       │
│                                                     AWS DEPLOYMENT                                                                                    │
│                                                                                                                                                       │
│  ┌───────────────────────┐                 ┌───────────────────────┐                 ┌───────────────────────┐                 ┌───────────────────────┐
│  │                       │                 │                       │                 │                       │                 │                       │
│  │  EventBridge          │                 │  Lambda Function      │                 │  S3 Bucket            │                 │  SNS Topic            │
│  │  - Schedule Rule      │ ───Trigger────▶ │  - Aggregator Code    │ ───Store─────▶ │  - Content Storage    │                 │  - Email              │
│  │  - Daily/Weekly       │                 │  - Python Runtime     │                 │  - Static Website     │                 │    Distribution       │
│  │  - Custom Rate        │                 │  - Environment Vars   │ ───Notify────▶ │  - Public Access      │                 │  - Subscribers        │
│  │                       │                 │  - IAM Role           │                 │                       │                 │                       │
│  └───────────────────────┘                 └───────────────────────┘                 └───────────────────────┘                 └──────────┬────────────┘
│                                                       │                                                                                   │            │
│                                                       │                                                                                   │            │
│                                                       │                                                                                   ▼            │
│                                                       │                                                                    ┌───────────────────────────┐│
│                                                       │                                                                    │                          ││
│                                                       │                                                                    │  Email Recipients        ││
│                                                       │                                                                    │  - Daily/Weekly Digests  ││
│                                                       │                                                                    │  - Content Updates       ││
│                                                       │                                                                    │                          ││
│                                                       │                                                                    └──────────────────────────┘│
│                                                       │                                                                                               │
│                                                       ▼                                                                                               │
│                                            ┌───────────────────────┐                                                                                  │
│                                            │                       │                                                                                  │
│                                            │  CloudWatch Logs      │                                                                                  │
│                                            │  - Execution Logs     │                                                                                  │
│                                            │  - Error Tracking     │                                                                                  │
│                                            │  - Metrics            │                                                                                  │
│                                            │                       │                                                                                  │
│                                            └───────────────────────┘                                                                                  │
│                                                                                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Sequence

1. **Content Acquisition**
   - Fetchers retrieve content from external sources
   - Each fetcher normalizes content to a standard format
   - Content is tagged with source and category information

2. **Content Aggregation**
   - ContentAggregator combines content from all fetchers
   - Content is deduplicated and processed
   - Content is filtered based on user preferences

3. **Content Storage**
   - Processed content is saved to JSON files
   - Files are stored locally or in S3 bucket
   - Content is versioned with timestamps

4. **Content Delivery**
   - Web interface displays content with filtering options
   - Email digest generator creates HTML emails
   - AWS Lambda executes the process on schedule

5. **User Interaction**
   - Users view content via web interface
   - Users subscribe to email digests
   - Users filter and search content

## Technology Stack

- **Backend**: Python 3.9+
- **Web Framework**: Flask
- **Data Processing**: Custom Python modules
- **API Clients**: 
  - feedparser (RSS)
  - requests (GitHub API)
  - google-api-python-client (YouTube API)
- **Frontend**: HTML, CSS, JavaScript
- **Cloud Services**: AWS (Lambda, S3, SNS, EventBridge)
- **Data Storage**: JSON files, S3 objects
- **Email**: SNS, HTML templates
