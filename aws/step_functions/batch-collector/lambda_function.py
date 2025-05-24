#!/usr/bin/env python3
"""
Batch Collector Lambda Function

This Lambda function collects and merges summarized batches.
"""

import json
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    AWS Lambda function handler for batch collection.
    
    Args:
        event (dict): Event data with batch results
        context (object): Lambda context
        
    Returns:
        dict: Response with merged content items
    """
    try:
        logger.info("Batch Collector Lambda function invoked")
        
        # Extract parameters from the event
        batch_results = event.get("batch_results", [])
        original_content_s3_uri = event.get("original_content_s3_uri")
        
        logger.info(f"Collecting results from {len(batch_results)} batches")
        logger.info(f"Original content S3 URI: {original_content_s3_uri}")
        
        if not batch_results or not original_content_s3_uri:
            logger.warning("No batch results or original content S3 URI to collect")
            return {
                "content_s3_uri": None,
                "stats": {
                    "total_items": 0,
                    "summarized_count": 0
                }
            }
        
        # Import the necessary modules
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.utils.s3_utils import S3Handler
        
        # Initialize the S3 handler
        s3_handler = S3Handler()
        
        # Retrieve the original content items
        content_items = s3_handler.retrieve_content_from_uri(original_content_s3_uri)
        logger.info(f"Retrieved {len(content_items)} original content items")
        
        # Track summary statistics
        total_summary_count = 0
        
        # Update items with summaries from batches
        for batch_result in batch_results:
            summarized_s3_uri = batch_result.get("summarized_s3_uri")
            batch_start = batch_result.get("batch_start", 0)
            batch_end = batch_result.get("batch_end", 0)
            summary_count = batch_result.get("summary_count", 0)
            
            if not summarized_s3_uri:
                logger.warning(f"No summarized S3 URI for batch {batch_result.get('batch_index')}")
                continue
                
            logger.info(f"Processing batch result: {summarized_s3_uri}, indices {batch_start}-{batch_end}, {summary_count} summaries")
            
            # Update the total summary count
            total_summary_count += summary_count
            
            # Retrieve summarized items
            summarized_items = s3_handler.retrieve_content_from_uri(summarized_s3_uri)
            
            # Update items with summaries
            for i, item in enumerate(summarized_items):
                if batch_start + i < len(content_items):
                    if item.get('ai_summary'):
                        content_items[batch_start + i]['ai_summary'] = item['ai_summary']
                    if item.get('generated_summary'):
                        content_items[batch_start + i]['generated_summary'] = item['generated_summary']
        
        logger.info(f"Merged {len(content_items)} items with {total_summary_count} summaries")
        
        # Store the merged content in S3
        merged_key = s3_handler.generate_key(prefix='content', suffix='merged')
        merged_s3_uri = s3_handler.store_content(content_items, merged_key)
        
        # Pass through any parameters from the input event
        result = {
            "content_s3_uri": merged_s3_uri,
            "stats": {
                "total_items": len(content_items),
                "summarized_count": total_summary_count
            }
        }
        
        # Add any additional parameters from the input event
        for key, value in event.items():
            if key not in result and key != "batch_results" and key != "original_content_s3_uri":
                result[key] = value
        
        return result
        
    except Exception as e:
        logger.error(f"Error in Batch Collector Lambda: {e}", exc_info=True)
        raise
