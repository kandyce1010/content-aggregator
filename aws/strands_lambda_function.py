#!/usr/bin/env python3
"""
AWS Lambda Function for Content Aggregator using Strands

This module contains the Lambda function handler that uses Strands to orchestrate
the content aggregation and summarization workflow.
"""

import os
import json
import logging
import asyncio
from datetime import datetime
import boto3
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    AWS Lambda function handler.
    
    Args:
        event (dict): Event data from EventBridge
        context (object): Lambda context
        
    Returns:
        dict: Response with status information
    """
    try:
        logger.info("Content Aggregator Lambda function invoked with Strands workflow")
        logger.info(f"Event: {json.dumps(event)}")
        
        # Extract parameters from the event
        params = event.get('params', {})
        email = params.get('email', os.environ.get('RECIPIENT_EMAIL'))
        days = int(params.get('days', os.environ.get('DAYS', '7')))
        max_items = int(params.get('max_items', os.environ.get('MAX_ITEMS', '10')))
        category = params.get('category', os.environ.get('CATEGORY', ''))
        enable_summarization = params.get('enable_summarization', 'true').lower() == 'true'
        batch_size = int(params.get('batch_size', os.environ.get('BATCH_SIZE', '10')))
        
        if not email:
            raise ValueError("Recipient email is required")
        
        # Import the necessary modules
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.strands.workflow import ContentAggregatorWorkflow
        from backend.email_digest.email_sender import EmailSender
        
        # Create and run the workflow
        workflow = ContentAggregatorWorkflow(
            email=email,
            days=days,
            max_items=max_items,
            category=category,
            enable_summarization=enable_summarization,
            batch_size=batch_size
        )
        
        # Run the workflow asynchronously
        loop = asyncio.get_event_loop()
        workflow_results = loop.run_until_complete(workflow.run())
        
        # Extract the digest content
        digest_results = workflow_results.get('generate_digest', {})
        digest_content = digest_results.get('digest', '')
        
        # Send the email
        if digest_content:
            logger.info(f"Sending email digest to {email}")
            sender = EmailSender()
            response = sender.send_digest(email, "Your Daily Content Digest", digest_content)
            logger.info(f"Email process completed! Status: {response.get('Status', 'Sent')}")
        else:
            logger.warning("No digest content generated, email not sent")
        
        # Collect statistics from all steps
        stats = {
            'fetch': workflow_results.get('fetch_content', {}).get('stats', {}),
            'filter': workflow_results.get('filter_content', {}).get('stats', {}),
            'summarize': workflow_results.get('summarize_content', {}).get('stats', {}) if enable_summarization else {},
            'digest': digest_results.get('stats', {})
        }
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Content digest generated and sent successfully',
                'timestamp': datetime.now().isoformat(),
                'recipient': email,
                'stats': stats
            })
        }
        
    except Exception as e:
        logger.error(f"Error in Lambda function: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Error generating or sending content digest: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })
        }

# For local testing
if __name__ == "__main__":
    test_event = {
        'params': {
            'email': 'your.email@example.com',
            'days': '1',
            'max_items': '3',
            'enable_summarization': 'true',
            'batch_size': '5'
        }
    }
    print(lambda_handler(test_event, None))
