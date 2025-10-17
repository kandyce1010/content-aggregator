#!/usr/bin/env python3
"""
Email Sender Module

This module handles sending email digests using AWS SNS.
"""

import os
import logging
import json
import boto3
from botocore.exceptions import ClientError
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmailSender:
    """
    A class to send email digests using AWS SNS.
    """
    
    def __init__(self, region_name: str = 'us-east-1', profile_name: Optional[str] = None):
        """
        Initialize the email sender with AWS credentials.
        
        Args:
            region_name (str): AWS region name.
            profile_name (str, optional): AWS profile name.
        """
        self.region_name = region_name
        
        # Initialize AWS session
        session_kwargs = {'region_name': region_name}
        if profile_name:
            session_kwargs['profile_name'] = profile_name
            
        self.session = boto3.Session(**session_kwargs)
        self.sns = self.session.client('sns')
        
    def create_topic(self, topic_name: str) -> str:
        """
        Create an SNS topic for email digests.
        
        Args:
            topic_name (str): Name of the SNS topic.
            
        Returns:
            str: ARN of the created topic.
        """
        try:
            response = self.sns.create_topic(Name=topic_name)
            topic_arn = response['TopicArn']
            logger.info(f"Created SNS topic: {topic_arn}")
            return topic_arn
        except ClientError as e:
            logger.error(f"Error creating SNS topic: {e}")
            raise
    
    def subscribe_email(self, topic_arn: str, email: str) -> str:
        """
        Subscribe an email address to an SNS topic.
        
        Args:
            topic_arn (str): ARN of the SNS topic.
            email (str): Email address to subscribe.
            
        Returns:
            str: Subscription ARN.
        """
        try:
            response = self.sns.subscribe(
                TopicArn=topic_arn,
                Protocol='email',
                Endpoint=email
            )
            subscription_arn = response['SubscriptionArn']
            logger.info(f"Subscribed {email} to topic {topic_arn}")
            return subscription_arn
        except ClientError as e:
            logger.error(f"Error subscribing {email} to topic: {e}")
            raise
    
    def send_email_digest(self, 
                         topic_arn: str, 
                         subject: str, 
                         html_content: str) -> Dict[str, Any]:
        """
        Send an email digest via SNS.
        
        Args:
            topic_arn (str): ARN of the SNS topic.
            subject (str): Email subject.
            html_content (str): HTML content of the email.
            
        Returns:
            dict: Response from SNS publish API.
        """
        try:
            # For SNS email protocol, we need to send the HTML content directly
            # SNS will handle the email formatting
            
            # Publish the message to the topic
            response = self.sns.publish(
                TopicArn=topic_arn,
                Message=html_content,  # Send HTML content directly
                Subject=subject
            )
            
            logger.info(f"Sent email digest via SNS: {response['MessageId']}")
            return response
        except ClientError as e:
            logger.error(f"Error sending email digest: {e}")
            raise
    
    def send_digest(self, email_address: str, subject: str, html_content: str) -> Dict[str, Any]:
        """
        Send a digest to an email address using a persistent topic.
        
        Args:
            email_address (str): Recipient email address
            subject (str): Email subject
            html_content (str): HTML content of the email
        
        Returns:
            dict: Response from SNS publish API
        """
        try:
            # Get or create a persistent topic
            topic_name = "content-aggregator-digest"
            
            # List topics to check if ours exists
            topics_response = self.sns.list_topics()
            topic_arn = None
            
            for topic in topics_response.get('Topics', []):
                if topic_name in topic['TopicArn']:
                    topic_arn = topic['TopicArn']
                    break
            
            # Create topic if it doesn't exist
            if not topic_arn:
                create_response = self.sns.create_topic(Name=topic_name)
                topic_arn = create_response['TopicArn']
                logger.info(f"Created new SNS topic: {topic_arn}")
                
                # Set topic attributes for better display name
                self.sns.set_topic_attributes(
                    TopicArn=topic_arn,
                    AttributeName='DisplayName',
                    AttributeValue='Content Aggregator'
                )
            else:
                logger.info(f"Using existing SNS topic: {topic_arn}")
            
            # Check if email is already subscribed
            subscriptions = self.sns.list_subscriptions_by_topic(TopicArn=topic_arn)
            is_subscribed = False
            is_confirmed = False
            
            for sub in subscriptions.get('Subscriptions', []):
                if sub.get('Protocol') == 'email' and sub.get('Endpoint') == email_address:
                    is_subscribed = True
                    if sub.get('SubscriptionArn') == 'PendingConfirmation':
                        logger.info(f"Email {email_address} is pending confirmation. Please check your inbox.")
                    else:
                        logger.info(f"Email {email_address} is already subscribed and confirmed.")
                        is_confirmed = True
                    break
            
            # Subscribe email if not already subscribed
            if not is_subscribed:
                self.sns.subscribe(
                    TopicArn=topic_arn,
                    Protocol='email',
                    Endpoint=email_address
                )
                logger.info(f"Subscription email sent to {email_address}. Please confirm before receiving digests.")
                return {"MessageId": "Pending subscription confirmation", "Status": "Subscription email sent"}
            
            # If subscribed but not confirmed, remind user
            if is_subscribed and not is_confirmed:
                return {"MessageId": "Pending subscription confirmation", "Status": "Please confirm your subscription"}
            
            # Send the digest with direct HTML content
            response = self.sns.publish(
                TopicArn=topic_arn,
                Message=html_content,  # Send HTML content directly
                Subject=subject
            )
            
            logger.info(f"Digest sent via SNS: {response['MessageId']}")
            return response
            
        except Exception as e:
            logger.error(f"Error sending digest: {e}")
            raise
    
    def send_direct_email(self, 
                         email_address: str, 
                         subject: str, 
                         html_content: str) -> Dict[str, Any]:
        """
        Send an email directly to an address without using a topic.
        This is useful for testing or one-off emails.
        
        Args:
            email_address (str): Recipient email address.
            subject (str): Email subject.
            html_content (str): HTML content of the email.
            
        Returns:
            dict: Response from SNS publish API.
        """
        try:
            # Create a temporary topic
            temp_topic_name = f"temp-digest-{os.urandom(8).hex()}"
            topic_arn = self.create_topic(temp_topic_name)
            
            # Set topic attributes for better display name
            self.sns.set_topic_attributes(
                TopicArn=topic_arn,
                AttributeName='DisplayName',
                AttributeValue='Content Aggregator'
            )
            
            # Subscribe the email address
            self.subscribe_email(topic_arn, email_address)
            
            # Send the email
            response = self.send_email_digest(topic_arn, subject, html_content)
            
            # Clean up the temporary topic (optional)
            # Note: We might want to keep it for a while to ensure delivery
            # self.sns.delete_topic(TopicArn=topic_arn)
            
            return response
        except Exception as e:
            logger.error(f"Error sending direct email: {e}")
            raise


if __name__ == "__main__":
    # Example usage when run directly
    import argparse
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description='Send email digest via AWS SNS')
    parser.add_argument('--email', required=True, help='Recipient email address')
    parser.add_argument('--subject', default='Your Daily Content Digest', help='Email subject')
    parser.add_argument('--digest', help='Path to HTML digest file')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--profile', help='AWS profile name')
    
    args = parser.parse_args()
    
    # If no digest file is specified, find the most recent one
    if not args.digest:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                               '..', '..', 'data')
        digest_files = list(Path(data_dir).glob('digest_*.html'))
        if not digest_files:
            print("No digest files found. Please generate a digest first.")
            exit(1)
        
        # Get the most recent file
        args.digest = str(max(digest_files, key=lambda p: p.stat().st_mtime))
        print(f"Using latest digest file: {args.digest}")
    
    # Load the HTML content
    with open(args.digest, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Send the email
    sender = EmailSender(region_name=args.region, profile_name=args.profile)
    response = sender.send_digest(args.email, args.subject, html_content)
    
    print(f"Email process completed! Status: {response.get('Status', 'Sent')} Message ID: {response.get('MessageId', 'N/A')}")
