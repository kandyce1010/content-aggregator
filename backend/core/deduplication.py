#!/usr/bin/env python3
"""
Content Deduplication Module

This module provides functionality to detect and remove duplicate content
from various sources, with special handling for Google Alert RSS feeds.
"""

import re
import logging
from typing import List, Dict, Any, Set, Tuple
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import hashlib
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContentDeduplicator:
    """
    A class to detect and remove duplicate content items using multiple factors.
    """
    
    def __init__(self, similarity_threshold=0.85, time_window_hours=24, 
                 consider_domains=True, consider_titles=True, consider_content=True):
        """
        Initialize the content deduplicator with configuration.
        
        Args:
            similarity_threshold (float): Threshold for title/content similarity (0.0-1.0)
            time_window_hours (int): Time window to consider for duplicates (in hours)
            consider_domains (bool): Whether to consider domains in deduplication
            consider_titles (bool): Whether to consider titles in deduplication
            consider_content (bool): Whether to consider content in deduplication
        """
        self.similarity_threshold = similarity_threshold
        self.time_window_hours = time_window_hours
        self.consider_domains = consider_domains
        self.consider_titles = consider_titles
        self.consider_content = consider_content
        
        # Common words to remove when creating content fingerprints
        self.common_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
            'when', 'where', 'how', 'why', 'which', 'who', 'whom', 'this', 'that',
            'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'to', 'at',
            'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through',
            'during', 'before', 'after', 'above', 'below', 'from', 'up', 'down', 'in',
            'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once',
            'here', 'there', 'all', 'any', 'both', 'each', 'few', 'more', 'most',
            'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
            'than', 'too', 'very', 'can', 'will', 'just', 'should', 'now'
        }
    
    def deduplicate_content(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate content items based on multiple factors.
        
        Args:
            items: List of content items
            
        Returns:
            List of deduplicated content items
        """
        if not items:
            return []
        
        # Sort items by published date (newest first) to prioritize newer content
        try:
            sorted_items = sorted(
                items, 
                key=lambda x: self._parse_date(x.get('published', '')), 
                reverse=True
            )
        except Exception as e:
            logger.warning(f"Error sorting items by date: {e}. Using original order.")
            sorted_items = items
        
        unique_items = []
        seen_fingerprints = set()
        seen_urls = set()
        seen_normalized_urls = set()
        
        for item in sorted_items:
            # Skip items without links
            if not item.get('link'):
                unique_items.append(item)
                continue
            
            # Check for exact URL duplicates
            item_url = item.get('link', '').strip()
            if item_url in seen_urls:
                logger.debug(f"Skipping duplicate URL: {item_url}")
                continue
            
            # Check for normalized URL duplicates (handles tracking parameters)
            normalized_url = self._normalize_url(item_url)
            if normalized_url in seen_normalized_urls:
                logger.debug(f"Skipping normalized URL duplicate: {item_url}")
                continue
            
            # Create content fingerprint
            fingerprint = self._create_content_fingerprint(item)
            
            # Check if we've seen this fingerprint before
            if fingerprint in seen_fingerprints:
                # If we have, check if it's a true duplicate using additional factors
                if self._is_duplicate(item, unique_items):
                    logger.debug(f"Skipping duplicate content: {item.get('title')}")
                    continue
            
            # If we get here, the item is unique
            unique_items.append(item)
            seen_urls.add(item_url)
            seen_normalized_urls.add(normalized_url)
            seen_fingerprints.add(fingerprint)
        
        logger.info(f"Deduplicated {len(items)} items to {len(unique_items)} items")
        return unique_items
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize a URL by removing tracking parameters and fragments.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        try:
            # Parse the URL
            parsed_url = urlparse(url)
            
            # Get the query parameters
            query_params = parse_qs(parsed_url.query)
            
            # Remove common tracking parameters
            tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 
                              'utm_content', 'fbclid', 'gclid', 'msclkid', 'ref'}
            
            filtered_params = {k: v for k, v in query_params.items() if k.lower() not in tracking_params}
            
            # Reconstruct the URL without tracking parameters and without fragments
            normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
            
            # Add back non-tracking query parameters if any
            if filtered_params:
                normalized_url += '?'
                param_strings = []
                for k, v in filtered_params.items():
                    param_strings.append(f"{k}={v[0]}")
                normalized_url += '&'.join(param_strings)
            
            return normalized_url
        except Exception as e:
            logger.warning(f"Error normalizing URL {url}: {e}")
            return url
    
    def _create_content_fingerprint(self, item: Dict[str, Any]) -> str:
        """
        Create a fingerprint of the content for comparison.
        
        Args:
            item: Content item
            
        Returns:
            Content fingerprint as a string
        """
        # Start with an empty fingerprint
        fingerprint_parts = []
        
        # Add domain if configured
        if self.consider_domains and item.get('link'):
            try:
                domain = urlparse(item.get('link', '')).netloc
                fingerprint_parts.append(domain)
            except Exception:
                pass
        
        # Add processed title if configured
        if self.consider_titles and item.get('title'):
            title = self._process_text(item.get('title', ''))
            fingerprint_parts.append(title)
        
        # Add processed summary if configured
        if self.consider_content and item.get('summary'):
            # Get the first 100 words of the summary
            summary = ' '.join(self._process_text(item.get('summary', '')).split()[:100])
            fingerprint_parts.append(summary)
        
        # Join all parts and create a hash
        fingerprint_text = ' '.join(fingerprint_parts)
        return hashlib.md5(fingerprint_text.encode('utf-8')).hexdigest()
    
    def _process_text(self, text: str) -> str:
        """
        Process text by removing common words, punctuation, and converting to lowercase.
        
        Args:
            text: Text to process
            
        Returns:
            Processed text
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove punctuation and special characters
        text = re.sub(r'[^\w\s]', '', text)
        
        # Split into words
        words = text.split()
        
        # Remove common words
        words = [word for word in words if word not in self.common_words]
        
        # Join back into a string
        return ' '.join(words)
    
    def _is_duplicate(self, item: Dict[str, Any], existing_items: List[Dict[str, Any]]) -> bool:
        """
        Check if an item is a duplicate of any existing items using multiple factors.
        
        Args:
            item: Item to check
            existing_items: List of existing items to compare against
            
        Returns:
            True if the item is a duplicate, False otherwise
        """
        # Get the publication date of the item
        item_date = self._parse_date(item.get('published', ''))
        
        # Get the title and summary
        item_title = item.get('title', '').lower()
        item_summary = item.get('summary', '').lower()
        
        # Get the domain
        item_domain = ''
        if item.get('link'):
            try:
                item_domain = urlparse(item.get('link', '')).netloc
            except Exception:
                pass
        
        for existing in existing_items:
            # Skip comparison if the item is the same object
            if item is existing:
                continue
            
            # Check if the titles are similar
            title_similarity = self._calculate_similarity(
                item_title, 
                existing.get('title', '').lower()
            )
            
            # Check if the summaries are similar
            summary_similarity = self._calculate_similarity(
                item_summary, 
                existing.get('summary', '').lower()
            )
            
            # Check if the domains match
            domain_match = False
            if item_domain and item.get('link'):
                try:
                    existing_domain = urlparse(existing.get('link', '')).netloc
                    domain_match = (item_domain == existing_domain)
                except Exception:
                    pass
            
            # Check if the publication dates are close
            date_proximity = False
            existing_date = self._parse_date(existing.get('published', ''))
            if item_date and existing_date:
                time_diff = abs((item_date - existing_date).total_seconds()) / 3600  # hours
                date_proximity = time_diff <= self.time_window_hours
            
            # Determine if it's a duplicate based on our criteria
            is_duplicate = False
            
            # High title similarity and date proximity is a strong indicator
            if title_similarity >= self.similarity_threshold and date_proximity:
                is_duplicate = True
            
            # High summary similarity and matching domain is also a strong indicator
            if summary_similarity >= self.similarity_threshold and domain_match:
                is_duplicate = True
            
            # Very high title similarity alone can indicate duplication
            if title_similarity >= 0.95:
                is_duplicate = True
            
            if is_duplicate:
                return True
        
        return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate the similarity between two texts using SequenceMatcher.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0
        
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse a date string into a datetime object.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            Datetime object or None if parsing fails
        """
        if not date_str:
            return datetime.now()
        
        try:
            # Try ISO format first
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            # Try common date formats
            for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%d %H:%M:%S', 
                       '%d %b %Y %H:%M:%S', '%Y/%m/%d %H:%M:%S']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # If all else fails, return current time
            logger.warning(f"Could not parse date: {date_str}")
            return datetime.now()
        except Exception as e:
            logger.warning(f"Error parsing date {date_str}: {e}")
            return datetime.now()


def deduplicate_content(items: List[Dict[str, Any]], 
                       similarity_threshold=0.85, 
                       time_window_hours=24) -> List[Dict[str, Any]]:
    """
    Convenience function to deduplicate content items.
    
    Args:
        items: List of content items
        similarity_threshold: Threshold for title similarity (0.0-1.0)
        time_window_hours: Time window to consider for duplicates (in hours)
        
    Returns:
        List of deduplicated content items
    """
    deduplicator = ContentDeduplicator(
        similarity_threshold=similarity_threshold,
        time_window_hours=time_window_hours
    )
    return deduplicator.deduplicate_content(items)


if __name__ == "__main__":
    # Example usage when run directly
    import json
    import argparse
    
    parser = argparse.ArgumentParser(description='Content Deduplicator')
    parser.add_argument('--input', required=True, help='Input JSON file with content items')
    parser.add_argument('--output', help='Output JSON file for deduplicated content')
    parser.add_argument('--threshold', type=float, default=0.85, help='Similarity threshold (0.0-1.0)')
    parser.add_argument('--time-window', type=int, default=24, help='Time window in hours')
    
    args = parser.parse_args()
    
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            items = json.load(f)
        
        deduplicator = ContentDeduplicator(
            similarity_threshold=args.threshold,
            time_window_hours=args.time_window
        )
        
        unique_items = deduplicator.deduplicate_content(items)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(unique_items, f, ensure_ascii=False, indent=2)
            print(f"Deduplicated {len(items)} items to {len(unique_items)} items. Saved to {args.output}")
        else:
            print(f"Deduplicated {len(items)} items to {len(unique_items)} items.")
            
    except Exception as e:
        print(f"Error: {e}")
