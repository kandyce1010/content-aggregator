#!/usr/bin/env python3
"""
Test script for Step Functions workflow

This script simulates the Step Functions workflow by calling each Lambda function in sequence.
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the Lambda functions
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aws/step_functions/content-fetcher'))
from lambda_function import lambda_handler as content_fetcher

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aws/step_functions/content-filter'))
from lambda_function import lambda_handler as content_filter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aws/step_functions/batch-distributor'))
from lambda_function import lambda_handler as batch_distributor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aws/step_functions/content-summarizer'))
from lambda_function import lambda_handler as content_summarizer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aws/step_functions/batch-collector'))
from lambda_function import lambda_handler as batch_collector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aws/step_functions/digest-generator'))
from lambda_function import lambda_handler as digest_generator

async def test_workflow():
    """
    Test the Step Functions workflow by calling each Lambda function in sequence.
    """
    try:
        # Initial input
        input_event = {
            "email": "test@example.com",  # Replace with your email for actual testing
            "days": 1,
            "max_items": 5,
            "batch_size": 2
        }
        
        logger.info("Starting test workflow")
        logger.info(f"Input: {json.dumps(input_event)}")
        
        # Step 1: Fetch content
        logger.info("Step 1: Fetch content")
        fetch_result = content_fetcher(input_event, None)
        logger.info(f"Fetched {fetch_result['stats']['total_count']} content items")
        
        # Step 2: Filter content
        logger.info("Step 2: Filter content")
        filter_result = content_filter(fetch_result, None)
        logger.info(f"Filtered to {filter_result['stats']['filtered_count']} content items")
        
        # Step 3: Distribute batches
        logger.info("Step 3: Distribute batches")
        distribute_result = batch_distributor(filter_result, None)
        logger.info(f"Created {distribute_result['num_batches']} batches")
        
        # Step 4: Summarize batches
        logger.info("Step 4: Summarize batches")
        batch_results = []
        for batch in distribute_result['batches']:
            logger.info(f"Processing batch {batch['batch_index'] + 1}/{distribute_result['num_batches']}")
            summarize_result = content_summarizer(batch, None)
            batch_results.append(summarize_result)
            logger.info(f"Generated {summarize_result['summary_count']} summaries for batch {batch['batch_index'] + 1}")
        
        # Step 5: Collect batches
        logger.info("Step 5: Collect batches")
        collect_input = {
            "batch_results": batch_results,
            "content_items": distribute_result['content_items']
        }
        collect_result = batch_collector(collect_input, None)
        logger.info(f"Collected {collect_result['stats']['summarized_count']} summaries")
        
        # Step 6: Generate digest (skip sending email in test)
        logger.info("Step 6: Generate digest (email sending disabled for test)")
        # Set email to None to skip sending
        collect_result['email'] = None
        digest_result = digest_generator(collect_result, None)
        
        # Print the digest
        logger.info("Digest content:")
        print("\n" + "=" * 80)
        print(digest_result['digest'])
        print("=" * 80)
        
        logger.info("Test workflow completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in test workflow: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    # Run the test workflow
    success = asyncio.run(test_workflow())
    if success:
        print("Test completed successfully!")
    else:
        print("Test failed!")
        sys.exit(1)
