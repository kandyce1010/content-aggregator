#!/usr/bin/env python3
"""
RSS Feed Fetcher Module

This module handles fetching and parsing RSS feeds from configured sources.
It uses the feedparser library to parse RSS feeds and returns structured data.
"""

import os
import json
import logging
import feedparser
from datetime import datetime
import time
from pathlib import Path
from backend.core.utils.http_client import SecureHTTPClient
from backend.core.utils.exceptions import FetchError, ConfigurationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RSSFetcher:
    """
    A class to fetch and parse RSS feeds from configured sources.
    """
    
    def __init__(self, config_path=None):
        """
        Initialize the RSS fetcher with configuration.
        
        Args:
            config_path (str, optional): Path to the configuration file.
                Defaults to '../config/sources.json'.
        """
        if config_path is None:
            # In Lambda, files are in /var/task/
            if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
                config_path = '/var/task/config/sources.json'
            else:
                # Local development
                current_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(current_dir, '..', '..', '..', 'config', 'sources.json')
        
        self.config_path = config_path
        self.feeds = self._load_feed_config()
        self.http_client = SecureHTTPClient(timeout=15, max_retries=3)
        
        # Create data directory if it doesn't exist
        # Use /tmp directory in Lambda environment
        if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            self.data_dir = '/tmp/data'
        else:
            # Use regular path for local development
            self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                        '..', '..', '..', 'data')
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        
    def _load_feed_config(self):
        """
        Load RSS feed configuration from the config file.
        
        Returns:
            list: List of RSS feed configurations.
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                feeds = config.get('rss_feeds', [])
                
                # Validate feed configurations
                validated_feeds = []
                for feed in feeds:
                    if self._validate_feed_config(feed):
                        validated_feeds.append(feed)
                    else:
                        logger.warning(f"Skipping invalid feed configuration: {feed}")
                
                return validated_feeds
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading configuration: {e}")
            raise ConfigurationError(f"Failed to load RSS feed configuration: {e}")
    
    def _validate_feed_config(self, feed):
        """Validate a single feed configuration."""
        required_fields = ['name', 'url', 'category']
        
        for field in required_fields:
            if field not in feed or not feed[field]:
                return False
        
        # Validate URL format
        url = feed['url']
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Validate name and category length
        if len(feed['name']) > 100 or len(feed['category']) > 50:
            return False
        
        return True
    
    def fetch_all_feeds(self):
        """
        Fetch all configured RSS feeds.
        
        Returns:
            list: List of dictionaries containing feed items.
        """
        all_items = []
        failed_feeds = []
        
        for feed_config in self.feeds:
            try:
                feed_items = self.fetch_feed(feed_config)
                all_items.extend(feed_items)
                # Be nice to servers - add a small delay between requests
                time.sleep(1)
            except FetchError as e:
                logger.error(f"Failed to fetch feed {feed_config['name']}: {e}")
                failed_feeds.append(feed_config['name'])
            except Exception as e:
                logger.error(f"Unexpected error fetching feed {feed_config['name']}: {e}")
                failed_feeds.append(feed_config['name'])
        
        if failed_feeds:
            logger.warning(f"Failed to fetch {len(failed_feeds)} feeds: {', '.join(failed_feeds)}")
        
        logger.info(f"Successfully fetched {len(all_items)} total items from {len(self.feeds) - len(failed_feeds)} feeds")
        return all_items
    
    def fetch_feed(self, feed_config):
        """
        Fetch and parse a single RSS feed.
        
        Args:
            feed_config (dict): Configuration for the feed to fetch.
        
        Returns:
            list: List of dictionaries containing feed items.
        """
        logger.info(f"Fetching feed: {feed_config['name']}")
        
        try:
            # Use secure HTTP client to fetch the feed content
            response = self.http_client.get(feed_config['url'])
            
            # Parse the feed content
            feed = feedparser.parse(response.content)
            
            if feed.bozo and hasattr(feed, 'bozo_exception'):
                logger.warning(f"Feed parsing warning for {feed_config['name']}: {feed.bozo_exception}")
            
            items = []
            for entry in feed.entries:
                # Extract and standardize the item data
                item = {
                    'id': entry.get('id', entry.get('link', '')),
                    'title': self._sanitize_text(entry.get('title', 'No title')),
                    'link': entry.get('link', ''),
                    'summary': self._sanitize_text(entry.get('summary', entry.get('description', ''))),
                    'published': self._parse_date(entry),
                    'source': feed_config['name'],
                    'category': feed_config.get('category', 'uncategorized'),
                    'content_type': 'rss',
                    'fetched_at': datetime.now().isoformat()
                }
                
                # Add author if available
                if 'author' in entry:
                    item['author'] = self._sanitize_text(entry.author)
                elif 'authors' in entry and entry.authors:
                    item['author'] = self._sanitize_text(entry.authors[0].get('name', ''))
                else:
                    item['author'] = 'Unknown'
                
                # Validate the item before adding
                if self._validate_item(item):
                    items.append(item)
                else:
                    logger.warning(f"Skipping invalid item: {item.get('title', 'Unknown')}")
            
            logger.info(f"Successfully fetched {len(items)} items from {feed_config['name']}")
            return items
            
        except Exception as e:
            logger.error(f"Error fetching feed {feed_config['name']}: {e}")
            raise FetchError(f"Failed to fetch RSS feed {feed_config['name']}: {e}")
    
    def _sanitize_text(self, text):
        """Sanitize text content to prevent issues."""
        if not text:
            return ''
        
        # Convert to string and strip whitespace
        text = str(text).strip()
        
        # Limit length to prevent extremely long content
        if len(text) > 5000:
            text = text[:5000] + '...'
        
        return text
    
    def _validate_item(self, item):
        """Validate a feed item."""
        # Must have title and link
        if not item.get('title') or not item.get('link'):
            return False
        
        # Link must be a valid URL
        link = item.get('link', '')
        if not link.startswith(('http://', 'https://')):
            return False
        
        return True
    
    def _parse_date(self, entry):
        """
        Parse and standardize the publication date from a feed entry.
        
        Args:
            entry (dict): Feed entry from feedparser.
        
        Returns:
            str: ISO formatted date string.
        """
        for date_field in ['published', 'updated', 'created']:
            if hasattr(entry, f'{date_field}_parsed') and getattr(entry, f'{date_field}_parsed'):
                try:
                    parsed_time = getattr(entry, f'{date_field}_parsed')
                    dt = datetime(*parsed_time[:6])
                    return dt.isoformat()
                except (TypeError, ValueError):
                    pass
        
        # If no parsed date is available, try to use string fields
        for date_field in ['published', 'updated', 'created']:
            if hasattr(entry, date_field) and getattr(entry, date_field):
                return getattr(entry, date_field)
        
        # If no date is found, use current time
        return datetime.now().isoformat()
    
    def save_to_json(self, items, filename=None):
        """
        Save fetched items to a JSON file.
        
        Args:
            items (list): List of feed items to save.
            filename (str, optional): Name of the file to save to.
                Defaults to 'rss_items_{timestamp}.json'.
        
        Returns:
            str: Path to the saved file.
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'rss_items_{timestamp}.json'
        
        file_path = os.path.join(self.data_dir, filename)
        
        try:
            with open(file_path, 'w') as f:
                json.dump(items, f, indent=2)
            logger.info(f"Saved {len(items)} items to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving items to {file_path}: {e}")
            return None


if __name__ == "__main__":
    # Example usage when run directly
    fetcher = RSSFetcher()
    items = fetcher.fetch_all_feeds()
    fetcher.save_to_json(items)
    
    # Print summary of fetched items
    print(f"\nFetched {len(items)} items from {len(fetcher.feeds)} feeds:")
    for feed in fetcher.feeds:
        feed_items = [item for item in items if item['source'] == feed['name']]
        print(f"  - {feed['name']}: {len(feed_items)} items")
