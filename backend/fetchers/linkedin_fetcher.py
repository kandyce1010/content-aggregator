#!/usr/bin/env python3
"""
LinkedIn Fetcher Module

This module handles fetching content from LinkedIn profiles and company pages.
It uses web scraping techniques to extract posts and updates.
"""

import os
import json
import logging
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LinkedInFetcher:
    """
    A class to fetch content from LinkedIn profiles and company pages.
    """
    
    def __init__(self, config_path=None):
        """
        Initialize the LinkedIn fetcher with configuration.
        
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
        self.profiles = self._load_profile_config()
        
        # Create data directory if it doesn't exist
        # Use /tmp directory in Lambda environment
        if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            self.data_dir = '/tmp/data'
        else:
            # Use regular path for local development
            self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                        '..', '..', 'data')
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        
        # User agent rotation to avoid detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
        ]
    
    def _load_profile_config(self):
        """
        Load LinkedIn profile configuration from the config file.
        
        Returns:
            list: List of LinkedIn profile configurations.
        """
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                return config.get('linkedin_profiles', [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading configuration: {e}")
            return []
    
    def _get_random_user_agent(self):
        """
        Get a random user agent to avoid detection.
        
        Returns:
            str: Random user agent string.
        """
        return random.choice(self.user_agents)
    
    def fetch_profile(self, profile_config):
        """
        Fetch content from a LinkedIn profile.
        
        Args:
            profile_config (dict): Configuration for the profile to fetch.
        
        Returns:
            list: List of dictionaries containing profile posts.
        """
        logger.info(f"Fetching LinkedIn profile: {profile_config['name']}")
        
        url = profile_config['url']
        if '/posts' not in url and '/recent-activity' not in url:
            # Append /recent-activity to get the posts page if not already there
            url = url.rstrip('/') + '/recent-activity/shares/'
        
        headers = {
            'User-Agent': self._get_random_user_agent(),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        try:
            # Add a delay to avoid rate limiting
            time.sleep(random.uniform(1, 3))
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch {url}: Status code {response.status_code}")
                return []
            
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract posts
            posts = []
            
            # Find post containers - this selector may need to be updated as LinkedIn changes their HTML structure
            post_elements = soup.select('div.ember-view.occludable-update')
            
            if not post_elements:
                # Try alternative selectors
                post_elements = soup.select('div.feed-shared-update-v2')
            
            if not post_elements:
                # Try another alternative
                post_elements = soup.select('div.feed-shared-card')
            
            for post_element in post_elements:
                try:
                    # Extract post content - these selectors may need to be updated
                    content_element = post_element.select_one('div.feed-shared-text') or \
                                     post_element.select_one('div.feed-shared-update-v2__description') or \
                                     post_element.select_one('div.feed-shared-text-view')
                    
                    content = ""
                    if content_element:
                        content = content_element.get_text(strip=True)
                    
                    # If no content found, try to find article title
                    if not content:
                        title_element = post_element.select_one('div.feed-shared-article__title') or \
                                       post_element.select_one('span.feed-shared-article__title')
                        if title_element:
                            content = title_element.get_text(strip=True)
                    
                    # If still no content, skip this post
                    if not content:
                        continue
                    
                    # Extract post link
                    link_element = post_element.select_one('a.app-aware-link') or \
                                  post_element.select_one('a.feed-shared-article__link')
                    
                    link = ""
                    if link_element and 'href' in link_element.attrs:
                        link = link_element['href']
                        # Make sure the link is absolute
                        if link.startswith('/'):
                            link = f"https://www.linkedin.com{link}"
                    
                    # Extract timestamp
                    time_element = post_element.select_one('span.feed-shared-actor__sub-description') or \
                                  post_element.select_one('time.feed-shared-actor__sub-description')
                    
                    timestamp = ""
                    if time_element:
                        timestamp = time_element.get_text(strip=True)
                    
                    # Create post item
                    post = {
                        'id': link or f"linkedin-{profile_config['name']}-{len(posts)}",
                        'title': content[:100] + ('...' if len(content) > 100 else ''),
                        'link': link or profile_config['url'],
                        'summary': content,
                        'published': self._parse_linkedin_date(timestamp),
                        'source': f"LinkedIn - {profile_config['name']}",
                        'category': profile_config.get('category', 'linkedin'),
                        'content_type': 'linkedin',
                        'author': profile_config['name'],
                        'fetched_at': datetime.now().isoformat()
                    }
                    
                    posts.append(post)
                except Exception as e:
                    logger.error(f"Error parsing post: {e}")
            
            logger.info(f"Successfully fetched {len(posts)} posts from {profile_config['name']}")
            return posts
            
        except Exception as e:
            logger.error(f"Error fetching LinkedIn profile {profile_config['name']}: {e}")
            return []
    
    def _parse_linkedin_date(self, date_str):
        """
        Parse LinkedIn date format into ISO format.
        
        Args:
            date_str (str): Date string from LinkedIn.
            
        Returns:
            str: ISO formatted date string.
        """
        try:
            now = datetime.now()
            
            # LinkedIn uses relative dates like "1d", "2w", etc.
            if not date_str:
                return now.isoformat()
                
            date_str = date_str.lower()
            
            if 'now' in date_str or 'just now' in date_str:
                return now.isoformat()
            
            if 'h' in date_str:  # Hours
                hours = int(''.join(filter(str.isdigit, date_str)))
                date = now - timedelta(hours=hours)
                return date.isoformat()
                
            if 'd' in date_str:  # Days
                days = int(''.join(filter(str.isdigit, date_str)))
                date = now - timedelta(days=days)
                return date.isoformat()
                
            if 'w' in date_str:  # Weeks
                weeks = int(''.join(filter(str.isdigit, date_str)))
                date = now - timedelta(weeks=weeks)
                return date.isoformat()
                
            if 'm' in date_str:  # Months
                months = int(''.join(filter(str.isdigit, date_str)))
                # Approximate months as 30 days
                date = now - timedelta(days=months*30)
                return date.isoformat()
                
            if 'y' in date_str:  # Years
                years = int(''.join(filter(str.isdigit, date_str)))
                # Approximate years as 365 days
                date = now - timedelta(days=years*365)
                return date.isoformat()
            
            # If we can't parse it, return current date
            return now.isoformat()
            
        except Exception:
            return datetime.now().isoformat()
    
    def fetch_all_profiles(self):
        """
        Fetch all configured LinkedIn profiles.
        
        Returns:
            list: List of dictionaries containing posts from all profiles.
        """
        all_posts = []
        
        for profile_config in self.profiles:
            try:
                profile_posts = self.fetch_profile(profile_config)
                all_posts.extend(profile_posts)
                # Add a delay between profile requests
                time.sleep(random.uniform(3, 7))
            except Exception as e:
                logger.error(f"Error fetching profile {profile_config['name']}: {e}")
        
        return all_posts
    
    def save_to_json(self, posts, filename=None):
        """
        Save fetched posts to a JSON file.
        
        Args:
            posts (list): List of posts to save.
            filename (str, optional): Name of the file to save to.
                Defaults to 'linkedin_posts_{timestamp}.json'.
        
        Returns:
            str: Path to the saved file.
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'linkedin_posts_{timestamp}.json'
        
        file_path = os.path.join(self.data_dir, filename)
        
        try:
            with open(file_path, 'w') as f:
                json.dump(posts, f, indent=2)
            logger.info(f"Saved {len(posts)} posts to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving posts to {file_path}: {e}")
            return None


if __name__ == "__main__":
    # Example usage when run directly
    fetcher = LinkedInFetcher()
    posts = fetcher.fetch_all_profiles()
    fetcher.save_to_json(posts)
    
    # Print summary of fetched posts
    print(f"\nFetched {len(posts)} posts from {len(fetcher.profiles)} profiles:")
    for profile in fetcher.profiles:
        profile_posts = [post for post in posts if post['source'] == f"LinkedIn - {profile['name']}"]
        print(f"  - {profile['name']}: {len(profile_posts)} posts")
