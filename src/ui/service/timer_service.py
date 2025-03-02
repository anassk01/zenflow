"""
timer_service.py - Service layer implementation for timer and statistics
"""
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, List, Set, Optional
import logging
import json
import os

from ...config.constants import APP_DIR
from .data_models import (
    TimerState, SessionType, SessionStatus, SessionRecord,
    StatisticsManager, TimerSessionManager
)

logger = logging.getLogger(__name__)

class StatsService:
    """Service for accessing statistics data"""
    
    def __init__(self, stats_manager: StatisticsManager):
        self.stats_manager = stats_manager
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics"""
        return self.stats_manager.get_summary_stats()
    
    def get_day_stats(self, date_key: Optional[str] = None) -> Dict:
        """Get statistics for a specific day"""
        return self.stats_manager.get_daily_stats(date_key)
    
    def get_week_stats(self, week_key: Optional[str] = None) -> Dict:
        """Get statistics for a specific week"""
        return self.stats_manager.get_weekly_stats(week_key)
    
    def get_month_stats(self, month_key: Optional[str] = None) -> Dict:
        """Get statistics for a specific month"""
        return self.stats_manager.get_monthly_stats(month_key)
    
    def get_available_days(self) -> List[str]:
        """Get list of days that have session records"""
        return self.stats_manager.get_session_days()
    
    def get_available_weeks(self) -> List[str]:
        """Get list of weeks that have session records"""
        return self.stats_manager.get_session_weeks()
    
    def get_available_months(self) -> List[str]:
        """Get list of months that have session records"""
        return self.stats_manager.get_session_months()
    
    def set_daily_goal(self, minutes: int) -> None:
        """Set daily goal in minutes"""
        self.stats_manager.set_daily_goal(minutes)
    
    def reset_statistics(self) -> None:
        """Reset all statistics"""
        self.stats_manager.clear_statistics()
    
    def save_statistics(self, file_path: Optional[str] = None) -> bool:
        """Save statistics to file"""
        if file_path is None:
            file_path = os.path.join(APP_DIR, "statistics.json")
            
        try:
            data = self.stats_manager.save_to_dict()
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving statistics: {e}")
            return False
    
    def load_statistics(self, file_path: Optional[str] = None) -> bool:
        """Load statistics from file"""
        if file_path is None:
            file_path = os.path.join(APP_DIR, "statistics.json")
            
        if not os.path.exists(file_path):
            logger.info(f"Statistics file not found: {file_path}")
            return False
            
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return self.stats_manager.load_from_dict(data)
        except Exception as e:
            logger.error(f"Error loading statistics: {e}")
            return False


class TimerService:
    """Service for managing timer sessions"""
    
    def __init__(self, timer_manager: TimerSessionManager):
        self.timer_manager = timer_manager
        self.timer_callback = None
    
    def start(self) -> None:
        """Start a new timer session"""
        self.timer_manager.start_session()
        if self.timer_callback:
            self.timer_callback()
    
    def pause(self) -> None:
        """Pause the current timer"""
        self.timer_manager.pause_session()
        if self.timer_callback:
            self.timer_callback()
    
    def resume(self) -> None:
        """Resume from paused state"""
        self.timer_manager.resume_session()
        if self.timer_callback:
            self.timer_callback()
    
    def skip(self) -> None:
        """Skip the current timer phase"""
        self.timer_manager.skip_session()
        if self.timer_callback:
            self.timer_callback()
    
    def stop(self) -> None:
        """Stop the current timer"""
        self.timer_manager.stop_session()
        if self.timer_callback:
            self.timer_callback()
    
    def update(self) -> None:
        """Update timer state - should be called every second"""
        self.timer_manager.update_session()
    
    def get_state(self) -> TimerState:
        """Get current timer state"""
        return self.timer_manager.state
    
    def get_session_info(self) -> Dict:
        """Get information about the current session"""
        return self.timer_manager.get_session_info()
    
    def get_settings(self) -> Dict:
        """Get timer settings"""
        return self.timer_manager.get_settings()
    
    def update_settings(self, settings: Dict) -> None:
        """Update timer settings"""
        self.timer_manager.update_settings(settings)
    
    def register_callback(self, callback) -> None:
        """Register callback to be called on timer state changes"""
        self.timer_callback = callback
    
    def get_statistics(self) -> Dict:
        """Get combined statistics for timer sessions"""
        # Get quick counts
        completed = 0
        skipped = 0
        partial = 0
        
        # Get all session data from stats manager
        sessions = self.timer_manager.stats_manager.all_sessions
        
        # Count work sessions by status
        for session in sessions:
            if session.type != SessionType.WORK:
                continue
                
            if session.status == SessionStatus.COMPLETED:
                completed += 1
            elif session.status == SessionStatus.SKIPPED:
                skipped += 1
            elif session.status == SessionStatus.PARTIAL:
                partial += 1
        
        # Return statistics
        return {
            'completed_sessions': completed,
            'skipped_sessions': skipped,
            'partial_sessions': partial,
            'total_sessions': completed + skipped + partial
        }


class ServiceProvider:
    """Central service provider for application components"""
    
    def __init__(self):
        # Create core managers
        self.stats_manager = StatisticsManager()
        self.timer_manager = TimerSessionManager(self.stats_manager)
        
        # Create services
        self.stats_service = StatsService(self.stats_manager)
        self.timer_service = TimerService(self.timer_manager)
        
        # Try to load saved statistics
        self.stats_service.load_statistics()
    
    def save_all_data(self) -> bool:
        """Save all application data"""
        return self.stats_service.save_statistics()