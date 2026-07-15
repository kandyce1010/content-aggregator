#!/usr/bin/env python3
"""
Send Digest Script

Fetches content from all sources, generates an HTML email digest,
and sends it via Amazon SES. Useful for manual runs and local testing
without waiting for the scheduled EventBridge trigger.
"""

import os
import argparse
import logging
from datetime import datetime
from pathlib import Path

from backend.core.aggregator import ContentAggregator
from backend.core.email_digest.digest_generator import DigestGenerator
from backend.core.email_digest.email_sender import EmailSender

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Fetch content and send HTML digest via SES')
    parser.add_argument('--email', required=True, help='Recipient email address')
    parser.add_argument('--subject', default='Your Daily Content Digest', help='Email subject')
    parser.add_argument('--days', type=int, default=2, help='Include content from the last N days')
    parser.add_argument('--category', help='Filter by category')
    parser.add_argument('--max-items', type=int, default=10, help='Maximum items per category')
    parser.add_argument('--github-token', help='GitHub personal access token')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--profile', help='AWS profile name (~/.aws credentials)')
    parser.add_argument('--save-only', action='store_true', help='Save digest HTML without sending email')
    parser.add_argument('--summarize', action='store_true', help='Enable content summarization with Bedrock')

    args = parser.parse_args()

    try:
        logger.info("Aggregating content from all sources")
        aggregator = ContentAggregator(
            github_token=args.github_token,
            enable_summarization=args.summarize,
            bedrock_region=args.region,
            bedrock_profile=args.profile
        )

        all_content = aggregator.fetch_rss_content() + aggregator.fetch_github_content()
        logger.info(f"Fetched {len(all_content)} items total")

        if args.summarize and aggregator.summarizer:
            logger.info("Summarizing content with Bedrock")
            all_content = aggregator.summarizer.batch_summarize(all_content)
            for item in all_content:
                if item.get('generated_summary'):
                    item['ai_summary'] = item['generated_summary']

        all_content = aggregator.deduplicate_content(all_content)

        if args.category:
            all_content = aggregator.filter_content_by_category(all_content, args.category)
            logger.info(f"Filtered to {len(all_content)} items in category '{args.category}'")

        all_content = aggregator.filter_content_by_date(all_content, args.days)
        logger.info(f"Filtered to {len(all_content)} items from the last {args.days} days")

        logger.info("Generating HTML digest")
        html_content = DigestGenerator().generate_digest(all_content, max_items_per_category=args.max_items)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        digest_path = Path(aggregator.data_dir) / f'digest_{timestamp}.html'
        digest_path.parent.mkdir(parents=True, exist_ok=True)
        digest_path.write_text(html_content, encoding='utf-8')
        logger.info(f"Saved digest to {digest_path}")

        if not args.save_only:
            logger.info(f"Sending email digest to {args.email}")
            sender = EmailSender(region_name=args.region, profile_name=args.profile)
            response = sender.send_digest(args.email, args.subject, html_content)
            logger.info(f"Digest sent: {response.get('MessageId')}")
        else:
            logger.info(f"Saved to {digest_path} (--save-only, email not sent)")

    except Exception as e:
        logger.error(f"Error in digest process: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
