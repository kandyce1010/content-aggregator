#!/usr/bin/env python3
"""
Command Line Interface for Content Aggregator

This module provides a CLI for running the content aggregator.
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime

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
    parser.add_argument('--filter-days', type=int, default=7, help='Filter content from the last X days')
    
    # Output options
    parser.add_argument('--save', action='store_true', help='Save fetched content to a file')
    parser.add_argument('--load', type=str, help='Load content from a file')
    parser.add_argument('--search', type=str, help='Search content for a query string')
    
    # Email options
    parser.add_argument('--email', type=str, help='Send digest to email address')
    parser.add_argument('--max-items', type=int, default=10, help='Maximum items per category')
    
    # Workflow options
    parser.add_argument('--use-strands', action='store_true', help='Use Strands workflow')
    parser.add_argument('--enable-summarization', action='store_true', help='Enable content summarization')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for summarization')
    
    return parser.parse_args()

async def run_strands_workflow(args):
    """Run the content aggregator using Strands workflow."""
    from backend.strands.workflow import ContentAggregatorWorkflow
    from backend.email_digest.email_sender import EmailSender
    
    logger.info("Running content aggregator with Strands workflow")
    
    # Create and run the workflow
    workflow = ContentAggregatorWorkflow(
        email=args.email,
        days=args.filter_days,
        max_items=args.max_items,
        category=args.filter_category or "",
        enable_summarization=args.enable_summarization,
        batch_size=args.batch_size
    )
    
    # Run the workflow
    workflow_results = await workflow.run()
    
    # Extract the digest content
    digest_results = workflow_results.get('generate_digest', {})
    digest_content = digest_results.get('digest', '')
    
    # Print the digest content
    print("\n" + "=" * 80)
    print("CONTENT DIGEST")
    print("=" * 80)
    print(digest_content)
    print("=" * 80)
    
    # Send the email if requested
    if args.email and digest_content:
        logger.info(f"Sending email digest to {args.email}")
        sender = EmailSender()
        response = sender.send_digest(args.email, "Your Daily Content Digest", digest_content)
        logger.info(f"Email process completed! Status: {response.get('Status', 'Sent')}")
    
    # Save the content if requested
    if args.save:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'content_{timestamp}.json'
        
        # Get the content items from the workflow results
        content_items = None
        if workflow_results.get('summarize_content'):
            content_items = workflow_results['summarize_content'].get('content_items', [])
        elif workflow_results.get('filter_content'):
            content_items = workflow_results['filter_content'].get('content_items', [])
        
        if content_items:
            import json
            with open(filename, 'w') as f:
                json.dump(content_items, f, indent=2)
            logger.info(f"Saved content to {filename}")
    
    return workflow_results

def run_traditional_workflow(args):
    """Run the content aggregator using the traditional approach."""
    from backend.aggregator import ContentAggregator
    from backend.email_digest.digest_generator import DigestGenerator
    from backend.email_digest.email_sender import EmailSender
    
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
        filename = f'content_{timestamp}.json'
        aggregator.save_content(all_content, filename)
        logger.info(f"Saved content to {filename}")
    
    # Generate and send digest
    if args.email:
        digest_generator = DigestGenerator()
        digest = digest_generator.generate_digest(all_content, max_items=args.max_items)
        
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
    args = parse_args()
    
    try:
        if args.use_strands:
            # Run the Strands workflow
            asyncio.run(run_strands_workflow(args))
        else:
            # Run the traditional workflow
            run_traditional_workflow(args)
    except Exception as e:
        logger.error(f"Error running content aggregator: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
