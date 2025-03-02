"""
Input validation utilities for ZenFlow application.
"""

import re
from typing import List, Optional
from ..config.constants import MIN_DURATION, MAX_DURATION, MAX_SESSIONS

def validate_duration(value: int) -> bool:
    """
    Validate timer duration value
    
    Args:
        value: Duration in minutes
        
    Returns:
        bool: True if valid
    """
    return MIN_DURATION <= value <= MAX_DURATION

def validate_sessions(value: int) -> bool:
    """
    Validate number of sessions
    
    Args:
        value: Number of sessions
        
    Returns:
        bool: True if valid
    """
    return 1 <= value <= MAX_SESSIONS

def validate_website(domain: str) -> bool:
    """
    Validate website domain format
    
    Args:
        domain: Website domain name
        
    Returns:
        bool: True if valid
    """
    pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    return bool(re.match(pattern, domain))

def validate_website_list(domains: List[str]) -> List[str]:
    """
    Validate and clean website list
    
    Args:
        domains: List of domain names
        
    Returns:
        List of valid domains
    """
    valid_domains = []
    for domain in domains:
        domain = domain.strip().lower()
        # Remove http(s):// if present
        domain = re.sub(r'^https?://', '', domain)
        # Remove trailing slashes
        domain = domain.rstrip('/')
        
        if validate_website(domain):
            valid_domains.append(domain)
            
    return valid_domains

def validate_path(path: str) -> bool:
    """
    Validate file path format
    
    Args:
        path: File path
        
    Returns:
        bool: True if valid
    """
    import os
    try:
        # Check if parent directory exists
        parent = os.path.dirname(os.path.abspath(path))
        return os.path.exists(parent)
    except:
        return False

def validate_positive_int(value: str) -> Optional[int]:
    """
    Validate and convert string to positive integer
    
    Args:
        value: String value
        
    Returns:
        int if valid, None otherwise
    """
    try:
        num = int(value)
        return num if num > 0 else None
    except ValueError:
        return None

def validate_percentage(value: float) -> bool:
    """
    Validate percentage value
    
    Args:
        value: Percentage value
        
    Returns:
        bool: True if valid
    """
    return 0 <= value <= 100