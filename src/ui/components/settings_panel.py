"""
Settings panel component for ZenFlow application.
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Callable, Optional, Dict
from ...core.settings import SettingsManager

logger = logging.getLogger(__name__)

class SettingsPanel(tk.Toplevel):
    """Settings configuration window"""
    
    def __init__(self, parent: tk.Widget,
                settings_manager: SettingsManager,
                callback: Optional[Callable] = None):
        """Initialize settings panel"""
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.callback = callback
        
        # Configure window
        self.title("Settings")
        self.geometry("500x600")
        self.resizable(False, False)
        self.withdraw()  # Hide initially
        
        # Make it modal
        self.transient(parent)
        self.grab_set()
        
        # Variables for settings
        self._init_variables()
        
        # Create UI
        self._create_widgets()
        self._setup_layout()
        self._load_settings()
        
        # Window management
        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.bind("<Escape>", lambda e: self.hide())

    def _init_variables(self) -> None:
        """Initialize variables for settings"""
        # Timer settings
        self.work_duration = tk.IntVar()
        self.break_duration = tk.IntVar()
        self.total_sessions = tk.IntVar()
        self.auto_start_breaks = tk.BooleanVar()
        self.sound_notifications = tk.BooleanVar()
        
        # Application settings
        self.auto_start = tk.BooleanVar()
        self.minimize_to_tray = tk.BooleanVar()
        self.start_minimized = tk.BooleanVar()
        self.block_during_breaks = tk.BooleanVar()
        
        # Daily goals
        self.daily_goal = tk.IntVar()
        self.weekly_goal = tk.IntVar()
        
        # Store entries by name
        self.timer_entries: Dict[str, ttk.Entry] = {}

    def _create_widgets(self) -> None:
        """Create settings widgets"""
        # Main container
        self.main_frame = ttk.Frame(self, padding=10)
        
        # Notebook for settings categories
        self.notebook = ttk.Notebook(self.main_frame)
        
        # Timer Settings
        self.timer_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.timer_frame, text="Timer")
        
        timer_settings = [
            ("Work Duration (minutes):", "work_duration", self.work_duration),
            ("Break Duration (minutes):", "break_duration", self.break_duration),
            ("Number of Sessions:", "total_sessions", self.total_sessions)
        ]
        
        for label_text, name, var in timer_settings:
            container = ttk.Frame(self.timer_frame)
            ttk.Label(container, text=label_text).pack(side="left", padx=5)
            entry = ttk.Entry(container, textvariable=var, width=10)
            entry.pack(side="left", padx=5)
            self.timer_entries[name] = entry
            container.pack(fill="x", pady=2)
        
        ttk.Checkbutton(
            self.timer_frame,
            text="Auto-start breaks",
            variable=self.auto_start_breaks
        ).pack(fill="x", pady=5)
        
        ttk.Checkbutton(
            self.timer_frame,
            text="Sound notifications",
            variable=self.sound_notifications
        ).pack(fill="x", pady=5)
        
        # Application Settings
        self.app_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.app_frame, text="Application")
        
        ttk.Checkbutton(
            self.app_frame,
            text="Start with system",
            variable=self.auto_start
        ).pack(fill="x", pady=5)
        
        ttk.Checkbutton(
            self.app_frame,
            text="Minimize to system tray",
            variable=self.minimize_to_tray
        ).pack(fill="x", pady=5)
        
        ttk.Checkbutton(
            self.app_frame,
            text="Start minimized",
            variable=self.start_minimized
        ).pack(fill="x", pady=5)
        
        ttk.Checkbutton(
            self.app_frame,
            text="Block websites during breaks",
            variable=self.block_during_breaks
        ).pack(fill="x", pady=5)
        
        # Goals Settings
        self.goals_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.goals_frame, text="Goals")
        
        goals_settings = [
            ("Daily Focus Goal (minutes):", self.daily_goal),
            ("Weekly Focus Goal (minutes):", self.weekly_goal)
        ]
        
        for label_text, var in goals_settings:
            container = ttk.Frame(self.goals_frame)
            ttk.Label(container, text=label_text).pack(side="left", padx=5)
            ttk.Entry(container, textvariable=var, width=10).pack(side="left", padx=5)
            container.pack(fill="x", pady=2)
        
        # Buttons
        self.button_frame = ttk.Frame(self.main_frame)
        
        ttk.Button(
            self.button_frame,
            text="Apply",
            command=self._apply_settings,
            width=10
        ).pack(side="left", padx=5)
        
        ttk.Button(
            self.button_frame,
            text="Cancel",
            command=self.hide,
            width=10
        ).pack(side="left", padx=5)
        
        ttk.Button(
            self.button_frame,
            text="Reset to Default",
            command=self._reset_defaults,
            width=15
        ).pack(side="right", padx=5)

    def _setup_layout(self) -> None:
        """Arrange widgets in the window"""
        self.main_frame.pack(fill="both", expand=True)
        self.notebook.pack(fill="both", expand=True, pady=(0, 10))
        self.button_frame.pack(fill="x", pady=10)

    def _load_settings(self) -> None:
        """Load current settings into UI"""
        settings = self.settings_manager.settings
        timer = settings.timer
        
        # Timer settings
        self.work_duration.set(timer.work_duration)
        self.break_duration.set(timer.break_duration)
        self.total_sessions.set(timer.total_sessions)
        self.auto_start_breaks.set(timer.auto_start_breaks)
        self.sound_notifications.set(timer.sound_notifications)
        
        # Application settings
        self.auto_start.set(settings.auto_start)
        self.minimize_to_tray.set(settings.minimize_to_tray)
        self.start_minimized.set(settings.start_minimized)
        self.block_during_breaks.set(settings.block_during_breaks)
        
        # Goals (these would normally be loaded from settings)
        self.daily_goal.set(120)  # Default 2 hours
        self.weekly_goal.set(600)  # Default 10 hours

    def _apply_settings(self) -> None:
        """Apply settings changes"""
        try:
            # Update timer settings
            self.settings_manager.update_timer_settings(
                work_duration=self.work_duration.get(),
                break_duration=self.break_duration.get(),
                total_sessions=self.total_sessions.get(),
                auto_start_breaks=self.auto_start_breaks.get(),
                sound_notifications=self.sound_notifications.get()
            )
            
            # Update application settings
            self.settings_manager.update_settings(
                auto_start=self.auto_start.get(),
                minimize_to_tray=self.minimize_to_tray.get(),
                start_minimized=self.start_minimized.get(),
                block_during_breaks=self.block_during_breaks.get()
            )
            
            # Notify callback
            if self.callback:
                self.callback()
            
            self.hide()
            
        except Exception as e:
            logger.error(f"Failed to apply settings: {e}")
            tk.messagebox.showerror(
                "Error",
                f"Failed to apply settings: {str(e)}"
            )

    def _reset_defaults(self) -> None:
        """Reset settings to defaults"""
        if tk.messagebox.askyesno(
            "Reset Settings",
            "Are you sure you want to reset all settings to default values?"
        ):
            # Reset settings manager
            self.settings_manager = SettingsManager()
            
            # Reload UI
            self._load_settings()
            
            # Notify callback
            if self.callback:
                self.callback()

    def show(self) -> None:
        """Show settings panel"""
        self._load_settings()  # Refresh settings
        self.deiconify()
        self.lift()
        self.focus_force()

    def hide(self) -> None:
        """Hide settings panel"""
        self.grab_release()
        self.withdraw()