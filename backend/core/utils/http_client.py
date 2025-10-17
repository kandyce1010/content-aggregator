"""Secure HTTP client for Content Aggregator."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SecureHTTPClient:
    """Secure HTTP client with proper timeouts, retries, and SSL verification."""
    
    def __init__(self, timeout: int = 10, max_retries: int = 3):
        """Initialize the secure HTTP client."""
        self.session = requests.Session()
        self.timeout = timeout
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'User-Agent': 'Content-Aggregator/1.0 (+https://github.com/yourusername/content-aggregator)'
        })
    
    def get(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
        """Make a secure GET request."""
        try:
            # Validate URL
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f"Invalid URL scheme: {url}")
            
            response = self.session.get(
                url,
                headers=headers,
                timeout=self.timeout,
                verify=True,  # Always verify SSL
                **kwargs
            )
            response.raise_for_status()
            return response
            
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL verification failed for {url}: {e}")
            raise
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout for {url}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed for {url}: {e}")
            raise
    
    def post(self, url: str, data: Optional[Dict] = None, json: Optional[Dict] = None, 
             headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
        """Make a secure POST request."""
        try:
            # Validate URL
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f"Invalid URL scheme: {url}")
            
            response = self.session.post(
                url,
                data=data,
                json=json,
                headers=headers,
                timeout=self.timeout,
                verify=True,  # Always verify SSL
                **kwargs
            )
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP POST request failed for {url}: {e}")
            raise
    
    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

# Global instance for convenience
_default_client = None

def get_default_client() -> SecureHTTPClient:
    """Get the default HTTP client instance."""
    global _default_client
    if _default_client is None:
        _default_client = SecureHTTPClient()
    return _default_client

def secure_get(url: str, **kwargs) -> requests.Response:
    """Make a secure GET request using the default client."""
    return get_default_client().get(url, **kwargs)

def secure_post(url: str, **kwargs) -> requests.Response:
    """Make a secure POST request using the default client."""
    return get_default_client().post(url, **kwargs)
