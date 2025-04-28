"""
GitHub repository fetcher module.

This module handles fetching content from GitHub repositories including:
- New releases
- Recent issues and pull requests
- README and documentation updates
"""

import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class GitHubFetcher:
    def __init__(self, token=None):
        """
        Initialize GitHub fetcher.
        
        Args:
            token (str, optional): GitHub API token for authenticated requests
                                  (increases rate limits and allows access to private repos)
        """
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Content-Aggregator-App"
        }
        
        # Add token if provided
        if token:
            self.headers["Authorization"] = f"token {token}"
    
    def fetch_repository_info(self, owner, repo):
        """
        Fetch basic information about a repository.
        
        Args:
            owner (str): Repository owner/organization
            repo (str): Repository name
            
        Returns:
            dict: Repository information
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching repository info for {owner}/{repo}: {str(e)}")
            return None
    
    def fetch_releases(self, owner, repo, limit=5):
        """
        Fetch recent releases for a repository.
        
        Args:
            owner (str): Repository owner/organization
            repo (str): Repository name
            limit (int): Maximum number of releases to fetch
            
        Returns:
            list: List of release dictionaries
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/releases"
            response = requests.get(url, headers=self.headers, params={"per_page": limit})
            response.raise_for_status()
            
            releases = response.json()
            processed_releases = []
            
            for release in releases:
                processed_release = {
                    'id': release['id'],
                    'title': release['name'] or f"Release {release['tag_name']}",
                    'tag': release['tag_name'],
                    'body': release['body'],
                    'url': release['html_url'],
                    'published_at': release['published_at'],
                    'source': 'github',
                    'source_type': 'release',
                    'repo': f"{owner}/{repo}"
                }
                processed_releases.append(processed_release)
                
            return processed_releases
            
        except Exception as e:
            logger.error(f"Error fetching releases for {owner}/{repo}: {str(e)}")
            return []
    
    def fetch_issues(self, owner, repo, limit=10, days=7):
        """
        Fetch recent issues for a repository.
        
        Args:
            owner (str): Repository owner/organization
            repo (str): Repository name
            limit (int): Maximum number of issues to fetch
            days (int): Only fetch issues from the last X days
            
        Returns:
            list: List of issue dictionaries
        """
        try:
            # Calculate date for filtering
            since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            url = f"{self.base_url}/repos/{owner}/{repo}/issues"
            params = {
                "state": "all",
                "sort": "created",
                "direction": "desc",
                "per_page": limit,
                "since": since_date
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            issues = response.json()
            processed_issues = []
            
            for issue in issues:
                # Skip pull requests (they're also returned by the issues endpoint)
                if 'pull_request' in issue:
                    continue
                    
                processed_issue = {
                    'id': issue['id'],
                    'title': issue['title'],
                    'body': issue['body'],
                    'url': issue['html_url'],
                    'state': issue['state'],
                    'created_at': issue['created_at'],
                    'updated_at': issue['updated_at'],
                    'source': 'github',
                    'source_type': 'issue',
                    'repo': f"{owner}/{repo}"
                }
                processed_issues.append(processed_issue)
                
            return processed_issues
            
        except Exception as e:
            logger.error(f"Error fetching issues for {owner}/{repo}: {str(e)}")
            return []
    
    def fetch_readme(self, owner, repo):
        """
        Fetch README content for a repository.
        
        Args:
            owner (str): Repository owner/organization
            repo (str): Repository name
            
        Returns:
            dict: README information
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/readme"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            readme = response.json()
            
            # Get the actual content
            content_url = f"{self.base_url}/repos/{owner}/{repo}/contents/{readme['path']}"
            content_response = requests.get(content_url, headers=self.headers)
            content_response.raise_for_status()
            content_data = content_response.json()
            
            processed_readme = {
                'id': f"{owner}/{repo}/readme",
                'title': f"README for {owner}/{repo}",
                'content': content_data.get('content', ''),  # Base64 encoded content
                'encoding': content_data.get('encoding', 'base64'),
                'url': readme['html_url'],
                'updated_at': content_data.get('last_modified', datetime.now().isoformat()),
                'source': 'github',
                'source_type': 'readme',
                'repo': f"{owner}/{repo}"
            }
                
            return processed_readme
            
        except Exception as e:
            logger.error(f"Error fetching README for {owner}/{repo}: {str(e)}")
            return None
    
    def fetch_all_content(self, repo_config):
        """
        Fetch all relevant content for a repository.
        
        Args:
            repo_config (dict): Repository configuration with owner and name
            
        Returns:
            dict: All fetched content for the repository
        """
        owner = repo_config['owner']
        repo = repo_config['name']
        category = repo_config.get('category', 'github')
        
        logger.info(f"Fetching content for GitHub repository: {owner}/{repo}")
        
        repo_info = self.fetch_repository_info(owner, repo)
        releases = self.fetch_releases(owner, repo)
        issues = self.fetch_issues(owner, repo)
        readme = self.fetch_readme(owner, repo)
        
        return {
            'repo_info': repo_info,
            'releases': releases,
            'issues': issues,
            'readme': readme,
            'category': category
        }
