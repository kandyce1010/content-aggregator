#!/usr/bin/env python3
"""
Helper functions for the Content Aggregator.

This module contains utility functions that are used across different parts of the application.
"""

import re
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clean_html(text: str) -> str:
    """
    Clean HTML content for email compatibility.
    
    Args:
        text (str): HTML text to clean.
        
    Returns:
        str: Cleaned HTML text.
    """
    if not text:
        return ""
        
    # Basic HTML cleaning for email compatibility
    # Remove potentially problematic tags or attributes
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<iframe[^>]*>.*?</iframe>', '', text, flags=re.DOTALL)
    
    return text

def truncate_text(text: str, length: int = 200) -> str:
    """
    Truncate text to a specified length.
    
    Args:
        text (str): Text to truncate.
        length (int): Maximum length of the truncated text.
        
    Returns:
        str: Truncated text.
    """
    if not text:
        return ""
        
    if len(text) <= length:
        return text
    
    # Truncate the text
    truncated_text = text[:length].strip()
    
    # Add ellipsis if truncated
    if len(text) > length:
        truncated_text += '...'
    
    return truncated_text

def format_date(date_str: str) -> str:
    """
    Format a date string into a readable format.
    
    Args:
        date_str (str): ISO format date string.
        
    Returns:
        str: Formatted date string.
    """
    if not date_str:
        return ""
        
    try:
        # Handle different date formats
        if 'T' in date_str:
            # ISO format
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            # Try other formats
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
                except ValueError:
                    # Return original if unparseable
                    return date_str
        
        return dt.strftime('%b %d, %Y')
    except (ValueError, TypeError):
        return date_str

def calculate_relevance_score(item: Dict[str, Any]) -> int:
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
