import os
import subprocess
import atexit
import logging
from pathlib import Path

class DisplayManager:
    def __init__(self):
        self.display = os.environ.get('DISPLAY', ':0')
        self.xauth_file = Path('/tmp/.Xauthority')
        self.original_xauth = None

    def setup_display_access(self):
        """Set up secure X11 display access for the current user"""
        try:
            # Store current user
            self.current_user = os.environ.get('SUDO_USER') or os.environ.get('USER')
            if not self.current_user:
                logging.error("Could not determine current user")
                return False

            # Get current user's home directory
            self.user_home = str(Path(f'/home/{self.current_user}'))
            
            # Backup original .Xauthority if it exists
            user_xauth = Path(self.user_home) / '.Xauthority'
            if user_xauth.exists():
                self.original_xauth = user_xauth.read_bytes()

            # Set up clean environment variables
            os.environ['XAUTHORITY'] = str(self.xauth_file)
            os.environ['DISPLAY'] = self.display

            # Generate new .Xauthority file
            subprocess.run(['xauth', 'generate', self.display, '.', 'trusted'], 
                         check=True, capture_output=True)

            # Register cleanup
            atexit.register(self.cleanup)
            
            return True
        except Exception as e:
            logging.error(f"Failed to set up display access: {e}")
            return False

    def cleanup(self):
        """Clean up X11 display access settings"""
        try:
            # Restore original .Xauthority if it existed
            if self.original_xauth:
                user_xauth = Path(self.user_home) / '.Xauthority'
                user_xauth.write_bytes(self.original_xauth)

            # Remove temporary .Xauthority file
            if self.xauth_file.exists():
                self.xauth_file.unlink()
        except Exception as e:
            logging.error(f"Failed to clean up display access: {e}")

def init_display():
    """Initialize display manager and set up X11 access"""
    display_manager = DisplayManager()
    return display_manager.setup_display_access() 