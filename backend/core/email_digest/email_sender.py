#!/usr/bin/env python3
"""
Email Sender Module

This module handles sending email digests using Amazon SES.
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmailSender:
    """
    Sends email digests via Amazon SES.

    Requires:
    - FROM_EMAIL env var set to a SES-verified sender address
    - The recipient address must also be verified if the account is in SES sandbox mode
    """

    def __init__(self, region_name: str = 'us-east-1', profile_name: str = None):
        if profile_name:
            session = boto3.Session(profile_name=profile_name, region_name=region_name)
            self.ses = session.client('ses')
        else:
            self.ses = boto3.client('ses', region_name=region_name)
        self.from_email = os.environ.get('FROM_EMAIL', '')

    def send_digest(self, email_address: str, subject: str, html_content: str) -> Dict[str, Any]:
        """
        Send an HTML digest to an email address via SES.

        Args:
            email_address: Recipient email address
            subject: Email subject line
            html_content: Full HTML body of the email

        Returns:
            SES send_email response dict
        """
        if not self.from_email:
            raise ValueError("FROM_EMAIL environment variable must be set to a SES-verified address")

        try:
            response = self.ses.send_email(
                Source=self.from_email,
                Destination={'ToAddresses': [email_address]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Html': {'Data': html_content, 'Charset': 'UTF-8'},
                        'Text': {
                            'Data': 'Please view this email in an HTML-capable client.',
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )
            logger.info(f"Digest sent via SES: {response['MessageId']}")
            return response
        except ClientError as e:
            logger.error(f"SES error sending to {email_address}: {e}")
            raise
