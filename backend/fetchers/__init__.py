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

__all__ = ['RSSFetcher']
