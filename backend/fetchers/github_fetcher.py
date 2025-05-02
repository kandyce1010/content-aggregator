#!/usr/bin/env python3
"""
GitHub Fetcher Module

This module handles fetching activity from GitHub repositories.
It uses the GitHub REST API to extract releases, issues, pull requests, and commits.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GitHubFetcher:
    """
    A class to fetch activity from GitHub repositories.
    """
    
    def __init__(self, config_path=None, token=None):
        """
        Initialize the GitHub fetcher with configuration.
        
        Args:
            config_path (str, optional): Path to the configuration file.
                Defaults to '../config/sources.json'.
            token (str, optional): GitHub personal access token.
                If not provided, will use unauthenticated requests (rate limited).
        """
        if config_path is None:
            # Get the directory of the current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Navigate to the config directory
            config_path = os.path.join(current_dir, '..', '..', 'config', 'sources.json')
        
        self.config_path = config_path
        self.repositories = self._load_repository_config()
        self.token = token
        
        # Create data directory if it doesn't exist
        # Use /tmp directory in Lambda environment
        if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            self.data_dir = '/tmp/data'
        else:
            # Use regular path for local development
            self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                        '..', '..', 'data')
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        
        # Set up headers for GitHub API requests
        self.headers = {
            'Accept': 'application/vnd.github.v3+json'
        }
        
        if self.token:
            self.headers['Authorization'] = f'token {self.token}'
    
    def _load_repository_config(self):
        """
        Load GitHub repository configuration from the config file.
        
        Returns:
            list: List of GitHub repository configurations.
        """
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                return config.get('github_repositories', [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading configuration: {e}")
            return []
    
    def fetch_repository(self, repo_config):
        """
        Fetch activity from a GitHub repository.
        
        Args:
            repo_config (dict): Configuration for the repository to fetch.
        
        Returns:
            list: List of dictionaries containing repository activity.
        """
        repo_name = repo_config['name']
        repo_url = repo_config['url']
        category = repo_config.get('category', 'github')
        
        # Extract owner and repo from URL
        # URL format: https://github.com/owner/repo
        parts = repo_url.rstrip('/').split('/')
        owner = parts[-2]
        repo = parts[-1]
        
        logger.info(f"Fetching GitHub repository: {owner}/{repo}")
        
        activities = []
        
        # Fetch releases
        activities.extend(self._fetch_releases(owner, repo, repo_name, category))
        
        # Fetch pull requests
        activities.extend(self._fetch_pull_requests(owner, repo, repo_name, category))
        
        # Sort by date (newest first)
        activities.sort(key=lambda x: x['published'], reverse=True)
        
        logger.info(f"Successfully fetched {len(activities)} activities from {repo_name}")
        return activities
    
    def _fetch_releases(self, owner, repo, repo_name, category):
        """
        Fetch releases from a GitHub repository.
        
        Args:
            owner (str): Repository owner.
            repo (str): Repository name.
            repo_name (str): Display name for the repository.
            category (str): Category for the content.
            
        Returns:
            list: List of release activities.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/releases"
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch releases for {owner}/{repo}: Status code {response.status_code}")
                return []
            
            releases = response.json()
            activities = []
            
            for release in releases:
                # Skip draft releases
                if release.get('draft', False):
                    continue
                
                published_at = release.get('published_at')
                if not published_at:
                    continue
                
                tag_name = release.get('tag_name', '')
                name = release.get('name', tag_name)
                
                activity = {
                    'id': f"github-release-{release['id']}",
                    'title': f"Release {name}",
                    'link': release['html_url'],
                    'summary': release.get('body', ''),
                    'published': published_at,
                    'source': f"GitHub - {repo_name}",
                    'category': category,
                    'content_type': 'github_release',
                    'author': release.get('author', {}).get('login', 'Unknown'),
                    'fetched_at': datetime.now().isoformat()
                }
                
                activities.append(activity)
            
            logger.info(f"Fetched {len(activities)} releases from {owner}/{repo}")
            return activities
            
        except Exception as e:
            logger.error(f"Error fetching releases for {owner}/{repo}: {e}")
            return []
    
    def _fetch_pull_requests(self, owner, repo, repo_name, category):
        """
        Fetch recent pull requests from a GitHub repository.
        
        Args:
            owner (str): Repository owner.
            repo (str): Repository name.
            repo_name (str): Display name for the repository.
            category (str): Category for the content.
            
        Returns:
            list: List of pull request activities.
        """
        # GitHub API doesn't have a direct 'since' filter for PRs, so we'll fetch recent ones and filter
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=all&sort=updated&direction=desc"
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch PRs for {owner}/{repo}: Status code {response.status_code}")
                return []
            
            prs = response.json()
            activities = []
            
            # Get PRs from the last 7 days
            cutoff_date = datetime.now() - timedelta(days=7)
            
            for pr in prs:
                updated_at = datetime.fromisoformat(pr['updated_at'].replace('Z', '+00:00'))
                
                # Skip PRs updated before the cutoff date
                if updated_at < cutoff_date:
                    continue
                
                created_at = pr.get('created_at')
                if not created_at:
                    continue
                
                # Determine PR status
                status = "merged" if pr.get('merged_at') else pr.get('state', 'open')
                
                activity = {
                    'id': f"github-pr-{pr['id']}",
                    'title': f"PR: {pr['title']} ({status})",
                    'link': pr['html_url'],
                    'summary': pr.get('body', ''),
                    'published': created_at,
                    'source': f"GitHub - {repo_name}",
                    'category': category,
                    'content_type': 'github_pr',
                    'author': pr.get('user', {}).get('login', 'Unknown'),
                    'fetched_at': datetime.now().isoformat()
                }
                
                activities.append(activity)
            
            logger.info(f"Fetched {len(activities)} pull requests from {owner}/{repo}")
            return activities
            
        except Exception as e:
            logger.error(f"Error fetching pull requests for {owner}/{repo}: {e}")
            return []
    
    def _fetch_issues(self, owner, repo, repo_name, category):
        """
        Fetch recent issues from a GitHub repository.
        
        Args:
            owner (str): Repository owner.
            repo (str): Repository name.
            repo_name (str): Display name for the repository.
            category (str): Category for the content.
            
        Returns:
            list: List of issue activities.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/issues?state=all&sort=updated&direction=desc"
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch issues for {owner}/{repo}: Status code {response.status_code}")
                return []
            
            issues = response.json()
            activities = []
            
            # Get issues from the last 7 days
            cutoff_date = datetime.now() - timedelta(days=7)
            
            for issue in issues:
                # Skip pull requests (they have a 'pull_request' key)
                if 'pull_request' in issue:
                    continue
                    
                updated_at = datetime.fromisoformat(issue['updated_at'].replace('Z', '+00:00'))
                
                # Skip issues updated before the cutoff date
                if updated_at < cutoff_date:
                    continue
                
                created_at = issue.get('created_at')
                if not created_at:
                    continue
                
                activity = {
                    'id': f"github-issue-{issue['id']}",
                    'title': f"Issue: {issue['title']} ({issue['state']})",
                    'link': issue['html_url'],
                    'summary': issue.get('body', ''),
                    'published': created_at,
                    'source': f"GitHub - {repo_name}",
                    'category': category,
                    'content_type': 'github_issue',
                    'author': issue.get('user', {}).get('login', 'Unknown'),
                    'fetched_at': datetime.now().isoformat()
                }
                
                activities.append(activity)
            
            logger.info(f"Fetched {len(activities)} issues from {owner}/{repo}")
            return activities
            
        except Exception as e:
            logger.error(f"Error fetching issues for {owner}/{repo}: {e}")
            return []
            
    def _fetch_commits(self, owner, repo, repo_name, category):
        """
        Fetch recent commits from a GitHub repository.
        
        Args:
            owner (str): Repository owner.
            repo (str): Repository name.
            repo_name (str): Display name for the repository.
            category (str): Category for the content.
            
        Returns:
            list: List of commit activities.
        """
        # Get commits from the last 3 days
        since = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%SZ')
        url = f"https://api.github.com/repos/{owner}/{repo}/commits?since={since}"
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch commits for {owner}/{repo}: Status code {response.status_code}")
                return []
            
            commits = response.json()
            activities = []
            
            for commit in commits:
                # Skip commits without author info
                if not commit.get('commit', {}).get('author', {}).get('date'):
                    continue
                
                commit_date = commit['commit']['author']['date']
                commit_message = commit['commit']['message']
                
                # Get first line of commit message as title
                title_line = commit_message.split('\n')[0]
                
                activity = {
                    'id': f"github-commit-{commit['sha']}",
                    'title': f"Commit: {title_line[:60]}{'...' if len(title_line) > 60 else ''}",
                    'link': commit['html_url'],
                    'summary': commit_message,
                    'published': commit_date,
                    'source': f"GitHub - {repo_name}",
                    'category': category,
                    'content_type': 'github_commit',
                    'author': commit.get('author', {}).get('login', commit['commit']['author'].get('name', 'Unknown')),
                    'fetched_at': datetime.now().isoformat()
                }
                
                activities.append(activity)
            
            logger.info(f"Fetched {len(activities)} commits from {owner}/{repo}")
            return activities
            
        except Exception as e:
            logger.error(f"Error fetching commits for {owner}/{repo}: {e}")
            return []
    
    def fetch_all_repositories(self):
        """
        Fetch activity from all configured GitHub repositories.
        
        Returns:
            list: List of dictionaries containing activities from all repositories.
        """
        all_activities = []
        
        for repo_config in self.repositories:
            try:
                repo_activities = self.fetch_repository(repo_config)
                all_activities.extend(repo_activities)
            except Exception as e:
                logger.error(f"Error fetching repository {repo_config['name']}: {e}")
        
        return all_activities
    
    def save_to_json(self, activities, filename=None):
        """
        Save fetched activities to a JSON file.
        
        Args:
            activities (list): List of activities to save.
            filename (str, optional): Name of the file to save to.
                Defaults to 'github_activities_{timestamp}.json'.
        
        Returns:
            str: Path to the saved file.
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'github_activities_{timestamp}.json'
        
        file_path = os.path.join(self.data_dir, filename)
        
        try:
            with open(file_path, 'w') as f:
                json.dump(activities, f, indent=2)
            logger.info(f"Saved {len(activities)} activities to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving activities to {file_path}: {e}")
            return None


if __name__ == "__main__":
    # Example usage when run directly
    fetcher = GitHubFetcher()
    activities = fetcher.fetch_all_repositories()
    fetcher.save_to_json(activities)
    
    # Print summary of fetched activities
    print(f"\nFetched {len(activities)} activities from {len(fetcher.repositories)} repositories:")
    for repo in fetcher.repositories:
        repo_activities = [a for a in activities if a['source'] == f"GitHub - {repo['name']}"]
        print(f"  - {repo['name']}: {len(repo_activities)} activities")
