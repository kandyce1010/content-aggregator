#!/usr/bin/env python3
"""
Unified Content Aggregator

This module combines content from all sources (RSS, GitHub, LinkedIn, YouTube)
and provides a unified interface for accessing aggregated content.
"""

import os
import json
import logging
from pathlib import Path
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import concurrent.futures

# Import fetchers
from backend.core.fetchers.rss_fetcher import RSSFetcher
from backend.core.fetchers.github_fetcher import GitHubFetcher
try:
    from backend.core.fetchers.linkedin_fetcher import LinkedInFetcher
    LINKEDIN_AVAILABLE = True
except ImportError:
    LINKEDIN_AVAILABLE = False
    logging.warning("LinkedIn fetcher not available. LinkedIn content will be skipped.")

try:
    from backend.core.summarization import BedrockSummarizer
    SUMMARIZATION_AVAILABLE = True
except ImportError:
    SUMMARIZATION_AVAILABLE = False
    logging.warning("Summarization module not available. Content summarization will be skipped.")

try:
    from backend.core.fetchers.youtube_fetcher import YouTubeFetcher
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False
    logging.warning("YouTube fetcher not available. YouTube content will be skipped.")

try:
    from backend.core.deduplication import ContentDeduplicator
    DEDUPLICATION_AVAILABLE = True
