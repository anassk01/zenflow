"""
statistics.py - Completely rewritten statistics component with consistent tracking
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import calendar

from ..ui_config import (
    DEFAULT_PADDING, SECTION_PADDING,
    create_button, create_section_frame,
    ScrollableFrame
)
from ...config.constants import COLORS, FONTS
from ..service import StatsService



logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)  # Only show errors

class StatisticsFrame(ttk.Frame):
    """Reimplemented statistics display with reliable data handling"""
    
    def __init__(
        self,
        parent: tk.Widget,
        stats_service: StatsService,
        work_duration: int = 25,        # Default work duration in minutes
        on_reset: Optional[callable] = None
    ):
        super().__init__(parent)
        
        # Store references
        self.stats_service = stats_service
        self.work_duration = work_duration
        self.on_reset = on_reset
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Make history expandable
        
        # Track current view state
        self.current_view = "Daily"  # Default view
        self.selected_date = date.today().strftime("%Y-%m-%d")  # Default to today
        self.selected_week = None  # Will be determined from today
        self.selected_month = date.today().strftime("%Y-%m")  # Default to current month
        
        # Create UI components
        self._create_widgets()
        
        # Initial display update
        self._update_display()
        
        # Schedule periodic updates
        self._schedule_updates()
        
    def _create_widgets(self):
        """Create statistics display widgets"""
        # Today's Overview Section
        self._create_overview_section()
        
        # Statistics Grid Section
        self._create_stats_section()
        
        # History Section (Scrollable)
        self._create_history_section()
        
    def _create_overview_section(self):
        """Create today's overview section with progress"""
        overview_frame = ttk.LabelFrame(
            self,
            text="Today's Overview",
            padding=(10, 5)
        )
        overview_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(0, 10))
        overview_frame.grid_columnconfigure(0, weight=1)
        
        # Progress container
        progress_frame = ttk.Frame(overview_frame, padding=5)
        progress_frame.grid(row=0, column=0, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)
        
        # Today's time label
        ttk.Label(
            progress_frame,
            text="Today's Focus Time",
            font=FONTS['subtitle'],
            foreground=COLORS['primary']
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        # Progress bar container
        bar_frame = ttk.Frame(progress_frame)
        bar_frame.grid(row=1, column=0, sticky="ew")
        bar_frame.grid_columnconfigure(0, weight=1)
        
        # Progress bar
        self.time_progress = ttk.Progressbar(
            bar_frame,
            mode='determinate',
            maximum=100,
            style="Progress.Horizontal.TProgressbar"
        )
        self.time_progress.grid(row=0, column=0, sticky="ew")
        
        # Progress info frame
        info_frame = ttk.Frame(progress_frame)
        info_frame.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        info_frame.grid_columnconfigure(1, weight=1)
        
        # Progress text
        self.progress_label = ttk.Label(
            info_frame,
            text="0 min / 120 min",
            font=FONTS['body']
        )
        self.progress_label.grid(row=0, column=0, sticky="w")
        
        # Session info
        self.session_label = ttk.Label(
            info_frame,
            text="Sessions: 0 completed of 0 attempted",
            font=FONTS['body']
        )
        self.session_label.grid(row=1, column=0, sticky="w", pady=(5, 0))
        
        # Goal button
        self.goal_button = create_button(
            info_frame,
            text="Set Goal",
            command=self._show_goal_dialog,
            style="Action.TButton",
            width=8
        )
        self.goal_button.grid(row=0, column=1, sticky="e")
        
    def _create_stats_section(self):
        """Create statistics grid section"""
        stats_frame = ttk.LabelFrame(
            self,
            text="Focus Statistics",
            padding=(10, 5)
        )
        stats_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 10))
        
        # Statistics grid
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X, expand=True)
        
        # Configure grid columns for even spacing
        for i in range(2):
            stats_grid.grid_columnconfigure(i, weight=1)
        
        # Statistics labels storage
        self.stat_values = {}
        self._create_stat_labels(stats_grid)
        
    def _create_history_section(self):
        """Create historical data section with scrolling"""
        history_frame = ttk.LabelFrame(
            self,
            text="Focus History",
            padding=(10, 5)
        )
        history_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=(0, 10))
        history_frame.grid_rowconfigure(0, weight=1)
        history_frame.grid_columnconfigure(0, weight=1)
        
        # Scrollable container for history
        self.history_scroll = ScrollableFrame(history_frame)
        self.history_scroll.grid(row=0, column=0, sticky="nsew")
        
        # Create treeview inside scrollable frame
        self._create_history_treeview(self.history_scroll.scrollable_frame)
        
        # Control buttons
        control_frame = ttk.Frame(self)
        control_frame.grid(row=3, column=0, sticky="ew", padx=5)
        
        create_button(
            control_frame,
            text="Reset Statistics",
            command=self._reset_stats,
            style="Action.TButton"
        ).pack(side=tk.RIGHT)
        
        # View selector
        view_frame = ttk.Frame(control_frame)
        view_frame.pack(side=tk.LEFT)
        
        ttk.Label(view_frame, text="View:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.view_var = tk.StringVar(value="Daily")
        ttk.Radiobutton(
            view_frame, 
            text="Daily", 
            variable=self.view_var, 
            value="Daily",
            command=self._change_history_view
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            view_frame, 
            text="Weekly", 
            variable=self.view_var, 
            value="Weekly",
            command=self._change_history_view
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            view_frame, 
            text="Monthly", 
            variable=self.view_var, 
            value="Monthly",
            command=self._change_history_view
        ).pack(side=tk.LEFT, padx=5)
        
    def _create_stat_labels(self, container):
        """Create statistics labels with proper formatting"""
        summary = self.stats_service.get_summary_stats()
        
        # Extract values for display
        all_time = summary.get("all_time", {})
        streak = summary.get("streak", {})
        
        total_time = all_time.get("effective_minutes", 0)
        sessions_completed = all_time.get("completed_sessions", 0)
        daily_average = all_time.get("daily_average", 0)
        current_streak = streak.get("current", 0)
        longest_streak = streak.get("longest", 0)
        completion_rate = all_time.get("completion_rate", 0)
        
        labels = [
            ("Total Focus Time:", self._format_time(total_time)),
            ("Sessions Completed:", f"{sessions_completed}"),
            ("Daily Average:", self._format_time(daily_average)),
            ("Current Streak:", f"{current_streak} days"),
            ("Longest Streak:", f"{longest_streak} days"),
            ("Completion Rate:", f"{completion_rate:.1f}%")
        ]
        
        # Create labels in grid layout
        for i, (label, initial) in enumerate(labels):
            row = i // 2
            col = i % 2
            
            # Container for label pair
            frame = ttk.Frame(container)
            frame.grid(row=row, column=col, padx=10, pady=5, sticky="nsew")
            frame.grid_columnconfigure(0, weight=1)
            
            # Title label
            ttk.Label(
                frame,
                text=label,
                font=FONTS['body'],
                foreground=COLORS['text_secondary']
            ).grid(row=0, column=0, sticky="w")
            
            # Value label
            value_label = ttk.Label(
                frame,
                text=initial,
                font=FONTS['body']
            )
            value_label.grid(row=1, column=0, sticky="w")
            
            self.stat_values[label] = value_label
            
    def _create_history_treeview(self, container):
        """Create and configure history treeview"""
        # Create treeview
        self.history_tree = ttk.Treeview(
            container,
            columns=("date", "time", "sessions", "completion"),
            show="headings",
            height=10,
            style="History.Treeview"
        )
        
        # Configure columns
        columns = [
            ("date", "Date", 100),
            ("time", "Focus Time", 100),
            ("sessions", "Sessions", 80),
            ("completion", "Completion", 100)
        ]
        
        for col, heading, width in columns:
            self.history_tree.heading(col, text=heading)
            self.history_tree.column(col, width=width, minwidth=width)
        
        # Configure tag for today's record
        self.history_tree.tag_configure(
            'today',
            foreground=COLORS['primary']
        )
        
        self.history_tree.tag_configure(
            'goal-met',
            foreground=COLORS['success']
        )
        
        # Pack treeview with proper expansion
        self.history_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind selection event
        self.history_tree.bind('<<TreeviewSelect>>', self._on_history_select)
    
    def _schedule_updates(self, interval_ms=30000):
        """Schedule periodic updates (every 30 seconds by default)"""
        self._update_display()
        self.after(interval_ms, lambda: self._schedule_updates(interval_ms))
        
    def _update_display(self):
        """Update all statistics displays"""
        # Get fresh data
        summary = self.stats_service.get_summary_stats()
        today = summary.get("today", {})
        streak = summary.get("streak", {})
        goal = summary.get("goal", {})
        all_time = summary.get("all_time", {})
        
        # Update progress bar
        progress = goal.get("today_progress", 0)
        self.time_progress['value'] = progress
        
        # Update progress labels
        today_minutes = today.get("effective_minutes", 0)
        goal_minutes = goal.get("daily_minutes", 120)
        self.progress_label.configure(
            text=f"{self._format_time(today_minutes)} / {self._format_time(goal_minutes)}"
        )
        
        completed = today.get("completed_count", 0)
        total = today.get("total_count", 0)
        self.session_label.configure(
            text=f"Sessions: {completed} completed of {total} attempted"
        )
        
        # Update statistics values
        stats = {
            "Total Focus Time:": self._format_time(all_time.get("effective_minutes", 0)),
            "Sessions Completed:": str(all_time.get("completed_sessions", 0)),
            "Daily Average:": self._format_time(all_time.get("daily_average", 0)),
            "Current Streak:": f"{streak.get('current', 0)} days",
            "Longest Streak:": f"{streak.get('longest', 0)} days",
            "Completion Rate:": f"{all_time.get('completion_rate', 0):.1f}%"
        }
        
        for label, value in stats.items():
            if label in self.stat_values:
                self.stat_values[label].configure(text=value)
            
        # Update history display
        self._update_history_display()
        
    def _update_history_display(self):
        """Update history treeview with selected view"""
        # Force stats service to rebuild caches
        self.stats_service.stats_manager._cache_valid = False
        self.stats_service.stats_manager._build_caches()
        
        view_type = self.view_var.get()
        
        if view_type == "Daily":
            self._show_daily_history()
        elif view_type == "Weekly":
            self._show_weekly_history()
        elif view_type == "Monthly":
            self._show_monthly_history()
            
    def _show_daily_history(self):
        """Show daily history records"""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
            
        # Update column headings for daily view
        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("time", text="Focus Time")
        self.history_tree.heading("sessions", text="Sessions")
        self.history_tree.heading("completion", text="Completion")
        
        # Get available days
        days = self.stats_service.get_available_days()
        
        # Add records
        for day_key in days:
            # Get day stats
            day_stats = self.stats_service.get_day_stats(day_key)
            
            # Prepare display values
            date_display = day_key
            try:
                date_obj = datetime.strptime(day_key, "%Y-%m-%d").date()
                date_display = date_obj.strftime("%a, %b %d")
            except:
                pass
                
            time_display = self._format_time(day_stats.get("effective_minutes", 0))
            sessions_display = f"{day_stats.get('completed_count', 0)} sessions"
            completion_display = f"{day_stats.get('completion_rate', 0):.1f}%"
            
            # Determine tags
            tags = []
            if day_key == date.today().strftime("%Y-%m-%d"):
                tags.append('today')
                
            if day_stats.get("goal_percent", 0) >= 100:
                tags.append('goal-met')
                
            # Insert into tree
            self.history_tree.insert(
                "",
                0,  # Insert at top for newest first
                values=(
                    date_display,
                    time_display,
                    sessions_display,
                    completion_display
                ),
                tags=tuple(tags)
            )
            
    def _show_weekly_history(self):
        """Show weekly history records"""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
            
        # Update column headings for weekly view
        self.history_tree.heading("date", text="Week")
        self.history_tree.heading("time", text="Focus Time")
        self.history_tree.heading("sessions", text="Sessions")
        self.history_tree.heading("completion", text="Daily Avg")
            
        # Get available weeks
        weeks = self.stats_service.get_available_weeks()
        
        # Add records
        for week_key in weeks:
            # Get week stats
            week_stats = self.stats_service.get_week_stats(week_key)
            
            # Prepare display values
            date_range = week_key
            if week_stats.get("start_date") and week_stats.get("end_date"):
                start_date = datetime.strptime(week_stats.get("start_date"), "%Y-%m-%d").date()
                end_date = datetime.strptime(week_stats.get("end_date"), "%Y-%m-%d").date()
                
                # Show date range
                month1 = start_date.strftime("%b")
                month2 = end_date.strftime("%b")
                
                if month1 == month2:
                    date_range = f"{month1} {start_date.day}-{end_date.day}"
                else:
                    date_range = f"{month1} {start_date.day}-{month2} {end_date.day}"
                    
                date_range = f"{week_key} ({date_range})"
            
            time_display = self._format_time(week_stats.get("effective_minutes", 0))
            sessions_display = f"{week_stats.get('completed_count', 0)} sessions"
            daily_avg = week_stats.get("daily_average", 0)
            avg_display = self._format_time(int(daily_avg))
            
            # Determine tags
            tags = []
            today = date.today()
            year, week, _ = today.isocalendar()
            current_week = f"{year}-W{week:02d}"
            
            if week_key == current_week:
                tags.append('today')
            
            # Insert into tree
            self.history_tree.insert(
                "",
                0,  # Insert at top for newest first
                values=(
                    date_range,
                    time_display,
                    sessions_display,
                    avg_display
                ),
                tags=tuple(tags)
            )
            
    def _show_monthly_history(self):
        """Show monthly history records"""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
            
        # Update column headings for monthly view
        self.history_tree.heading("date", text="Month")
        self.history_tree.heading("time", text="Focus Time")
        self.history_tree.heading("sessions", text="Sessions")
        self.history_tree.heading("completion", text="Daily Avg")
            
        # Get available months
        months = self.stats_service.get_available_months()
        
        # Add records
        for month_key in months:
            # Get month stats
            month_stats = self.stats_service.get_month_stats(month_key)
            
            # Prepare display values
            date_display = month_stats.get("month_name", month_key)
            time_display = self._format_time(month_stats.get("effective_minutes", 0))
            sessions_display = f"{month_stats.get('completed_count', 0)} sessions"
            daily_avg = month_stats.get("daily_average", 0)
            avg_display = self._format_time(int(daily_avg))
            
            # Determine tags
            tags = []
            current_month = date.today().strftime("%Y-%m")
            
            if month_key == current_month:
                tags.append('today')
            
            # Insert into tree
            self.history_tree.insert(
                "",
                0,  # Insert at top for newest first
                values=(
                    date_display,
                    time_display,
                    sessions_display,
                    avg_display
                ),
                tags=tuple(tags)
            )
            
    def _on_history_select(self, event):
        """Handle selection in history view"""
        selected = self.history_tree.selection()
        if not selected:
            return
            
        # Get selected item
        item = selected[0]
        values = self.history_tree.item(item, 'values')
        
        # Handle based on current view
        view_type = self.view_var.get()
        
        if view_type == "Daily":
            # Extract date from item (currently just taking what's visible)
            # In a full implementation, would store the date key as a tag or hidden field
            date_str = values[0]
        elif view_type == "Weekly":
            # Extract week from item
            week_str = values[0].split(" ")[0]
        elif view_type == "Monthly":
            # Extract month from item
            month_str = values[0]
            
    def _change_history_view(self):
        """Handle change of history view"""
        self.current_view = self.view_var.get()
        self._update_history_display()
        
    def _show_goal_dialog(self):
        """Show dialog to configure daily goal"""
        dialog = tk.Toplevel(self)
        dialog.title("Set Daily Goal")
        dialog.geometry("300x200")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Content frame
        content = ttk.Frame(dialog, padding=DEFAULT_PADDING)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Goal input section
        input_frame = ttk.Frame(content)
        input_frame.pack(fill=tk.X, pady=10)
        
        # Get current goal
        summary = self.stats_service.get_summary_stats()
        current_goal = summary.get("goal", {}).get("daily_minutes", 120)
        
        # Goal label
        ttk.Label(
            input_frame,
            text="Daily Focus Goal:",
            font=FONTS['body']
        ).pack(anchor="w", pady=(0, 5))

        # Help text
        ttk.Label(
            input_frame,
            text="Enter time in minutes (max 1440)",
            font=FONTS['small'],
            foreground=COLORS['text_secondary']
        ).pack(anchor="w", pady=(0, 10))
        
        # Entry field
        goal_var = tk.StringVar(value=str(current_goal))
        entry = ttk.Entry(input_frame, textvariable=goal_var, width=15)
        entry.pack(pady=(0, 10))
        entry.focus()
        
        # Current value display
        current_text = f"Current goal: {self._format_time(current_goal)}"
        current_label = ttk.Label(
            input_frame,
            text=current_text,
            font=FONTS['small'],
            foreground=COLORS['text_secondary']
        )
        current_label.pack(pady=(0, 10))
        
        def validate_and_save():
            """Validate and save new goal"""
            try:
                new_goal = int(goal_var.get())
                if new_goal <= 0:
                    raise ValueError("Goal must be positive")
                if new_goal > 1440:  # 24 hours in minutes
                    raise ValueError("Goal cannot exceed 24 hours")
                    
                # Update goal in service
                self.stats_service.set_daily_goal(new_goal)
                
                # Update display
                self._update_display()
                dialog.destroy()
                
            except ValueError as e:
                messagebox.showerror(
                    "Invalid Input",
                    str(e) if len(str(e).split()) > 3 else "Please enter a valid number"
                )
                entry.focus()
        
        # Button frame
        button_frame = ttk.Frame(content)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Save button
        save_btn = create_button(
            button_frame,
            text="Save",
            command=validate_and_save,
            style="Primary.TButton",
            width=8
        )
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        cancel_btn = create_button(
            button_frame,
            text="Cancel",
            command=dialog.destroy,
            width=8
        )
        cancel_btn.pack(side=tk.RIGHT)
        
        # Key bindings
        dialog.bind('<Return>', lambda e: validate_and_save())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
            
    def _reset_stats(self):
        """Reset all statistics with confirmation"""
        if not messagebox.askyesno(
            "Reset Statistics",
            "Are you sure you want to reset all statistics?\n"
            "This action cannot be undone.",
            icon='warning'
        ):
            return
            
        # Reset via service
        self.stats_service.reset_statistics()
        
        # Update display
        self._update_display()
        
        # Notify callback
        if self.on_reset:
            self.on_reset()
            
    def _format_time(self, minutes: int) -> str:
        """Format time duration for display"""
        if minutes == 0:
            return "0 min"
            
        if minutes < 60:
            return f"{minutes} min"
        
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        if remaining_minutes == 0:
            return f"{hours}h"
        
        return f"{hours}h {remaining_minutes}m"