# Self-Service Subscription System

This document outlines the implementation details for the content aggregator's self-service subscription system.

## Architecture Overview

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

## Components

### 1. Subscription Form (S3 Static Website)

A simple HTML form hosted on S3 that allows users to enter their email address to subscribe to the content digest.

**HTML Template:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Content Aggregator Subscription</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
        .form-container { background-color: #f9f9f9; padding: 20px; border-radius: 5px; }
        input[type="email"] { width: 100%; padding: 10px; margin: 10px 0; box-sizing: border-box; }
        button { background-color: #4CAF50; color: white; padding: 10px 15px; border: none; cursor: pointer; }
        .response { margin-top: 20px; padding: 10px; border-radius: 5px; }
        .success { background-color: #dff0d8; color: #3c763d; }
        .error { background-color: #f2dede; color: #a94442; }
    </style>
</head>
<body>
    <h1>Subscribe to Content Aggregator</h1>
    <p>Get daily updates on AWS, Amazon Q, and AI coding assistants delivered to your inbox.</p>
    
    <div class="form-container">
        <form id="subscription-form">
            <label for="email">Email address:</label>
            <input type="email" id="email" name="email" required placeholder="your.email@example.com">
            <button type="submit">Subscribe</button>
        </form>
    </div>
    
    <div id="response" class="response" style="display: none;"></div>
    
    <script>
        document.getElementById('subscription-form').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const responseDiv = document.getElementById('response');
            
            // Call API Gateway endpoint
            fetch('https://YOUR-API-GATEWAY-URL/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email: email }),
            })
            .then(response => response.json())
            .then(data => {
                responseDiv.style.display = 'block';
                if (data.success) {
                    responseDiv.className = 'response success';
                    responseDiv.innerHTML = 'Subscription request sent! Please check your email to confirm your subscription.';
                } else {
                    responseDiv.className = 'response error';
                    responseDiv.innerHTML = 'Error: ' + data.message;
                }
            })
            .catch(error => {
                responseDiv.style.display = 'block';
                responseDiv.className = 'response error';
                responseDiv.innerHTML = 'Error: Could not process your request. Please try again later.';
                console.error('Error:', error);
            });
        });
    </script>
</body>
</html>
```

### 2. API Gateway REST API

Create a REST API with the following endpoints:

- **POST /subscribe**: Handle subscription requests
- **POST /unsubscribe**: Handle unsubscription requests (optional)
- **GET /status**: Check subscription status (optional)

Enable CORS to allow the S3-hosted form to make requests to the API.

### 3. Lambda Function (Subscription Handler)

```python
import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        # Parse the incoming request
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        
        if not email:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'success': False,
                    'message': 'Email address is required'
                })
            }
        
        # Initialize SNS client
        sns = boto3.client('sns')
        
        # Subscribe the email to the topic
        topic_arn = 'arn:aws:sns:us-east-1:797963488632:content-aggregator-digest'
        
        response = sns.subscribe(
            TopicArn=topic_arn,
            Protocol='email',
            Endpoint=email
        )
        
        logger.info(f"Subscription request sent to {email}: {response}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'success': True,
                'message': 'Subscription request sent. Please check your email to confirm.'
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing subscription request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'success': False,
                'message': 'An error occurred processing your request'
            })
        }
```

### 4. Amazon SNS Topic

Use the existing SNS topic:
```
arn:aws:sns:us-east-1:797963488632:content-aggregator-digest
```

## Implementation Steps

1. **Create the S3 bucket for hosting the subscription form**:
   ```bash
   aws s3 mb s3://content-aggregator-subscription-form
   ```

2. **Configure the S3 bucket for static website hosting**:
   ```bash
   aws s3 website s3://content-aggregator-subscription-form --index-document index.html
   ```

3. **Set bucket policy to allow public read access**:
   ```bash
   aws s3api put-bucket-policy --bucket content-aggregator-subscription-form --policy '{
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": "*",
         "Action": "s3:GetObject",
         "Resource": "arn:aws:s3:::content-aggregator-subscription-form/*"
       }
     ]
   }'
   ```

4. **Create the Lambda function for subscription handling**:
   ```bash
   aws lambda create-function \
     --function-name content-aggregator-subscription \
     --runtime python3.9 \
     --handler lambda_function.lambda_handler \
     --role arn:aws:iam::797963488632:role/content-aggregator-subscription-role \
     --zip-file fileb://subscription-handler.zip
   ```

5. **Create the API Gateway REST API**:
   ```bash
   aws apigateway create-rest-api \
     --name "Content Aggregator Subscription API" \
     --description "API for managing content aggregator subscriptions"
   ```

6. **Upload the subscription form to S3**:
   ```bash
   aws s3 cp index.html s3://content-aggregator-subscription-form/
   ```

## Future Enhancements

1. **Subscription Preferences**:
   - Allow users to select content categories
   - Choose digest frequency (daily, weekly)
   - Set preferred time of day for receiving digests

2. **Subscription Management Portal**:
   - Allow users to manage their subscription settings
   - View past digests
   - Update email address

3. **Admin Dashboard**:
   - View all subscribers
   - Manage subscriptions
   - View subscription analytics

4. **Email Verification**:
   - Add double opt-in process
   - Verify email addresses before adding to subscription list

5. **Integration with User Authentication**:
   - Allow users to create accounts
   - Link subscriptions to user accounts
   - Personalize content based on user preferences
