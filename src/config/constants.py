"""
constants.py - Updated application constants for domain-based blocking
"""
from pathlib import Path
import os

# Application Info
APP_NAME = "ZenFlow"
APP_VERSION = "2.1.0"
APP_AUTHOR = "AnassK"

# File Paths
APP_DIR = Path.home() / ".zenflow"
CONFIG_FILE = APP_DIR / "config.json"
LOG_FILE = APP_DIR / "zenflow.log"
DOMAIN_STORE_FILE = APP_DIR / "domain_data.json"

# Timer Settings
DEFAULT_WORK_DURATION = 25  # minutes
DEFAULT_SHORT_BREAK = 5     # minutes
DEFAULT_LONG_BREAK = 15     # minutes
MIN_DURATION = 1
MAX_DURATION = 120
DEFAULT_SESSIONS = 4
MAX_SESSIONS = 12

# Network Configuration
NFQUEUE_NUM = 1
CONNECTION_TIMEOUT = 2  # seconds
DEFAULT_ALLOWED_DOMAINS = [
    "github.com",
    "stackoverflow.com",
    "docs.python.org"
]

# Known TLD Patterns
KNOWN_TLDS = {
    'co.uk', 'com.au', 'co.jp', 'co.nz', 
    'co.za', 'com.br', 'com.mx', 'org.uk', 
    'net.au', 'gov.uk', 'edu.au'
}

# Common Third-party Service Domains
COMMON_SERVICES = [
    # CDNs and Content Delivery
    'cloudfront.net',
    'akamai.net',
    'cloudflare.com',
    'fastly.net',
    'jsdelivr.net',
    'unpkg.com',
    
    # Google Services
    'googleapis.com',
    'gstatic.com',
    'google-analytics.com',
    'doubleclick.net',
    'ggpht.com',
    
    # Social Media and Tracking
    'facebook.com',
    'fbcdn.net',
    'twitter.com',
    'linkedin.com',
    
    # Other Common Services
    'amazonaws.com',
    'gravatar.com',
    'typekit.net',
    'hotjar.com'
]

# Network Ports
HTTP_PORTS = [80, 8080]
HTTPS_PORTS = [443, 8443]
DNS_PORTS = [53, 5353]  # Standard DNS and mDNS

# Discovery Settings
DISCOVERY_TIMEOUT = 120  # seconds
BROWSER_WAIT_TIMEOUT = 5  # seconds
MAX_DISCOVERY_DOMAINS = 100

# UI Constants
WINDOW_SIZE = "1000x700"
MIN_WINDOW_SIZE = (800, 600)

# UI Colors
COLORS = {
    'primary': '#2563eb',        # Blue
    'secondary': '#4b5563',      # Gray
    'success': '#059669',        # Green
    'warning': '#d97706',        # Orange
    'error': '#dc2626',          # Red
    'background': '#ffffff',     # White
    'surface': '#f3f4f6',        # Light Gray
    'text': '#111827',           # Dark Gray
    'text_secondary': '#6b7280', # Medium Gray
    'subdomain': '#9ca3af'       # Subdomain Text
}

# UI Fonts
FONTS = {
    
    'display': ('Helvetica', 32, 'bold'),
    'title': ('Helvetica', 24, 'bold'),
    'subtitle': ('Helvetica', 18),
    'body': ('Helvetica', 12),
    'small': ('Helvetica', 10)
}

# Tree View Tags and Styles
TREE_TAGS = {
    'main_domain': {
        'foreground': COLORS['primary'],
        'font': FONTS['body']
    },
    'subdomain': {
        'foreground': COLORS['subdomain'],
        'font': FONTS['small']
    },
    'discovered': {
        'foreground': COLORS['success'],
        'font': FONTS['body']
    }
}

# System Requirements
REQUIRED_COMMANDS = {
    'iptables': 'iptables',
    'python3': 'python3',
    'chrome': 'google-chrome',
    'netfilter': 'python3-netfilter-queue'
}

# Error Messages
ERROR_MESSAGES = {
    'root_required': "Root privileges required for network management",
    'browser_start': "Failed to start browser for domain discovery",
    'discovery_failed': "Failed to discover domains for {}",
    'network_error': "Failed to update network rules: {}",
    'missing_deps': "Missing required dependencies: {}",
    'invalid_domain': "Invalid domain name format",
    'connection_timeout': "Connection timed out while inspecting traffic",
    'max_domains': "Maximum number of domains ({}) reached"
}

# Status Messages
STATUS_MESSAGES = {
    'discovering': "Discovering domains for {}...",
    'discovery_complete': "Domain discovery complete. Found {} domains",
    'blocking_enabled': "Website blocking enabled",
    'blocking_disabled': "Website blocking disabled",
    'domain_allowed': "Domain {} and its subdomains are now allowed",
    'domain_removed': "Domain {} has been removed from allowed list",
    'subdomain_found': "Found subdomain: {}",
    'base_domain_added': "Added base domain: {}"
}

# Regex Patterns
DOMAIN_PATTERN = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
IP_PATTERN = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'

# Save File Structure
SAVE_FILE_VERSION = 1
SAVE_FILE_SCHEMA = {
    'version': int,
    'timestamp': str,
    'allowed_domains': list,
    'domain_groups': dict,
    'statistics': dict
}