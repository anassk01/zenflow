"""
session.py - Enhanced session management with accurate state tracking
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable, List
import logging
from ..config.constants import (
    DEFAULT_WORK_DURATION,
    DEFAULT_SHORT_BREAK,
    DEFAULT_LONG_BREAK,
    DEFAULT_SESSIONS
)

logger = logging.getLogger(__name__)

class SessionState(Enum):
    """Possible states for a focus session"""
    IDLE = auto()
    WORKING = auto()
    BREAK = auto()
    PAUSED = auto()
    COMPLETED = auto()

class SessionEvent(Enum):
    """Events that can trigger session state changes"""
    START = auto()
    PAUSE = auto()
    RESUME = auto()
    SKIP = auto()
    RESET = auto()
    COMPLETE = auto()
    STOP = auto()

@dataclass
class SessionStats:
    """Statistics for a focus session"""
    start_time: datetime
    end_time: Optional[datetime] = None
    completed: bool = False
    interruptions: int = 0
    total_pause_time: timedelta = field(default_factory=lambda: timedelta(0))
    last_pause_time: Optional[datetime] = None
    effective_duration: int = 0  # Duration in minutes

@dataclass
class SessionConfig:
    """Configuration for focus sessions"""
    work_duration: int = DEFAULT_WORK_DURATION
    short_break: int = DEFAULT_SHORT_BREAK
    long_break: int = DEFAULT_LONG_BREAK
    sessions: int = DEFAULT_SESSIONS
    auto_start_breaks: bool = True
    sound_enabled: bool = True
    block_during_breaks: bool = False

class SessionManager:
    """Manages focus session state and transitions"""
    
    def __init__(self, config: SessionConfig):
        self.config = config
        self.state = SessionState.IDLE
        self.current_session = 0
        self.stats = None
        self._state_handlers = {
            SessionState.IDLE: self._handle_idle_state,
            SessionState.WORKING: self._handle_working_state,
            SessionState.BREAK: self._handle_break_state,
            SessionState.PAUSED: self._handle_paused_state,
            SessionState.COMPLETED: self._handle_completed_state,
        }

    def handle_event(self, event: SessionEvent) -> None:
        """Handle session state transitions"""
        try:
            old_state = self.state
            handler = self._state_handlers.get(self.state)
            if not handler:
                logger.error(f"Invalid session state: {self.state}")
                return

            new_state = handler(event)
            if new_state:
                self._transition_to(new_state)
            else:
                logger.error(f"Invalid event {event.name} for state {self.state.name}")

        except Exception as e:
            logger.error(f"Session error: {e}")
            raise

    def _transition_to(self, new_state: SessionState) -> None:
        """Handle state transition"""
        if new_state == SessionState.WORKING:
            if not self.stats:
                self.stats = SessionStats(start_time=datetime.now())
            self.current_session += 1
        elif new_state == SessionState.COMPLETED:
            if self.stats:
                self.stats.completed = True
                self.stats.end_time = datetime.now()

        self.state = new_state

    def _handle_idle_state(self, event: SessionEvent) -> Optional[SessionState]:
        if event == SessionEvent.START:
            return SessionState.WORKING
        return None

    def _handle_working_state(self, event: SessionEvent) -> Optional[SessionState]:
        if event == SessionEvent.PAUSE:
            return SessionState.PAUSED
        elif event == SessionEvent.SKIP:
            return SessionState.BREAK
        elif event == SessionEvent.COMPLETE:
            return SessionState.BREAK
        elif event == SessionEvent.STOP:
            return SessionState.IDLE
        elif event == SessionEvent.RESET:
            return SessionState.IDLE
        return None

    def _handle_break_state(self, event: SessionEvent) -> Optional[SessionState]:
        if event == SessionEvent.PAUSE:
            return SessionState.PAUSED
        elif event == SessionEvent.SKIP:
            return SessionState.WORKING
        elif event == SessionEvent.COMPLETE:
            return SessionState.COMPLETED
        elif event == SessionEvent.STOP:
            return SessionState.IDLE
        elif event == SessionEvent.RESET:
            return SessionState.IDLE
        return None

    def _handle_paused_state(self, event: SessionEvent) -> Optional[SessionState]:
        if event == SessionEvent.RESUME:
            return self.state
        elif event == SessionEvent.STOP:
            return SessionState.IDLE
        elif event == SessionEvent.RESET:
            return SessionState.IDLE
        return None

    def _handle_completed_state(self, event: SessionEvent) -> Optional[SessionState]:
        if event == SessionEvent.START:
            return SessionState.WORKING
        elif event == SessionEvent.RESET:
            return SessionState.IDLE
        return None

    def tick(self) -> None:
        """Update session timer"""
        if self.state not in (SessionState.WORKING, SessionState.BREAK):
            return
            
        now = datetime.now()
        if self.last_tick:
            elapsed = (now - self.last_tick).total_seconds()
            self.remaining_time = max(0, self.remaining_time - int(elapsed))
            
            if self.on_tick:
                self.on_tick(self.remaining_time)
                
            if self.remaining_time <= 0:
                self.handle_event(SessionEvent.COMPLETE)
                
        self.last_tick = now
        
    def _start_session(self) -> None:
        """Start a new focus session"""
        self.current_session = 1
        self.remaining_time = self.config.work_duration * 60
        self.start_time = datetime.now()
        self.last_tick = datetime.now()
        self.total_pause_time = timedelta()
        
        self._current_stats = SessionStats(start_time=datetime.now())
        self._change_state(SessionState.WORKING)
        
    def _pause_session(self) -> None:
        """Pause the current session"""
        self.previous_state = self.state
        self.pause_start = datetime.now()
        
        if self._current_stats:
            self._current_stats.interruptions += 1
            self._current_stats.last_pause_time = datetime.now()
            
        self._change_state(SessionState.PAUSED)
        
    def _resume_session(self) -> None:
        """Resume from pause"""
        if self.pause_start:
            pause_duration = datetime.now() - self.pause_start
            self.total_pause_time += pause_duration
            
            if self._current_stats:
                self._current_stats.total_pause_time += pause_duration
                
        self.pause_start = None
        self.last_tick = datetime.now()
        self._change_state(self.previous_state)
        
    def _complete_work(self) -> None:
        """Complete work period"""
        if self._current_stats:
            self._current_stats.end_time = datetime.now()
            self._current_stats.completed = True
            self._current_stats.effective_duration = self._calculate_effective_duration()
            self.stats.append(self._current_stats)
            
        self.remaining_time = (
            self.config.long_break if self.current_session % 4 == 0 
            else self.config.short_break
        ) * 60
        
        self._current_stats = SessionStats(start_time=datetime.now())
        self._change_state(SessionState.BREAK)
        
    def _complete_break(self) -> None:
        """Complete break period"""
        if self.current_session >= self.config.sessions:
            self._change_state(SessionState.COMPLETED)
            return
            
        self.current_session += 1
        self.remaining_time = self.config.work_duration * 60
        self.start_time = datetime.now()
        self.last_tick = datetime.now()
        self.total_pause_time = timedelta()
        
        self._current_stats = SessionStats(start_time=datetime.now())
        self._change_state(SessionState.WORKING)
        
    def _stop_session(self) -> None:
        """Stop the current session"""
        if self._current_stats:
            self._current_stats.end_time = datetime.now()
            self._current_stats.completed = False
            self._current_stats.effective_duration = self._calculate_effective_duration()
            self.stats.append(self._current_stats)
            
        self._reset_session()
        
    def _reset_session(self) -> None:
        """Reset session state"""
        self.state = SessionState.IDLE
        self.previous_state = None
        self.remaining_time = 0
        self.current_session = 0
        self.start_time = None
        self.pause_start = None
        self.total_pause_time = timedelta()
        self.last_tick = None
        self._current_stats = None
        
    def _skip_to_break(self) -> None:
        """Skip to break period"""
        self._complete_work()
        
    def _skip_to_work(self) -> None:
        """Skip to work period"""
        self._complete_break()
        
    def _change_state(self, new_state: SessionState) -> None:
        """Update session state and notify callback"""
        old_state = self.state
        self.state = new_state
        
        if self.on_state_change:
            self.on_state_change(old_state, new_state)
            
        logger.debug(f"State changed: {old_state} -> {new_state}")
        
    def _calculate_effective_duration(self) -> int:
        """Calculate effective session duration in minutes"""
        if not self.start_time:
            return 0
            
        total_duration = datetime.now() - self.start_time
        effective_duration = total_duration - self.total_pause_time
        return int(effective_duration.total_seconds() / 60)
        
    def get_session_stats(self) -> List[SessionStats]:
        """Get statistics for all sessions"""
        return self.stats.copy()
        
    def get_current_progress(self) -> float:
        """Get current session progress percentage"""
        if self.state in (SessionState.IDLE, SessionState.COMPLETED):
            return 0.0
            
        total_time = self.config.work_duration * 60
        if self.state == SessionState.BREAK:
            total_time = (
                self.config.long_break if self.current_session % 4 == 0 
                else self.config.short_break
            ) * 60
            
        elapsed = total_time - self.remaining_time
        return (elapsed / total_time) * 100 if total_time > 0 else 0.0
        
    @property
    def is_break(self) -> bool:
        """Check if currently in break period"""
        return self.state == SessionState.BREAK