"""
resource_store.py - Manages storage of discovered website resources
"""
import json
from pathlib import Path
from typing import Dict, List, Set
import logging

logger = logging.getLogger(__name__)

class ResourceStore:
    def __init__(self, storage_file: str = 'website_resources.json'):
        """Initialize resource storage"""
        self.storage_file = Path(storage_file)
        self.resources = self._load_resources()
        
    def _load_resources(self) -> Dict:
        """Load resources from storage file"""
        try:
            if self.storage_file.exists():
                with open(self.storage_file, 'r') as f:
                    # Convert sets from lists in stored JSON
                    data = json.load(f)
                    return {
                        domain: {
                            category: set(resources)
                            for category, resources in details.items()
                        }
                        for domain, details in data.items()
                    }
            return {}
        except Exception as e:
            logger.error(f"Error loading resources: {e}")
            return {}
            
    def save_resources(self):
        """Save resources to storage file"""
        try:
            # Convert sets to lists for JSON serialization
            data = {
                domain: {
                    category: list(resources)
                    for category, resources in details.items()
                }
                for domain, details in self.resources.items()
            }
            
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=4)
                
        except Exception as e:
            logger.error(f"Error saving resources: {e}")
            
    def add_website_resources(self, domain: str, resources: Dict[str, Set[str]]):
        """
        Add or update resources for a website
        
        Args:
            domain: Main website domain
            resources: Dictionary of categorized resources
        """
        self.resources[domain] = resources
        self.save_resources()
        
    def get_website_resources(self, domain: str) -> Dict[str, Set[str]]:
        """Get resources for a specific website"""
        return self.resources.get(domain, {})
        
    def get_all_domains(self, domain: str) -> Set[str]:
        """Get all domains associated with a website"""
        resources = self.get_website_resources(domain)
        all_domains = set()
        for category in resources.values():
            all_domains.update(category)
        return all_domains
        
    def remove_website(self, domain: str):
        """Remove a website and its resources"""
        if domain in self.resources:
            del self.resources[domain]
            self.save_resources()