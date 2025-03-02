"""
System-related utility functions for ZenFlow
"""

import os
import subprocess
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from ..config.constants import REQUIRED_COMMANDS

logger = logging.getLogger(__name__)

@dataclass
class CommandResult:
    """Represents the result of a system command execution"""
    stdout: str
    stderr: str
    returncode: int

def is_root() -> bool:
    """Check if the application is running with root privileges"""
    return os.geteuid() == 0

def check_dependencies() -> Dict[str, bool]:
    """
    Check if all required system dependencies are installed
    
    Returns:
        Dictionary mapping command names to their availability status
    """
    status = {}
    for cmd in REQUIRED_COMMANDS:
        try:
            subprocess.run(['which', cmd], 
                         check=True, 
                         capture_output=True)
            status[cmd] = True
        except subprocess.CalledProcessError:
            status[cmd] = False
            logger.warning(f"Required command '{cmd}' not found")
    
    return status

def get_missing_packages() -> List[str]:
    """
    Get list of package names that need to be installed
    
    Returns:
        List of package names that are missing
    """
    status = check_dependencies()
    return [REQUIRED_COMMANDS[cmd] for cmd, available in status.items() 
            if not available]

def run_command(command: List[str], 
                check: bool = True, 
                timeout: Optional[int] = None) -> CommandResult:
    """
    Run a system command safely and return its output
    
    Args:
        command: List of command arguments
        check: Whether to raise exception on non-zero return code
        timeout: Command timeout in seconds
    
    Returns:
        CommandResult object containing stdout, stderr and return code
    
    Raises:
        subprocess.CalledProcessError: If check=True and command returns non-zero
        subprocess.TimeoutExpired: If command exceeds timeout
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=check,
            timeout=timeout
        )
        return CommandResult(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {' '.join(command)}")
        logger.error(f"Error output: {e.stderr}")
        raise
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out: {' '.join(command)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error running command: {e}")
        raise

def setup_app_directory() -> None:
    """
    Create application directory structure if it doesn't exist
    """
    from ..config.constants import APP_DIR
    
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Application directory created at {APP_DIR}")
    except Exception as e:
        logger.error(f"Failed to create application directory: {e}")
        raise

def get_system_notification_command() -> Optional[List[str]]:
    """
    Get the appropriate notification command for the current system
    
    Returns:
        List of command arguments or None if no notification command available
    """
    # Try different notification commands
    if subprocess.run(['which', 'spd-say'], 
                     capture_output=True).returncode == 0:
        return ['spd-say']
    elif subprocess.run(['which', 'notify-send'], 
                       capture_output=True).returncode == 0:
        return ['notify-send', '-u', 'critical']
    else:
        logger.warning("No system notification command found")
        return None