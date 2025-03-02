"""
data_models.py - Core data models for ZenFlow app
"""
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum, auto
from typing import Dict, List, Set, Optional
import json
import logging
import calendar

logger = logging.getLogger(__name__)

class TimerState(Enum):
    """Timer states"""
    IDLE = auto()
    WORKING = auto()
    SHORT_BREAK = auto()
    LONG_BREAK = auto()
    PAUSED = auto()
    COMPLETED = auto()

class SessionType(Enum):
    """Session types for record keeping"""
    WORK = auto()
    SHORT_BREAK = auto()
    LONG_BREAK = auto()

class SessionStatus(Enum):
    """Session completion status"""
    COMPLETED = auto()  # Completed fully 
    PARTIAL = auto()    # Started but not completed
    SKIPPED = auto()    # Skipped via button
    INTERRUPTED = auto() # Interrupted by app close or reset

@dataclass
class SessionRecord:
    """Record of a single focus/break session"""
    # Session metadata
    session_id: str  # Unique identifier
    type: SessionType  # WORK, SHORT_BREAK, LONG_BREAK
    status: SessionStatus  # COMPLETED, PARTIAL, SKIPPED, INTERRUPTED
    
    # Timing data
    start_time: datetime  
    end_time: Optional[datetime] = None
    planned_duration: int = 0  # Duration in seconds
    actual_duration: int = 0  # Actual time spent in seconds
    effective_duration: int = 0  # Time minus pauses in seconds
    
    # Pause tracking
    pause_count: int = 0
    total_pause_duration: int = 0  # In seconds
    
    # Date grouping helpers (derived)
    date_key: str = field(default="")  # YYYY-MM-DD
    week_key: str = field(default="")  # YYYY-Www
    month_key: str = field(default="")  # YYYY-MM
    
    def __post_init__(self):
        """Generate date keys after initialization"""
        dt = self.start_time
        
        logger.debug(f"Generating date keys from: {dt}")
        
        # Generate date_key in YYYY-MM-DD format
        self.date_key = dt.strftime("%Y-%m-%d")
        
        # ISO week format
        year, week, _ = dt.isocalendar()
        self.week_key = f"{year}-W{week:02d}"
        
        # Month format
        self.month_key = dt.strftime("%Y-%m")
        
        logger.debug(f"Generated keys: date_key={self.date_key}, week_key={self.week_key}, month_key={self.month_key}")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "session_id": self.session_id,
            "type": self.type.name,
            "status": self.status.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "planned_duration": self.planned_duration,
            "actual_duration": self.actual_duration,
            "effective_duration": self.effective_duration,
            "pause_count": self.pause_count,
            "total_pause_duration": self.total_pause_duration,
            "date_key": self.date_key,
            "week_key": self.week_key,
            "month_key": self.month_key
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SessionRecord':
        """Create from dictionary"""
        return cls(
            session_id=data["session_id"],
            type=SessionType[data["type"]],
            status=SessionStatus[data["status"]],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            planned_duration=data["planned_duration"],
            actual_duration=data["actual_duration"],
            effective_duration=data["effective_duration"],
            pause_count=data["pause_count"],
            total_pause_duration=data["total_pause_duration"],
            date_key=data["date_key"],
            week_key=data["week_key"],
            month_key=data["month_key"]
        )

