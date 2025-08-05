#!/usr/bin/env python3
"""
Email Digest Generator

This module generates HTML email digests from aggregated content.
It formats content items into a readable email format using templates.
"""

import os
import json
import logging
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import re
from typing import Dict, List, Any, Optional
import html
from jinja2 import Environment, FileSystemLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DigestGenerator:
    """
    A class to generate email digests from aggregated content.
    """
    
    def __init__(self, template_dir=None):
        """
        Initialize the digest generator with template directory.
        
        Args:
            template_dir (str, optional): Path to the email templates directory.
        """
        if template_dir is None:
            # Get the directory of the current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Navigate to the templates directory
            template_dir = os.path.join(current_dir, 'templates')
        
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,
            enable_async=False
        )
        
        # Add custom filters
        self.env.filters['format_date'] = self._format_date
        self.env.filters['truncate'] = self._truncate_html
    
    def _format_date(self, date_str: str) -> str:
        """
        Format a date string into a readable format.
        
        Args:
            date_str (str): ISO format date string.
            
        Returns:
            str: Formatted date string.
        """
        try:
            dt = datetime.fromisoformat(date_str)
            return dt.strftime('%b %d, %Y')
        except (ValueError, TypeError):
            return date_str
    
    def _truncate_html(self, text: str, length: int = 200) -> str:
        """
        Truncate HTML text to a specified length while preserving HTML structure.
        
        Args:
            text (str): HTML text to truncate.
            length (int): Maximum length of the truncated text.
            
        Returns:
            str: Truncated HTML text.
        """
        # Simple HTML tag removal for truncation purposes
        text_without_tags = re.sub(r'<[^>]+>', '', text)
        
        if len(text_without_tags) <= length:
            return text
        
        # Truncate the text without tags
        truncated_text = text_without_tags[:length].strip()
        
        # Add ellipsis if truncated
        if len(text_without_tags) > length:
            truncated_text += '...'
        
        return truncated_text
    
    def _clean_html(self, text: str) -> str:
        """
        Clean HTML content for email compatibility.
        
        Args:
            text (str): HTML text to clean.
            
        Returns:
            str: Cleaned HTML text.
        """
        # Basic HTML cleaning for email compatibility
        # Remove potentially problematic tags or attributes
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<iframe[^>]*>.*?</iframe>', '', text, flags=re.DOTALL)
        
        return text
        
    def _is_q_related(self, item: Dict[str, Any]) -> bool:
        """
        Determine if an item is related to Amazon Q or coding assistants.
        
        Args:
            item (dict): Content item to check
            
        Returns:
            bool: True if the item is related to Amazon Q or coding assistants
        """
        q_keywords = [
            'amazon q', 'q developer', 'coding assistant', 'ai pair programming',
            'code generation', 'code completion', 'ai coding', 'generative ai',
            'llm', 'large language model', 'codewhisperer', 'copilot'
        ]
        
        # Check title
        title = item.get('title', '').lower()
        for keyword in q_keywords:
            if keyword in title:
                return True
        
        # Check summary/description
        summary = item.get('summary', '').lower()
        for keyword in q_keywords:
            if keyword in summary:
                return True
        
        return False

    def _get_item_relevance_score(self, item: Dict[str, Any]) -> int:
        """
        Calculate a relevance score for an item based on Q-related keywords.
        Higher score means more relevant to Amazon Q.
        
        Args:
            item (dict): Content item to score
            
        Returns:
            int: Relevance score (0-100)
        """
        primary_keywords = ['amazon q', 'q developer', 'codewhisperer', 'kiro']
        secondary_keywords = ['coding assistant', 'ai pair programming', 'code generation']
        tertiary_keywords = ['generative ai', 'llm', 'large language model', 'ai coding']
        competitor_keywords = ['github copilot', 'anthropic claude', 'openai', 'gpt', 'bard', 'gemini']
        
        score = 0
        # Handle None values properly
        title = item.get('title', '') or ''
        title = title.lower()
        summary = item.get('summary', '') or ''
        summary = summary.lower()
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
    
    def _organize_by_category(self, items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Organize content items by category.
        
        Args:
            items (list): List of content items.
            
        Returns:
            dict: Dictionary of items organized by category.
        """
        by_category = defaultdict(list)
        
        for item in items:
            category = item.get('category', 'uncategorized')
            by_category[category].append(item)
        
        # Sort items within each category by published date (newest first)
        for category in by_category:
            by_category[category].sort(
                key=lambda x: x.get('published', ''), 
                reverse=True
            )
        
        return dict(by_category)
    
    def generate_digest(self, items: List[Dict[str, Any]], max_items_per_category: int = 10) -> str:
        """
        Generate an HTML email digest from content items.
        
        Args:
            items (list): List of content items.
            max_items_per_category (int): Maximum number of items to include per category.
            
        Returns:
            str: HTML email digest.
        """
        logger.info(f"Generating digest from {len(items)} items")
        
        # Clean and prepare items
        for item in items:
            if 'summary' in item:
                item['summary'] = self._clean_html(item['summary'])
        
        # Organize items by category
        content_by_category = self._organize_by_category(items)
        
        # Limit items per category
        for category in content_by_category:
            content_by_category[category] = content_by_category[category][:max_items_per_category]
        
        # Prepare template context
        context = {
            'date': datetime.now().strftime('%A, %B %d, %Y'),
            'content_by_category': content_by_category,
            'unsubscribe_link': '#',  # Placeholder
            'preferences_link': '#'    # Placeholder
        }
        
        # Render the template
        template = self.env.get_template('email_template.html')
        html_content = template.render(**context)
        
        return html_content
    
    def generate_text_digest(self, items: List[Dict[str, Any]], max_items_per_category: int = 10) -> str:
        """
        Generate a plain text email digest from content items with Q-relevance prioritization.
        
        Args:
            items (list): List of content items.
            max_items_per_category (int): Maximum number of items to include per category.
            
        Returns:
            str: Plain text email digest.
        """
        logger.info(f"Generating text digest from {len(items)} items")
        
        # Organize items by category
        content_by_category = self._organize_by_category(items)
        
        # Limit items per category and sort by relevance
        for category in content_by_category:
            # Sort by relevance score (highest first)
            content_by_category[category].sort(
                key=lambda x: self._get_item_relevance_score(x),
                reverse=True
            )
            content_by_category[category] = content_by_category[category][:max_items_per_category]
        
        # Generate text digest
        digest_lines = []
        digest_lines.append("Content Digest")
        digest_lines.append("=" * 50)
        digest_lines.append(f"Generated on: {datetime.now().strftime('%A, %B %d, %Y')}")
        digest_lines.append("")
        
        for category, category_items in content_by_category.items():
            if not category_items:
                continue
                
            digest_lines.append(f"{category.upper()}")
            digest_lines.append("-" * len(category))
            digest_lines.append("")
            
            for item in category_items:
                title = item.get('title', 'No Title')
                url = item.get('url', '#')
                published = item.get('published', '')
                summary = item.get('summary', '')
                
                # Format date
                if published:
                    try:
                        dt = datetime.fromisoformat(published)
                        published = dt.strftime('%b %d, %Y')
                    except (ValueError, TypeError):
                        pass
                
                # Clean summary for text
                if summary:
                    summary = re.sub(r'<[^>]+>', '', summary)  # Remove HTML tags
                    summary = summary.strip()
                    if len(summary) > 200:
                        summary = summary[:200] + '...'
                
                digest_lines.append(f"• {title}")
                if published:
                    digest_lines.append(f"  Date: {published}")
                if summary:
                    digest_lines.append(f"  Summary: {summary}")
                digest_lines.append(f"  Link: {url}")
                digest_lines.append("")
            
            digest_lines.append("")
        
        return "\n".join(digest_lines)