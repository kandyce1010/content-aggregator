#!/usr/bin/env python3
"""
Digest Generator Lambda Function

This Lambda function generates and sends an email digest from summarized content.
"""

import os
import json
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    AWS Lambda function handler for digest generation.
    
    Args:
        event (dict): Event data with content S3 URI
        context (object): Lambda context
        
    Returns:
        dict: Response with digest information
    """
    try:
        logger.info("Digest Generator Lambda function invoked")
        
        # Extract parameters from the event
        content_s3_uri = event.get("content_s3_uri")
        email = event.get("email", os.environ.get('RECIPIENT_EMAIL'))
        max_items = int(event.get("max_items", os.environ.get('MAX_ITEMS', '10')))
        
        logger.info(f"Generating digest from content S3 URI: {content_s3_uri}")
        logger.info(f"Email recipient: {email}")
        logger.info(f"Max items per category: {max_items}")
        
        if not content_s3_uri:
            logger.warning("No content S3 URI for digest generation")
            return {
                "digest": "",
                "email": email,
                "stats": {
                    "items_count": 0
                }
            }
        
        # Import the necessary modules
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.email_digest.digest_generator import DigestGenerator
        from backend.email_digest.email_sender import EmailSender
        from backend.utils.s3_utils import S3Handler
        
        # Initialize the S3 handler and retrieve content
        s3_handler = S3Handler()
        content_items = s3_handler.retrieve_content_from_uri(content_s3_uri)
        
        logger.info(f"Retrieved {len(content_items)} content items from S3")
        
        if not content_items:
            logger.warning("No content items for digest generation")
            return {
                "digest": "",
                "email": email,
                "stats": {
                    "items_count": 0
                }
            }
        
        if not email:
            logger.warning("No email recipient specified")
            return {
                "digest": "",
                "email": "",
                "stats": {
                    "items_count": len(content_items)
                }
            }
        
        # Generate the digest
        logger.info("Generating digest content")
        digest_generator = DigestGenerator()
        digest = digest_generator.generate_text_digest(content_items, max_items_per_category=max_items)
        
        # Send the email
        logger.info(f"Sending email digest to {email}")
        sender = EmailSender()
        response = sender.send_digest(email, "Your Daily Content Digest", digest)
        logger.info(f"Email process completed! Status: {response.get('Status', 'Sent')}")
        
        return {
            "digest": digest,
            "email": email,
            "stats": {
                "items_count": len(content_items),
                "email_status": response.get('Status', 'Sent'),
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error in Digest Generator Lambda: {e}", exc_info=True)
        raise
