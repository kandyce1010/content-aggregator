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
            # Get the directory of the current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Navigate to the config directory
            config_path = os.path.join(current_dir, '..', '..', 'config', 'sources.json')
        
        self.config_path = config_path
        self.feeds = self._load_feed_config()
        
        # Create data directory if it doesn't exist
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                     '..', '..', 'data')
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        
    def _load_feed_config(self):
        """
        Load RSS feed configuration from the config file.
        
        Returns:
            list: List of RSS feed configurations.
        """
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                return config.get('rss_feeds', [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading configuration: {e}")
            return []
    
    def fetch_all_feeds(self):
        """
        Fetch all configured RSS feeds.
        
        Returns:
            list: List of dictionaries containing feed items.
        """
        all_items = []
        
        for feed_config in self.feeds:
            try:
                feed_items = self.fetch_feed(feed_config)
                all_items.extend(feed_items)
                # Be nice to servers - add a small delay between requests
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error fetching feed {feed_config['name']}: {e}")
        
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
            feed = feedparser.parse(feed_config['url'])
            
            if feed.bozo and hasattr(feed, 'bozo_exception'):
                logger.warning(f"Feed parsing warning for {feed_config['name']}: {feed.bozo_exception}")
            
            items = []
            for entry in feed.entries:
                # Extract and standardize the item data
                item = {
                    'id': entry.get('id', entry.get('link', '')),
                    'title': entry.get('title', 'No title'),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', entry.get('description', '')),
                    'published': self._parse_date(entry),
                    'source': feed_config['name'],
                    'category': feed_config.get('category', 'uncategorized'),
                    'content_type': 'rss',
                    'fetched_at': datetime.now().isoformat()
                }
                
                # Add author if available
                if 'author' in entry:
                    item['author'] = entry.author
                elif 'authors' in entry and entry.authors:
                    item['author'] = entry.authors[0].get('name', '')
                else:
                    item['author'] = 'Unknown'
                
                items.append(item)
            
            logger.info(f"Successfully fetched {len(items)} items from {feed_config['name']}")
            return items
            
        except Exception as e:
            logger.error(f"Error fetching feed {feed_config['name']}: {e}")
            return []
    
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
