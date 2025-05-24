# Content Aggregator

A unified content aggregator that combines information from multiple sources including RSS feeds, GitHub repositories, LinkedIn profiles, and YouTube channels.

## Features

- Fetch content from multiple sources:
  - RSS feeds
  - GitHub repositories
  - LinkedIn profiles (optional)
  - YouTube channels (optional)
- Filter content by category or date
- Save and load content from JSON files
- Search functionality
- Email digest generation
- Web interface for viewing aggregated content
- AWS Lambda deployment support

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/content-aggregator.git
   cd content-aggregator
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configure your content sources in `config/sources.json`:
   - Add RSS feeds
   - Add GitHub repositories
   - Add YouTube channels

4. Set up API keys (as needed):
   ```
   export GITHUB_TOKEN=your_github_token
   export YOUTUBE_API_KEY=your_youtube_api_key
   ```

## Usage

### Command Line Interface

Run the CLI tool to fetch and process content:

```
python cli.py --fetch-all
```

Basic Options:
- `--fetch-all`: Fetch content from all sources
- `--rss-only`: Fetch only RSS content
- `--github-only`: Fetch only GitHub content
- `--youtube-only`: Fetch only YouTube content
- `--save`: Save fetched content to a file
- `--load FILE`: Load content from a file
- `--filter-category CATEGORY`: Filter content by category
- `--filter-days DAYS`: Filter content from the last X days
- `--search QUERY`: Search content for a query string

Advanced Options:
- `--use-strands`: Use Strands-based workflow for better performance
- `--enable-summarization`: Enable content summarization with Amazon Bedrock
- `--batch-size SIZE`: Set batch size for summarization (default: 10)
- `--email EMAIL`: Send digest to specified email address
- `--max-items COUNT`: Maximum items per category in digest (default: 10)

### Web Interface

Start the web server:

```
python app.py
```

Then open your browser to http://localhost:5000

### Email Digest

Send an email digest of the latest content:

```
python send_digest.py --recipients email@example.com
```

## AWS Deployment

Deploy to AWS Lambda:

1. Build the Lambda layer:
   ```
   python aws/layer-build.py
   ```

2. Deploy using CloudFormation:
   ```
   aws cloudformation deploy --template-file aws/cloudformation.yaml --stack-name content-aggregator --capabilities CAPABILITY_IAM
   ```

### Step Functions Workflow

For improved performance and scalability, the content aggregator can be deployed as a Step Functions workflow:

1. Deploy the Step Functions workflow:
   ```
   aws cloudformation deploy --template-file aws/step-functions-cloudformation.yaml --stack-name content-aggregator-workflow --capabilities CAPABILITY_IAM
   ```

2. Start a workflow execution:
   ```
   aws stepfunctions start-execution --state-machine-arn <state-machine-arn> --input '{"email":"your-email@example.com","days":7,"max_items":10}'
   ```

## Configuration

### sources.json

The `config/sources.json` file contains the configuration for all content sources:

```json
{
  "rss_feeds": [
    {
      "name": "Example Feed",
      "url": "https://example.com/feed",
      "category": "Example"
    }
  ],
  "github_repositories": [
    {
      "name": "Example Repo",
      "owner": "username",
      "repo": "repo-name",
      "category": "Example"
    }
  ],
  "youtube_channels": [
    {
      "name": "Example Channel",
      "channel_id": "UC-channel-id",
      "category": "Example"
    }
  ]
}
```

## License

MIT