#!/usr/bin/env python3
"""
Digest Generator Lambda Function

This Lambda function generates an HTML email digest and sends it via SES.
"""

import os
import json
import logging
import sys
import re
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sanitize_for_logging(value):
    """Sanitize input for safe logging by removing control characters."""
    if value is None:
        return 'None'
    return re.sub(r'[\x00-\x1f\x7f]', ' ', str(value))


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

        content_s3_uri = event.get("content_s3_uri")
        email = event.get("email", os.environ.get('RECIPIENT_EMAIL'))
        max_items = int(event.get("max_items", os.environ.get('MAX_ITEMS', '10')))

        logger.info(f"Generating digest from content S3 URI: {sanitize_for_logging(content_s3_uri)}")
        logger.info(f"Email recipient: {sanitize_for_logging(email)}")
        logger.info(f"Max items per category: {max_items}")

        if not content_s3_uri:
            logger.warning("No content S3 URI for digest generation")
            return {"digest_sent": False, "email": email, "stats": {"items_count": 0}}

        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.core.email_digest.digest_generator import DigestGenerator
        from backend.core.email_digest.email_sender import EmailSender
        from backend.core.utils.s3_utils import S3Handler

        s3_handler = S3Handler()
        content_items = s3_handler.retrieve_content_from_uri(content_s3_uri)

        logger.info(f"Retrieved {len(content_items) if content_items else 0} content items from S3")

        if not content_items:
            logger.warning("No content items for digest generation")
            return {"digest_sent": False, "email": email, "stats": {"items_count": 0}}

        if not email:
            logger.warning("No email recipient specified")
            return {"digest_sent": False, "email": "", "stats": {"items_count": len(content_items)}}

        digest_generator = DigestGenerator()
        html_content = digest_generator.generate_digest(content_items, max_items_per_category=max_items)

        sender = EmailSender()
        response = sender.send_digest(email, "Your Daily Content Digest", html_content)
        logger.info(f"Digest sent via SES: {response.get('MessageId')}")

        return {
            "digest_sent": True,
            "email": email,
            "stats": {
                "items_count": len(content_items),
                "message_id": response.get('MessageId'),
                "timestamp": datetime.now().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Error in Digest Generator Lambda: {sanitize_for_logging(e)}", exc_info=True)
        raise
