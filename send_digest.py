#!/usr/bin/env python3
"""
Send Digest Script

This script aggregates content from all sources, generates an email digest,
and sends it via AWS SNS.
"""

import os
import argparse
import logging
from datetime import datetime
from pathlib import Path

from backend.aggregator import ContentAggregator
from backend.email_digest.digest_generator import DigestGenerator
from backend.email_digest.email_sender import EmailSender

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """
    Main function to aggregate content, generate digest, and send email.
    """
    parser = argparse.ArgumentParser(description='Send content digest email')
    parser.add_argument('--email', required=True, help='Recipient email address')
    parser.add_argument('--subject', default='Your Daily Content Digest', help='Email subject')
    parser.add_argument('--days', type=int, default=7, help='Include content from the last X days')
    parser.add_argument('--category', help='Filter by category')
    parser.add_argument('--max-items', type=int, default=10, help='Maximum items per category')
    parser.add_argument('--github-token', help='GitHub personal access token')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--save-only', action='store_true', help='Save digest without sending email')
    parser.add_argument('--text-digest', action='store_true', help='Generate plain text digest')
    
    args = parser.parse_args()
    
    try:
        # Step 1: Aggregate content from all sources
        logger.info("Aggregating content from all sources")
        aggregator = ContentAggregator(github_token=args.github_token)
        all_content = aggregator.fetch_all_content(parallel=True)
        
        # Filter by category if specified
        if args.category:
            all_content = aggregator.filter_content_by_category(all_content, args.category)
            logger.info(f"Filtered to {len(all_content)} items in category '{args.category}'")
        
        # Filter by date
        all_content = aggregator.filter_content_by_date(all_content, args.days)
        logger.info(f"Filtered to {len(all_content)} items from the last {args.days} days")
        
        # Save aggregated content
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        aggregator.save_content(all_content, f'aggregated_content_{timestamp}.json')
        
        # Step 2: Generate email digest
        logger.info("Generating email digest")
        generator = DigestGenerator()
        
        if args.text_digest:
            digest_content = generator.generate_text_digest(all_content, args.max_items)
            digest_path = os.path.join(aggregator.data_dir, f'digest_{timestamp}.txt')
            with open(digest_path, 'w', encoding='utf-8') as f:
                f.write(digest_content)
            logger.info(f"Saved text digest to {digest_path}")
        else:
            digest_content = generator.generate_digest(all_content, args.max_items)
            digest_path = generator.save_digest(digest_content, 
                                              os.path.join(aggregator.data_dir, f'digest_{timestamp}.html'))
        
        # Step 3: Send email (if not save-only)
        if not args.save_only:
            logger.info(f"Sending email digest to {args.email}")
            sender = EmailSender(region_name=args.region, profile_name=args.profile)
            response = sender.send_digest(args.email, args.subject, digest_content)
            logger.info(f"Email process completed! Status: {response.get('Status', 'Sent')}")
        else:
            logger.info(f"Digest saved to {digest_path} (not sending email)")
        
        logger.info("Digest process completed successfully")
        
    except Exception as e:
        logger.error(f"Error in digest process: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
