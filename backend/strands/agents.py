#!/usr/bin/env python3
"""
Strands Agents for Content Aggregator

This module defines specialized agents for the content aggregation workflow.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from strands import Agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContentFetcherAgent(Agent):
    """
    Agent responsible for fetching content from various sources.
    """
    
    def __init__(self, aggregator=None):
        """
        Initialize the ContentFetcherAgent.
        
        Args:
            aggregator: ContentAggregator instance to use for fetching content
        """
        super().__init__()
        self.aggregator = aggregator
    
    async def process(self, sources: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch content from various sources.
        
        Args:
            sources: Configuration for content sources
            
        Returns:
            Dict containing fetched content items
        """
        logger.info("ContentFetcherAgent: Starting content fetching")
        
        if not self.aggregator:
            # Import here to avoid circular imports
            from backend.aggregator import ContentAggregator
            self.aggregator = ContentAggregator(enable_summarization=False)
        
        # Fetch content from different sources
        rss_content = self.aggregator.fetch_rss_content()
        logger.info(f"Fetched {len(rss_content)} RSS items")
        
        github_content = self.aggregator.fetch_github_content()
        logger.info(f"Fetched {len(github_content)} GitHub items")
        
        # Fetch YouTube content if available
        youtube_content = []
        if hasattr(self.aggregator, 'fetch_youtube_content'):
            try:
                youtube_content = self.aggregator.fetch_youtube_content()
                logger.info(f"Fetched {len(youtube_content)} YouTube items")
            except Exception as e:
                logger.error(f"Error fetching YouTube content: {e}")
        
        # Combine all content
        all_content = rss_content + github_content + youtube_content
        logger.info(f"ContentFetcherAgent: Completed fetching {len(all_content)} total items")
        
        return {
            "content_items": all_content,
            "stats": {
                "rss_count": len(rss_content),
                "github_count": len(github_content),
                "youtube_count": len(youtube_content),
                "total_count": len(all_content)
            }
        }


