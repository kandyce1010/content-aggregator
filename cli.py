#!/usr/bin/env python3
"""
Content Aggregator CLI

A command-line interface for the Content Aggregator that allows fetching
and displaying content from various sources.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the parent directory to sys.path to allow importing from backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.fetchers.rss_fetcher import RSSFetcher


def display_item(item, index, verbose=False):
    """
    Display a single content item in the terminal.
    
    Args:
        item (dict): The content item to display
        index (int): The item number
        verbose (bool): Whether to show detailed information
    """
    print(f"\n{'-' * 80}")
    print(f"{index}. [{item['source']}] {item['title']}")
    print(f"   Category: {item['category']}")
    print(f"   Published: {item['published']}")
    print(f"   Link: {item['link']}")
    
    if verbose:
        print(f"\n   Summary:")
        # Print summary with word wrap
        summary = item['summary']
        # Simple HTML tag removal (very basic)
        summary = summary.replace('<p>', '').replace('</p>', '\n')
        summary = summary.replace('<br>', '\n').replace('<br/>', '\n')
        
        # Print with word wrap (80 chars)
        words = summary.split()
        line = "   "
        for word in words:
            if len(line) + len(word) + 1 > 80:
                print(line)
                line = "   " + word + " "
            else:
                line += word + " "
        if line.strip():
            print(line)
    
    print(f"{'-' * 80}")


def fetch_and_display_rss(args):
    """
    Fetch RSS feeds and display them according to command line arguments.
    
    Args:
        args: Command line arguments
    """
    fetcher = RSSFetcher()
    print(f"Fetching RSS feeds...")
    items = fetcher.fetch_all_feeds()
    
    if not items:
        print("No items found.")
        return
    
    # Filter by category if specified
    if args.category:
        items = [item for item in items if item['category'] == args.category]
        if not items:
            print(f"No items found in category '{args.category}'.")
            return
    
    # Sort items by date (newest first)
    items.sort(key=lambda x: x['published'], reverse=True)
    
    # Limit number of items if specified
    if args.limit and args.limit > 0:
        items = items[:args.limit]
    
    print(f"\nDisplaying {len(items)} items:")
    
    for i, item in enumerate(items, 1):
        display_item(item, i, args.verbose)
    
    # Save to file if requested
    if args.save:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'rss_items_{timestamp}.json'
        file_path = os.path.join(data_dir, filename)
        
        with open(file_path, 'w') as f:
            json.dump(items, f, indent=2)
        print(f"\nSaved {len(items)} items to {file_path}")


def list_categories(args):
    """
    List all available categories from the configuration.
    
    Args:
        args: Command line arguments
    """
    fetcher = RSSFetcher()
    categories = set()
    
    for feed in fetcher.feeds:
        categories.add(feed.get('category', 'uncategorized'))
    
    print("\nAvailable categories:")
    for category in sorted(categories):
        print(f"  - {category}")


def main():
    """
    Main entry point for the CLI.
    """
    parser = argparse.ArgumentParser(
        description='Content Aggregator CLI',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # RSS command
    rss_parser = subparsers.add_parser('rss', help='Fetch and display RSS feeds')
    rss_parser.add_argument('-c', '--category', help='Filter by category')
    rss_parser.add_argument('-l', '--limit', type=int, help='Limit number of items')
    rss_parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed information')
    rss_parser.add_argument('-s', '--save', action='store_true', help='Save results to JSON file')
    
    # Categories command
    categories_parser = subparsers.add_parser('categories', help='List available categories')
    
    args = parser.parse_args()
    
    if args.command == 'rss':
        fetch_and_display_rss(args)
    elif args.command == 'categories':
        list_categories(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
