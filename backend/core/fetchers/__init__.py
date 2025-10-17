"""
Content Aggregator Fetchers Package

This package contains modules for fetching content from various sources:
- RSS feeds
- YouTube channels
- LinkedIn profiles
- GitHub repositories
- Search-based content (Medium, Dev.to)
"""

from .rss_fetcher import RSSFetcher
from .linkedin_fetcher import LinkedInFetcher
from .github_fetcher import GitHubFetcher

# Try to import YouTubeFetcher, but provide a dummy implementation if it fails
try:
    from .youtube_fetcher import YouTubeFetcher
except ImportError:
    # Define a dummy YouTubeFetcher that does nothing
    class YouTubeFetcher:
        def __init__(self, *args, **kwargs):
            self.available = False
            
        def fetch(self, *args, **kwargs):
            return []

__all__ = ['RSSFetcher', 'LinkedInFetcher', 'GitHubFetcher', 'YouTubeFetcher']
