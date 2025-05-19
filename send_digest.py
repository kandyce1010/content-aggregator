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
    title = item.get('title', '').lower()
    summary = item.get('summary', '').lower()
    ai_summary = item.get('ai_summary', '').lower()
    content = title + ' ' + summary + ' ' + ai_summary
    
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
    parser.add_argument('--summarize', action='store_true', help='Enable content summarization with Bedrock')
    parser.add_argument('--mock-bedrock', action='store_true', help='Use mock mode for Bedrock (for testing)')
    
    args = parser.parse_args()
    
    # Set mock mode environment variable if requested
    if args.mock_bedrock:
        os.environ['BEDROCK_MOCK_MODE'] = '1'
    
    try:
        # Step 1: Aggregate content from all sources (excluding LinkedIn)
        logger.info("Aggregating content from all sources")
        aggregator = ContentAggregator(
            github_token=args.github_token,
            enable_summarization=args.summarize,
            bedrock_region=args.region,
            bedrock_profile=args.profile
        )
        
        # Fetch RSS content
        rss_content = aggregator.fetch_rss_content()
        
        # Fetch GitHub content
        github_content = aggregator.fetch_github_content()
        
        # Combine content (excluding LinkedIn)
        all_content = rss_content + github_content
        
        # Process content with summarization if enabled
        if args.summarize:
            logger.info("Summarizing content with Bedrock")
            if aggregator.summarizer:
                all_content = aggregator.summarizer.batch_summarize(all_content)
                
                # Copy generated_summary to ai_summary for compatibility
                for item in all_content:
                    if item.get('generated_summary'):
                        item['ai_summary'] = item['generated_summary']
                
                # Debug: Check if summaries were generated
                summary_count = sum(1 for item in all_content if item.get('ai_summary'))
                logger.info(f"Generated summaries for {summary_count}/{len(all_content)} items")
                
                # Print first few summaries for debugging
                for i, item in enumerate(all_content[:3]):
                    logger.info(f"Item {i+1} title: {item.get('title', 'Unknown')}")
                    logger.info(f"Item {i+1} has summary: {'Yes' if item.get('ai_summary') else 'No'}")
                    if item.get('ai_summary'):
                        logger.info(f"Item {i+1} summary: {item.get('ai_summary')[:50]}...")
            else:
                logger.warning("Summarization requested but summarizer not available")
        
        # Filter by category if specified
        if args.category:
            all_content = aggregator.filter_content_by_category(all_content, args.category)
            logger.info(f"Filtered to {len(all_content)} items in category '{args.category}'")
        
        # Filter by date
        all_content = aggregator.filter_content_by_date(all_content, args.days)
        logger.info(f"Filtered to {len(all_content)} items from the last {args.days} days")
        
        # Calculate relevance scores
        for item in all_content:
            item['relevance_score'] = calculate_relevance_score(item)
        
        # Save aggregated content
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        aggregator.save_content(all_content, f'aggregated_content_{timestamp}.json')
        
        # Step 2: Generate plain text digest
        logger.info("Generating plain text digest")
        
        # Separate Q-related and general content
        q_related_items = [item for item in all_content if item['relevance_score'] >= 30]
        general_items = [item for item in all_content if item['relevance_score'] < 30]
        
        # Find competitor-related items
        competitor_keywords = ['github copilot', 'anthropic claude', 'openai', 'gpt', 'bard', 'gemini']
        competitor_items = []
        for item in all_content:
            title = item.get('title', '').lower()
            summary = item.get('summary', '').lower()
            ai_summary = item.get('ai_summary', '').lower()
            content = title + ' ' + summary + ' ' + ai_summary
            for keyword in competitor_keywords:
                if keyword in content:
                    competitor_items.append(item)
                    break
        
        # Sort by relevance score (highest first)
        q_related_items.sort(key=lambda x: x['relevance_score'], reverse=True)
        competitor_items.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Organize general items by category
        content_by_category = {}
        for item in general_items:
            category = item.get('category', 'uncategorized')
            if category not in content_by_category:
                content_by_category[category] = []
            content_by_category[category].append(item)
        
        # Sort items within each category by published date (newest first)
        for category in content_by_category:
            content_by_category[category].sort(
                key=lambda x: x.get('published', ''), 
                reverse=True
            )
            # Limit items per category
            content_by_category[category] = content_by_category[category][:args.max_items]
        
        # Build plain text digest
        text_lines = []
        text_lines.append("YOUR DAILY CONTENT DIGEST")
        text_lines.append(datetime.now().strftime('%A, %B %d, %Y'))
        text_lines.append("=" * 60)
        text_lines.append("")
        
        # Amazon Q Related Content Section
        if q_related_items:
            text_lines.append("AMAZON Q & CODING ASSISTANT HIGHLIGHTS")
            text_lines.append("-" * 40)
            
            for item in q_related_items[:args.max_items]:
                text_lines.append(f"* {item['title']} [Relevance: {item['relevance_score']}]")
                text_lines.append(f"  Source: {item['source']}")
                if item.get('author') and item['author'] != 'Unknown':
                    text_lines.append(f"  By: {item['author']}")
                if item.get('ai_summary'):
                    text_lines.append(f"  Summary: {item['ai_summary']}")
                text_lines.append(f"  Link: {item['link']}")
                text_lines.append("")
            
            text_lines.append("")
        
        # Competitive Awareness Section
        if competitor_items:
            text_lines.append("COMPETITIVE AWARENESS")
            text_lines.append("-" * 40)
            
            for item in competitor_items[:args.max_items]:
                text_lines.append(f"* {item['title']} [Relevance: {item['relevance_score']}]")
                text_lines.append(f"  Source: {item['source']}")
                if item.get('author') and item['author'] != 'Unknown':
                    text_lines.append(f"  By: {item['author']}")
                if item.get('ai_summary'):
                    text_lines.append(f"  Summary: {item['ai_summary']}")
                text_lines.append(f"  Link: {item['link']}")
                text_lines.append("")
            
            text_lines.append("")
        
        # General Content by Category
        if content_by_category:
            text_lines.append("GENERAL INDUSTRY NEWS")
            text_lines.append("-" * 40)
            
            for category, items in sorted(content_by_category.items()):
                text_lines.append(f"{category.upper()}")
                
                for item in items[:args.max_items // 2]:  # Show fewer general items
                    text_lines.append(f"* {item['title']}")
                    text_lines.append(f"  Source: {item['source']}")
                    if item.get('author') and item['author'] != 'Unknown':
                        text_lines.append(f"  By: {item['author']}")
                    if item.get('ai_summary'):
                        text_lines.append(f"  Summary: {item['ai_summary']}")
                    text_lines.append(f"  Link: {item['link']}")
                    text_lines.append("")
                
                text_lines.append("")
        
        text_lines.append("=" * 60)
        text_lines.append("This digest was generated by Content Aggregator.")
        
        digest_content = "\n".join(text_lines)
        
        # Save digest to file
        digest_path = os.path.join(aggregator.data_dir, f'digest_{timestamp}.txt')
        with open(digest_path, 'w', encoding='utf-8') as f:
            f.write(digest_content)
        logger.info(f"Saved text digest to {digest_path}")
        
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
