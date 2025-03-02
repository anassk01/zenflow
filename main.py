#!/usr/bin/env python3
"""
ZenFlow - A powerful productivity suite for achieving optimal focus
Created by AnassK

Main entry point for ZenFlow application
"""

import sys
import logging
import os
from pathlib import Path
from src.ui.app import ZenFlowApp
from src.config.constants import APP_NAME, LOG_FILE
from src.utils.display_manager import init_display

def setup_logging():
    """Configure application logging"""
    log_dir = Path(LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Silence all loggers by default
    logging.getLogger().setLevel(logging.ERROR)
    
    # Silence specific noisy modules
    for logger_name in [
        'selenium',
        'urllib3',
        'src.ui',
        'src.utils',
        'src.core.session',
        'src.ui.service',
        'src.ui.components'
    ]:
        logging.getLogger(logger_name).setLevel(logging.ERROR)
    
    # Configure file logging - only errors
    logging.basicConfig(
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Network logging - only critical events
    network_logger = logging.getLogger('src.core.network')
    network_logger.setLevel(logging.ERROR)

def check_root():
    """Check for root privileges"""
    if os.geteuid() != 0:
        print(f"Error: {APP_NAME} requires root privileges")
        print("Please run with: sudo python3 main.py")
        sys.exit(1)

def main():
    """Application entry point"""
    try:
        setup_logging()
        check_root()
        
        # Initialize display access for Selenium
        if not init_display():
            logging.error("Failed to initialize display access. Please check X11 configuration.")
            sys.exit(1)
            
        app = ZenFlowApp()
        app.run()
    except Exception as e:
        logging.error(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()