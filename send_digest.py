#!/usr/bin/env python3
"""
Send Digest Script

This script fetches content from RSS feeds, generates an email digest,
and sends it via AWS SNS.
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add the parent directory to sys.path to allow importing from backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.fetchers.rss_fetcher import RSSFetcher
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
    Main function to fetch content, generate digest, and send email.
    """
    parser = argparse.ArgumentParser(description='Generate and send content digest')
    parser.add_argument('--email', required=True, help='Recipient email address')
    parser.add_argument('--subject', default='Your Daily Content Digest', help='Email subject')
    parser.add_argument('--max-items', type=int, default=10, help='Maximum items per category')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--save-only', action='store_true', help='Generate digest but do not send email')
    
    args = parser.parse_args()
    
    try:
        # Step 1: Fetch content from RSS feeds
        logger.info("Fetching content from RSS feeds...")
        fetcher = RSSFetcher()
        items = fetcher.fetch_all_feeds()
        
        if not items:
            logger.error("No content items found. Exiting.")
            return 1
        
        logger.info(f"Fetched {len(items)} items from RSS feeds")
        
        # Step 2: Generate email digest
        logger.info("Generating email digest...")
        generator = DigestGenerator()
        html_content = generator.generate_digest(items, max_items_per_category=args.max_items)
        
        # Save the digest to a file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        digest_path = os.path.join(data_dir, f'digest_{timestamp}.html')
        
        with open(digest_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Saved digest to {digest_path}")
        
        # Step 3: Send email (if not save-only)
        if not args.save_only:
            logger.info(f"Sending email digest to {args.email}...")
            sender = EmailSender(region_name=args.region, profile_name=args.profile)
            response = sender.send_direct_email(args.email, args.subject, html_content)
            logger.info(f"Email sent successfully! Message ID: {response['MessageId']}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
