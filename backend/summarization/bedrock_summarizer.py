#!/usr/bin/env python3
"""
Amazon Bedrock Summarizer

This module provides functionality to summarize content using Amazon Bedrock.
"""

import os
import json
import logging
import time
import hashlib
import concurrent.futures
import requests
from typing import Dict, List, Any, Optional, Union
import boto3
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BedrockSummarizer:
    """
    A class to summarize content using Amazon Bedrock.
    """
    
    def __init__(self, 
                region_name: str = 'us-east-1', 
                model_id: str = 'anthropic.claude-v2', 
                max_tokens: int = 300,
                temperature: float = 0.2,
                profile_name: Optional[str] = None):
        """
        Initialize the Bedrock summarizer with AWS credentials.
        
        Args:
            region_name (str): AWS region name.
            model_id (str): Bedrock model ID to use for summarization.
            max_tokens (int): Maximum number of tokens to generate.
            temperature (float): Temperature for text generation (0.0-1.0).
            profile_name (str, optional): AWS profile name.
        """
        self.region_name = region_name
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Initialize AWS session
        session_kwargs = {'region_name': region_name}
        if profile_name:
            session_kwargs['profile_name'] = profile_name
            
        self.session = boto3.Session(**session_kwargs)
        self.bedrock_runtime = self.session.client(
            service_name='bedrock-runtime',
            region_name=region_name
        )
        
        # Set up cache directory
        self.cache_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '..', 'data', 'summary_cache'
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Load cache if it exists
        self.cache_file = os.path.join(self.cache_dir, 'summary_cache.json')
        self.cache = self._load_cache()
        
        logger.info(f"Initialized Bedrock summarizer with model {model_id}")
    
    def _load_cache(self) -> Dict[str, Any]:
        """
        Load the summary cache from disk.
        
        Returns:
            dict: The summary cache.
        """
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading summary cache: {e}")
                return {}
        return {}
    
    def _save_cache(self) -> None:
        """
        Save the summary cache to disk.
        """
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving summary cache: {e}")
    
    def _get_content_hash(self, content: str) -> str:
        """
        Generate a hash for the content to use as a cache key.
        
        Args:
            content (str): Content to hash.
            
        Returns:
            str: Hash of the content.
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_prompt_for_content(self, content: str, max_length: int = 150) -> str:
        """
        Generate a prompt for summarizing the given content.
        
        Args:
            content (str): Content to summarize.
            max_length (int): Target length of summary in characters.
            
        Returns:
            str: Prompt for the model.
        """
        # For Claude models
        if self.model_id.startswith('anthropic.claude'):
            prompt = f"""Human: Please summarize the following content in about {max_length//10}-{max_length//5} words. Focus on the main points and key takeaways:
            
            {content}
            
            Assistant:"""
            return prompt
        
        # For Titan models
        elif self.model_id.startswith('amazon.titan'):
            prompt = f"""Summarize the following content in about {max_length//10}-{max_length//5} words. Focus on the main points and key takeaways:
            
            {content}"""
            return prompt
        
        # Default prompt format
        else:
            prompt = f"""Summarize the following content in about {max_length//10}-{max_length//5} words:
            
            {content}"""
            return prompt
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """
        Extract plain text from HTML content.
        
        Args:
            html_content (str): HTML content.
            
        Returns:
            str: Plain text extracted from HTML.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            # Get text
            text = soup.get_text(separator=' ', strip=True)
            # Remove extra whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            return text
        except Exception as e:
            logger.error(f"Error extracting text from HTML: {e}")
            return html_content
    
    def _prepare_content_for_summarization(self, content: str, max_length: int = 8000) -> str:
        """
        Prepare content for summarization by extracting text and truncating if needed.
        
        Args:
            content (str): Content to prepare.
            max_length (int): Maximum length of content to summarize.
            
        Returns:
            str: Prepared content.
        """
        # Check if content is HTML
        if content.strip().startswith('<') and '>' in content:
            content = self._extract_text_from_html(content)
        
        # Truncate if too long
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        return content
    
    def _invoke_bedrock_model(self, prompt: str) -> str:
        """
        Invoke the Bedrock model to generate a summary.
        
        Args:
            prompt (str): Prompt for the model.
            
        Returns:
            str: Generated summary.
        """
        try:
            # Add exponential backoff retry logic
            max_retries = 5
            base_delay = 1  # Start with 1 second delay
            
            for attempt in range(max_retries):
                try:
                    # Prepare request body based on model
                    if self.model_id.startswith('anthropic.claude'):
                        request_body = {
                            "prompt": prompt,
                            "max_tokens_to_sample": self.max_tokens,
                            "temperature": self.temperature,
                            "anthropic_version": "bedrock-2023-05-31"
                        }
                    elif self.model_id.startswith('amazon.titan'):
                        request_body = {
                            "inputText": prompt,
                            "textGenerationConfig": {
                                "maxTokenCount": self.max_tokens,
                                "temperature": self.temperature,
                                "topP": 0.9
                            }
                        }
                    else:
                        # Generic format for other models
                        request_body = {
                            "prompt": prompt,
                            "max_tokens": self.max_tokens,
                            "temperature": self.temperature
                        }
                    
                    # Invoke the model
                    response = self.bedrock_runtime.invoke_model(
                        modelId=self.model_id,
                        body=json.dumps(request_body)
                    )
                    
                    # Parse the response
                    response_body = json.loads(response['body'].read().decode('utf-8'))
                    
                    # Extract the generated text based on model
                    if self.model_id.startswith('anthropic.claude'):
                        summary = response_body.get('completion', '').strip()
                    elif self.model_id.startswith('amazon.titan'):
                        summary = response_body.get('results', [{}])[0].get('outputText', '').strip()
                    else:
                        # Generic extraction for other models
                        summary = response_body.get('generated_text', '').strip()
                    
                    return summary
                    
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code')
                    
                    # If it's a throttling exception, retry with backoff
                    if error_code == 'ThrottlingException' and attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Bedrock API throttled. Retrying in {delay} seconds (attempt {attempt+1}/{max_retries})")
                        time.sleep(delay)
                    else:
                        # For other errors or if we've exhausted retries, re-raise
                        raise
        
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            error_message = e.response.get('Error', {}).get('Message')
            logger.error(f"Bedrock API error: {error_code} - {error_message}")
            raise
        except Exception as e:
            logger.error(f"Error invoking Bedrock model: {e}")
            raise
    
    def summarize_content(self, content: str, max_length: int = 150) -> str:
        """
        Summarize the given content using Amazon Bedrock.
        
        Args:
            content (str): Content to summarize.
            max_length (int): Target length of summary in characters.
            
        Returns:
            str: Generated summary.
        """
        if not content or len(content.strip()) < 100:
            logger.warning("Content too short for summarization")
            return content
        
        # Generate a hash for the content
        content_hash = self._get_content_hash(content)
        
        # Check if we have a cached summary
        if content_hash in self.cache:
            logger.info("Using cached summary")
            return self.cache[content_hash]
        
        # Prepare content for summarization
        prepared_content = self._prepare_content_for_summarization(content)
        
        # Generate prompt
        prompt = self._get_prompt_for_content(prepared_content, max_length)
        
        try:
            # Invoke the model
            summary = self._invoke_bedrock_model(prompt)
            
            # Cache the summary
            self.cache[content_hash] = summary
            self._save_cache()
            
            return summary
        
        except Exception as e:
            logger.error(f"Error summarizing content: {e}")
            return content[:max_length] + "..."
    
    def summarize_url_content(self, url: str, max_length: int = 150) -> str:
        """
        Fetch content from a URL and summarize it.
        
        Args:
            url (str): URL to fetch and summarize.
            max_length (int): Target length of summary in characters.
            
        Returns:
            str: Generated summary.
        """
        try:
            # Generate a hash for the URL
            url_hash = self._get_content_hash(url)
            
            # Check if we have a cached summary
            if url_hash in self.cache:
                logger.info(f"Using cached summary for URL: {url}")
                return self.cache[url_hash]
            
            # Fetch the content
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Extract text from HTML
            content = self._extract_text_from_html(response.text)
            
            # Summarize the content
            summary = self.summarize_content(content, max_length)
            
            # Cache the summary
            self.cache[url_hash] = summary
            self._save_cache()
            
            return summary
        
        except Exception as e:
            logger.error(f"Error summarizing URL content: {e}")
            return f"Failed to summarize content from {url}: {str(e)}"
    
    def batch_summarize(self, items: List[Dict[str, Any]], 
                       content_key: str = 'summary', 
                       url_key: str = 'link',
                       max_workers: int = 1) -> List[Dict[str, Any]]:
        """
        Batch summarize content items.
        
        Args:
            items (list): List of content items to summarize.
            content_key (str): Key for the content to summarize.
            url_key (str): Key for the URL to fetch content from if content is not available.
            max_workers (int): Maximum number of concurrent workers.
            
        Returns:
            list: List of content items with summaries.
        """
        logger.info(f"Batch summarizing {len(items)} items")
        
        # Create a copy of the items to avoid modifying the original
        summarized_items = items.copy()
        
        # Use ThreadPoolExecutor for parallel summarization
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a list to store futures
            future_to_index = {}
            
            # Submit summarization tasks
            for i, item in enumerate(summarized_items):
                # Skip if already has a generated summary
                if item.get('generated_summary'):
                    continue
                
                # Get content to summarize
                content = item.get(content_key, '')
                url = item.get(url_key, '')
                
                # If content is not available but URL is, submit URL summarization
                if (not content or len(content.strip()) < 100) and url:
                    future = executor.submit(self.summarize_url_content, url)
                # Otherwise, submit content summarization
                elif content and len(content.strip()) >= 100:
                    future = executor.submit(self.summarize_content, content)
                else:
                    # Skip if no content or URL
                    continue
                
                future_to_index[future] = i
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    summary = future.result()
                    summarized_items[index]['generated_summary'] = summary
                    # Add a small delay between processing results to avoid rate limits
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Error in batch summarization: {e}")
        
        logger.info(f"Completed batch summarization of {len(items)} items")
        return summarized_items
