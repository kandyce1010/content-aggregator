# Content Aggregator

A unified content aggregator that combines information from multiple sources including RSS feeds, GitHub repositories, and YouTube channels. Built with security best practices and designed for both personal use and public deployment.

## Features

- **Multi-source content fetching**:
  - RSS feeds (blogs, news sites, etc.)
  - GitHub repositories (releases, commits, issues)
  - YouTube channels (optional, requires API key)
- **Smart filtering** by category, date, and search terms
- **Content summarization** using Amazon Bedrock (optional)
- **Email digest generation** with customizable formatting
- **Web interface** for viewing aggregated content
- **AWS Lambda deployment** support with CloudFormation
- **Security-first design** with input validation and secure HTTP handling

## Security Features

- Input validation for all user inputs
- Secure file handling with path traversal protection
- SSL/TLS verification for all HTTP requests
- Rate limiting and retry logic for external APIs
- Comprehensive error handling and logging
- Environment variable validation

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/content-aggregator.git
   cd content-aggregator
   ```

2. **Set up virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure content sources**:
   ```bash
   cp config/sources.example.json config/sources.json
   # Edit config/sources.json with your preferred sources
   ```

4. **Run the aggregator**:
   ```bash
   python3 cli.py --fetch-all --save
   ```

## Configuration

### Content Sources

Edit `config/sources.json` to configure your content sources:

```json
{
  "rss_feeds": [
    {
      "name": "AWS Blog",
      "url": "https://aws.amazon.com/blogs/aws/feed/",
      "category": "AWS"
    }
  ],
  "github_repositories": [
    {
      "name": "aws-cdk",
      "owner": "aws",
      "repo": "aws-cdk",
      "category": "AWS"
    }
  ],
  "youtube_channels": [
    {
      "name": "AWS Events",
      "channel_id": "UCdoadna9HFHsxXWhafhNvKw",
      "category": "AWS"
    }
  ]
}
```

### Environment Variables

Optional environment variables for enhanced functionality:

```bash
# GitHub API (recommended for better rate limits)
export GITHUB_TOKEN=your_github_token

# YouTube API (required for YouTube content)
export YOUTUBE_API_KEY=your_youtube_api_key

# AWS credentials (for Bedrock summarization and email)
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

## Usage

### Command Line Interface

**Basic content fetching**:
```bash
# Fetch from all sources
python3 cli.py --fetch-all

# Fetch only RSS content
python3 cli.py --rss-only

# Fetch and save to file
python3 cli.py --fetch-all --save
```

**Filtering and search**:
```bash
# Filter by category
python3 cli.py --fetch-all --filter-category "AWS"

# Filter by date (last 3 days)
python3 cli.py --fetch-all --filter-days 3

# Search content
python3 cli.py --fetch-all --search "serverless"
```

**Email digest**:
```bash
# Send digest via email
python3 cli.py --fetch-all --email your-email@example.com

# Customize digest
python3 cli.py --fetch-all --email your-email@example.com --max-items 5 --filter-days 1
```

**Advanced features**:
```bash
# Enable AI summarization (requires AWS Bedrock)
python3 cli.py --fetch-all --enable-summarization --batch-size 5

# Use Strands workflow for better performance
python3 cli.py --fetch-all --use-strands --enable-summarization
```

### Web Interface

Start the web server:
```bash
python3 app.py
```

Then open your browser to http://localhost:5000

### Email Digest Script

Send scheduled digests:
```bash
python3 send_digest.py --recipients your-email@example.com
```

## AWS Deployment

Deploy to AWS Lambda for automated content aggregation:

1. **Build and deploy**:
   ```bash
   cd aws
   ./deploy-all.sh
   ```

2. **Deploy Step Functions workflow** (recommended for production):
   ```bash
   aws cloudformation deploy \
     --template-file aws/step-functions-cloudformation.yaml \
     --stack-name content-aggregator-workflow \
     --capabilities CAPABILITY_IAM
   ```

3. **Start a workflow execution**:
   ```bash
   aws stepfunctions start-execution \
     --state-machine-arn <state-machine-arn> \
     --input '{"email":"your-email@example.com","days":7,"max_items":10}'
   ```

## Development

### Project Structure

```
content-aggregator/
├── backend/
│   ├── fetchers/          # Content fetching modules
│   ├── email_digest/      # Email generation and sending
│   ├── summarization/     # AI summarization with Bedrock
│   ├── strands/          # Strands workflow implementation
│   └── utils/            # Utilities and validation
├── config/               # Configuration files
├── aws/                  # AWS deployment files
└── data/                 # Generated content and cache
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/

# Run with coverage
pytest --cov=backend tests/
```

### Security Guidelines

- All user inputs are validated
- File operations use secure path handling
- HTTP requests include SSL verification and timeouts
- Environment variables are validated on startup
- Error messages don't expose sensitive information

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code follows the security guidelines and includes appropriate tests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with AWS services (Lambda, Bedrock, SNS, Step Functions)
- Uses public RSS feeds and APIs
- Inspired by the need for automated content curation

## Support

For issues and questions:
- Open an issue on GitHub
