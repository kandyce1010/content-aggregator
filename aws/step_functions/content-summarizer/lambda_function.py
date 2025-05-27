#!/usr/bin/env python3
"""
Content Summarizer Lambda Function

This Lambda function summarizes a batch of content items using Amazon Bedrock.
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
    AWS Lambda function handler for content summarization.
    
    Args:
        event (dict): Event data with batch S3 URI
        context (object): Lambda context
        
    Returns:
        dict: Response with summarized items
    """
    try:
        logger.info("Content Summarizer Lambda function invoked")
        
        # Extract parameters from the event
        batch_s3_uri = event.get("batch_s3_uri")
        batch_index = event.get("batch_index", 0)
        batch_size = event.get("batch_size", 10)
        batch_start = event.get("batch_start", 0)
        batch_end = event.get("batch_end", 0)
        
        logger.info(f"Processing batch {batch_index}: S3 URI {batch_s3_uri} (indices {batch_start}-{batch_end})")
        
        if not batch_s3_uri:
            logger.warning("No batch S3 URI provided")
            return {
                "summarized_s3_uri": None,
                "batch_index": batch_index,
                "batch_size": batch_size,
                "batch_start": batch_start,
                "batch_end": batch_end,
                "summary_count": 0
            }
        
        # Import the necessary modules
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.summarization.bedrock_summarizer import BedrockSummarizer
        from backend.utils.s3_utils import S3Handler
        
        # Initialize the S3 handler and retrieve batch items
        s3_handler = S3Handler()
        batch_items = s3_handler.retrieve_content_from_uri(batch_s3_uri)
        
        logger.info(f"Retrieved {len(batch_items)} items from batch {batch_index}")
        
        # Initialize the summarizer
        logger.info("Initializing BedrockSummarizer")
        summarizer = BedrockSummarizer()
        
        # Summarize the batch
        logger.info(f"Summarizing {len(batch_items)} items")
        summarized_items = []
        
        # Process items in smaller sub-batches to avoid timeouts
        sub_batch_size = 3  # Process just a few items at a time
        for i in range(0, len(batch_items), sub_batch_size):
            sub_batch = batch_items[i:i+sub_batch_size]
            try:
                logger.info(f"Processing sub-batch {i//sub_batch_size + 1} with {len(sub_batch)} items")
                summarized_sub_batch = summarizer.batch_summarize(sub_batch)
                summarized_items.extend(summarized_sub_batch)
            except Exception as e:
                logger.error(f"Error summarizing sub-batch: {e}")
                # If summarization fails, add the original items without summaries
                summarized_items.extend(sub_batch)
        
        # Copy generated_summary to ai_summary for compatibility
        summary_count = 0
        for item in summarized_items:
            if item.get('generated_summary'):
                item['ai_summary'] = item['generated_summary']
                summary_count += 1
        
        logger.info(f"Generated summaries for {summary_count}/{len(batch_items)} items")
        
        # Store summarized items in S3
        summarized_key = s3_handler.generate_key(prefix=f'batch/{batch_index}', suffix='summarized')
        summarized_s3_uri = s3_handler.store_content(summarized_items, summarized_key)
        
        return {
            "summarized_s3_uri": summarized_s3_uri,
            "batch_index": batch_index,
            "batch_size": batch_size,
            "batch_start": batch_start,
            "batch_end": batch_end,
            "summary_count": summary_count
        }
        
    except Exception as e:
        logger.error(f"Error in Content Summarizer Lambda: {e}", exc_info=True)
        raise
