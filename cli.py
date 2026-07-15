#!/usr/bin/env python3
"""
Command Line Interface for Content Aggregator

This module provides a CLI for running the content aggregator.
"""

import argparse
import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Import validation utilities
from backend.core.utils.validation import (
    validate_email_address, 
    validate_days, 
    validate_max_items, 
    validate_batch_size,
    sanitize_filename,
    ValidationError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Content Aggregator CLI')
    
    # Basic options
    parser.add_argument('--fetch-all', action='store_true', help='Fetch content from all sources')
    parser.add_argument('--rss-only', action='store_true', help='Fetch only RSS content')
    parser.add_argument('--github-only', action='store_true', help='Fetch only GitHub content')
    parser.add_argument('--youtube-only', action='store_true', help='Fetch only YouTube content')
    
    # Filter options
    parser.add_argument('--filter-category', type=str, help='Filter content by category')
    parser.add_argument('--filter-days', type=int, default=7, help='Filter content from the last X days (1-365)')
    
    # Output options
    parser.add_argument('--save', action='store_true', help='Save fetched content to a file')
    parser.add_argument('--load', type=str, help='Load content from a file')
    parser.add_argument('--search', type=str, help='Search content for a query string')
    
    # Email options
    parser.add_argument('--email', type=str, help='Send digest to email address')
    parser.add_argument('--max-items', type=int, default=10, help='Maximum items per category (1-100)')
    
    # Workflow options
    parser.add_argument('--enable-summarization', action='store_true', help='Enable content summarization')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for summarization (1-50)')
    
    return parser.parse_args()

def validate_args(args):
    """Validate command line arguments."""
    try:
        # Validate email if provided
        if args.email:
            args.email = validate_email_address(args.email)
        
        # Validate numeric parameters
        args.filter_days = validate_days(args.filter_days)
        args.max_items = validate_max_items(args.max_items)
        args.batch_size = validate_batch_size(args.batch_size)
        
        # Validate file paths
        if args.load:
            load_path = Path(args.load)
            if not load_path.exists():
                raise ValidationError(f"File not found: {args.load}")
            if not load_path.is_file():
                raise ValidationError(f"Path is not a file: {args.load}")
            # Ensure file is within current directory or subdirectories for security
            try:
                load_path.resolve().relative_to(Path.cwd().resolve())
            except ValueError:
                raise ValidationError("File must be within the current directory")
        
        # Validate search query
        if args.search:
            if len(args.search) > 200:
                raise ValidationError("Search query too long (max 200 characters)")
            args.search = args.search.strip()
        
        # Validate category filter
        if args.filter_category:
            if len(args.filter_category) > 50:
                raise ValidationError("Category name too long (max 50 characters)")
            args.filter_category = args.filter_category.strip()
        
        return args
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)

def run_traditional_workflow(args):
    """Run the content aggregator using the traditional approach."""
    from backend.core.aggregator import ContentAggregator
    from backend.core.email_digest.digest_generator import DigestGenerator
    from backend.core.email_digest.email_sender import EmailSender
    
    logger.info("Running content aggregator with traditional workflow")
    
    # Initialize the aggregator
    aggregator = ContentAggregator(enable_summarization=args.enable_summarization)
    
    # Fetch content based on options
    all_content = []
    
    if args.load:
        # Load content from file
        all_content = aggregator.load_content(args.load)
        logger.info(f"Loaded {len(all_content)} items from {args.load}")
    else:
        # Fetch content from sources
        if args.fetch_all or args.rss_only:
            rss_content = aggregator.fetch_rss_content()
            all_content.extend(rss_content)
            logger.info(f"Fetched {len(rss_content)} RSS items")
        
        if args.fetch_all or args.github_only:
            github_content = aggregator.fetch_github_content()
            all_content.extend(github_content)
            logger.info(f"Fetched {len(github_content)} GitHub items")
        
        if (args.fetch_all or args.youtube_only) and hasattr(aggregator, 'fetch_youtube_content'):
            try:
                youtube_content = aggregator.fetch_youtube_content()
                all_content.extend(youtube_content)
                logger.info(f"Fetched {len(youtube_content)} YouTube items")
            except Exception as e:
                logger.error(f"Error fetching YouTube content: {e}")
    
    # Filter content
    if args.filter_category:
        all_content = aggregator.filter_content_by_category(all_content, args.filter_category)
        logger.info(f"Filtered to {len(all_content)} items in category '{args.filter_category}'")
    
    all_content = aggregator.filter_content_by_date(all_content, args.filter_days)
    logger.info(f"Filtered to {len(all_content)} items from the last {args.filter_days} days")
    
    # Search content
    if args.search:
        all_content = [item for item in all_content if args.search.lower() in item.get('title', '').lower() or 
                      args.search.lower() in item.get('summary', '').lower()]
        logger.info(f"Found {len(all_content)} items matching '{args.search}'")
    
    # Save content
    if args.save:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = sanitize_filename(f'content_{timestamp}.json')
        
        # Ensure we save to a safe location
        safe_path = Path.cwd() / 'data' / filename
        safe_path.parent.mkdir(exist_ok=True)
        
        try:
            aggregator.save_content(all_content, str(safe_path))
            logger.info(f"Saved content to {safe_path}")
        except Exception as e:
            logger.error(f"Failed to save content: {e}")
    
    # Generate and send digest
    if args.email:
        digest_generator = DigestGenerator()
        digest = digest_generator.generate_digest(all_content, max_items_per_category=args.max_items)
        
        sender = EmailSender()
        response = sender.send_digest(args.email, "Your Daily Content Digest", digest)
        logger.info(f"Email process completed! Status: {response.get('Status', 'Sent')}")
    
    # Print summary
    print("\n" + "=" * 80)
    print(f"CONTENT SUMMARY: {len(all_content)} items")
    print("=" * 80)
    
    for i, item in enumerate(all_content[:10], 1):
        print(f"{i}. {item['title']}")
        print(f"   Source: {item['source']}")
        print(f"   Link: {item['link']}")
        print()
    
    if len(all_content) > 10:
        print(f"... and {len(all_content) - 10} more items")
    
    print("=" * 80)
    
    return all_content

def main():
    """Main entry point for the CLI."""
    try:
        args = parse_args()
        args = validate_args(args)
        
        # Check if at least one action is specified
        if not any([args.fetch_all, args.rss_only, args.github_only, args.youtube_only, args.load]):
            logger.error("No action specified. Use --fetch-all, --rss-only, --github-only, --youtube-only, or --load")
            sys.exit(1)
        
        # Run the workflow
        run_traditional_workflow(args)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running content aggregator: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
