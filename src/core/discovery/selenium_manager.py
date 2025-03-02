"""
selenium_manager.py - Enhanced domain discovery with configurable capture filters
"""

import logging
from typing import Set, Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import subprocess
from urllib.parse import urlparse
import json
import time
import threading
from dataclasses import dataclass
from ...config.constants import DISCOVERY_TIMEOUT

logger = logging.getLogger(__name__)

def get_chromium_version():
    """Get the installed Chromium version"""
    try:
        result = subprocess.run(['chromium-browser', '--version'], capture_output=True, text=True)
        version = result.stdout.strip().split()[-1]  # Get the last word which should be the version
        return version
    except Exception as e:
        logger.warning(f"Could not determine Chromium version: {e}")
        return None

@dataclass
class CaptureFilters:
    """Configuration for domain capture filters"""
    capture_all_resources: bool = True  
    capture_subdomains: bool = False
    capture_cdn: bool = False
    enhanced_discovery: bool = False

class ResourceDiscovery:
    """Discovers domains and their relationships during browsing"""
    
    def __init__(self):
        self.driver = None
        self.is_capturing = False
        self.capture_thread = None
        self.domains: Set[str] = set()
        self.main_domain: Optional[str] = None
        self.domain_relationships: Dict[str, Set[str]] = {}
        self.filters = CaptureFilters()

    def set_capture_filters(self, filters: CaptureFilters):
        """Update capture filters"""
        self.filters = filters

    def _extract_base_domain(self, domain: str) -> str:
        """Extract base domain from a domain name"""
        if not domain:
            return ""
            
        parts = domain.split('.')
        if len(parts) > 2:
            # Check for multi-part TLDs
            if len(parts[-2]) <= 3 and len(parts[-1]) <= 3:
                if len(parts) > 3:
                    return '.'.join(parts[-3:])
            return '.'.join(parts[-2:])
        return domain

    def _is_related_domain(self, domain: str, base_domain: str) -> bool:
        """Check if domain is related to base domain"""
        if not domain or not base_domain:
            return False
            
        domain = domain.lower()
        base_domain = base_domain.lower()
        
        # Direct match
        if domain == base_domain:
            return True
            
        # Subdomain relationship
        if self.filters.capture_subdomains and domain.endswith('.' + base_domain):
            return True
            
        # Check for common base domain
        return self._extract_base_domain(domain) == self._extract_base_domain(base_domain)

    def _should_track_domain(self, domain: str) -> bool:
        """Determine if domain should be tracked based on filters"""
        if not domain or len(domain) < 3:
            return False

        domain = domain.lower()
        
        # Skip invalid domains
        if domain in ('localhost', '127.0.0.1') or domain.endswith(('.local', '.test')):
            return False
            
        # Always track main domain
        if domain == self.main_domain:
            return True

        # Filter based on capture settings
        if self.filters.capture_all_resources:
            return True
            
        if self.filters.capture_subdomains and self.main_domain:
            if domain.endswith('.' + self.main_domain):
                return True

        if self.filters.capture_cdn:
            if self._is_cdn_resource(domain):
                return True

        if self.filters.enhanced_discovery:
            if self._is_related_resource(domain):
                return True

        return self._is_related_domain(domain, self.main_domain)

    def _is_cdn_resource(self, domain: str) -> bool:
        """Check if domain is a CDN resource"""
        cdn_indicators = {'.cdn.', '.cache.', '.static.', '.assets.', 
                         '.content.', '.media.', '.images.', '.files.'}
        return any(indicator in domain.lower() for indicator in cdn_indicators)

    def _is_related_resource(self, domain: str) -> bool:
        """Check if domain is a related resource"""
        if not self.main_domain:
            return False
            
        main_parts = self.main_domain.split('.')
        domain_parts = domain.split('.')
        
        # Check for partial domain matches
        return any(part in domain_parts for part in main_parts)

    def start_interactive_discovery(self, url: str) -> Set[str]:
        """Start interactive browser session for domain discovery"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--start-maximized')
            chrome_options.binary_location = '/usr/bin/chromium-browser'  # Specify Chromium binary
            
            # Enhanced logging based on filters
            logging_prefs = {
                'performance': 'ALL',
                'browser': 'ALL',
                'network': 'ALL'
            }
            chrome_options.set_capability('goog:loggingPrefs', logging_prefs)
            
            if self.filters.enhanced_discovery:
                chrome_options.add_experimental_option('perfLoggingPrefs', {
                    'enableNetwork': True,
                    'enablePage': True,
                    'traceCategories': 'browser,devtools.timeline,devtools'
                })

            # Get installed Chromium version
            chromium_version = get_chromium_version()
            
            # Use webdriver_manager to handle ChromeDriver installation for Chromium
            driver_manager = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM)
            if chromium_version:
                driver_manager.driver_version = chromium_version
            
            service = Service(driver_manager.install())
            
            logger.info(f"Starting domain discovery for {url}")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            # Reset state
            self.domains.clear()
            self.domain_relationships.clear()
            
            # Set main domain
            self.main_domain = urlparse(url).netloc.lower()
            if self._should_track_domain(self.main_domain):
                self.domains.add(self.main_domain)
                self.domain_relationships[self.main_domain] = set()
            
            # Start capture
            self.is_capturing = True
            self.capture_thread = threading.Thread(target=self._capture_domains)
            self.capture_thread.daemon = True
            self.capture_thread.start()

            # Open URL and wait
            self.driver.get(url)
            start_time = time.time()
            
            while self.driver and self.driver.window_handles:
                if time.time() - start_time > DISCOVERY_TIMEOUT:
                    logger.info("Discovery timeout reached")
                    break
                time.sleep(0.5)

            return self._get_organized_domains()

        except Exception as e:
            logger.error(f"Error during discovery: {e}")
            return self.domains
        finally:
            self.stop_discovery()

    def _capture_domains(self):
        """Capture domains from network traffic"""
        while self.is_capturing:
            try:
                if not self.driver or not self.driver.window_handles:
                    break

                logs = self.driver.get_log('performance')
                for entry in logs:
                    try:
                        message = json.loads(entry['message'])
                        message = message.get('message', {})
                        params = message.get('params', {})
                        
                        # Process network requests
                        self._process_network_entry(params)

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        logger.debug(f"Error processing log entry: {e}")

                time.sleep(0.1)

            except Exception as e:
                if "disconnected" not in str(e):
                    logger.debug(f"Capture error: {e}")
                break

    def _process_network_entry(self, params):
        """Process network entries based on capture filters"""
        try:
            urls = []
            
            # Request URL
            if 'request' in params:
                request_url = params['request'].get('url')
                if request_url:
                    urls.append(request_url)
            
            # Response URL
            if 'response' in params:
                response_url = params['response'].get('url')
                if response_url:
                    urls.append(response_url)
            
            # Document URL
            doc_url = params.get('documentURL')
            if doc_url:
                urls.append(doc_url)

            # Additional resources if enabled
            if self.filters.enhanced_discovery or self.filters.capture_all_resources:
                if 'initiator' in params:
                    initiator_url = params['initiator'].get('url')
                    if initiator_url:
                        urls.append(initiator_url)

            # Process discovered URLs
            for url in urls:
                try:
                    domain = urlparse(url).netloc.lower()
                    if self._should_track_domain(domain):
                        self.domains.add(domain)
                        
                        # Track relationship with main domain
                        if self.main_domain and self._is_related_domain(domain, self.main_domain):
                            if self.main_domain not in self.domain_relationships:
                                self.domain_relationships[self.main_domain] = set()
                            self.domain_relationships[self.main_domain].add(domain)
                        
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"Error processing network entry: {e}")

    def _get_organized_domains(self) -> Set[str]:
        """Get organized set of discovered domains"""
        organized = set()
        
        # Add main domain and related domains
        if self.main_domain and self.main_domain in self.domain_relationships:
            organized.add(self.main_domain)
            organized.update(self.domain_relationships[self.main_domain])
        
        # Add other discovered domains based on filters
        for domain in self.domains:
            if self._should_track_domain(domain):
                if self.filters.capture_all_resources:
                    organized.add(domain)
                elif self.filters.capture_cdn and self._is_cdn_resource(domain):
                    organized.add(domain)
                elif domain == self.main_domain or \
                     (self.main_domain and self._is_related_domain(domain, self.main_domain)):
                    organized.add(domain)
        
        return organized

    def stop_discovery(self):
        """Stop the discovery process"""
        self.is_capturing = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2)

        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.debug(f"Error closing driver: {e}")
            finally:
                self.driver = None

    def get_domain_relationships(self) -> Dict[str, Set[str]]:
        """Get discovered domain relationships"""
        return self.domain_relationships.copy()