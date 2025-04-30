#!/usr/bin/env python3
"""
Lambda Layer Builder

This script creates a Lambda Layer with the required dependencies for the Content Aggregator.
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

def create_layer_package(requirements_file, output_zip):
    """
    Create a Lambda Layer package with the specified requirements.
    
    Args:
        requirements_file (str): Path to the requirements.txt file
        output_zip (str): Path to the output zip file
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Create the python directory structure
        python_dir = os.path.join(temp_dir, 'python')
        os.makedirs(python_dir, exist_ok=True)
        
        # Install the requirements
        cmd = [
            sys.executable, '-m', 'pip', 'install',
            '-r', requirements_file,
            '--target', python_dir,
            '--no-cache-dir'
        ]
        logger.info(f"Installing dependencies: {' '.join(cmd)}")
        subprocess.check_call(cmd)
        
        # Create the zip file
        logger.info(f"Creating zip file: {output_zip}")
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        logger.info(f"Layer package created: {output_zip}")
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

def publish_layer(layer_name, s3_bucket, s3_key, description, runtimes):
    """
    Publish a Lambda Layer.
    
    Args:
        layer_name (str): Name of the layer
        s3_bucket (str): S3 bucket containing the layer package
        s3_key (str): S3 key of the layer package
        description (str): Description of the layer
        runtimes (list): List of compatible runtimes
    """
    cmd = [
        'aws', 'lambda', 'publish-layer-version',
        '--layer-name', layer_name,
        '--content', f'S3Bucket={s3_bucket},S3Key={s3_key}',
        '--description', description,
        '--compatible-runtimes'
    ] + runtimes
    
    logger.info(f"Publishing layer: {' '.join(cmd)}")
    output = subprocess.check_output(cmd)
    logger.info(f"Layer published: {output.decode('utf-8')}")
    return output.decode('utf-8')

def main():
    """
    Main function to create and publish a Lambda Layer.
    """
    parser = argparse.ArgumentParser(description='Create and publish a Lambda Layer')
    parser.add_argument('--requirements', default='aws/layer-requirements.txt', help='Path to requirements.txt file')
    parser.add_argument('--output', default='layer.zip', help='Path to output zip file')
    parser.add_argument('--bucket', default='content-aggregator-lambda-deployment-kanbo', help='S3 bucket name')
    parser.add_argument('--key', default='layer.zip', help='S3 key')
    parser.add_argument('--layer-name', default='content-aggregator-dependencies', help='Layer name')
    parser.add_argument('--description', default='Dependencies for Content Aggregator', help='Layer description')
    parser.add_argument('--runtimes', default=['python3.9'], nargs='+', help='Compatible runtimes')
    
    args = parser.parse_args()
    
    try:
        # Create the layer package
        create_layer_package(args.requirements, args.output)
        
        # Upload to S3
        upload_to_s3(args.output, args.bucket, args.key)
        
        # Publish the layer
        publish_layer(args.layer_name, args.bucket, args.key, args.description, args.runtimes)
        
        logger.info("Layer creation and publishing completed successfully")
    except Exception as e:
        logger.error(f"Error creating or publishing layer: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
