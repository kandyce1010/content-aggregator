#!/usr/bin/env python3
"""
Content Filter Lambda Function

This Lambda function filters and scores content items.
"""

import os
import json
import logging
import sys
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def sanitize_for_logging(value):
    """Sanitize input for safe logging by removing control characters."""
    if value is None:
        return 'None'
    # Remove all control characters (ASCII 0-31 and 127) except space (32)
    return re.sub(r'[\x00-\x1f\x7f]', ' ', str(value))

def lambda_handler(event, context):
    """
    AWS Lambda function handler for content filtering.
    
    Args:
        event (dict): Event data with content S3 URI
        context (object): Lambda context
        
    Returns:
        dict: Response with filtered content
    """
    try:
        logger.info("Content Filter Lambda function invoked")
        
        # Extract parameters from the event
        content_s3_uri = event.get("content_s3_uri")
        days = int(event.get("days", 7))
        category = event.get("category", "")
        
        logger.info(f"Processing content from S3 URI: {sanitize_for_logging(content_s3_uri)}")
        logger.info(f"Filter parameters: days={days}, category={sanitize_for_logging(category)}")
        
        if not content_s3_uri:
            logger.warning("No content S3 URI provided")
            return {
                "content_s3_uri": None,
                "stats": {
                    "original_count": 0,
                    "filtered_count": 0
                }
            }
        
        # Import the necessary modules
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.core.aggregator import ContentAggregator
        from backend.core.utils.s3_utils import S3Handler
        
        # Initialize the S3 handler and retrieve content
        s3_handler = S3Handler()
        content_items = s3_handler.retrieve_content_from_uri(content_s3_uri)
        
        # Initialize the aggregator (without summarization)
        aggregator = ContentAggregator(enable_summarization=False)
        
        # Deduplicate content
        original_count = len(content_items)
        logger.info(f"Deduplicating {original_count} content items")
        content_items = aggregator.deduplicate_content(content_items)
        logger.info(f"After deduplication: {len(content_items)} items")
        
        # Filter by category if specified
        if category:
            logger.info(f"Filtering by category: {sanitize_for_logging(category)}")
            content_items = aggregator.filter_content_by_category(content_items, category)
            logger.info(f"After category filtering: {len(content_items)} items")
        
        # Filter by date - restrict to only the last 1-2 days
        logger.info(f"Filtering by date: last {days} days")
        # Override days parameter to ensure we only get recent content (1-2 days)
        days = min(days, 2)  # Limit to maximum of 2 days
        content_items = aggregator.filter_content_by_date(content_items, days)
        logger.info(f"After date filtering: {len(content_items)} items")
        
        # Calculate relevance scores
        logger.info("Calculating relevance scores")
        for item in content_items:
            item['relevance_score'] = calculate_relevance_score(item)
        
        # Sort by relevance score (highest first)
        content_items.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Store filtered content in S3
        filtered_key = s3_handler.generate_key(prefix='content', suffix='filtered')
        filtered_s3_uri = s3_handler.store_content(content_items, filtered_key)
        
        # Pass through any parameters from the input event
        result = {
            "content_s3_uri": filtered_s3_uri,
            "stats": {
                "original_count": original_count,
                "filtered_count": len(content_items)
            }
        }
        
        # Add any additional parameters from the input event
        for key, value in event.items():
            if key not in result and key != "content_s3_uri":
                result[key] = value
        
        return result
        
    except Exception as e:
        logger.error(f"Error in Content Filter Lambda: {sanitize_for_logging(e)}", exc_info=True)
        raise

def calculate_relevance_score(item):
    """
    Calculate a relevance score for an item based on Q-related keywords.
    Higher score means more relevant to Amazon Q.
    
    Args:
        item (dict): Content item to score
        
    Returns:
        int: Relevance score (0-100)
    """
    primary_keywords = ['amazon q', 'q developer', 'codewhisperer']
    secondary_keywords = ['coding assistant', 'ai pair programming', 'code generation']
    tertiary_keywords = ['generative ai', 'llm', 'large language model', 'ai coding']
    competitor_keywords = ['github copilot', 'anthropic claude', 'openai', 'gpt', 'bard', 'gemini']
    
    score = 0
    title = item.get('title', '').lower() if item.get('title') is not None else ''
    summary = item.get('summary', '').lower() if item.get('summary') is not None else ''
    content = title + ' ' + summary
    
    # Primary keywords (Amazon Q specific)
    for keyword in primary_keywords:
        if keyword in title:
            score += 50
        elif keyword in summary:
            score += 30
    
    # Secondary keywords (coding assistant specific)
    for keyword in secondary_keywords:
        if keyword in title:
            score += 30
        elif keyword in summary:
            score += 20
    
    # Tertiary keywords (general AI/ML)
    for keyword in tertiary_keywords:
        if keyword in title:
            score += 15
        elif keyword in summary:
            score += 10
    
    # Competitor keywords
    for keyword in competitor_keywords:
        if keyword in title:
            score += 25
        elif keyword in summary:
            score += 15
    
    # Cap the score at 100
    return min(score, 100)
