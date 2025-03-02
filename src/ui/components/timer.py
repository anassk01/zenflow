"""
timer.py - Completely rewritten timer component with reliable tracking
"""
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Optional, Callable, Dict
import uuid
from datetime import datetime

from ..ui_config import (
    DEFAULT_PADDING,
    SECTION_PADDING,
    create_button,
    configure_styles
)
from ...config.constants import COLORS, FONTS
from ..service import TimerService, TimerState, SessionStatus


logger = logging.getLogger(__name__)

class TimerFrame(ttk.Frame):
    """Fully rewritten timer component with accurate tracking"""
    
    def __init__(
        self,
        parent: tk.Widget,
        timer_service: TimerService,
        work_duration: int = 25,
        short_break: int = 5,
        long_break: int = 15,
        long_break_interval: int = 4,
        total_sessions: int = 4,
        on_complete: Optional[Callable[[int, bool], None]] = None,
        on_state_change: Optional[Callable[[TimerState], None]] = None,
        auto_start_breaks: bool = True
    ):
        super().__init__(parent)
        
        # Store timer service
        self.timer_service = timer_service
        
        # Initialize timer service settings
        initial_settings = {
            "work_duration": work_duration,
            "short_break": short_break,
            "long_break": long_break,
            "long_break_interval": long_break_interval,
            "total_sessions": total_sessions,
            "auto_start_breaks": auto_start_breaks
        }
        self.timer_service.update_settings(initial_settings)
        
        # Callbacks
        self.on_complete = on_complete
        self.on_state_change = on_state_change
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        
        # Create UI
        self._setup_ui()
        
        # Start timer update loop
        self._schedule_timer_update()
        
    def _setup_ui(self):
        """Create timer UI elements with vertical layout"""
        # Main container with padding
        main_frame = ttk.Frame(self, padding=DEFAULT_PADDING)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Create UI sections
        self._create_header_section(main_frame)
        self._create_timer_section(main_frame)
        self._create_controls_section(main_frame)
        self._create_details_section(main_frame)
        
    def _create_header_section(self, parent):
        """Create header with session info"""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, SECTION_PADDING))
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Session counter
        self.session_label = ttk.Label(
            header_frame,
            text=self._format_session_text(),
            font=FONTS['subtitle'],
            foreground=COLORS['primary']
        )
        self.session_label.grid(row=0, column=0, sticky="w")
        
        # Settings button
        ttk.Button(
            header_frame,
            text="⚙️",
            command=self._show_settings_dialog,
            width=3,
            style="Icon.TButton"
        ).grid(row=0, column=2, sticky="e")
        
    def _create_timer_section(self, parent):
        """Create main timer display"""
        timer_frame = ttk.Frame(parent)
        timer_frame.grid(row=1, column=0, sticky="ew", pady=SECTION_PADDING)
        timer_frame.grid_columnconfigure(0, weight=1)
        
        # Time display
        self.time_label = ttk.Label(
            timer_frame,
            text="25:00",
            font=FONTS['display'],
            foreground=COLORS['primary'],
            anchor="center"
        )
        self.time_label.grid(row=0, column=0, sticky="ew", pady=10)
        
        # State label
        self.state_label = ttk.Label(
            timer_frame,
            text="Ready to start",
            font=FONTS['subtitle'],
            foreground=COLORS['text_secondary'],
            anchor="center"
        )
        self.state_label.grid(row=1, column=0, sticky="ew")
        
        # Progress section
        progress_frame = ttk.Frame(timer_frame)
        progress_frame.grid(row=2, column=0, sticky="ew", pady=10, padx=20) 
        progress_frame.grid_columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            mode='determinate',
            maximum=100,
            style="Timer.Horizontal.TProgressbar"
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=20)
        
        # Time elapsed label
        self.elapsed_label = ttk.Label(
            progress_frame,
            text="0:00 / 25:00",
            font=FONTS['small'],
            foreground=COLORS['text_secondary']
        )
        self.elapsed_label.grid(row=1, column=0, sticky="e", padx=20, pady=(5, 0))
        
    def _create_controls_section(self, parent):
        """Create timer controls"""
        controls_frame = ttk.Frame(parent)
        controls_frame.grid(row=2, column=0, sticky="ew", pady=SECTION_PADDING)
        controls_frame.grid_columnconfigure(1, weight=1)
        
        # Start/Pause button
        self.start_button = create_button(
            controls_frame,
            text="Start",
            command=self._toggle_timer,
            style="Primary.TButton",
            width=8
        )
        self.start_button.grid(row=0, column=0, padx=5)
        
        # Reset button
        self.reset_button = create_button(
            controls_frame,
            text="Reset",
            command=self._reset_timer,
            width=8,
            state="disabled"
        )
        self.reset_button.grid(row=0, column=1, padx=5)
        
        # Skip button
        self.skip_button = create_button(
            controls_frame,
            text="Skip",
            command=self._skip_timer,
            width=8,
            state="disabled"
        )
        self.skip_button.grid(row=0, column=2, padx=5)
        
    def _create_details_section(self, parent):
        """Create expandable details section"""
        self.details_frame = ttk.LabelFrame(
            parent,
            text="Session Details",
            padding=(10, 5)
        )
        self.details_frame.grid(row=3, column=0, sticky="nsew", pady=(SECTION_PADDING, 0))
        self.details_frame.grid_columnconfigure(0, weight=1)
        
        # Session schedule
        self.schedule_frame = ttk.Frame(self.details_frame)
        self.schedule_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(
            self.schedule_frame,
            text="Schedule:",
            font=FONTS['body'],
            foreground=COLORS['text_secondary']
        ).pack(anchor="w")
        
        self.schedule_label = ttk.Label(
            self.schedule_frame,
            text=self._get_schedule_text(),
            font=FONTS['body']
        )
        self.schedule_label.pack(anchor="w", padx=20)
        
        # Session progress
        progress_frame = ttk.Frame(self.details_frame)
        progress_frame.grid(row=1, column=0, sticky="ew")
        
        ttk.Label(
            progress_frame,
            text="Progress:",
            font=FONTS['body'],
            foreground=COLORS['text_secondary']
        ).pack(anchor="w")
        
        self.progress_text = ttk.Label(
            progress_frame,
            text="Not started",
            font=FONTS['body']
        )
        self.progress_text.pack(anchor="w", padx=20)
    
    def _schedule_timer_update(self):
        """Schedule periodic timer updates"""
        # Update timer state
        self.timer_service.update()
        
        # Update UI
        self._update_display()
        
        # Schedule next update
        self.after(1000, self._schedule_timer_update)
    
    def _toggle_timer(self):
        """Toggle between start, pause, and resume states"""
        state = self.timer_service.get_state()
        
        if state == TimerState.IDLE or state == TimerState.COMPLETED:
            # Start new session from either IDLE or COMPLETED state
            self.timer_service.start()
        elif state == TimerState.PAUSED:
            # Resume from pause
            self.timer_service.resume()
        else:
            # Pause active session
            self.timer_service.pause()
            
        # Update UI immediately
        self._update_display()


    def _reset_timer(self):
        """Reset the timer to initial state"""
        self.timer_service.stop()
        
        # Update UI immediately
        self._update_display()
        
        # Notify state change
        if self.on_state_change:
            self.on_state_change(self.timer_service.get_state())
    
    def _skip_timer(self):
        """Skip to the next timer phase"""
        self.timer_service.skip()
        
        # Update UI immediately
        self._update_display()
        
        # Notify state change
        if self.on_state_change:
            self.on_state_change(self.timer_service.get_state())
        
        # Check if work session completed
        session_info = self.timer_service.get_session_info()
        if session_info.get("work_completed", False):
            # Work session was just completed
            if self.on_complete:
                minutes = session_info.get("effective_minutes", 0)
                self.on_complete(minutes, True)
    
    def _update_display(self):
        """Update all display elements based on current timer state"""
        # Get current session info
        session_info = self.timer_service.get_session_info()
        state = self.timer_service.get_state()
        
        # Update time display
        self.time_label.configure(text=session_info.get("time_display", "00:00"))
        
        # Update progress bar
        self.progress_var.set(session_info.get("progress_percent", 0))
        
        # Update elapsed time label
        self.elapsed_label.configure(text=session_info.get("elapsed_display", "0:00 / 0:00"))
        
        # Update state label
        state_text = self._get_state_text(state)
        self.state_label.configure(text=state_text)
        
        # Update session counter
        current = session_info.get("current_session", 1)
        total = session_info.get("total_sessions", 4)
        self.session_label.configure(text=f"Session {min(current, total)}/{total}")
        
        # Update progress text
        self.progress_text.configure(text=self._get_progress_text(session_info))
        
        # Update button states and text
        self._update_button_states(state, session_info)
    
    def _update_button_states(self, state: TimerState, session_info: Dict):
        """Update button states and text based on timer state"""
        if state == TimerState.IDLE:
            # Initial state
            self.start_button.configure(text="Start", state="normal")
            self.reset_button.configure(state="disabled")
            self.skip_button.configure(state="disabled")
        elif state == TimerState.COMPLETED:
            # All sessions completed - ready to start new
            self.start_button.configure(text="Start New", state="normal") 
            self.reset_button.configure(state="disabled")
            self.skip_button.configure(state="disabled")
        elif state == TimerState.PAUSED:
            # Paused state
            is_break = session_info.get("is_break", False)
            self.start_button.configure(
                text="Start Break" if is_break else "Resume"
            )
            self.reset_button.configure(state="normal")
            self.skip_button.configure(state="normal")
        else:
            # Active state (working or break)
            self.start_button.configure(text="Pause")
            self.reset_button.configure(state="normal")
            self.skip_button.configure(state="normal")


    def _format_session_text(self) -> str:
        """Format session counter text"""
        session_info = self.timer_service.get_session_info()
        current = session_info.get("current_session", 1)
        total = session_info.get("total_sessions", 4)
        return f"Session {min(current, total)}/{total}"
    
    def _get_state_text(self, state: TimerState) -> str:
        """Get display text for current state"""
        if state == TimerState.IDLE:
            return "Ready to start"
        elif state == TimerState.WORKING:
            return "Focus Time"
        elif state == TimerState.SHORT_BREAK:
            return "Short Break"
        elif state == TimerState.LONG_BREAK:
            return "Long Break"
        elif state == TimerState.PAUSED:
            # Get more specific text based on what was paused
            session_info = self.timer_service.get_session_info()
            if session_info.get("is_work", False):
                return "Focus Paused"
            elif session_info.get("is_break", False):
                return "Break Paused"
            return "Paused"
        elif state == TimerState.COMPLETED:
            return "Sessions Complete!"
        return ""
    
    def _get_progress_text(self, session_info: Dict) -> str:
        """Get detailed progress text"""
        state = self.timer_service.get_state()
        
        if state == TimerState.IDLE:
            return "Not started"
        
        # Build progress lines
        progress = []
        completed = session_info.get("pomodoros_completed", 0)
        total = session_info.get("total_sessions", 4)
        
        if completed > 0:
            progress.append(f"Completed: {completed} sessions")
        
        remaining = total - completed
        if remaining > 0:
            progress.append(f"Remaining: {remaining} sessions")
            
        if state != TimerState.IDLE and state != TimerState.COMPLETED:
            is_break = session_info.get("is_break", False)
            current_type = "Break" if is_break else "Work"
            progress.append(f"Current: {current_type} session")
            
        if session_info.get("pause_count", 0) > 0:
            pause_seconds = session_info.get("total_pause_duration", 0)
            pause_minutes = pause_seconds // 60
            pause_remainder = pause_seconds % 60
            progress.append(f"Paused: {pause_minutes}:{pause_remainder:02d} ({session_info.get('pause_count', 0)} times)")
            
        return "\n".join(progress)
    
    def _get_schedule_text(self) -> str:
        """Get schedule text based on current settings"""
        settings = self.timer_service.get_settings()
        return (
            f"• Work: {settings.get('work_duration', 25)} minutes\n"
            f"• Short Break: {settings.get('short_break', 5)} minutes\n"
            f"• Long Break: {settings.get('long_break', 15)} minutes "
            f"(every {settings.get('long_break_interval', 4)} sessions)\n"
            f"• Total Sessions: {settings.get('total_sessions', 4)}"
        )
        
    def _show_settings_dialog(self):
        """Show settings dialog"""
        dialog = tk.Toplevel(self)
        dialog.title("Timer Settings")
        dialog.geometry("350x430")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Main container with padding
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Timer Settings",
            font=FONTS['title']
        )
        title_label.pack(pady=(0, 20))
        
        # Settings container
        settings_frame = ttk.Frame(main_frame)
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        # Get current settings
        current_settings = self.timer_service.get_settings()
        
        # Duration settings
        settings = [
            ("Work Duration (min):", current_settings.get("work_duration", 25), 1, 120),
            ("Short Break (min):", current_settings.get("short_break", 5), 1, 30),
            ("Long Break (min):", current_settings.get("long_break", 15), 1, 60),
            ("Long Break After # Sessions:", current_settings.get("long_break_interval", 4), 1, 10),
            ("Total Sessions:", current_settings.get("total_sessions", 4), 1, 12)
        ]

        # Variables to store settings
        vars = {}
        for label, value, min_val, max_val in settings:
            # Container for each setting
            setting_frame = ttk.Frame(settings_frame)
            setting_frame.pack(fill=tk.X, pady=10)
            
            # Label
            ttk.Label(
                setting_frame,
                text=label,
                font=FONTS['body']
            ).pack(side=tk.LEFT)
            
            # Entry with validation
            var = tk.StringVar(value=str(value))
            entry = ttk.Entry(
                setting_frame,
                textvariable=var,
                width=10,
                justify='center'
            )
            entry.pack(side=tk.RIGHT)
            
            # Store variables and validation values
            vars[label] = (var, min_val, max_val)
            
            # Add help text
            help_text = f"({min_val}-{max_val})"
            ttk.Label(
                setting_frame,
                text=help_text,
                font=FONTS['small'],
                foreground=COLORS['text_secondary']
            ).pack(side=tk.RIGHT, padx=5)
            
        # Auto-start breaks option
        auto_breaks_var = tk.BooleanVar(value=current_settings.get("auto_start_breaks", True))
        auto_breaks_frame = ttk.Frame(settings_frame)
        auto_breaks_frame.pack(fill=tk.X, pady=10)
        
        ttk.Checkbutton(
            auto_breaks_frame,
            text="Auto-start breaks",
            variable=auto_breaks_var
        ).pack(side=tk.LEFT)

        def validate_and_save():
            """Validate and save timer settings"""
            try:
                new_settings = {}
                for label, (var, min_val, max_val) in vars.items():
                    try:
                        value = int(var.get())
                        if not min_val <= value <= max_val:
                            raise ValueError(
                                f"{label.strip(':')} must be between {min_val} and {max_val}"
                            )
                        
                        # Map labels to setting keys
                        key = label.lower().replace(" (min):", "").replace(" # ", "_").replace(":", "").replace(" ", "_")
                        new_settings[key] = value
                    except ValueError as e:
                        if "must be between" not in str(e):
                            raise ValueError(f"{label.strip(':')} must be a number")
                        raise
                
                # Handle special cases
                if "long_break_after" in new_settings:
                    new_settings["long_break_interval"] = new_settings.pop("long_break_after")
                
                # Special validation: long break interval shouldn't exceed total sessions
                if new_settings.get("long_break_interval", 4) > new_settings.get("total_sessions", 4):
                    raise ValueError("Long break interval cannot exceed total sessions")
                
                # Add auto-start setting
                new_settings["auto_start_breaks"] = auto_breaks_var.get()
                
                # Apply settings
                self.timer_service.update_settings(new_settings)
                
                # Update schedule display
                self.schedule_label.configure(text=self._get_schedule_text())
                
                dialog.destroy()
                
            except ValueError as e:
                messagebox.showerror(
                    "Invalid Input",
                    str(e)
                )
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Save button
        save_button = create_button(
            button_frame,
            text="Save",
            command=validate_and_save,
            style="Primary.TButton",
            width=8
        )
        save_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Cancel button
        cancel_button = create_button(
            button_frame,
            text="Cancel",
            command=dialog.destroy,
            width=8
        )
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # Key bindings
        dialog.bind('<Return>', lambda e: validate_and_save())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def get_statistics(self) -> Dict:
        """Get statistics for all completed sessions"""
        return self.timer_service.get_statistics()