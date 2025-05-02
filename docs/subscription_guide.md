# Content Aggregator Subscription Guide

This guide explains how to subscribe to the Content Aggregator digest emails.

## How to Subscribe

The Content Aggregator uses Amazon SNS (Simple Notification Service) to manage email subscriptions. To subscribe to the digest emails, follow these steps:

### Option 1: Request an Invitation

1. Ask the administrator to add your email address to the subscription list.
2. The administrator will run:
   ```bash
   aws sns subscribe \
     --topic-arn arn:aws:sns:us-east-1:797963488632:content-aggregator-digest \
     --protocol email \
     --notification-endpoint your.email@example.com
   ```
3. You'll receive a confirmation email from AWS Notifications.
4. Click the "Confirm subscription" link in the email to start receiving digests.

### Option 2: Self-Service Subscription (Coming Soon)

We're working on a self-service subscription page that will allow you to:
1. Enter your email address in a web form
2. Receive a confirmation email
3. Confirm your subscription to start receiving digests

## How to Unsubscribe

To unsubscribe from the digest emails:

1. Open any digest email you've received
2. Click the "Unsubscribe" link at the bottom of the email
3. Confirm your unsubscription on the AWS page that opens

## Subscription Management for Administrators

### Add a New Subscriber

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:797963488632:content-aggregator-digest \
  --protocol email \
  --notification-endpoint new.subscriber@example.com
```

### List Current Subscribers

```bash
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:797963488632:content-aggregator-digest
```

### Remove a Subscriber

First, find the subscription ARN:

```bash
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:797963488632:content-aggregator-digest
```

Then unsubscribe using the ARN:

```bash
aws sns unsubscribe \
  --subscription-arn arn:aws:sns:us-east-1:797963488632:content-aggregator-digest:subscription-id
```

## Troubleshooting

### Not Receiving Emails

1. Check your spam/junk folder
2. Verify that you confirmed your subscription
3. Ask the administrator to check if your email is in the subscription list

### Confirmation Link Expired

If your confirmation link has expired, ask the administrator to send a new subscription request.

## Contact

For any issues with your subscription, please contact the administrator at kanbo@amazon.com.
