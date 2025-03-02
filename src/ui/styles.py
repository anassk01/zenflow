"""
UI styling configuration for ZenFlow application.
"""

import tkinter as tk
from tkinter import ttk
import logging

logger = logging.getLogger(__name__)

# Color scheme
COLORS = {
    'primary': '#2196F3',      # Blue
    'secondary': '#757575',    # Gray
    'success': '#4CAF50',      # Green
    'warning': '#FFC107',      # Amber
    'error': '#F44336',        # Red
    'background': '#FAFAFA',   # Light gray
    'text': '#212121',         # Dark gray
    'disabled': '#BDBDBD'      # Light gray
}

# Font configurations
FONTS = {
    'default': ('Arial', 10),
    'header': ('Arial', 12, 'bold'),
    'title': ('Arial', 14, 'bold'),
    'timer': ('Arial', 48, 'bold'),
    'small': ('Arial', 9)
}

def apply_styles(root: tk.Tk) -> None:
    """
    Apply custom styles to application widgets
    
    Args:
        root: Root window for style application
    """
    try:
        style = ttk.Style()
        
        # Configure basic styles
        style.configure('.',
            font=FONTS['default'],
            background=COLORS['background'],
            foreground=COLORS['text']
        )
        
        # Frame styles
        style.configure('TFrame',
            background=COLORS['background']
        )
        
        style.configure('Card.TFrame',
            background='white',
            relief='solid',
            borderwidth=1
        )
        
        # Label styles
        style.configure('TLabel',
            background=COLORS['background'],
            foreground=COLORS['text']
        )
        
        style.configure('Header.TLabel',
            font=FONTS['header']
        )
        
        style.configure('Title.TLabel',
            font=FONTS['title']
        )
        
        style.configure('Timer.TLabel',
            font=FONTS['timer'],
            foreground=COLORS['primary']
        )
        
        # Button styles
        style.configure('TButton',
            padding=5,
            font=FONTS['default']
        )
        
        style.configure('Primary.TButton',
            background=COLORS['primary'],
            foreground='white'
        )
        
        style.map('Primary.TButton',
            background=[('active', COLORS['primary'])],
            foreground=[('active', 'white')]
        )
        
        style.configure('Success.TButton',
            background=COLORS['success'],
            foreground='white'
        )
        
        style.map('Success.TButton',
            background=[('active', COLORS['success'])],
            foreground=[('active', 'white')]
        )
        
        # Progress bar styles
        style.configure('TProgressbar',
            troughcolor=COLORS['background'],
            background=COLORS['primary'],
            thickness=10
        )
        
        # Entry styles
        style.configure('TEntry',
            padding=5,
            fieldbackground='white'
        )
        
        # Notebook styles
        style.configure('TNotebook',
            background=COLORS['background']
        )
        
        style.configure('TNotebook.Tab',
            padding=[10, 5],
            font=FONTS['default']
        )
        
        # Treeview styles
        style.configure('Treeview',
            background='white',
            fieldbackground='white',
            font=FONTS['default']
        )
        
        style.configure('Treeview.Heading',
            font=FONTS['header'],
            background=COLORS['background']
        )
        
        logger.info("Custom styles applied successfully")
        
    except Exception as e:
        logger.error(f"Failed to apply styles: {e}")
        # Continue with default styles
        pass

def get_color(name: str) -> str:
    """
    Get color by name from color scheme
    
    Args:
        name: Color name
        
    Returns:
        Color hex code
    """
    return COLORS.get(name, COLORS['primary'])

def get_font(name: str) -> tuple:
    """
    Get font configuration by name
    
    Args:
        name: Font configuration name
        
    Returns:
        Font configuration tuple
    """
    return FONTS.get(name, FONTS['default'])