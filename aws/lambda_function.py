#!/usr/bin/env python3
"""
AWS Lambda Function for Content Aggregator

This module contains the Lambda function handler that will be invoked by EventBridge
to generate and send the content digest.
"""

import os
import json
import logging
from datetime import datetime
import boto3
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    AWS Lambda function handler.
    
    Args:
        event (dict): Event data from EventBridge
        context (object): Lambda context
        
    Returns:
        dict: Response with status information
    """
    try:
        logger.info("Content Aggregator Lambda function invoked")
        logger.info(f"Event: {json.dumps(event)}")
        
        # Extract parameters from the event
        params = event.get('params', {})
        email = params.get('email', os.environ.get('RECIPIENT_EMAIL'))
        days = params.get('days', os.environ.get('DAYS', '7'))
        max_items = params.get('max_items', os.environ.get('MAX_ITEMS', '10'))
        category = params.get('category', os.environ.get('CATEGORY', ''))
        
        if not email:
            raise ValueError("Recipient email is required")
        
        # Import the necessary modules
        # Note: In a real Lambda deployment, these would be packaged with the function
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.aggregator import ContentAggregator
        from backend.email_digest.digest_generator import DigestGenerator
        from backend.email_digest.email_sender import EmailSender
        
        # Step 1: Aggregate content from all sources
        logger.info("Aggregating content from all sources")
        aggregator = ContentAggregator(enable_summarization=True)
        
        # Fetch RSS content
        rss_content = aggregator.fetch_rss_content()
        
        # Fetch GitHub content
        github_content = aggregator.fetch_github_content()
        
        # Fetch YouTube content if available
        youtube_content = []
        if hasattr(aggregator, 'fetch_youtube_content'):
            try:
                youtube_content = aggregator.fetch_youtube_content()
                logger.info(f"Fetched {len(youtube_content)} YouTube items")
            except Exception as e:
                logger.error(f"Error fetching YouTube content: {e}")
        
        # Combine content
        all_content = rss_content + github_content + youtube_content
        
        # Enable content summarization with Bedrock if available
        try:
            if hasattr(aggregator, 'summarizer') and aggregator.summarizer:
                logger.info("Summarizing content with Bedrock")
                all_content = aggregator.summarizer.batch_summarize(all_content)
                
                # Copy generated_summary to ai_summary for compatibility
                for item in all_content:
                    if item.get('generated_summary'):
                        item['ai_summary'] = item['generated_summary']
                
                summary_count = sum(1 for item in all_content if item.get('ai_summary'))
                logger.info(f"Generated summaries for {summary_count}/{len(all_content)} items")
        except Exception as e:
            logger.error(f"Error summarizing content: {e}")
        
        # Deduplicate content
        try:
            original_count = len(all_content)
            all_content = aggregator.deduplicate_content(all_content)
            logger.info(f"Deduplicated from {original_count} to {len(all_content)} items")
        except Exception as e:
            logger.error(f"Error deduplicating content: {e}")
        
        # Filter by category if specified
        if category:
            all_content = aggregator.filter_content_by_category(all_content, category)
            logger.info(f"Filtered to {len(all_content)} items in category '{category}'")
        
        # Filter by date
        all_content = aggregator.filter_content_by_date(all_content, int(days))
        logger.info(f"Filtered to {len(all_content)} items from the last {days} days")
        
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
            content = title + ' ' + summary
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
            content_by_category[category] = content_by_category[category][:int(max_items)]
        
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
            
            for item in q_related_items[:int(max_items)]:
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
            
            for item in competitor_items[:int(max_items)]:
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
                
                for item in items[:int(max_items) // 2]:  # Show fewer general items
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
        
        # Step 3: Send email
        logger.info(f"Sending email digest to {email}")
        sender = EmailSender()
        response = sender.send_digest(email, "Your Daily Content Digest", digest_content)
        logger.info(f"Email process completed! Status: {response.get('Status', 'Sent')}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Content digest generated and sent successfully',
                'timestamp': datetime.now().isoformat(),
                'recipient': email,
                'items_count': len(all_content)
            })
        }
        
    except Exception as e:
        logger.error(f"Error in Lambda function: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Error generating or sending content digest: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })
        }

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
    content = title + ' ' + summary
    
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

# For local testing
if __name__ == "__main__":
    test_event = {
        'params': {
            'email': 'your.email@example.com',
            'days': '1',
            'max_items': '3'
        }
    }
    print(lambda_handler(test_event, None))