class StatisticsManager:
    """Centralized statistics management with consistent storage and retrieval"""
    
    def __init__(self):
        # Session records
        self.all_sessions: List[SessionRecord] = []
        
        # Current session tracking
        self.current_streak: int = 0
        self.longest_streak: int = 0
        self.last_focus_date: Optional[str] = None
        
        # Settings
        self.daily_goal_minutes: int = 120  # Default 2 hours daily goal
        
        # Aggregation caches (for performance)
        self._daily_cache: Dict[str, Dict] = {}
        self._weekly_cache: Dict[str, Dict] = {}
        self._monthly_cache: Dict[str, Dict] = {}
        self._cache_valid: bool = False
    
    def add_session(self, session: SessionRecord) -> None:
        """Add a new session record and update statistics"""
        # Add to records
        self.all_sessions.append(session)
        
        # Only update streak for completed work sessions
        if session.type == SessionType.WORK and session.status == SessionStatus.COMPLETED:
            self._update_streak(session.date_key)
        
        # Invalidate caches - make sure this happens!
        self._cache_valid = False
        self._build_caches()  #

    
    def _update_streak(self, date_key: str) -> None:
        """Update streak information"""
        today = date.today().strftime("%Y-%m-%d")
        
        # Check if this is a new day
        if self.last_focus_date is None:
            # First session ever
            self.current_streak = 1
            self.longest_streak = 1
            self.last_focus_date = date_key
        elif date_key != self.last_focus_date:
            # New day
            if date_key == today:
                # Today's session
                prev_date = datetime.strptime(self.last_focus_date, "%Y-%m-%d").date()
                today_date = datetime.strptime(date_key, "%Y-%m-%d").date()
                days_diff = (today_date - prev_date).days
                
                if days_diff == 1:
                    # Consecutive day
                    self.current_streak += 1
                    self.longest_streak = max(self.current_streak, self.longest_streak)
                elif days_diff > 1:
                    # Streak broken
                    self.current_streak = 1
            
            # Update last focus date
            self.last_focus_date = date_key
    
    def _build_caches(self) -> None:
        """Build caches for quick statistics access"""
        # Clear existing caches
        self._daily_cache = {}
        self._weekly_cache = {}
        self._monthly_cache = {}
        
        # Aggregate by date
        for session in self.all_sessions:
            # Skip non-work sessions for statistics
            if session.type != SessionType.WORK:
                continue
                
            # Daily aggregation
            if session.date_key not in self._daily_cache:
                self._daily_cache[session.date_key] = {
                    "total_time": 0,
                    "effective_time": 0,
                    "completed_count": 0,
                    "partial_count": 0,
                    "skipped_count": 0,
                    "interrupted_count": 0,
                    "total_count": 0,
                    "pause_count": 0,
                    "total_pause_duration": 0
                }
                
            # Weekly aggregation 
            if session.week_key not in self._weekly_cache:
                self._weekly_cache[session.week_key] = {
                    "total_time": 0,
                    "effective_time": 0,
                    "completed_count": 0,
                    "partial_count": 0,
                    "skipped_count": 0,
                    "interrupted_count": 0,
                    "total_count": 0,
                    "active_days": set(),
                    "pause_count": 0,
                    "total_pause_duration": 0
                }
                
            # Monthly aggregation
            if session.month_key not in self._monthly_cache:
                self._monthly_cache[session.month_key] = {
                    "total_time": 0,
                    "effective_time": 0,
                    "completed_count": 0,
                    "partial_count": 0,
                    "skipped_count": 0,
                    "interrupted_count": 0,
                    "total_count": 0,
                    "active_days": set(),
                    "pause_count": 0,
                    "total_pause_duration": 0
                }
                
            # Update daily stats
            daily = self._daily_cache[session.date_key]
            daily["total_time"] += session.actual_duration
            daily["effective_time"] += session.effective_duration
            daily["total_count"] += 1
            daily["pause_count"] += session.pause_count
            daily["total_pause_duration"] += session.total_pause_duration
            
            if session.status == SessionStatus.COMPLETED:
                daily["completed_count"] += 1
            elif session.status == SessionStatus.PARTIAL:
                daily["partial_count"] += 1
            elif session.status == SessionStatus.SKIPPED:
                daily["skipped_count"] += 1
            elif session.status == SessionStatus.INTERRUPTED:
                daily["interrupted_count"] += 1
            
            # Update weekly stats
            weekly = self._weekly_cache[session.week_key]
            weekly["total_time"] += session.actual_duration
            weekly["effective_time"] += session.effective_duration
            weekly["total_count"] += 1
            weekly["active_days"].add(session.date_key)
            weekly["pause_count"] += session.pause_count
            weekly["total_pause_duration"] += session.total_pause_duration
            
            if session.status == SessionStatus.COMPLETED:
                weekly["completed_count"] += 1
            elif session.status == SessionStatus.PARTIAL:
                weekly["partial_count"] += 1
            elif session.status == SessionStatus.SKIPPED:
                weekly["skipped_count"] += 1
            elif session.status == SessionStatus.INTERRUPTED:
                weekly["interrupted_count"] += 1
            
            # Update monthly stats
            monthly = self._monthly_cache[session.month_key]
            monthly["total_time"] += session.actual_duration
            monthly["effective_time"] += session.effective_duration
            monthly["total_count"] += 1
            monthly["active_days"].add(session.date_key)
            monthly["pause_count"] += session.pause_count
            monthly["total_pause_duration"] += session.total_pause_duration
            
            if session.status == SessionStatus.COMPLETED:
                monthly["completed_count"] += 1
            elif session.status == SessionStatus.PARTIAL:
                monthly["partial_count"] += 1
            elif session.status == SessionStatus.SKIPPED:
                monthly["skipped_count"] += 1
            elif session.status == SessionStatus.INTERRUPTED:
                monthly["interrupted_count"] += 1
        
        # Mark caches as valid
        self._cache_valid = True
    
    def get_daily_stats(self, date_key: Optional[str] = None) -> Dict:
        """Get statistics for a specific day"""
        if not self._cache_valid:
            self._build_caches()
            
        if date_key is None:
            # Force today's date in the correct format
            date_key = date.today().strftime("%Y-%m-%d")
        
        logger.debug(f"Looking for date_key: {date_key}, Available keys: {list(self._daily_cache.keys())}")
        
        if date_key in self._daily_cache:
            stats = self._daily_cache[date_key].copy()
            # Convert seconds to minutes for API consistency
            stats["total_minutes"] = round(stats["total_time"] / 60)
            stats["effective_minutes"] = round(stats["effective_time"] / 60)
            stats["goal_minutes"] = self.daily_goal_minutes
            stats["goal_percent"] = min(100, (stats["effective_minutes"] / self.daily_goal_minutes) * 100) if self.daily_goal_minutes > 0 else 0
            stats["date"] = date_key
            
            # Calculate completion rate
            if stats["total_count"] > 0:
                stats["completion_rate"] = (stats["completed_count"] / stats["total_count"]) * 100
            else:
                stats["completion_rate"] = 0
                
            return stats
        else:
            # Empty stats for day with no sessions
            return {
                "total_time": 0,
                "effective_time": 0,
                "total_minutes": 0,
                "effective_minutes": 0,
                "completed_count": 0,
                "partial_count": 0,
                "skipped_count": 0,
                "interrupted_count": 0,
                "total_count": 0,
                "pause_count": 0,
                "total_pause_duration": 0,
                "goal_minutes": self.daily_goal_minutes,
                "goal_percent": 0,
                "date": date_key,
                "completion_rate": 0
            }
    
    def get_weekly_stats(self, week_key: Optional[str] = None) -> Dict:
        """Get statistics for a specific week"""
        if not self._cache_valid:
            self._build_caches()
            
        if week_key is None:
            # Current week
            today = date.today()
            year, week, _ = today.isocalendar()
            week_key = f"{year}-W{week:02d}"
            
        if week_key in self._weekly_cache:
            stats = self._weekly_cache[week_key].copy()
            # Convert seconds to minutes for API consistency
            stats["total_minutes"] = round(stats["total_time"] / 60)
            stats["effective_minutes"] = round(stats["effective_time"] / 60)
            
            # Calculate dates for the week
            try:
                year, week = week_key.split("-W")
                # ISO week date format - first day is Monday
                first_day = datetime.strptime(f"{year}-{week}-1", "%Y-%W-%w").date()
                # Convert active days to list for serialization
                stats["active_days"] = sorted(list(stats["active_days"]))
                stats["week"] = week_key
                stats["start_date"] = first_day.strftime("%Y-%m-%d")
                stats["end_date"] = (first_day + timedelta(days=6)).strftime("%Y-%m-%d")
                
                # Add day names for display
                stats["day_names"] = []
                for i in range(7):
                    day = first_day + timedelta(days=i)
                    stats["day_names"].append(day.strftime("%a %d"))
                
                # Add daily breakdown
                stats["daily_breakdown"] = []
                for i in range(7):
                    day = first_day + timedelta(days=i)
                    day_key = day.strftime("%Y-%m-%d")
                    day_stats = self.get_daily_stats(day_key)
                    stats["daily_breakdown"].append({
                        "date": day_key,
                        "day_name": day.strftime("%a"),
                        "minutes": day_stats["effective_minutes"],
                        "sessions": day_stats["total_count"]
                    })
            except Exception as e:
                logger.error(f"Error calculating week dates: {e}")
                stats["active_days"] = sorted(list(stats["active_days"]))
                stats["week"] = week_key
                stats["start_date"] = ""
                stats["end_date"] = ""
                stats["day_names"] = []
                stats["daily_breakdown"] = []
                
            # Calculate completion rate
            if stats["total_count"] > 0:
                stats["completion_rate"] = (stats["completed_count"] / stats["total_count"]) * 100
            else:
                stats["completion_rate"] = 0
                
            # Calculate daily average (active days only)
            if len(stats["active_days"]) > 0:
                stats["daily_average"] = stats["total_minutes"] / len(stats["active_days"])
            else:
                stats["daily_average"] = 0
                
            return stats
        else:
            # Empty stats for week with no sessions
            return {
                "total_time": 0,
                "effective_time": 0,
                "total_minutes": 0,
                "effective_minutes": 0,
                "completed_count": 0,
                "partial_count": 0,
                "skipped_count": 0,
                "interrupted_count": 0,
                "total_count": 0,
                "active_days": [],
                "pause_count": 0,
                "total_pause_duration": 0,
                "week": week_key,
                "start_date": "",
                "end_date": "",
                "day_names": [],
                "daily_breakdown": [],
                "completion_rate": 0,
                "daily_average": 0
            }
    
    def get_monthly_stats(self, month_key: Optional[str] = None) -> Dict:
        """Get statistics for a specific month"""
        if not self._cache_valid:
            self._build_caches()
            
        if month_key is None:
            # Current month
            month_key = date.today().strftime("%Y-%m")
            
        if month_key in self._monthly_cache:
            stats = self._monthly_cache[month_key].copy()
            # Convert seconds to minutes for API consistency
            stats["total_minutes"] = round(stats["total_time"] / 60)
            stats["effective_minutes"] = round(stats["effective_time"] / 60)
            
            # Calculate month information
            try:
                year, month = month_key.split("-")
                year, month = int(year), int(month)
                
                # Month name
                first_day = date(year, month, 1)
                stats["month_name"] = first_day.strftime("%B %Y")
                stats["active_days"] = sorted(list(stats["active_days"]))
                stats["month"] = month_key
                
                # Calculate days in month
                _, last_day = calendar.monthrange(year, month)
                stats["days_in_month"] = last_day
                
                # Add daily breakdown
                stats["daily_breakdown"] = []
                for day in range(1, last_day + 1):
                    day_date = date(year, month, day)
                    day_key = day_date.strftime("%Y-%m-%d")
                    
                    # Only include days up to today for current month
                    if day_date > date.today():
                        break
                        
                    day_stats = self.get_daily_stats(day_key)
                    stats["daily_breakdown"].append({
                        "date": day_key,
                        "day": day,
                        "minutes": day_stats["effective_minutes"],
                        "sessions": day_stats["total_count"]
                    })
            except Exception as e:
                logger.error(f"Error calculating month information: {e}")
                stats["active_days"] = sorted(list(stats["active_days"]))
                stats["month"] = month_key
                stats["month_name"] = month_key
                stats["days_in_month"] = 0
                stats["daily_breakdown"] = []
                
            # Calculate completion rate
            if stats["total_count"] > 0:
                stats["completion_rate"] = (stats["completed_count"] / stats["total_count"]) * 100
            else:
                stats["completion_rate"] = 0
                
            # Calculate daily average (active days only)
            if len(stats["active_days"]) > 0:
                stats["daily_average"] = stats["total_minutes"] / len(stats["active_days"])
            else:
                stats["daily_average"] = 0
                
            return stats
        else:
            # Empty stats for month with no sessions
            return {
                "total_time": 0,
                "effective_time": 0,
                "total_minutes": 0,
                "effective_minutes": 0,
                "completed_count": 0,
                "partial_count": 0,
                "skipped_count": 0,
                "interrupted_count": 0,
                "total_count": 0,
                "active_days": [],
                "pause_count": 0,
                "total_pause_duration": 0,
                "month": month_key,
                "month_name": month_key,
                "days_in_month": 0,
                "daily_breakdown": [],
                "completion_rate": 0,
                "daily_average": 0
            }
    
    def get_summary_stats(self) -> Dict:
        """Get overall summary statistics"""
        if not self._cache_valid:
            self._build_caches()
            
        # Calculate total statistics
        total_sessions = 0
        completed_sessions = 0
        total_minutes = 0
        effective_minutes = 0
        total_days = len(self._daily_cache)
        
        for date_key, daily in self._daily_cache.items():
            total_sessions += daily["total_count"]
            completed_sessions += daily["completed_count"]
            total_minutes += daily["total_time"] / 60  # Convert seconds to minutes
            effective_minutes += daily["effective_time"] / 60
        
        # Calculate averages and rates
        daily_average = round(effective_minutes / total_days) if total_days > 0 else 0
        completion_rate = (completed_sessions / total_sessions) * 100 if total_sessions > 0 else 0
        
        # Get today's stats
        today_stats = self.get_daily_stats()
        
        # Create summary
        return {
            "all_time": {
                "total_sessions": total_sessions,
                "completed_sessions": completed_sessions,
                "total_minutes": round(total_minutes),
                "effective_minutes": round(effective_minutes),
                "active_days": total_days,
                "daily_average": daily_average,
                "completion_rate": completion_rate
            },
            "today": today_stats,
            "streak": {
                "current": self.current_streak,
                "longest": self.longest_streak,
                "last_date": self.last_focus_date
            },
            "goal": {
                "daily_minutes": self.daily_goal_minutes,
                "today_progress": today_stats["goal_percent"]
            }
        }
    
    def get_session_days(self) -> List[str]:
        """Get list of days that have session records"""
        if not self._cache_valid:
            self._build_caches()
        days = sorted(list(self._daily_cache.keys()), reverse=True)
        logger.debug(f"Available session days: {days}")
        return days
    
    def get_session_weeks(self) -> List[str]:
        """Get list of weeks that have session records"""
        if not self._cache_valid:
            self._build_caches()
        return sorted(list(self._weekly_cache.keys()), reverse=True)
    
    def get_session_months(self) -> List[str]:
        """Get list of months that have session records"""
        if not self._cache_valid:
            self._build_caches()
        return sorted(list(self._monthly_cache.keys()), reverse=True)
    
    def clear_statistics(self) -> None:
        """Clear all statistics data"""
        self.all_sessions = []
        self.current_streak = 0
        self.longest_streak = 0
        self.last_focus_date = None
        self._cache_valid = False
        self._daily_cache = {}
        self._weekly_cache = {}
        self._monthly_cache = {}
    
    def set_daily_goal(self, minutes: int) -> None:
        """Set daily goal in minutes"""
        self.daily_goal_minutes = max(1, minutes)
        self._cache_valid = False
    
    def save_to_dict(self) -> Dict:
        """Export data for storage"""
        return {
            "sessions": [session.to_dict() for session in self.all_sessions],
            "streak": {
                "current": self.current_streak,
                "longest": self.longest_streak,
                "last_focus_date": self.last_focus_date
            },
            "settings": {
                "daily_goal_minutes": self.daily_goal_minutes
            },
            "schema_version": 1  # For future compatibility
        }
    
    def load_from_dict(self, data: Dict) -> bool:
        """Load data from dictionary"""
        try:
            # Check schema version
            version = data.get("schema_version", 0)
            if version == 1:
                # Clear existing data
                self.clear_statistics()
                
                # Load sessions
                for session_data in data.get("sessions", []):
                    try:
                        session = SessionRecord.from_dict(session_data)
                        self.all_sessions.append(session)
                    except Exception as e:
                        logger.error(f"Error loading session: {e}")
                
                # Load streak data
                streak_data = data.get("streak", {})
                self.current_streak = streak_data.get("current", 0)
                self.longest_streak = streak_data.get("longest", 0)
                self.last_focus_date = streak_data.get("last_focus_date")
                
                # Load settings
                settings = data.get("settings", {})
                self.daily_goal_minutes = settings.get("daily_goal_minutes", 120)
                
                # Rebuild caches
                self._cache_valid = False
                self._build_caches()
                
                return True
            else:
                logger.error(f"Unsupported schema version: {version}")
                return False
        except Exception as e:
            logger.error(f"Error loading statistics data: {e}")
            return False


