"""
Enhanced domain management with flexible grouping and discovery relationships
"""
from dataclasses import dataclass, field
from typing import Dict, Set, Optional, List, Tuple
import re
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

@dataclass
class DomainNode:
    """Represents a domain with its hierarchy"""
    domain: str
    is_discovered: bool = False
    discovery_source: Optional[str] = None
    discovered_domains: Set[str] = field(default_factory=set)
    
    @property
    def base_domain(self) -> str:
        """Get base domain"""
        parts = self.domain.split('.')
        if len(parts) > 2:
            return '.'.join(parts[-2:])
        return self.domain
        
    def is_subdomain(self) -> bool:
        """Check if this is a subdomain"""
        return len(self.domain.split('.')) > 2
        
    def is_related_to(self, other_domain: str) -> bool:
        """Check if domain is related to another domain"""
        return self.domain.endswith('.' + other_domain) or other_domain.endswith('.' + self.domain)

class DomainManager:
    """Manages domain hierarchy and relationships with flexible grouping"""
    
    def __init__(self):
        self.domains: Dict[str, DomainNode] = {}  # All domains
        self.grouped_state: bool = False  # Whether domains are currently grouped
        self.allowed_bases: Set[str] = set()  # Base domains that are explicitly allowed
        
    def add_domain(self, domain: str) -> Optional[DomainNode]:
        """Add a domain at top level"""
        domain = domain.strip().lower()
        if not self._validate_domain(domain):
            return None
            
        if domain not in self.domains:
            self.domains[domain] = DomainNode(domain=domain)
            
        return self.domains[domain]
    
    def remove_domain(self, domain: str) -> Set[str]:
        """Remove a domain and its discovered/nested domains"""
        try:
            domain = domain.strip().lower()
            removed = set()
            logger.info(f"Starting removal of domain: {domain}")
            
            # Handle removal when domain exists
            if domain in self.domains:
                node = self.domains[domain]
                removed.add(domain)
                logger.info(f"Removing domain {domain} with discovered domains: {node.discovered_domains}")
                
                # Remove all discovered domains
                for discovered in list(node.discovered_domains):
                    if discovered in self.domains:
                        logger.info(f"Removing discovered domain: {discovered}")
                        removed.add(discovered)
                        del self.domains[discovered]
                
                # If we're in grouped mode and this is a base domain or part of a group
                if self.grouped_state:
                    base = node.base_domain
                    logger.info(f"In grouped mode, base domain: {base}")
                    if domain == base:  # This is a base domain
                        for d in list(self.domains.keys()):
                            if d == base or (d in self.domains and self.domains[d].base_domain == base):
                                if d in self.domains:
                                    logger.info(f"Removing grouped domain: {d}")
                                    removed.add(d)
                                    del self.domains[d]
                
                # Remove from other domains' discovered lists
                for other_domain, other_node in list(self.domains.items()):
                    if domain in other_node.discovered_domains:
                        logger.info(f"Removing {domain} from {other_domain}'s discovered list")
                        other_node.discovered_domains.discard(domain)
                
                # Finally remove the node itself
                del self.domains[domain]
                logger.info(f"Successfully removed domain {domain} and related: {removed}")
            else:
                logger.warning(f"Domain {domain} not found in domains dict")
            
            if domain in self.domains:
                del self.domains[domain]
                logger.info(f"Successfully removed domain {domain} and related: {removed}")
            else:
                logger.warning(f"Domain {domain} not found when attempting final deletion")
            
            return removed
            
        except Exception as e:
            logger.error(f"Error in remove_domain: {str(e)}")
            raise
    
    def add_discovered_domains(self, source_domain: str, discovered: Set[str]) -> None:
        if source_domain not in self.domains:
            return
            
        source_node = self.domains[source_domain]
        
        for domain in discovered:
            if domain == source_domain:  # Prevent adding self to discovered domains
                continue
            if self._validate_domain(domain):
                # Add as a discovered domain
                if domain not in self.domains:
                    self.domains[domain] = DomainNode(
                        domain=domain,
                        is_discovered=True,
                        discovery_source=source_domain
                    )
                # Add to source's discovered list
                source_node.discovered_domains.add(domain)
    
    def group_by_base_domains(self) -> Dict[str, Set[str]]:
        """Group domains by their base domains"""
        groups: Dict[str, Set[str]] = {}
        
        # First pass: collect all base domains
        for domain in self.domains.keys():
            node = self.domains[domain]
            base = node.base_domain
            if base not in groups:
                groups[base] = set()
            groups[base].add(domain)
            
        # Add base domains to allowed list
        self.allowed_bases.update(groups.keys())
            
        return groups
    
    def ungroup_domains(self) -> None:
        """Remove grouping"""
        self.grouped_state = False
        self.allowed_bases.clear()
    
    def get_display_hierarchy(self) -> List[dict]:
        """
        Get domain hierarchy for display
        Returns list of dicts with structure info
        """
        if not self.grouped_state:
            # Ungrouped display - show discovery relationships
            hierarchy = []
            for domain, node in sorted(self.domains.items()):
                # Skip if this is a discovered domain that will be shown under its source
                if node.is_discovered and node.discovery_source in self.domains:
                    continue
                    
                domain_info = {
                    'domain': domain,
                    'is_discovered': node.is_discovered,
                    'discovery_source': node.discovery_source,
                    'children': sorted(node.discovered_domains)
                }
                hierarchy.append(domain_info)
            return hierarchy
            
        else:
            # Grouped display - show base domain groups
            groups = self.group_by_base_domains()
            hierarchy = []
            
            for base_domain, related in sorted(groups.items()):
                # Create list of child domains, excluding base domain if it exists
                children = []
                base_exists = base_domain in self.domains
                
                for domain in sorted(related):
                    # Skip adding base domain as a child if it exists as its own entry
                    if domain == base_domain and base_exists:
                        continue
                        
                    children.append({
                        'domain': domain,
                        'is_discovered': self.domains[domain].is_discovered,
                        'discovery_source': self.domains[domain].discovery_source,
                        'is_base': domain == base_domain
                    })
                
                # Only create group if there are children or if base doesn't exist
                if children or not base_exists:
                    group_info = {
                        'domain': base_domain,
                        'is_base_group': True,
                        'children': children
                    }
                    hierarchy.append(group_info)
                else:
                    # If base exists and no other domains, show it as regular domain
                    hierarchy.append({
                        'domain': base_domain,
                        'is_discovered': self.domains[base_domain].is_discovered,
                        'discovery_source': self.domains[base_domain].discovery_source,
                        'children': []
                    })
                
            return hierarchy
    
    def get_all_domains(self) -> Set[str]:
        """Get all domains"""
        return set(self.domains.keys())
    
    def get_allowed_domains(self) -> Set[str]:
        """Get domains that should be allowed"""
        allowed = set(self.domains.keys())  # Start with all domains
        if self.grouped_state:
            allowed.update(self.allowed_bases)  # Add explicitly allowed base domains
        return allowed
    
    def _validate_domain(self, domain: str) -> bool:
        """Validate domain name format"""
        if not domain or len(domain) > 255:
            return False
            
        try:
            parts = domain.split('.')
            if len(parts) < 2:
                return False
                
            return all(
                part and len(part) <= 63 and
                re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', part)
                for part in parts
            )
        except:
            return False