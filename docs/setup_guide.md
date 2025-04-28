# Content Aggregator Setup Guide

This guide provides step-by-step instructions for setting up the Content Aggregator email digest system using AWS services.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- AWS account with appropriate permissions
- AWS CLI installed and configured

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/content-aggregator.git
   cd content-aggregator
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

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

### AWS Configuration

1. Configure AWS CLI if you haven't already:
   ```bash
   aws configure
   ```

2. Update your `config/aws_config.json` file:
   ```json
   {
     "region": "us-east-1",
     "profile": "default",
     "sns": {
       "topic_name": "content-aggregator-digest",
       "email_subject": "Your Daily Content Digest"
     },
     "eventbridge": {
       "rule_name": "content-aggregator-daily-digest",
       "schedule_expression": "cron(0 8 * * ? *)",
       "description": "Trigger daily content digest at 8:00 AM"
     }
   }
   ```

## AWS Setup

### Step 1: Set Up Amazon SNS for Email Delivery

```bash
# Create the SNS topic
aws sns create-topic --name content-aggregator-digest

# Save the TopicArn from the output
TOPIC_ARN=$(aws sns create-topic --name content-aggregator-digest --output text --query 'TopicArn')
echo "Topic ARN: $TOPIC_ARN"

# Set the display name for the topic
aws sns set-topic-attributes \
    --topic-arn $TOPIC_ARN \
    --attribute-name DisplayName \
    --attribute-value "Content Aggregator"
```

### Step 2: Subscribe Your Email

```bash
# Replace your.email@example.com with your actual email
aws sns subscribe \
    --topic-arn $TOPIC_ARN \
    --protocol email \
    --notification-endpoint your.email@example.com
```

You will receive a confirmation email. Click the link in the email to confirm your subscription.

### Step 3: Set Up Amazon EventBridge for Scheduled Execution (Optional)

```bash
# Create a rule that triggers at 8:00 AM UTC every day
aws events put-rule \
    --name content-aggregator-daily-digest \
    --schedule-expression "cron(0 8 * * ? *)" \
    --state ENABLED \
    --description "Trigger daily content digest at 8:00 AM"
```

For more detailed EventBridge setup including IAM roles and targets, see the AWS documentation.

## Running the Content Aggregator

### Manual Execution

To fetch content and generate a digest without sending an email:

```bash
python cli.py rss --save
python send_digest.py --email your.email@example.com --save-only
```

To fetch content, generate a digest, and send it via email:

```bash
python send_digest.py --email your.email@example.com --region us-east-1
```

### Format Options

By default, the digest is sent in plain text format for maximum compatibility. To send in HTML format:

```bash
python send_digest.py --email your.email@example.com --region us-east-1 --format html
```

### Scheduled Execution

For a simple approach, you can use a cron job on a server:

```bash
# Edit crontab
crontab -e

# Add this line to run at 8:00 AM daily
0 8 * * * cd /path/to/content-aggregator && /path/to/python send_digest.py --email your.email@example.com --region us-east-1 >> /path/to/logs/digest.log 2>&1
```

## Troubleshooting

### Common Issues

1. **Email not received**: 
   - Check if you confirmed the SNS subscription
   - Verify the email wasn't filtered as spam
   - Check SNS delivery statistics

2. **Content not being fetched**:
   - Check the logs for any API errors
   - Verify your internet connectivity
   - Ensure the source URLs are still valid

3. **AWS permissions issues**:
   - Verify your AWS credentials are correct
   - Ensure you have the necessary permissions for SNS and EventBridge

### Checking Logs

The application logs to the console by default. To save logs to a file:

```bash
python send_digest.py --email your.email@example.com > digest.log 2>&1
```

## Customizing Content

To customize the content sources:
1. Edit `config/sources.json` to add or remove sources
2. Adjust categories to better organize your content
3. Run the application to test your changes

To customize the email format:
1. For HTML format: Edit `backend/email_digest/templates/email_template.html`
2. For text format: Modify the `generate_text_digest` method in `backend/email_digest/digest_generator.py`
