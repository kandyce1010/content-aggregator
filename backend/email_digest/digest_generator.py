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
        self.env = Environment(loader=FileSystemLoader(template_dir))
        
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
