"""Input validation utilities for Content Aggregator."""

import re
import os
from typing import Any, Optional
from email.utils import parseaddr

class ValidationError(Exception):
    """Raised when input validation fails."""
    pass

def validate_email_address(email: str) -> str:
    """Validate email address format."""
    if not email or not isinstance(email, str):
        raise ValidationError("Email address is required")
    
    email = email.strip()
    if len(email) > 254:  # RFC 5321 limit
        raise ValidationError("Email address too long")
    
    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError(f"Invalid email address format: {email}")
    
    return email

def validate_days(days: Any) -> int:
    """Validate days parameter."""
    if not isinstance(days, (int, str)):
        raise ValidationError("Days must be a number")
    
    try:
        days_int = int(days)
    except ValueError:
        raise ValidationError("Days must be a valid integer")
    
    if not 1 <= days_int <= 365:
        raise ValidationError("Days must be between 1 and 365")
    
    return days_int

def validate_max_items(max_items: Any) -> int:
    """Validate max_items parameter."""
    if not isinstance(max_items, (int, str)):
        raise ValidationError("Max items must be a number")
    
    try:
        max_items_int = int(max_items)
    except ValueError:
        raise ValidationError("Max items must be a valid integer")
    
    if not 1 <= max_items_int <= 100:
        raise ValidationError("Max items must be between 1 and 100")
    
    return max_items_int

def validate_batch_size(batch_size: Any) -> int:
    """Validate batch_size parameter."""
    if not isinstance(batch_size, (int, str)):
        raise ValidationError("Batch size must be a number")
    
    try:
        batch_size_int = int(batch_size)
    except ValueError:
        raise ValidationError("Batch size must be a valid integer")
    
    if not 1 <= batch_size_int <= 50:
        raise ValidationError("Batch size must be between 1 and 50")
    
    return batch_size_int

def validate_environment_variables():
    """Validate required environment variables are set."""
    required_vars = []
    optional_vars = {
        'GITHUB_TOKEN': 'GitHub API access will be limited without token',
        'YOUTUBE_API_KEY': 'YouTube content fetching will be disabled',
    }
    
    missing_required = [var for var in required_vars if not os.environ.get(var)]
    if missing_required:
        raise ValidationError(f"Missing required environment variables: {', '.join(missing_required)}")
    
    warnings = []
    for var, warning in optional_vars.items():
        if not os.environ.get(var):
            warnings.append(f"{var}: {warning}")
    
    return warnings

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    if not filename:
        raise ValidationError("Filename cannot be empty")
    
    # Remove path separators and dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.replace('..', '_')
    
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename
