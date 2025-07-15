#!/usr/bin/env python3
"""
Lambda Deployment Script

This script packages and deploys the Content Aggregator Lambda function.

DEPRECATED: This script is deprecated in favor of the unified deploy-all.sh script.
Please use ./aws/deploy-all.sh instead for all deployments.
"""

import os
import sys
import subprocess
import tempfile
import shutil
import zipfile
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_lambda_package(output_zip):
    """
    Create a Lambda deployment package.
    
    Args:
        output_zip (str): Path to the output zip file
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Create the zip file
        logger.info(f"Creating zip file: {output_zip}")
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add the aws directory
            aws_dir = os.path.join(project_root, 'aws')
            for root, dirs, files in os.walk(aws_dir):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, project_root)
                        zipf.write(file_path, arcname)
            
            # Add the backend directory
            backend_dir = os.path.join(project_root, 'backend')
            for root, dirs, files in os.walk(backend_dir):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, project_root)
                        zipf.write(file_path, arcname)
        
        logger.info(f"Lambda package created: {output_zip}")
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

def upload_to_s3(zip_file, bucket, key):
    """
    Upload the zip file to S3.
    
    Args:
        zip_file (str): Path to the zip file
        bucket (str): S3 bucket name
        key (str): S3 key
    """
    cmd = [
        'aws', 's3', 'cp',
        zip_file,
        f's3://{bucket}/{key}'
    ]
    logger.info(f"Uploading to S3: {' '.join(cmd)}")
    subprocess.check_call(cmd)
    logger.info(f"Uploaded to s3://{bucket}/{key}")

def update_lambda_function(function_name, s3_bucket, s3_key):
    """
    Update a Lambda function.
    
    Args:
        function_name (str): Name of the function
        s3_bucket (str): S3 bucket containing the deployment package
        s3_key (str): S3 key of the deployment package
    """
    cmd = [
        'aws', 'lambda', 'update-function-code',
        '--function-name', function_name,
        '--s3-bucket', s3_bucket,
        '--s3-key', s3_key,
        '--publish'
    ]
    
    logger.info(f"Updating Lambda function: {' '.join(cmd)}")
    output = subprocess.check_output(cmd)
    logger.info(f"Lambda function updated: {output.decode('utf-8')}")
    return output.decode('utf-8')

def main():
    """
    Main function to create and deploy a Lambda function.
    """
    parser = argparse.ArgumentParser(description='Create and deploy a Lambda function')
    parser.add_argument('--output', default='content-aggregator.zip', help='Path to output zip file')
    parser.add_argument('--bucket', default='content-aggregator-lambda-deployment-kanbo', help='S3 bucket name')
    parser.add_argument('--key', default='content-aggregator.zip', help='S3 key')
    parser.add_argument('--function-name', default='content-aggregator', help='Lambda function name')
    
    args = parser.parse_args()
    
    try:
        # Create the Lambda package
        create_lambda_package(args.output)
        
        # Upload to S3
        upload_to_s3(args.output, args.bucket, args.key)
        
        # Update the Lambda function
        update_lambda_function(args.function_name, args.bucket, args.key)
        
        logger.info("Lambda deployment completed successfully")
    except Exception as e:
        logger.error(f"Error deploying Lambda function: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
