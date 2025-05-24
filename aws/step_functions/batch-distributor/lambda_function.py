#!/usr/bin/env python3
"""
Batch Distributor Lambda Function

This Lambda function distributes content items into batches for parallel processing.
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
    AWS Lambda function handler for batch distribution.
    
    Args:
        event (dict): Event data with content S3 URI
        context (object): Lambda context
        
    Returns:
        dict: Response with batch configurations
    """
    try:
        logger.info("Batch Distributor Lambda function invoked")
        
        # Extract parameters from the event
        content_s3_uri = event.get("content_s3_uri")
        batch_size = int(event.get("batch_size", 10))
        
        logger.info(f"Processing content from S3 URI: {content_s3_uri}")
        logger.info(f"Batch size: {batch_size}")
        
        if not content_s3_uri:
            logger.warning("No content S3 URI provided")
            return {
                "batches": [],
                "num_batches": 0,
                "total_items": 0
            }
        
        # Import the necessary modules
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.utils.s3_utils import S3Handler
        
        # Initialize the S3 handler and retrieve content
        s3_handler = S3Handler()
        content_items = s3_handler.retrieve_content_from_uri(content_s3_uri)
        
        logger.info(f"Retrieved {len(content_items)} content items from S3")
        
        # Calculate the number of batches
        num_items = len(content_items)
        num_batches = (num_items + batch_size - 1) // batch_size  # Ceiling division
        
        logger.info(f"Creating {num_batches} batches")
        
        # Create batch configurations
        batches = []
        for i in range(num_batches):
            # Calculate batch start and end indices
            start_idx = i * batch_size
            end_idx = min(start_idx + batch_size, num_items)
            
            # Get the batch of items
            batch_items = content_items[start_idx:end_idx]
            
            # Store batch in S3
            batch_key = s3_handler.generate_key(prefix=f'batch/{i}', suffix='items')
            batch_s3_uri = s3_handler.store_content(batch_items, batch_key)
            
            batches.append({
                "batch_s3_uri": batch_s3_uri,
                "batch_index": i,
                "batch_size": batch_size,
                "batch_start": start_idx,
                "batch_end": end_idx,
                "item_count": len(batch_items)
            })
        
        # Store the original content S3 URI for later use
        result = {
            "batches": batches,
            "num_batches": num_batches,
            "total_items": num_items,
            "original_content_s3_uri": content_s3_uri
        }
        
        # Add any additional parameters from the input event
        for key, value in event.items():
            if key not in result and key != "content_s3_uri":
                result[key] = value
        
        return result
        
    except Exception as e:
        logger.error(f"Error in Batch Distributor Lambda: {e}", exc_info=True)
        raise