except ImportError:
    DEDUPLICATION_AVAILABLE = False
    logging.warning("Deduplication module not available. Content deduplication will be skipped.")

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
    
    def __init__(self, config_path=None, github_token=None, youtube_api_key=None, 
                 enable_summarization=False, bedrock_region=None, bedrock_profile=None):
        """
        Initialize the content aggregator with configuration.
        
        Args:
            config_path (str, optional): Path to the configuration file.
            github_token (str, optional): GitHub personal access token.
            youtube_api_key (str, optional): YouTube Data API key.
            enable_summarization (bool): Whether to enable content summarization.
            bedrock_region (str, optional): AWS region for Bedrock.
            bedrock_profile (str, optional): AWS profile for Bedrock.
        """
        if config_path is None:
            # In Lambda, files are in /var/task/
            if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
                config_path = '/var/task/config/sources.json'
            else:
                # Local development
                current_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(current_dir, '..', '..', 'config', 'sources.json')
        
        self.config_path = config_path
        self.github_token = github_token
        self.youtube_api_key = youtube_api_key
        self.enable_summarization = enable_summarization
        
        # Create data directory if it doesn't exist
        # Use /tmp directory in Lambda environment
        if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            self.data_dir = '/tmp/data'
        else:
            # Use regular path for local development
            self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                        '..', 'data')
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize fetchers
        self.rss_fetcher = RSSFetcher(config_path)
        self.github_fetcher = GitHubFetcher(config_path, token=github_token)
        
        if LINKEDIN_AVAILABLE:
            self.linkedin_fetcher = LinkedInFetcher(config_path)
        
        if YOUTUBE_AVAILABLE:
            self.youtube_fetcher = YouTubeFetcher(config_path, api_key=youtube_api_key)
            
        # Initialize summarizer if enabled
        self.summarizer = None
        if enable_summarization and SUMMARIZATION_AVAILABLE:
            try:
                self.summarizer = BedrockSummarizer(
                    region_name=bedrock_region or 'us-east-1',
                    profile_name=bedrock_profile
                )
                logger.info("Content summarization enabled with Bedrock")
            except Exception as e:
                logger.error(f"Failed to initialize Bedrock summarizer: {e}")
                self.summarizer = None
    
    def fetch_all_content(self, parallel=True, deduplicate=True, summarize=None) -> List[Dict[str, Any]]:
        """
        Fetch content from all available sources.
        
        Args:
            parallel (bool): Whether to fetch content in parallel.
            deduplicate (bool): Whether to deduplicate content.
            summarize (bool, optional): Whether to summarize content. If None, uses the instance setting.
            
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
                
                # Removed YouTube fetcher call
                
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
            
            # Removed YouTube fetcher call
        
        # Deduplicate content if requested
        if deduplicate:
            all_content = self.deduplicate_content(all_content)
        
        # Sort by date (newest first)
        all_content.sort(key=lambda x: x.get('published', ''), reverse=True)
        
        # Summarize content if requested
        should_summarize = summarize if summarize is not None else self.enable_summarization
        if should_summarize and self.summarizer is not None:
            try:
                logger.info(f"Summarizing {len(all_content)} content items")
                all_content = self.summarizer.batch_summarize(all_content)
                logger.info("Content summarization completed")
            except Exception as e:
                logger.error(f"Error summarizing content: {e}")
        
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
        import pytz
        
        # Create a timezone-aware cutoff date in UTC
        cutoff_date = datetime.now(pytz.UTC) - timedelta(days=days)
        
        filtered_items = []
        for item in items:
            try:
                published_str = item.get('published', '')
                if not published_str:
                    continue
                
                # Handle different date formats
                published_date = None
                if 'T' in published_str:
                    # ISO format
                    try:
                        # Try to parse as timezone-aware ISO format
                        if 'Z' in published_str:
                            # Replace Z with +00:00 for UTC timezone
                            published_date = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                        elif '+' in published_str or '-' in published_str and published_str.rindex('-') > 10:
                            # Already has timezone info
                            published_date = datetime.fromisoformat(published_str)
                        else:
                            # No timezone info, assume UTC
                            published_date = datetime.fromisoformat(published_str).replace(tzinfo=pytz.UTC)
                    except ValueError:
                        # Fallback to naive datetime and add UTC timezone
                        try:
                            published_date = datetime.fromisoformat(published_str.split('T')[0])
                            published_date = published_date.replace(tzinfo=pytz.UTC)
                        except:
                            pass
                else:
                    # Try common date formats
                    for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%d %H:%M:%S', '%d %b %Y %H:%M:%S', '%Y/%m/%d %H:%M:%S']:
                        try:
                            published_date = datetime.strptime(published_str, fmt)
                            # Add UTC timezone if the parsed date is naive
                            if published_date.tzinfo is None:
                                published_date = published_date.replace(tzinfo=pytz.UTC)
                            break
                        except ValueError:
                            continue
                
                # If we couldn't parse the date, skip this item
                if published_date is None:
                    logger.warning(f"Could not parse date: {published_str}")
                    continue
                
                # Make sure cutoff_date and published_date are both timezone-aware
                if published_date.tzinfo is None:
                    published_date = published_date.replace(tzinfo=pytz.UTC)
                
                # Add item if it's newer than the cutoff date
                if published_date >= cutoff_date:
                    filtered_items.append(item)
                    
            except Exception as e:
                logger.error(f"Error processing date {item.get('published', '')}: {e}")
        
        return filtered_items
        
    def save_content(self, items: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        Save content items to a JSON file.
        
        Args:
            items (list): List of content items to save.
            filename (str, optional): Filename to save to. If not provided, a timestamp-based name will be used.
            
        Returns:
            str: Path to the saved file.
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"aggregated_content_{timestamp}.json"
        
        file_path = os.path.join(self.data_dir, filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(items)} items to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving content to {file_path}: {e}")
            return ""
    
    def load_content(self, filename: str) -> List[Dict[str, Any]]:
        """
        Load content items from a JSON file.
        
        Args:
            filename (str): Filename to load from.
            
        Returns:
            list: List of content items.
        """
        file_path = os.path.join(self.data_dir, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                items = json.load(f)
            logger.info(f"Loaded {len(items)} items from {file_path}")
            return items
        except Exception as e:
            logger.error(f"Error loading content from {file_path}: {e}")
            return []
    
    def get_latest_content_file(self) -> Optional[str]:
        """
        Get the latest content file in the data directory.
        
        Returns:
            str: Filename of the latest content file, or None if no files found.
        """
        try:
            files = [f for f in os.listdir(self.data_dir) if f.startswith("aggregated_content_") and f.endswith(".json")]
            if not files:
                return None
            
            # Sort files by timestamp (newest first)
            files.sort(reverse=True)
            return files[0]
        except Exception as e:
            logger.error(f"Error getting latest content file: {e}")
            return None
    
    def search_content(self, items: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Search content items for a query string.
        
        Args:
            items (list): List of content items to search.
            query (str): Query string to search for.
            
        Returns:
            list: List of matching content items.
        """
        query = query.lower()
        results = []
        
        for item in items:
            # Search in title and summary
            title = item.get('title', '').lower()
            summary = item.get('summary', '').lower()
            
            if query in title or query in summary:
                results.append(item)
        
        return results
    
    def deduplicate_content(self, items: List[Dict[str, Any]], 
                          similarity_threshold=0.85, 
                          time_window_hours=24) -> List[Dict[str, Any]]:
        """
        Remove duplicate content items based on multiple factors.
        
        Args:
            items: List of content items
            similarity_threshold: Threshold for title similarity (0.0-1.0)
            time_window_hours: Time window to consider for duplicates (in hours)
            
        Returns:
            List of deduplicated content items
        """
        # Import the deduplication module here to avoid circular imports
        if not DEDUPLICATION_AVAILABLE:
            logger.warning("Deduplication module not available. Skipping deduplication.")
            return items
            
        try:
            from backend.core.deduplication import ContentDeduplicator
            
            logger.info(f"Deduplicating {len(items)} content items")
            deduplicator = ContentDeduplicator(
                similarity_threshold=similarity_threshold,
                time_window_hours=time_window_hours
            )
            unique_items = deduplicator.deduplicate_content(items)
            logger.info(f"Deduplicated to {len(unique_items)} unique items")
            return unique_items
        except Exception as e:
            logger.error(f"Error during deduplication: {e}")
            return items


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
