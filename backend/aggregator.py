#!/usr/bin/env python3
"""
Unified Content Aggregator

This module combines content from all sources (RSS, GitHub, LinkedIn, YouTube)
and provides a unified interface for accessing aggregated content.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import concurrent.futures

# Import fetchers
from backend.fetchers.rss_fetcher import RSSFetcher
from backend.fetchers.github_fetcher import GitHubFetcher
try:
    from backend.fetchers.linkedin_fetcher import LinkedInFetcher
    LINKEDIN_AVAILABLE = True
except ImportError:
    LINKEDIN_AVAILABLE = False
    logging.warning("LinkedIn fetcher not available. LinkedIn content will be skipped.")

try:
    from backend.fetchers.youtube_fetcher import YouTubeFetcher
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False
    logging.warning("YouTube fetcher not available. YouTube content will be skipped.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContentAggregator:
    """
    A class to aggregate content from multiple sources.
    """
    
    def __init__(self, config_path=None, github_token=None):
        """
        Initialize the content aggregator with configuration.
        
        Args:
            config_path (str, optional): Path to the configuration file.
            github_token (str, optional): GitHub personal access token.
        """
        if config_path is None:
            # Get the directory of the current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Navigate to the config directory
            config_path = os.path.join(current_dir, '..', 'config', 'sources.json')
        
        self.config_path = config_path
        self.github_token = github_token
        
        # Create data directory if it doesn't exist
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                     '..', 'data')
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize fetchers
        self.rss_fetcher = RSSFetcher(config_path)
        self.github_fetcher = GitHubFetcher(config_path, token=github_token)
        
        if LINKEDIN_AVAILABLE:
            self.linkedin_fetcher = LinkedInFetcher(config_path)
        
        if YOUTUBE_AVAILABLE:
            self.youtube_fetcher = YouTubeFetcher(config_path)
    
    def fetch_all_content(self, parallel=True) -> List[Dict[str, Any]]:
        """
        Fetch content from all available sources.
        
        Args:
            parallel (bool): Whether to fetch content in parallel.
            
        Returns:
            list: List of content items from all sources.
        """
        logger.info("Fetching content from all sources")
        all_content = []
        
        if parallel:
            # Fetch content in parallel using ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Submit fetching tasks
                rss_future = executor.submit(self.fetch_rss_content)
                github_future = executor.submit(self.fetch_github_content)
                
                futures = [rss_future, github_future]
                
                if LINKEDIN_AVAILABLE:
                    linkedin_future = executor.submit(self.fetch_linkedin_content)
                    futures.append(linkedin_future)
                
                if YOUTUBE_AVAILABLE:
                    youtube_future = executor.submit(self.fetch_youtube_content)
                    futures.append(youtube_future)
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(futures):
                    try:
                        content = future.result()
                        all_content.extend(content)
                    except Exception as e:
                        logger.error(f"Error fetching content: {e}")
        else:
            # Fetch content sequentially
            all_content.extend(self.fetch_rss_content())
            all_content.extend(self.fetch_github_content())
            
            if LINKEDIN_AVAILABLE:
                all_content.extend(self.fetch_linkedin_content())
            
            if YOUTUBE_AVAILABLE:
                all_content.extend(self.fetch_youtube_content())
        
        # Sort by date (newest first)
        all_content.sort(key=lambda x: x.get('published', ''), reverse=True)
        
        logger.info(f"Fetched {len(all_content)} items from all sources")
        return all_content
    
    def fetch_rss_content(self) -> List[Dict[str, Any]]:
        """
        Fetch content from RSS feeds.
        
        Returns:
            list: List of content items from RSS feeds.
        """
        try:
            logger.info("Fetching RSS content")
            items = self.rss_fetcher.fetch_all_feeds()
            logger.info(f"Fetched {len(items)} items from RSS feeds")
            return items
        except Exception as e:
            logger.error(f"Error fetching RSS content: {e}")
            return []
    
    def fetch_github_content(self) -> List[Dict[str, Any]]:
        """
        Fetch content from GitHub repositories.
        
        Returns:
            list: List of content items from GitHub repositories.
        """
        try:
            logger.info("Fetching GitHub content")
            items = self.github_fetcher.fetch_all_repositories()
            logger.info(f"Fetched {len(items)} items from GitHub repositories")
            return items
        except Exception as e:
            logger.error(f"Error fetching GitHub content: {e}")
            return []
    
    def fetch_linkedin_content(self) -> List[Dict[str, Any]]:
        """
        Fetch content from LinkedIn profiles.
        
        Returns:
            list: List of content items from LinkedIn profiles.
        """
        if not LINKEDIN_AVAILABLE:
            logger.warning("LinkedIn fetcher not available")
            return []
        
        try:
            logger.info("Fetching LinkedIn content")
            items = self.linkedin_fetcher.fetch_all_profiles()
            logger.info(f"Fetched {len(items)} items from LinkedIn profiles")
            return items
        except Exception as e:
            logger.error(f"Error fetching LinkedIn content: {e}")
            return []
    
    def fetch_youtube_content(self) -> List[Dict[str, Any]]:
        """
        Fetch content from YouTube channels.
        
        Returns:
            list: List of content items from YouTube channels.
        """
        if not YOUTUBE_AVAILABLE:
            logger.warning("YouTube fetcher not available")
            return []
        
        try:
            logger.info("Fetching YouTube content")
            items = self.youtube_fetcher.fetch_all_channels()
            logger.info(f"Fetched {len(items)} items from YouTube channels")
            return items
        except Exception as e:
            logger.error(f"Error fetching YouTube content: {e}")
            return []
    
    def filter_content_by_category(self, items: List[Dict[str, Any]], category: str) -> List[Dict[str, Any]]:
        """
        Filter content items by category.
        
        Args:
            items (list): List of content items.
            category (str): Category to filter by.
            
        Returns:
            list: Filtered list of content items.
        """
        return [item for item in items if item.get('category') == category]
    
    def filter_content_by_date(self, items: List[Dict[str, Any]], days: int) -> List[Dict[str, Any]]:
        """
        Filter content items by date (items from the last X days).
        
        Args:
            items (list): List of content items.
            days (int): Number of days to include.
            
        Returns:
            list: Filtered list of content items.
        """
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        filtered_items = []
        for item in items:
            try:
                published_str = item.get('published', '')
                if not published_str:
                    continue
                
                # Handle different date formats
                if 'T' in published_str:
                    # ISO format
                    published_date = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                else:
                    # Try other formats
                    try:
                        published_date = datetime.strptime(published_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        try:
                            published_date = datetime.strptime(published_str, '%a, %d %b %Y %H:%M:%S %z')
                        except ValueError:
                            # Skip items with unparseable dates
                            continue
                
                if published_date >= cutoff_date:
                    filtered_items.append(item)
            except Exception:
                # Skip items with date parsing errors
                continue
        
        return filtered_items
    
    def save_content(self, items: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        Save content items to a JSON file.
        
        Args:
            items (list): List of content items to save.
            filename (str, optional): Name of the file to save to.
                If None, a default name will be used.
                
        Returns:
            str: Path to the saved file.
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'aggregated_content_{timestamp}.json'
        
        file_path = os.path.join(self.data_dir, filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(items, f, indent=2)
            logger.info(f"Saved {len(items)} items to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving content to {file_path}: {e}")
            return None


if __name__ == "__main__":
    # Example usage when run directly
    import argparse
    
    parser = argparse.ArgumentParser(description='Unified Content Aggregator')
    parser.add_argument('--github-token', help='GitHub personal access token')
    parser.add_argument('--category', help='Filter by category')
    parser.add_argument('--days', type=int, default=7, help='Include content from the last X days')
    parser.add_argument('--save', action='store_true', help='Save content to file')
    parser.add_argument('--parallel', action='store_true', help='Fetch content in parallel')
    
    args = parser.parse_args()
    
    aggregator = ContentAggregator(github_token=args.github_token)
    all_content = aggregator.fetch_all_content(parallel=args.parallel)
    
    # Filter by category if specified
    if args.category:
        all_content = aggregator.filter_content_by_category(all_content, args.category)
        print(f"Filtered to {len(all_content)} items in category '{args.category}'")
    
    # Filter by date
    all_content = aggregator.filter_content_by_date(all_content, args.days)
    print(f"Filtered to {len(all_content)} items from the last {args.days} days")
    
    # Save to file if requested
    if args.save:
        file_path = aggregator.save_content(all_content)
        print(f"Saved content to {file_path}")
    
    # Print summary
    print("\nContent Summary:")
    
    # Count by source
    sources = {}
    for item in all_content:
        source = item.get('source', 'Unknown')
        sources[source] = sources.get(source, 0) + 1
    
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {source}: {count} items")
    
    # Count by category
    categories = {}
    for item in all_content:
        category = item.get('category', 'uncategorized')
        categories[category] = categories.get(category, 0) + 1
    
    print("\nCategories:")
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {category}: {count} items")
