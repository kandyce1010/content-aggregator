# AWS Integration for Content Aggregator

This directory contains scripts and templates for deploying the Content Aggregator to AWS.

## EventBridge Scheduling

The `eventbridge_scheduler.py` script sets up an EventBridge rule to schedule the content aggregator to run on a regular basis.

### Prerequisites

1. An AWS Lambda function that runs the content aggregator
2. AWS CLI configured with appropriate credentials
3. Required IAM permissions to create EventBridge rules and targets

### Usage

```bash
python eventbridge_scheduler.py --lambda-function content-aggregator-function --schedule "cron(0 8 * * ? *)" --region us-east-1
```

This will create an EventBridge rule that triggers the specified Lambda function every day at 8:00 AM UTC.

### Options

- `--rule-name`: Name of the EventBridge rule (default: content-aggregator-daily)
- `--schedule`: Schedule expression in cron or rate format (default: cron(0 8 * * ? *))
- `--lambda-function`: Name or ARN of the Lambda function (required)
- `--input-json`: JSON input to pass to the Lambda function
- `--region`: AWS region (default: us-east-1)
- `--profile`: AWS profile name

## Lambda Function

The `lambda_function.py` file contains the AWS Lambda function handler that will be invoked by EventBridge to generate and send the content digest.

### Deployment

To deploy the Lambda function:

1. Package the content aggregator code and dependencies:

```bash
# Create a deployment package
mkdir -p deployment
pip install -r requirements.txt --target ./deployment
cp -r backend aws *.py ./deployment/
cd deployment
zip -r ../content-aggregator.zip .
cd ..
```

2. Create the Lambda function:

```bash
aws lambda create-function \
  --function-name content-aggregator \
  --runtime python3.9 \
  --handler aws.lambda_function.lambda_handler \
  --zip-file fileb://content-aggregator.zip \
  --role arn:aws:iam::123456789012:role/content-aggregator-lambda-role \
  --timeout 300 \
  --memory-size 512 \
  --environment Variables="{RECIPIENT_EMAIL=your.email@example.com,DAYS=7,MAX_ITEMS=10}"
```

3. Set up the EventBridge rule to trigger the Lambda function:

```bash
python aws/eventbridge_scheduler.py --lambda-function content-aggregator
```

## IAM Role for Lambda

The Lambda function requires an IAM role with the following permissions:

- AWSLambdaBasicExecutionRole (for CloudWatch Logs)
- SNS:Publish (for sending emails)
- Additional permissions as needed (e.g., DynamoDB, S3)

Example IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish",
        "sns:CreateTopic",
        "sns:Subscribe",
        "sns:ListTopics",
        "sns:ListSubscriptionsByTopic",
        "sns:SetTopicAttributes"
      ],
      "Resource": "*"
    }
  ]
}
```
