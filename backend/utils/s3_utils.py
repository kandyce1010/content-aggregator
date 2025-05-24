#!/usr/bin/env python3
"""
S3 Utilities for Content Aggregator

This module provides utilities for storing and retrieving content from S3.
"""

import os
import json
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class S3Handler:
    """
    A class to handle S3 operations for content storage and retrieval.
    """
    
    def __init__(self, bucket_name=None, region_name=None):
        """
        Initialize the S3 handler.
        
        Args:
            bucket_name (str, optional): S3 bucket name. Defaults to environment variable or 'content-aggregator-data'.
            region_name (str, optional): AWS region name. Defaults to environment variable or 'us-east-1'.
        """
        self.bucket_name = bucket_name or os.environ.get('S3_BUCKET_NAME', 'content-aggregator-data')
        self.region_name = region_name or os.environ.get('AWS_REGION', 'us-east-1')
        
        # Initialize S3 client
        self.s3_client = boto3.client('s3', region_name=self.region_name)
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """
        Ensure the S3 bucket exists, create it if it doesn't.
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket '{self.bucket_name}' exists")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    if self.region_name == 'us-east-1':
                        # Special case for us-east-1
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        # For other regions
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={
                                'LocationConstraint': self.region_name
                            }
                        )
                    logger.info(f"Created S3 bucket '{self.bucket_name}'")
                except ClientError as create_error:
                    logger.error(f"Error creating S3 bucket: {create_error}")
                    raise
            else:
                logger.error(f"Error checking S3 bucket: {e}")
                raise
    
    def store_content(self, content: Any, key: str) -> str:
        """
        Store content in S3.
        
        Args:
            content: Content to store (will be JSON serialized)
            key: S3 object key
            
        Returns:
            str: S3 URI for the stored content
        """
        try:
            # Convert content to JSON string
            content_json = json.dumps(content)
            
            # Store in S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content_json,
                ContentType='application/json'
            )
            
            # Return S3 URI
            s3_uri = f"s3://{self.bucket_name}/{key}"
            logger.info(f"Stored content in S3: {s3_uri}")
            return s3_uri
        except Exception as e:
            logger.error(f"Error storing content in S3: {e}")
            raise
    
    def retrieve_content(self, key: str) -> Any:
        """
        Retrieve content from S3.
        
        Args:
            key: S3 object key or S3 URI
            
        Returns:
            Content retrieved from S3 (JSON deserialized)
        """
        try:
            # Handle S3 URI format
            if key.startswith('s3://'):
                parts = key.replace('s3://', '').split('/', 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else ''
            else:
                bucket = self.bucket_name
            
            # Retrieve from S3
            response = self.s3_client.get_object(
                Bucket=bucket,
                Key=key
            )
            
            # Read and parse JSON content
            content_json = response['Body'].read().decode('utf-8')
            content = json.loads(content_json)
            
            logger.info(f"Retrieved content from S3: s3://{bucket}/{key}")
            return content
        except Exception as e:
            logger.error(f"Error retrieving content from S3: {e}")
            raise
    
    def retrieve_content_from_uri(self, s3_uri: str) -> Any:
        """
        Retrieve content from S3 using an S3 URI.
        
        Args:
            s3_uri: S3 URI (s3://bucket/key)
            
        Returns:
            Content retrieved from S3 (JSON deserialized)
        """
        return self.retrieve_content(s3_uri)
    
    def generate_key(self, prefix: str = 'content', suffix: str = None) -> str:
        """
        Generate a unique S3 key.
        
        Args:
            prefix (str, optional): Key prefix. Defaults to 'content'.
            suffix (str, optional): Key suffix. Defaults to None.
            
        Returns:
            str: Generated S3 key
        """
        import uuid
        from datetime import datetime
        
        # Generate timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Generate unique ID
        unique_id = str(uuid.uuid4())[:8]
        
        # Combine parts
        key = f"{prefix}/{timestamp}_{unique_id}"
        if suffix:
            key = f"{key}_{suffix}"
        
        return key
