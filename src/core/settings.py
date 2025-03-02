"""
settings.py - Settings and configuration management
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, date,timedelta

from ..config.constants import (
    CONFIG_FILE, DEFAULT_WORK_DURATION, DEFAULT_SHORT_BREAK,
    DEFAULT_LONG_BREAK, DEFAULT_ALLOWED_DOMAINS
)

logger = logging.getLogger(__name__)

@dataclass
class TimerSettings:
    work_duration: int = DEFAULT_WORK_DURATION
    short_break: int = DEFAULT_SHORT_BREAK
    long_break: int = DEFAULT_LONG_BREAK
    auto_start_breaks: bool = True
    sound_enabled: bool = True
    pomodoros_per_long_break: int = 4

@dataclass
class Statistics:
    total_focus_time: int = 0
    completed_sessions: int = 0
    completed_today: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    last_session_date: Optional[str] = None

@dataclass
class Settings:
    timer: TimerSettings = TimerSettings()
    statistics: Statistics = Statistics()
    allowed_websites: List[str] = None
    blocked_websites: List[str] = None
    start_minimized: bool = False
    minimize_to_tray: bool = True
    block_during_breaks: bool = False
    
    def __post_init__(self):
        if self.allowed_websites is None:
            self.allowed_websites = DEFAULT_ALLOWED_DOMAINS.copy()
        if self.blocked_websites is None:
            self.blocked_websites = []

class SettingsManager:
    def __init__(self):
        self._settings = Settings()
        self._load_settings()
        self._check_day_reset()

    def _load_settings(self) -> None:
        """Load settings from config file"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                
                # Load timer settings
                timer_data = data.get('timer', {})
                self._settings.timer = TimerSettings(
                    work_duration=timer_data.get('work_duration', DEFAULT_WORK_DURATION),
                    short_break=timer_data.get('short_break', DEFAULT_SHORT_BREAK),
                    long_break=timer_data.get('long_break', DEFAULT_LONG_BREAK),
                    auto_start_breaks=timer_data.get('auto_start_breaks', True),
                    sound_enabled=timer_data.get('sound_enabled', True),
                    pomodoros_per_long_break=timer_data.get('pomodoros_per_long_break', 4)
                )
                
                # Load statistics
                stats_data = data.get('statistics', {})
                self._settings.statistics = Statistics(
                    total_focus_time=stats_data.get('total_focus_time', 0),
                    completed_sessions=stats_data.get('completed_sessions', 0),
                    completed_today=stats_data.get('completed_today', 0),
                    current_streak=stats_data.get('current_streak', 0),
                    longest_streak=stats_data.get('longest_streak', 0),
                    last_session_date=stats_data.get('last_session_date')
                )
                
                # Load website lists and preferences
                self._settings.allowed_websites = data.get('allowed_websites', DEFAULT_ALLOWED_DOMAINS.copy())
                self._settings.blocked_websites = data.get('blocked_websites', [])
                self._settings.start_minimized = data.get('start_minimized', False)
                self._settings.minimize_to_tray = data.get('minimize_to_tray', True)
                self._settings.block_during_breaks = data.get('block_during_breaks', False)
                
                logger.info("Settings loaded successfully")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            logger.info("Using default settings")

    def save_settings(self) -> None:
        """Save current settings to config file"""
        try:
            # Ensure config directory exists
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert settings to dictionary
            settings_dict = {
                'timer': asdict(self._settings.timer),
                'statistics': asdict(self._settings.statistics),
                'allowed_websites': self._settings.allowed_websites,
                'blocked_websites': self._settings.blocked_websites,
                'start_minimized': self._settings.start_minimized,
                'minimize_to_tray': self._settings.minimize_to_tray,
                'block_during_breaks': self._settings.block_during_breaks
            }
            
            # Save to file
            with open(CONFIG_FILE, 'w') as f:
                json.dump(settings_dict, f, indent=4)
                
            logger.info("Settings saved successfully")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            raise

    def _check_day_reset(self) -> None:
        """Reset daily statistics if it's a new day"""
        if self._settings.statistics.last_session_date:
            last_date = datetime.strptime(
                self._settings.statistics.last_session_date,
                "%Y-%m-%d"
            ).date()
            if last_date < date.today():
                self._settings.statistics.completed_today = 0

    def update_statistics(self, session_completed: bool = True, focus_minutes: int = 0) -> None:
        """Update statistics after a session"""
        stats = self._settings.statistics
        
        if session_completed:
            stats.completed_sessions += 1
            stats.completed_today += 1
            stats.total_focus_time += focus_minutes
            
            # Update streak
            if stats.last_session_date:
                last_date = datetime.strptime(stats.last_session_date, "%Y-%m-%d").date()
                if last_date == date.today() - timedelta(days=1):
                    stats.current_streak += 1
                    stats.longest_streak = max(stats.current_streak, stats.longest_streak)
                elif last_date < date.today() - timedelta(days=1):
                    stats.current_streak = 1
            else:
                stats.current_streak = 1
        
        stats.last_session_date = date.today().strftime("%Y-%m-%d")
        self.save_settings()

    def reset_statistics(self) -> None:
        """Reset all statistics"""
        self._settings.statistics = Statistics()
        self.save_settings()

    @property
    def settings(self) -> Settings:
        """Get current settings"""
        return self._settings

    @property
    def timer_settings(self) -> TimerSettings:
        """Get timer settings"""
        return self._settings.timer

    @property
    def statistics(self) -> Statistics:
        """Get statistics"""
        return self._settings.statistics