#!/usr/bin/env python3
"""
YouTube Fetcher

This module fetches content from YouTube channels using the YouTube Data API.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import googleapiclient.discovery
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class YouTubeFetcher:
    """
    A class to fetch content from YouTube channels.
    """
    
    def __init__(self, config_path=None, api_key=None):
        """
        Initialize the YouTube fetcher with configuration.
        
        Args:
            config_path (str, optional): Path to the configuration file.
            api_key (str, optional): YouTube Data API key.
        """
        self.config_path = config_path
        self.api_key = api_key or os.environ.get('YOUTUBE_API_KEY')
        
        if not self.api_key:
            logger.warning("YouTube API key not provided. Set YOUTUBE_API_KEY environment variable.")
        
        # Load configuration
        self.channels = []
        if config_path is None:
            # Get the directory of the current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Navigate to the config directory
            config_path = os.path.join(current_dir, '..', '..', 'config', 'sources.json')
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.channels = config.get('youtube_channels', [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading configuration: {e}")
    
    def fetch_all_channels(self) -> List[Dict[str, Any]]:
        """
        Fetch content from all configured YouTube channels.
        
        Returns:
            list: List of content items from YouTube channels.
        """
        if not self.api_key:
            logger.error("YouTube API key not available. Cannot fetch YouTube content.")
            return []
        
        all_items = []
        for channel in self.channels:
            try:
                logger.info(f"Fetching videos from channel: {channel.get('name')}")
                items = self.fetch_channel_videos(channel)
                all_items.extend(items)
                logger.info(f"Fetched {len(items)} videos from {channel.get('name')}")
            except Exception as e:
                logger.error(f"Error fetching channel {channel.get('name')}: {e}")
        
        return all_items
    
    def fetch_channel_videos(self, channel: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch videos from a specific YouTube channel.
        
        Args:
            channel (dict): Channel configuration.
            
        Returns:
            list: List of videos from the channel.
        """
        try:
            # Create YouTube API client
            youtube = googleapiclient.discovery.build(
                'youtube', 'v3', developerKey=self.api_key, cache_discovery=False
            )
            
            # Get channel ID if not provided
            channel_id = channel.get('channel_id')
            if not channel_id and 'username' in channel:
                channel_id = self._get_channel_id_from_username(youtube, channel['username'])
            
            if not channel_id:
                logger.error(f"No channel ID available for {channel.get('name')}")
                return []
            
            # Get uploads playlist ID
            uploads_playlist_id = self._get_uploads_playlist_id(youtube, channel_id)
            if not uploads_playlist_id:
                logger.error(f"Could not find uploads playlist for channel {channel.get('name')}")
                return []
            
            # Get videos from uploads playlist
            videos = self._get_playlist_items(youtube, uploads_playlist_id, max_results=10)
            
            # Format videos to match our content structure
            formatted_items = []
            for video in videos:
                snippet = video.get('snippet', {})
                video_id = snippet.get('resourceId', {}).get('videoId')
                if not video_id:
                    continue
                
                # Get video details to get view count and other metadata
                video_details = self._get_video_details(youtube, video_id)
                
                # Format the published date
                published_at = snippet.get('publishedAt')
                if published_at:
                    # Convert to datetime object for easier filtering
                    published_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    
                    # Only include videos from the last 30 days
                    if published_date < datetime.now(published_date.tzinfo) - timedelta(days=30):
                        continue
                
                # Format the item
                item = {
                    'id': video_id,
                    'title': snippet.get('title', 'No title'),
                    'summary': snippet.get('description', 'No description'),
                    'link': f"https://www.youtube.com/watch?v={video_id}",
                    'published': published_at,
                    'source': f"YouTube - {channel.get('name', 'Unknown Channel')}",
                    'category': channel.get('category', 'YouTube'),
                    'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', '')
                }
                
                # Add video statistics if available
                if video_details:
                    statistics = video_details.get('statistics', {})
                    item['views'] = statistics.get('viewCount', '0')
                    item['likes'] = statistics.get('likeCount', '0')
                    item['comments'] = statistics.get('commentCount', '0')
                
                formatted_items.append(item)
            
            return formatted_items
            
        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching YouTube channel: {e}")
            return []
    
    def _get_channel_id_from_username(self, youtube, username: str) -> Optional[str]:
        """
        Get channel ID from username.
        
        Args:
            youtube: YouTube API client.
            username (str): YouTube username.
            
        Returns:
            str: Channel ID or None if not found.
        """
        try:
            response = youtube.channels().list(
                part='id',
                forUsername=username
            ).execute()
            
            items = response.get('items', [])
            if items:
                return items[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error getting channel ID from username: {e}")
            return None
    
    def _get_uploads_playlist_id(self, youtube, channel_id: str) -> Optional[str]:
        """
        Get the uploads playlist ID for a channel.
        
        Args:
            youtube: YouTube API client.
            channel_id (str): YouTube channel ID.
            
        Returns:
            str: Uploads playlist ID or None if not found.
        """
        try:
            response = youtube.channels().list(
                part='contentDetails',
                id=channel_id
            ).execute()
            
            items = response.get('items', [])
            if items:
                return items[0]['contentDetails']['relatedPlaylists']['uploads']
            return None
        except Exception as e:
            logger.error(f"Error getting uploads playlist ID: {e}")
            return None
    
    def _get_playlist_items(self, youtube, playlist_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Get items from a playlist.
        
        Args:
            youtube: YouTube API client.
            playlist_id (str): YouTube playlist ID.
            max_results (int): Maximum number of results to return.
            
        Returns:
            list: List of playlist items.
        """
        try:
            response = youtube.playlistItems().list(
                part='snippet',
                playlistId=playlist_id,
                maxResults=max_results
            ).execute()
            
            return response.get('items', [])
        except Exception as e:
            logger.error(f"Error getting playlist items: {e}")
            return []
    
    def _get_video_details(self, youtube, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a video.
        
        Args:
            youtube: YouTube API client.
            video_id (str): YouTube video ID.
            
        Returns:
            dict: Video details or None if not found.
        """
        try:
            response = youtube.videos().list(
                part='statistics,contentDetails',
                id=video_id
            ).execute()
            
            items = response.get('items', [])
            if items:
                return items[0]
            return None
        except Exception as e:
            logger.error(f"Error getting video details: {e}")
            return None


if __name__ == "__main__":
    # Example usage when run directly
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube Content Fetcher')
    parser.add_argument('--api-key', help='YouTube Data API key')
    parser.add_argument('--channel', help='Specific channel name to fetch')
    parser.add_argument('--limit', type=int, default=10, help='Maximum number of videos to fetch per channel')
    
    args = parser.parse_args()
    
    fetcher = YouTubeFetcher(api_key=args.api_key)
    
    if args.channel:
        # Fetch specific channel
        channel_config = None
        for channel in fetcher.channels:
            if channel.get('name') == args.channel:
                channel_config = channel
                break
        
        if channel_config:
            videos = fetcher.fetch_channel_videos(channel_config)
            print(f"Fetched {len(videos)} videos from {args.channel}")
            for video in videos:
                print(f"- {video['title']}")
                print(f"  Published: {video['published']}")
                print(f"  Link: {video['link']}")
                print()
        else:
            print(f"Channel '{args.channel}' not found in configuration")
    else:
        # Fetch all channels
        all_videos = fetcher.fetch_all_channels()
        print(f"Fetched {len(all_videos)} videos from all channels")
        
        # Group by channel
        videos_by_channel = {}
        for video in all_videos:
            channel = video['source']
            if channel not in videos_by_channel:
                videos_by_channel[channel] = []
            videos_by_channel[channel].append(video)
        
        # Print summary
        for channel, videos in videos_by_channel.items():
            print(f"\n{channel}: {len(videos)} videos")
            for video in videos[:3]:  # Show top 3 videos per channel
                print(f"- {video['title']}")
                print(f"  Published: {video['published']}")
                print(f"  Link: {video['link']}")
            
            if len(videos) > 3:
                print(f"  ... and {len(videos) - 3} more")