class TimerSessionManager:
    """Manages the current timer session with accurate tracking"""
    
    def __init__(self, stats_manager: StatisticsManager):
        # Link to stats manager
        self.stats_manager = stats_manager
        
        # Session settings
        self.work_duration = 25 * 60  # 25 minutes in seconds
        self.short_break_duration = 5 * 60  # 5 minutes in seconds
        self.long_break_duration = 15 * 60  # 15 minutes in seconds
        self.long_break_interval = 4  # Long break after 4 pomodoros
        self.auto_start_breaks = True
        self.total_sessions = 4  # Total number of work sessions to complete
        
        # Current session state
        self.state = TimerState.IDLE
        self.previous_state = None
        self.pomodoros_completed = 0
        self.current_session_id = ""
        
        # Current session timing
        self.session_start_time = None
        self.remaining_seconds = 0
        self.elapsed_seconds = 0
        self.planned_duration = 0
        
        # Pause tracking
        self.paused_at = None
        self.total_pause_duration = 0
        self.pause_count = 0
        
        # Quick stats for active session
        self.last_tick_time = None
    
    def start_session(self) -> None:
        """Start a new work session"""
        # Handle both IDLE and COMPLETED states as valid starting points
        if self.state != TimerState.IDLE and self.state != TimerState.COMPLETED:
            # Already running - stop current first
            self.stop_session(interrupted=True)
        
        # Reset pomodoros_completed if we were in COMPLETED state
        if self.state == TimerState.COMPLETED:
            self.pomodoros_completed = 0
        
        # Generate unique session ID
        self.current_session_id = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Set work duration
        self.planned_duration = self.work_duration
        self.remaining_seconds = self.work_duration
        self.elapsed_seconds = 0
        
        # Reset pause tracking
        self.paused_at = None
        self.total_pause_duration = 0
        self.pause_count = 0
        
        # Set session state
        self.state = TimerState.WORKING
        self.previous_state = None
        self.session_start_time = datetime.now()
        self.last_tick_time = datetime.now()
    
    def pause_session(self) -> None:
        """Pause the current session"""
        if self.state in (TimerState.WORKING, TimerState.SHORT_BREAK, TimerState.LONG_BREAK):
            self.previous_state = self.state
            self.state = TimerState.PAUSED
            self.paused_at = datetime.now()
            self.pause_count += 1
    
    def resume_session(self) -> None:
        """Resume from paused state"""
        if self.state == TimerState.PAUSED and self.previous_state:
            # Calculate pause duration
            if self.paused_at:
                pause_duration = (datetime.now() - self.paused_at).total_seconds()
                self.total_pause_duration += pause_duration
                self.paused_at = None
            
            # Restore previous state
            self.state = self.previous_state
            self.last_tick_time = datetime.now()
    
    def skip_session(self) -> None:
        """Skip current session"""
        if self.state == TimerState.WORKING:
            # Skip work session
            self._complete_work_session(skipped=True)
        elif self.state == TimerState.PAUSED and self.previous_state == TimerState.WORKING:
            # Skip paused work session
            self._complete_work_session(skipped=True)
        elif self.state in (TimerState.SHORT_BREAK, TimerState.LONG_BREAK):
            # Skip break session
            self._complete_break_session()
        elif self.state == TimerState.PAUSED and self.previous_state in (TimerState.SHORT_BREAK, TimerState.LONG_BREAK):
            # Skip paused break session
            self._complete_break_session()
    
    def stop_session(self, interrupted: bool = False) -> None:
        """Stop the current session and record it"""
        # Handle based on current state
        if self.state == TimerState.WORKING or (self.state == TimerState.PAUSED and self.previous_state == TimerState.WORKING):
            # Work session - record as partial if running or interrupted if requested
            status = SessionStatus.INTERRUPTED if interrupted else SessionStatus.PARTIAL
            self._save_current_session(status)
        elif self.state in (TimerState.SHORT_BREAK, TimerState.LONG_BREAK) or (
                self.state == TimerState.PAUSED and self.previous_state in (TimerState.SHORT_BREAK, TimerState.LONG_BREAK)):
            # Break session - we don't need to record these
            pass
        
        # Reset state
        self.state = TimerState.IDLE
        self.previous_state = None
        self.current_session_id = ""
        self.session_start_time = None
        self.remaining_seconds = 0
        self.elapsed_seconds = 0
        self.planned_duration = 0
        self.paused_at = None
        self.total_pause_duration = 0
        self.pause_count = 0
    
    def update_session(self) -> None:
        """Update session timers - call every second"""
        if self.state == TimerState.PAUSED:
            return
            
        if self.state in (TimerState.WORKING, TimerState.SHORT_BREAK, TimerState.LONG_BREAK):
            now = datetime.now()
            if self.last_tick_time:
                # Calculate elapsed time since last tick
                elapsed = (now - self.last_tick_time).total_seconds()
                # Update timers
                self.remaining_seconds = max(0, self.remaining_seconds - elapsed)
                self.elapsed_seconds = self.planned_duration - self.remaining_seconds
                
                # Check if timer completed
                if self.remaining_seconds <= 0:
                    self._handle_timer_complete()
            
            self.last_tick_time = now
    
    def _handle_timer_complete(self) -> None:
        """Handle timer completion"""
        if self.state == TimerState.WORKING:
            self._complete_work_session()
        elif self.state in (TimerState.SHORT_BREAK, TimerState.LONG_BREAK):
            self._complete_break_session()
    
    def _complete_work_session(self, skipped: bool = False) -> None:
        """Handle work session completion"""
        # Record the session
        status = SessionStatus.SKIPPED if skipped else SessionStatus.COMPLETED
        self._save_current_session(status)
        
        # Increment pomodoro count
        self.pomodoros_completed += 1
        
        # Check if all sessions completed
        if self.pomodoros_completed >= self.total_sessions:
            self.state = TimerState.COMPLETED
            return
        
        # Determine break type
        if self.pomodoros_completed % self.long_break_interval == 0:
            # Long break
            self.state = TimerState.LONG_BREAK
            self.planned_duration = self.long_break_duration
            self.remaining_seconds = self.long_break_duration
        else:
            # Short break
            self.state = TimerState.SHORT_BREAK
            self.planned_duration = self.short_break_duration
            self.remaining_seconds = self.short_break_duration
        
        # Reset session data
        self.current_session_id = datetime.now().strftime("%Y%m%d%H%M%S")
        self.session_start_time = datetime.now()
        self.elapsed_seconds = 0
        self.paused_at = None
        self.total_pause_duration = 0
        self.pause_count = 0
        self.last_tick_time = datetime.now()
        
        # If not auto-starting breaks, pause immediately
        if not self.auto_start_breaks:
            self.pause_session()
    
    def _complete_break_session(self) -> None:
        """Handle break session completion"""
        # No need to save break sessions
        
        # Check if all sessions completed
        if self.pomodoros_completed >= self.total_sessions:
            self.state = TimerState.COMPLETED
            return
        
        # Start next work session
        self.current_session_id = datetime.now().strftime("%Y%m%d%H%M%S")
        self.state = TimerState.WORKING
        self.planned_duration = self.work_duration
        self.remaining_seconds = self.work_duration
        self.elapsed_seconds = 0
        self.session_start_time = datetime.now()
        self.paused_at = None
        self.total_pause_duration = 0
        self.pause_count = 0
        self.last_tick_time = datetime.now()
    
    def _save_current_session(self, status: SessionStatus) -> None:
        """Save the current session to statistics"""
        if not self.session_start_time or not self.current_session_id:
            return
        
        # Calculate actual duration
        end_time = datetime.now()
        actual_duration_seconds = (end_time - self.session_start_time).total_seconds()
        
        # Calculate effective duration (minus pauses)
        effective_duration = actual_duration_seconds - self.total_pause_duration
        
        # Determine session type
        if self.previous_state == TimerState.WORKING or self.state == TimerState.WORKING:
            session_type = SessionType.WORK
        elif self.previous_state == TimerState.SHORT_BREAK or self.state == TimerState.SHORT_BREAK:
            session_type = SessionType.SHORT_BREAK
        elif self.previous_state == TimerState.LONG_BREAK or self.state == TimerState.LONG_BREAK:
            session_type = SessionType.LONG_BREAK
        else:
            session_type = SessionType.WORK  # Default to work if unclear
        
        logger.debug(f"Saving session: type={session_type.name}, status={status.name}, duration={effective_duration}")
        
        # Create session record
        session = SessionRecord(
            session_id=self.current_session_id,
            type=session_type,
            status=status,
            start_time=self.session_start_time,
            end_time=end_time,
            planned_duration=self.planned_duration,
            actual_duration=int(actual_duration_seconds),
            effective_duration=int(effective_duration),
            pause_count=self.pause_count,
            total_pause_duration=int(self.total_pause_duration)
        )
        
        logger.debug(f"Session date keys: {session.date_key}, {session.week_key}, {session.month_key}")
        
        # Add to statistics
        self.stats_manager.add_session(session)
    
    def get_session_progress(self) -> float:
        """Get current session progress as percentage"""
        if self.planned_duration == 0:
            return 0
        return min(100, (self.elapsed_seconds / self.planned_duration) * 100)
    
    def get_session_info(self) -> Dict:
        """Get current session information"""
        # Time formatting - MAKE THESE CHANGES:
        minutes = int(self.remaining_seconds // 60)
        seconds = int(self.remaining_seconds % 60)
        time_str = f"{minutes:02d}:{seconds:02d}"
        
        # Progress calculation
        progress = self.get_session_progress()
        
        # Elapsed formatting - MAKE THESE CHANGES:
        elapsed_min = int(self.elapsed_seconds // 60)
        elapsed_sec = int(self.elapsed_seconds % 60)
        planned_min = int(self.planned_duration // 60)
        
        # Determine if we're in a work or break session
        is_work = self.state == TimerState.WORKING or (self.state == TimerState.PAUSED and self.previous_state == TimerState.WORKING)
        is_break = self.state in (TimerState.SHORT_BREAK, TimerState.LONG_BREAK) or (
            self.state == TimerState.PAUSED and self.previous_state in (TimerState.SHORT_BREAK, TimerState.LONG_BREAK))
        
        # Flag for tracking UI updates after work completion
        work_completed = False
        
        return {
            "state": self.state.name,
            "previous_state": self.previous_state.name if self.previous_state else None,
            "pomodoros_completed": self.pomodoros_completed,
            "total_sessions": self.total_sessions, 
            "current_session": self.pomodoros_completed + 1,
            "time_display": time_str,
            "minutes_remaining": minutes,
            "seconds_remaining": seconds,
            "progress_percent": progress,
            "elapsed_display": f"{elapsed_min:d}:{elapsed_sec:02d} / {planned_min:d}:00",
            "is_paused": self.state == TimerState.PAUSED,
            "is_work": is_work,
            "is_break": is_break,
            "work_completed": work_completed,
            "effective_minutes": int(self.elapsed_seconds / 60),
            "pause_count": self.pause_count,
            "total_pause_duration": self.total_pause_duration
        }
    
    def get_settings(self) -> Dict:
        """Get timer settings"""
        return {
            "work_duration": self.work_duration // 60,  # Convert to minutes
            "short_break": self.short_break_duration // 60,
            "long_break": self.long_break_duration // 60,
            "long_break_interval": self.long_break_interval,
            "total_sessions": self.total_sessions,
            "auto_start_breaks": self.auto_start_breaks
        }
    
    def update_settings(self, settings: Dict) -> None:
        """Update timer settings"""
        if "work_duration" in settings:
            self.work_duration = settings["work_duration"] * 60  # Convert to seconds
        
        if "short_break" in settings:
            self.short_break_duration = settings["short_break"] * 60
        
        if "long_break" in settings:
            self.long_break_duration = settings["long_break"] * 60
        
        if "long_break_interval" in settings:
            self.long_break_interval = settings["long_break_interval"]
        
        if "total_sessions" in settings:
            self.total_sessions = settings["total_sessions"]
        
        if "auto_start_breaks" in settings:
            self.auto_start_breaks = settings["auto_start_breaks"]