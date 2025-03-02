"""
app.py - Main application with integrated timer and statistics system for ZenFlow
"""
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Optional
import json
from datetime import datetime
import os
import sys

from .components.timer import TimerFrame
from .components.statistics import StatisticsFrame
from .components.website_manager import WebsiteManagerFrame
from ..core.network import NetworkManager
from .ui_config import (
    MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT, DEFAULT_PADDING,
    ResponsiveFrame, ScrollableFrame, configure_styles
)
from ..config.constants import (
    APP_NAME, COLORS, APP_DIR, ERROR_MESSAGES, WINDOW_SIZE, FONTS
)
from .service import TimerState, ServiceProvider


logger = logging.getLogger(__name__)

class ZenFlowApp:
    """Main application window with integrated timer and statistics for ZenFlow"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        
        # Configure window
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.root.geometry(WINDOW_SIZE)
        
        # Configure grid weights for responsiveness
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Apply styles
        configure_styles()
        
        try:
            # Initialize network manager
            self.network_manager = NetworkManager()
        except PermissionError:
            messagebox.showerror(
                "Error",
                ERROR_MESSAGES['root_required']
            )
            raise
            
        # Create data directory if needed
        os.makedirs(APP_DIR, exist_ok=True)
        
        # Initialize service provider
        self.service_provider = ServiceProvider()
            
        # Setup UI
        self._create_menu()
        self._create_layout()
        
        # Window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Bind resize event
        self.root.bind('<Configure>', self._on_window_configure)
        
        logger.info("Application initialized")
        
    def _create_menu(self):
        """Create application menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Statistics", command=self._export_stats)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_closing)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Reset Statistics", command=self._reset_stats)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        
    def _create_layout(self):
        """Create main application layout with improved tabbed interface"""
        # Main container with padding
        main_frame = ResponsiveFrame(
            self.root,
            min_width=MIN_WINDOW_WIDTH - 40,
            min_height=MIN_WINDOW_HEIGHT - 40
        )
        main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        # Configure grid weights for main frame
        main_frame.grid_columnconfigure(1, weight=1)  # Let right panel expand
        main_frame.grid_rowconfigure(0, weight=1)
        
        # Left panel with fixed width and tabs
        self.left_panel = ttk.Frame(main_frame, width=600)
        self.left_panel.grid(row=0, column=0, sticky="ns", padx=(0, 20))
        self.left_panel.grid_rowconfigure(0, weight=1)
        self.left_panel.pack_propagate(False)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.left_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Timer Tab
        timer_tab = ttk.Frame(self.notebook, padding=DEFAULT_PADDING)
        timer_tab.grid_rowconfigure(0, weight=1)
        timer_tab.grid_columnconfigure(0, weight=1)
        self.notebook.add(timer_tab, text="Focus Timer")
        
        # Create timer in timer tab
        self.timer = TimerFrame(
            timer_tab,
            timer_service=self.service_provider.timer_service,
            on_complete=self._on_timer_complete,
            on_state_change=self._on_timer_state_change
        )
        self.timer.pack(fill=tk.BOTH, expand=True)
        
        # Statistics Tab
        stats_tab = ttk.Frame(self.notebook, padding=DEFAULT_PADDING)
        stats_tab.grid_rowconfigure(0, weight=1)
        stats_tab.grid_columnconfigure(0, weight=1)
        self.notebook.add(stats_tab, text="Statistics")
        
        # Create statistics in stats tab
        self.stats = StatisticsFrame(
            stats_tab,
            stats_service=self.service_provider.stats_service,
            on_reset=self._on_stats_reset
        )
        self.stats.pack(fill=tk.BOTH, expand=True)
        
        # Right panel (Website Management)
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(0, weight=1)
        
        # Website Manager
        self.website_manager = WebsiteManagerFrame(
            right_panel,
            self.network_manager,
            on_change=self._on_blocking_change
        )
        self.website_manager.pack(fill=tk.BOTH, expand=True)
        
        # Bind tab change event
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)
            
    def _on_tab_changed(self, event):
        """Handle tab changes"""
        current_tab = self.notebook.select()
        tab_id = self.notebook.index(current_tab)
        logger.debug(f"Switched to tab {tab_id}")
        
        # Update UI based on selected tab
        if tab_id == 1:  # Statistics tab
            # Statistics tab is always up-to-date via the shared service
            pass
            
    def _on_window_configure(self, event):
        """Handle window resize events"""
        if event.widget == self.root:
            # Maintain minimum window size
            width = max(event.width, MIN_WINDOW_WIDTH)
            height = max(event.height, MIN_WINDOW_HEIGHT)
            
            if width != event.width or height != event.height:
                self.root.geometry(f"{width}x{height}")
                
    def _on_timer_state_change(self, state: TimerState):
        """Handle timer state changes"""
        if state == TimerState.WORKING:
            if self.network_manager.is_blocking:
                self.website_manager.block_button.configure(state="disabled")
        else:
            self.website_manager.block_button.configure(state="normal")
            
    def _on_blocking_change(self):
        """Handle website blocking changes"""
        # Save all data to ensure it's persistent
        self._save_data()
        
    def _on_stats_reset(self):
        """Handle statistics reset"""
        # Nothing needed here since both timer and stats component
        # share the same statistics service
        pass
            
    def _on_timer_complete(self, completed_minutes: int, was_work: bool):
        """Handle timer completion"""
        try:
            if was_work:
                # Statistics are already updated via service layer
                
                # Check if all sessions completed
                session_info = self.service_provider.timer_service.get_session_info()
                if session_info.get("pomodoros_completed", 0) >= session_info.get("total_sessions", 4):
                    # Switch to statistics tab
                    self.notebook.select(1)
                
                # Save data
                self._save_data()
                
                # Log completion
                logger.info(f"Timer complete: {completed_minutes} minutes")
            
        except Exception as e:
            logger.error(f"Error handling timer completion: {e}")
            messagebox.showerror(
                "Error",
                "Failed to update statistics"
            )
            
    def _save_data(self):
        """Save application data with error handling"""
        try:
            # Save statistics via service provider
            self.service_provider.save_all_data()
            
            # Save website management data separately
            domains_data = {
                'allowed_domains': list(
                    self.network_manager.get_allowed_domains()
                )
            }
            
            # Save domains to file
            domains_path = os.path.join(APP_DIR, 'domains.json')
            
            # Create backup of existing file
            if os.path.exists(domains_path):
                backup_path = os.path.join(APP_DIR, 'domains.backup.json')
                os.rename(domains_path, backup_path)
            
            # Write new data
            with open(domains_path, 'w') as f:
                json.dump(domains_data, f, indent=4)
                
            # Remove backup if save successful
            backup_path = os.path.join(APP_DIR, 'domains.backup.json')
            if os.path.exists(backup_path):
                os.remove(backup_path)
                
            logger.info("Application data saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            messagebox.showerror(
                "Error",
                "Failed to save application data"
            )
            
    def _load_domains_data(self):
        """Load domain data for website manager"""
        try:
            domains_path = os.path.join(APP_DIR, 'domains.json')
            if not os.path.exists(domains_path):
                return
                
            with open(domains_path, 'r') as f:
                data = json.load(f)
                
            # Validate data structure
            if not isinstance(data, dict):
                raise ValueError("Invalid data format")
                
            # Load allowed domains if valid
            if 'allowed_domains' in data and isinstance(data['allowed_domains'], list):
                self.website_manager.load_domains(data['allowed_domains'])
                
            logger.info("Domains data loaded successfully")
                
        except Exception as e:
            logger.error(f"Error loading domains data: {e}")
            messagebox.showwarning(
                "Warning",
                "Failed to load saved domains data"
            )
            
    def _export_stats(self):
        """Export statistics to file"""
        try:
            filename = f"focus_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(os.path.expanduser("~"), filename)
            
            # Get all stats via service
            summary = self.service_provider.stats_service.get_summary_stats()
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=4)
                
            messagebox.showinfo(
                "Export Complete",
                f"Statistics exported to:\n{filepath}"
            )
            
        except Exception as e:
            logger.error(f"Error exporting stats: {e}")
            messagebox.showerror(
                "Error",
                "Failed to export statistics"
            )
            
    def _reset_stats(self):
        """Reset statistics with confirmation"""
        if messagebox.askyesno(
            "Reset Statistics",
            "Are you sure you want to reset all statistics?\nThis action cannot be undone.",
            icon='warning'
        ):
            # Reset via service provider
            self.service_provider.stats_service.reset_statistics()
            
            # Save changes
            self._save_data()
            
    def _show_about(self):
        """Show about dialog"""
        settings = self.service_provider.timer_service.get_settings()
        about_text = f"""
{APP_NAME}

A productivity tool to help you maintain focus and manage distractions.

Features:
• Customizable focus timer ({settings['work_duration']}m work / {settings['short_break']}m break)
• Website blocking during focus sessions
• Detailed statistics tracking
• Domain discovery and management
"""

        messagebox.showinfo("About", about_text.strip())
        
    def _on_closing(self):
        """Handle application closing with cleanup"""
        try:
            state = self.service_provider.timer_service.get_state()
            if state not in (TimerState.IDLE, TimerState.COMPLETED):
                if not messagebox.askyesno(
                    "Quit",
                    "A timer is currently running. Are you sure you want to quit?",
                    icon='warning'
                ):
                    return
                    
            # Save data before closing
            self._save_data()
            
            # Disable website blocking if active
            if self.network_manager.is_blocking:
                self.network_manager.unblock_all()
                
            self.root.quit()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            self.root.quit()

    def run(self):
        """Start the application"""
        try:
            logger.info("Starting application")
            
            # Load domain data
            self._load_domains_data()
            
            # Start main loop
            self.root.mainloop()
            
        except Exception as e:
            logger.error(f"Application error: {e}")
            messagebox.showerror(
                "Error",
                "An unexpected error occurred"
            )
            raise