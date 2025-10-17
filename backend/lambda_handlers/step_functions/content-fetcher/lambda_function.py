#!/usr/bin/env python3
"""
Content Fetcher Lambda Function

This Lambda function fetches content from various sources.
"""

import os
import json
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    AWS Lambda function handler for content fetching.
    
    Args:
        event (dict): Event data
        context (object): Lambda context
        
    Returns:
        dict: Response with fetched content
    """
    try:
        logger.info("Content Fetcher Lambda function invoked")
        logger.info(f"Event: {json.dumps(event).replace(chr(10), ' ').replace(chr(13), ' ').replace(chr(9), ' ')}")
        
        # Import the necessary modules
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.core.aggregator import ContentAggregator
        from backend.core.utils.s3_utils import S3Handler
        
        # Initialize the aggregator (without summarization)
        aggregator = ContentAggregator(enable_summarization=False)
        
        # Fetch RSS content
        logger.info("Fetching RSS content")
        rss_content = aggregator.fetch_rss_content()
        logger.info(f"Fetched {len(rss_content)} RSS items")
        
        # Fetch GitHub content
        logger.info("Fetching GitHub content")
        github_content = aggregator.fetch_github_content()
        logger.info(f"Fetched {len(github_content)} GitHub items")
        
        # Fetch YouTube content if available
        youtube_content = []
        if hasattr(aggregator, 'fetch_youtube_content'):
            try:
                logger.info("Fetching YouTube content")
                youtube_content = aggregator.fetch_youtube_content() or []
                logger.info(f"Fetched {len(youtube_content)} YouTube items")
            except Exception as e:
                logger.error(f"Error fetching YouTube content: {str(e).replace(chr(10), ' ').replace(chr(13), ' ').replace(chr(9), ' ')}")
        
        # Combine all content
        all_content = rss_content + github_content + youtube_content
        logger.info(f"Total content items: {len(all_content)}")
        
        # Store content in S3
        s3_handler = S3Handler()
        content_key = s3_handler.generate_key(prefix='content', suffix='raw')
        s3_uri = s3_handler.store_content(all_content, content_key)
        
        # Pass through any parameters from the input event
        result = {
            "content_s3_uri": s3_uri,
            "stats": {
                "rss_count": len(rss_content),
                "github_count": len(github_content),
                "youtube_count": len(youtube_content),
                "total_count": len(all_content)
            }
        }
        
        # Add any additional parameters from the input event
        for key, value in event.items():
            if key not in result:
                result[key] = value
        
        return result
        
    except Exception as e:
        logger.error(f"Error in Content Fetcher Lambda: {str(e).replace(chr(10), ' ').replace(chr(13), ' ').replace(chr(9), ' ')}", exc_info=True)
        raise
