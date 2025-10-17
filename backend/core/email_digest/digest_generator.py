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
from jinja2 import Environment, FileSystemLoader, select_autoescape

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
            autoescape=select_autoescape(['html', 'xml'])
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
            # Sanitize all string fields to prevent template injection
            for key, value in item.items():
                if isinstance(value, str):
                    # Escape Jinja2 template syntax to prevent code injection
                    item[key] = value.replace('{{', '&#123;&#123;').replace('}}', '&#125;&#125;')
                    item[key] = item[key].replace('{%', '&#123;%').replace('%}', '%&#125;')
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
        
        # Score and filter items
        for item in items:
            item['relevance_score'] = self._get_item_relevance_score(item)
        
        # Separate Q-related and general content
        q_related_items = [item for item in items if item['relevance_score'] >= 30]
        general_items = [item for item in items if item['relevance_score'] < 30]
        
        # Find competitor-related items
        competitor_keywords = ['github copilot', 'anthropic claude', 'openai', 'gpt', 'bard', 'gemini']
        competitor_items = []
        for item in items:
            # Handle None values properly
            title = item.get('title', '') or ''
            title = title.lower()
            summary = item.get('summary', '') or ''
            summary = summary.lower()
            content = title + ' ' + summary
            for keyword in competitor_keywords:
                if keyword in content:
                    competitor_items.append(item)
                    break
        
        # Sort by relevance score (highest first)
        q_related_items.sort(key=lambda x: x['relevance_score'], reverse=True)
        competitor_items.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Organize general items by category
        general_by_category = self._organize_by_category(general_items)
        
        # Build text email
        text = []
        text.append("YOUR DAILY CONTENT DIGEST")
        text.append(f"{datetime.now().strftime('%A, %B %d, %Y')}")
        text.append("=" * 60)
        text.append("")
        
        # Amazon Q Related Content Section
        if q_related_items:
            text.append("AMAZON Q & CODING ASSISTANT HIGHLIGHTS")
            text.append("-" * 40)
            
            for item in q_related_items[:max_items_per_category]:
                text.append(f"* {item['title']} [Relevance: {item['relevance_score']}]")
                text.append(f"  Source: {item['source']}")
                text.append(f"  Published: {self._format_date(item['published'])}")
                if item.get('author') and item['author'] != 'Unknown':
                    text.append(f"  By: {item['author']}")
                text.append(f"  Link: {item['link']}")
                text.append("")
            
            text.append("")
        
        # Competitive Awareness Section
        if competitor_items:
            text.append("COMPETITIVE AWARENESS")
            text.append("-" * 40)
            
            for item in competitor_items[:max_items_per_category]:
                text.append(f"* {item['title']}")
                text.append(f"  Source: {item['source']}")
                text.append(f"  Published: {self._format_date(item['published'])}")
                if item.get('author') and item['author'] != 'Unknown':
                    text.append(f"  By: {item['author']}")
                text.append(f"  Link: {item['link']}")
                text.append("")
            
            text.append("")
        
        # General Content by Category
        if general_by_category:
            text.append("GENERAL INDUSTRY NEWS")
            text.append("-" * 40)
            
            for category, cat_items in general_by_category.items():
                text.append(f"{category.upper()}")
                
                for item in cat_items[:max_items_per_category // 2]:  # Show fewer general items
                    text.append(f"* {item['title']}")
                    text.append(f"  Source: {item['source']}")
                    text.append(f"  Link: {item['link']}")
                    text.append("")
                
                text.append("")
        
        text.append("=" * 60)
        text.append("This digest was generated by Content Aggregator.")
        
        return "\n".join(text)
    
    def save_digest(self, html_content: str, output_path: Optional[str] = None) -> str:
        """
        Save the generated digest to a file.
        
        Args:
            html_content (str): HTML content to save.
            output_path (str, optional): Path to save the digest to.
                If None, a default path will be used.
                
        Returns:
            str: Path to the saved file.
        """
        if output_path is None:
            # Create data directory if it doesn't exist
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                   '..', '..', 'data')
            Path(data_dir).mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(data_dir, f'digest_{timestamp}.html')
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"Saved digest to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error saving digest to {output_path}: {e}")
            return None


if __name__ == "__main__":
    # Example usage when run directly
    from pathlib import Path
    
    # Find the most recent RSS items file
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                           '..', '..', 'data')
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    
    rss_files = list(Path(data_dir).glob('rss_items_*.json'))
    if not rss_files:
        print("No RSS item files found. Please run the RSS fetcher first.")
        exit(1)
    
    # Get the most recent file
    latest_file = max(rss_files, key=lambda p: p.stat().st_mtime)
    print(f"Using latest RSS items file: {latest_file}")
    
    # Load the items
    with open(latest_file, 'r') as f:
        items = json.load(f)
    
    # Generate and save the digest
    generator = DigestGenerator()
    html_content = generator.generate_digest(items)
    output_path = generator.save_digest(html_content)
    
    print(f"Generated digest with {len(items)} items")
    print(f"Saved to: {output_path}")
