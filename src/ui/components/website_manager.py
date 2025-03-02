"""
Enhanced website manager with flexible domain grouping and discovery
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, List
import logging

from ...config.constants import (
    COLORS, FONTS, TREE_TAGS, ERROR_MESSAGES, STATUS_MESSAGES
)
from ...core.network import NetworkManager
from ...core.discovery.selenium_manager import ResourceDiscovery, CaptureFilters
from .domain_manager import DomainManager

logger = logging.getLogger(__name__)

class WebsiteManagerFrame(ttk.LabelFrame):
    """Website management frame with enhanced domain handling"""
    
    def __init__(
        self,
        parent: tk.Widget,
        network_manager: NetworkManager,
        on_change: Optional[Callable] = None
    ):
        super().__init__(
            parent,
            text="Website Management",
            padding=10
        )
        
        # Initialize managers
        self.network_manager = network_manager
        self.resource_discovery = ResourceDiscovery()
        self.domain_manager = DomainManager()
        self.on_change = on_change
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Create UI
        self._create_ui()
        
    def _create_ui(self):
        """Create the user interface"""
        # Input section
        input_frame = ttk.Frame(self, padding=(0, 0, 0, 10))
        input_frame.grid(row=0, column=0, sticky="ew")
        input_frame.grid_columnconfigure(1, weight=1)
        
        # Domain input
        ttk.Label(
            input_frame, 
            text="Domain:",
            font=FONTS['body']
        ).grid(row=0, column=0, padx=(0, 5))
        
        self.domain_entry = ttk.Entry(input_frame)
        self.domain_entry.grid(row=0, column=1, sticky="ew")
        self.domain_entry.bind('<Return>', lambda e: self._add_domain())
        
        # Action buttons
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=0, column=2, padx=(10, 0))
        
        self.add_btn = ttk.Button(
            btn_frame,
            text="Add",
            command=self._add_domain,
            width=8
        )
        self.add_btn.pack(side=tk.LEFT, padx=2)
        
        self.edit_btn = ttk.Button(
            btn_frame,
            text="Edit",
            command=self._edit_domain,
            width=8,
            state="disabled"
        )
        self.edit_btn.pack(side=tk.LEFT, padx=2)
        
        self.remove_btn = ttk.Button(
            btn_frame,
            text="Remove",
            command=self._remove_domain,
            width=8,
            state="disabled"
        )
        self.remove_btn.pack(side=tk.LEFT, padx=2)
        
        # Domain tree
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        # Create tree with scrollbars
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("type", "source"),
            show="tree headings",
            selectmode="browse",
            height=15
        )
        
        vsb = ttk.Scrollbar(
            tree_frame, 
            orient="vertical",
            command=self.tree.yview
        )
        hsb = ttk.Scrollbar(
            tree_frame,
            orient="horizontal",
            command=self.tree.xview
        )
        
        self.tree.configure(
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        
        # Grid tree and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Configure tree columns
        self.tree.heading("type", text="Type")
        self.tree.heading("source", text="Source")
        self.tree.column("#0", width=300, minwidth=200)
        self.tree.column("type", width=100, minwidth=80)
        self.tree.column("source", width=150, minwidth=100)
        
        # Configure tree tags
        for tag, config in TREE_TAGS.items():
            self.tree.tag_configure(tag, **config)
        
        # Control buttons
        control_frame = ttk.Frame(self)
        control_frame.grid(row=2, column=0, sticky="ew")
        control_frame.grid_columnconfigure(2, weight=1)
        
        # Group toggle button
        self.group_btn = ttk.Button(
            control_frame,
            text="Group by Base Domain",
            command=self._toggle_grouping,
            width=20
        )
        self.group_btn.grid(row=0, column=0, padx=(0, 5))
        
        # Discovery controls
        self.discover_btn = ttk.Button(
            control_frame,
            text="Discover Related",
            command=self._discover_domains,
            state="disabled",
            width=15
        )
        self.discover_btn.grid(row=0, column=1, padx=(0, 5))
        
        self.settings_btn = ttk.Button(
            control_frame,
            text="⚙️",
            command=self._show_settings,
            width=3
        )
        self.settings_btn.grid(row=0, column=2, sticky="w")
        
        # Blocking control
        self.block_button = ttk.Button(
            control_frame,
            text="Enable Blocking",
            command=self._toggle_blocking,
            width=15
        )
        self.block_button.grid(row=0, column=3)

        # Bind events
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree.bind('<Double-1>', self._on_double_click)
        
        # Create and bind context menu
        self._create_context_menu()
        
    def _toggle_grouping(self):
        """Toggle domain grouping state"""
        if self.domain_manager.grouped_state:
            self.domain_manager.ungroup_domains()
            self.group_btn.configure(text="Group by Base Domain")
        else:
            self.domain_manager.grouped_state = True
            self.group_btn.configure(text="Ungroup Domains")
            
        self._update_tree()
        self._update_blocking()
        
    def _add_domain(self):
        """Add a new domain"""
        domain = self.domain_entry.get().strip().lower()
        if not domain:
            return
            
        # Add domain using manager
        node = self.domain_manager.add_domain(domain)
        if not node:
            messagebox.showerror(
                "Invalid Domain",
                "Please enter a valid domain name (e.g., example.com)"
            )
            return
            
        # Update display
        self._update_tree()
        self._update_blocking()
        self.domain_entry.delete(0, tk.END)
        
    def _edit_domain(self):
        """Edit selected domain"""
        selected = self.tree.selection()
        if not selected:
            return
            
        item = selected[0]
        current_domain = self.tree.item(item)['text']
        
        # Create edit dialog
        dialog = tk.Toplevel(self)
        dialog.title("Edit Domain")
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()
        
        # Content frame
        content = ttk.Frame(dialog, padding=10)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Domain entry
        ttk.Label(
            content,
            text="Domain:",
            font=FONTS['body']
        ).pack(anchor="w")
        
        entry = ttk.Entry(content, width=40)
        entry.insert(0, current_domain)
        entry.pack(fill=tk.X, pady=(5, 20))
        entry.select_range(0, tk.END)
        entry.focus()
        
        def save_changes():
            """Save domain changes"""
            new_domain = entry.get().strip().lower()
            if not new_domain:
                messagebox.showerror(
                    "Error",
                    "Domain cannot be empty"
                )
                return
                
            if new_domain == current_domain:
                dialog.destroy()
                return
                
            # Remove old domain and add new one
            removed = self.domain_manager.remove_domain(current_domain)
            if not removed:
                dialog.destroy()
                return
                
            node = self.domain_manager.add_domain(new_domain)
            if not node:
                # Restore old domain if new one is invalid
                self.domain_manager.add_domain(current_domain)
                messagebox.showerror(
                    "Invalid Domain",
                    "Please enter a valid domain name"
                )
                return
                
            self._update_tree()
            self._update_blocking()
            dialog.destroy()
            
        # Buttons
        btn_frame = ttk.Frame(content)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            btn_frame,
            text="Save",
            command=save_changes,
            width=8
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            width=8
        ).pack(side=tk.RIGHT)
        
    def _remove_domain(self):
        """Remove selected domain and its nested/discovered domains"""
        try:
            selected = self.tree.selection()
            if not selected:
                return
                
            item = selected[0]
            domain = self.tree.item(item)['text']
            parent = self.tree.parent(item)
            
            logger.info(f"Attempting to remove domain: {domain}")
            
            # Get children count before removal
            children = len(self.tree.get_children(item))
            logger.info(f"Number of children: {children}")
            
            # Determine what we're removing
            is_grouped = self.domain_manager.grouped_state
            is_group = any("Base Domain Group" in str(value) for value in self.tree.item(item)['values'])
            is_main_domain = not bool(parent) and children > 0
            
            logger.info(f"Domain status - Grouped: {is_grouped}, Group: {is_group}, Main: {is_main_domain}")
            
            # Create appropriate confirmation message
            if is_group:
                message = f"Remove '{domain}' and all its {children} related domain(s)?"
            elif is_grouped and domain in self.domain_manager.domains:
                try:
                    is_base = domain == self.domain_manager.domains[domain].base_domain
                    message = f"Remove '{domain}' and all its {children} related domain(s)?" if is_base else f"Remove '{domain}'?"
                except Exception as e:
                    logger.error(f"Error checking base domain: {e}")
                    is_base = False
                    message = f"Remove '{domain}'?"
            elif is_main_domain:
                message = f"Remove '{domain}' and its {children} discovered domain(s)?"
            else:
                message = f"Remove '{domain}'?"
                
            logger.info(f"Confirmation message: {message}")
            
            if not messagebox.askyesno("Confirm Removal", message):
                return
            
            # Get child domains before removal
            child_domains = []
            for child in self.tree.get_children(item):
                child_domains.append(self.tree.item(child)['text'])
            logger.info(f"Child domains to remove: {child_domains}")
            
            # Remove using manager
            try:
                # First remove child domains if this is a main domain
                if is_main_domain and not is_grouped:
                    for child_domain in child_domains:
                        self.domain_manager.remove_domain(child_domain)
                
                # Then remove the main domain
                removed = self.domain_manager.remove_domain(domain)
                logger.info(f"Removed domains: {removed}")
                
                # Update display
                self._update_tree()
                self._update_blocking()
                
                # Show result
                if len(removed) > 1:
                    messagebox.showinfo(
                        "Domains Removed",
                        f"Successfully removed {domain} and {len(removed)-1} related domain(s)"
                    )
                else:
                    messagebox.showinfo(
                        "Domain Removed",
                        f"Successfully removed {domain}"
                    )
                    
            except Exception as e:
                logger.error(f"Error in domain manager removal: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Error removing domain: {str(e)}")
            messagebox.showerror(
                "Error",
                "Failed to remove domain. Please try again."
            )
        
    def _discover_domains(self):
        """Start domain discovery process"""
        selected = self.tree.selection()
        if not selected:
            return
            
        item = selected[0]
        domain = self.tree.item(item)['text']
        
        messagebox.showinfo(
            "Domain Discovery",
            "A browser window will open for domain discovery.\n"
            "Browse the website normally to discover related domains.\n"
            "Close the browser when finished."
        )
        
        try:
            # Start discovery
            discovered = self.resource_discovery.start_interactive_discovery(domain)
            if discovered:
                # Process discovered domains
                self.domain_manager.add_discovered_domains(domain, discovered)
                
                # Update display
                self._update_tree()
                self._update_blocking()
                
                messagebox.showinfo(
                    "Discovery Complete",
                    f"Discovered {len(discovered)} domains"
                )
            else:
                messagebox.showwarning(
                    "Discovery Results",
                    "No additional domains were discovered"
                )
                
        except Exception as e:
            logger.error(f"Discovery error: {e}")
            messagebox.showerror(
                "Error",
                f"Failed to discover domains: {str(e)}"
            )
            
    def _update_tree(self):
        """Update the domain tree display"""
        # Store expanded state
        expanded_states = {}
        def store_expanded_state(item=""):
            if item == "":
                children = self.tree.get_children()
            else:
                children = self.tree.get_children(item)
                if self.tree.item(item, 'open'):
                    expanded_states[self.tree.item(item)['text']] = True
            for child in children:
                store_expanded_state(child)
                
        store_expanded_state()
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Get hierarchy from domain manager
        hierarchy = self.domain_manager.get_display_hierarchy()
        
        for entry in hierarchy:
            if 'is_base_group' in entry:
                # This is a base domain group
                group_item = self.tree.insert(
                    "",
                    "end",
                    text=entry['domain'],
                    values=("Base Domain Group", ""),
                    tags=('main_domain',)
                )
                
                for child in entry['children']:
                    # Add child domains (including base domain)
                    child_tags = ['main_domain' if child['is_base'] else 'subdomain']
                    if child['is_discovered']:
                        child_tags.append('discovered')
                        
                    self.tree.insert(
                        group_item,
                        "end",
                        text=child['domain'],
                        values=(
                            "Base Domain" if child['is_base'] else 
                            ("Discovered" if child['is_discovered'] else "Subdomain"),
                            child['discovery_source'] or ""
                        ),
                        tags=tuple(child_tags)
                    )
                    
                # Restore expanded state
                if entry['domain'] in expanded_states:
                    self.tree.item(group_item, open=True)
                    
            else:
                # This is a regular domain with potential discoveries
                domain_item = self.tree.insert(
                    "",
                    "end",
                    text=entry['domain'],
                    values=(
                        "Discovered" if entry['is_discovered'] else "Domain",
                        entry['discovery_source'] or ""
                    ),
                    tags=('discovered' if entry['is_discovered'] else 'main_domain',)
                )
                
                # Add discovered domains
                for child_domain in entry['children']:
                    self.tree.insert(
                        domain_item,
                        "end",
                        text=child_domain,
                        values=("Discovered", entry['domain']),
                        tags=('discovered',)
                    )
                    
                # Restore expanded state
                if entry['domain'] in expanded_states:
                    self.tree.item(domain_item, open=True)
                    
    def _update_blocking(self):
        """Update network blocking rules"""
        if not self.network_manager.is_blocking:
            return
            
        # Get allowed domains from manager
        domains = self.domain_manager.get_allowed_domains()
        
        # Update network rules
        self.network_manager.block_all_except_allowed(list(domains))
        
        if self.on_change:
            self.on_change()
            
    def _toggle_blocking(self):
        """Toggle website blocking"""
        try:
            if not self.network_manager.is_blocking:
                # Get allowed domains
                domains = self.domain_manager.get_allowed_domains()
                if not domains:
                    messagebox.showwarning(
                        "Warning",
                        "Please add at least one domain before enabling blocking"
                    )
                    return
                    
                # Enable blocking
                self.network_manager.block_all_except_allowed(list(domains))
                self.block_button.configure(text="Disable Blocking")
            else:
                # Disable blocking
                self.network_manager.unblock_all()
                self.block_button.configure(text="Enable Blocking")
                
            if self.on_change:
                self.on_change()
                
        except Exception as e:
            logger.error(f"Failed to toggle blocking: {e}")
            messagebox.showerror(
                "Error",
                f"Failed to update network rules: {str(e)}"
            )

    def load_domains(self, domains: List[str]) -> None:
        """Load domains from saved data"""
        for domain in domains:
            node = self.domain_manager.add_domain(domain)
            if node:
                self._update_tree()
                self._update_blocking()


            
    def _show_settings(self):
        """Show discovery settings dialog"""
        dialog = tk.Toplevel(self)
        dialog.title("Discovery Settings")
        dialog.geometry("300x200")
        dialog.transient(self)
        dialog.grab_set()
        
        # Content frame
        content = ttk.Frame(dialog, padding=10)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Settings
        current = self.resource_discovery.filters
        settings = {
            'capture_all': tk.BooleanVar(value=current.capture_all_resources),
            'capture_cdn': tk.BooleanVar(value=current.capture_cdn),
            'enhanced_discovery': tk.BooleanVar(value=current.enhanced_discovery)
        }
        
        # Create checkboxes
        ttk.Checkbutton(
            content,
            text="Capture All Resources",
            variable=settings['capture_all']
        ).pack(anchor="w", pady=5)
        
        ttk.Checkbutton(
            content,
            text="Include CDN Resources",
            variable=settings['capture_cdn']
        ).pack(anchor="w", pady=5)
        
        ttk.Checkbutton(
            content,
            text="Enhanced Discovery",
            variable=settings['enhanced_discovery']
        ).pack(anchor="w", pady=5)
        
        def apply_settings():
            """Apply capture settings"""
            filters = CaptureFilters(
                capture_all_resources=settings['capture_all'].get(),
                capture_cdn=settings['capture_cdn'].get(),
                enhanced_discovery=settings['enhanced_discovery'].get()
            )
            self.resource_discovery.set_capture_filters(filters)
            dialog.destroy()
            
        # Buttons
        btn_frame = ttk.Frame(content)
        btn_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(
            btn_frame,
            text="Apply",
            command=apply_settings,
            width=8
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            width=8
        ).pack(side=tk.RIGHT)
        
    def _on_select(self, event=None):
        """Handle tree item selection"""
        selected = self.tree.selection()
        
        if selected:
            item = selected[0]
            is_group = len(self.tree.get_children(item)) > 0
            
            # Enable/disable buttons based on selection
            self.edit_btn.configure(state="normal" if not is_group else "disabled")
            self.remove_btn.configure(state="normal")
            self.discover_btn.configure(state="normal")
        else:
            self.edit_btn.configure(state="disabled")
            self.remove_btn.configure(state="disabled")
            self.discover_btn.configure(state="disabled")
            
    def _on_double_click(self, event):
        """Handle double click on tree items"""
        item = self.tree.identify_row(event.y)
        if item:
            # Toggle item expansion
            if self.tree.item(item, "open"):
                self.tree.item(item, open=False)
            else:
                self.tree.item(item, open=True)
                
    def _create_context_menu(self):
        """Create right-click context menu"""
        self.context_menu = tk.Menu(self, tearoff=0)
        
        # Add menu items
        self.context_menu.add_command(
            label="Edit",
            command=self._edit_domain
        )
        self.context_menu.add_command(
            label="Remove",
            command=self._remove_domain
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="Discover Related",
            command=self._discover_domains
        )
        
        # Bind right-click event
        self.tree.bind(
            '<Button-3>',
            self._show_context_menu
        )
        
    def _show_context_menu(self, event):
        """Show context menu at mouse position"""
        # Select item under mouse
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            # Get item info
            is_group = len(self.tree.get_children(item)) > 0
            
            # Enable/disable menu items based on selection
            self.context_menu.entryconfig(
                0,  # Edit option
                state="normal" if not is_group else "disabled"
            )
            self.context_menu.entryconfig(
                1,  # Remove option
                state="normal"
            )
            self.context_menu.entryconfig(
                3,  # Discover option
                state="normal"
            )
            
            # Show menu
            self.context_menu.post(event.x_root, event.y_root)