class ContentFilterAgent(Agent):
    """
    Agent responsible for filtering and scoring content.
    """
    
    def __init__(self, aggregator=None):
        """
        Initialize the ContentFilterAgent.
        
        Args:
            aggregator: ContentAggregator instance to use for filtering content
        """
        super().__init__()
        self.aggregator = aggregator
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter and score content items.
        
        Args:
            input_data: Dictionary containing content items to filter
            
        Returns:
            Dict containing filtered and scored content items
        """
        logger.info("ContentFilterAgent: Starting content filtering and scoring")
        
        content_items = input_data.get("content_items", [])
        days = input_data.get("days", 7)
        category = input_data.get("category", "")
        
        if not content_items:
            logger.warning("No content items to filter")
            return {"content_items": [], "stats": {"filtered_count": 0}}
        
        if not self.aggregator:
            # Import here to avoid circular imports
            from backend.aggregator import ContentAggregator
            self.aggregator = ContentAggregator(enable_summarization=False)
        
        # Deduplicate content
        original_count = len(content_items)
        content_items = self.aggregator.deduplicate_content(content_items)
        logger.info(f"Deduplicated from {original_count} to {len(content_items)} items")
        
        # Filter by category if specified
        if category:
            content_items = self.aggregator.filter_content_by_category(content_items, category)
            logger.info(f"Filtered to {len(content_items)} items in category '{category}'")
        
        # Filter by date
        content_items = self.aggregator.filter_content_by_date(content_items, int(days))
        logger.info(f"Filtered to {len(content_items)} items from the last {days} days")
        
        # Calculate relevance scores
        for item in content_items:
            item['relevance_score'] = self._calculate_relevance_score(item)
        
        # Sort by relevance score (highest first)
        content_items.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        logger.info(f"ContentFilterAgent: Completed filtering and scoring {len(content_items)} items")
        
        return {
            "content_items": content_items,
            "stats": {
                "original_count": original_count,
                "filtered_count": len(content_items)
            }
        }
    
    def _calculate_relevance_score(self, item: Dict[str, Any]) -> int:
        """
        Calculate a relevance score for an item based on Q-related keywords.
        Higher score means more relevant to Amazon Q.
        
        Args:
            item: Content item to score
            
        Returns:
            Relevance score (0-100)
        """
        primary_keywords = ['amazon q', 'q developer', 'codewhisperer']
        secondary_keywords = ['coding assistant', 'ai pair programming', 'code generation']
        tertiary_keywords = ['generative ai', 'llm', 'large language model', 'ai coding']
        competitor_keywords = ['github copilot', 'anthropic claude', 'openai', 'gpt', 'bard', 'gemini']
        
        score = 0
        title = item.get('title', '').lower() if item.get('title') is not None else ''
        summary = item.get('summary', '').lower() if item.get('summary') is not None else ''
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


class SummarizationAgent(Agent):
    """
    Agent responsible for summarizing content using Amazon Bedrock.
    """
    
    def __init__(self, batch_size: int = 10):
        """
        Initialize the SummarizationAgent.
        
        Args:
            batch_size: Number of items to process in each batch
        """
        super().__init__()
        self.batch_size = batch_size
        self.summarizer = None
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Summarize content items using Amazon Bedrock.
        
        Args:
            input_data: Dictionary containing content items to summarize
            
        Returns:
            Dict containing summarized content items
        """
        logger.info("SummarizationAgent: Starting content summarization")
        
        content_items = input_data.get("content_items", [])
        
        if not content_items:
            logger.warning("No content items to summarize")
            return {"content_items": [], "stats": {"summarized_count": 0}}
        
        # Initialize the summarizer if not already done
        if not self.summarizer:
            try:
                # Import here to avoid circular imports
                from backend.summarization.bedrock_summarizer import BedrockSummarizer
                self.summarizer = BedrockSummarizer()
            except Exception as e:
                logger.error(f"Error initializing BedrockSummarizer: {e}")
                return {
                    "content_items": content_items,
                    "stats": {"summarized_count": 0, "error": str(e)}
                }
        
        # Create batches for processing
        batches = self._create_batches(content_items, self.batch_size)
        logger.info(f"Created {len(batches)} batches of size {self.batch_size}")
        
        # Process batches asynchronously
        summarized_items = []
        summary_count = 0
        
        for i, batch in enumerate(batches):
            logger.info(f"Processing batch {i+1}/{len(batches)}")
            try:
                # Process the batch
                summarized_batch = await self._summarize_batch(batch)
                summarized_items.extend(summarized_batch)
                
                # Count items with summaries
                batch_summary_count = sum(1 for item in summarized_batch if item.get('generated_summary'))
                summary_count += batch_summary_count
                
                logger.info(f"Batch {i+1}: Summarized {batch_summary_count}/{len(batch)} items")
            except Exception as e:
                logger.error(f"Error processing batch {i+1}: {e}")
                # Add the batch without summaries
                summarized_items.extend(batch)
        
        # Copy generated_summary to ai_summary for compatibility with existing code
        for item in summarized_items:
            if item.get('generated_summary'):
                item['ai_summary'] = item['generated_summary']
        
        logger.info(f"SummarizationAgent: Completed summarization of {summary_count}/{len(content_items)} items")
        
        return {
            "content_items": summarized_items,
            "stats": {
                "total_count": len(content_items),
                "summarized_count": summary_count
            }
        }
    
    def _create_batches(self, items: List[Dict[str, Any]], batch_size: int) -> List[List[Dict[str, Any]]]:
        """
        Create batches of items for processing.
        
        Args:
            items: List of items to batch
            batch_size: Size of each batch
            
        Returns:
            List of batches
        """
        return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    
    async def _summarize_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Summarize a batch of content items.
        
        Args:
            batch: Batch of content items to summarize
            
        Returns:
            Batch of summarized content items
        """
        # Create a copy of the batch to avoid modifying the original
        summarized_batch = batch.copy()
        
        try:
            # Use the synchronous batch_summarize method but wrap it in an executor
            loop = asyncio.get_event_loop()
            summarized_batch = await loop.run_in_executor(
                None, 
                self.summarizer.batch_summarize, 
                summarized_batch
            )
        except Exception as e:
            logger.error(f"Error in batch summarization: {e}")
        
        return summarized_batch


class DigestGeneratorAgent(Agent):
    """
    Agent responsible for generating the email digest.
    """
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate email digest from summarized content.
        
        Args:
            input_data: Dictionary containing summarized content items
            
        Returns:
            Dict containing the generated digest
        """
        logger.info("DigestGeneratorAgent: Starting digest generation")
        
        content_items = input_data.get("content_items", [])
        email = input_data.get("email", "")
        max_items = input_data.get("max_items", 10)
        
        if not content_items:
            logger.warning("No content items for digest generation")
            return {"digest": "", "stats": {"items_count": 0}}
        
        # Separate Q-related and general content
        q_related_items = [item for item in content_items if item.get('relevance_score', 0) >= 30]
        general_items = [item for item in content_items if item.get('relevance_score', 0) < 30]
        
        # Find competitor-related items
        competitor_keywords = ['github copilot', 'anthropic claude', 'openai', 'gpt', 'bard', 'gemini']
        competitor_items = []
        for item in content_items:
            title = item.get('title', '').lower() if item.get('title') is not None else ''
            summary = item.get('summary', '').lower() if item.get('summary') is not None else ''
            content = title + ' ' + summary
            for keyword in competitor_keywords:
                if keyword in content:
                    competitor_items.append(item)
                    break
        
        # Sort by relevance score (highest first)
        q_related_items.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        competitor_items.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
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
        
        # Generate the digest content
        from datetime import datetime
        
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
        
        logger.info(f"DigestGeneratorAgent: Completed digest generation with {len(content_items)} items")
        
        return {
            "digest": digest_content,
            "email": email,
            "subject": "Your Daily Content Digest",
            "stats": {
                "items_count": len(content_items),
                "q_related_count": len(q_related_items),
                "competitor_count": len(competitor_items)
            }
        }
