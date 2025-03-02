"""
ui_config.py - Enhanced UI configuration with improved styling and component definitions
"""
import tkinter as tk
from tkinter import ttk
from typing import Tuple, Optional

# Window Configuration
MIN_WINDOW_WIDTH = 1400
MIN_WINDOW_HEIGHT = 700
DEFAULT_PADDING = 10
SECTION_PADDING = 8

# Component Sizes
BUTTON_WIDTH = 12           # Standard button width in characters
BUTTON_HEIGHT = 1          # Standard button height
INPUT_WIDTH = 30          # Standard input width in characters
TIMER_WIDTH = 400         # Timer width
PROGRESSBAR_HEIGHT = 20    # Height for progress bars

# Tab Configuration
TAB_PADDING = 15          # Padding inside tabs
TAB_LABEL_PADDING = 8     # Padding for tab labels

class ResponsiveFrame(ttk.Frame):
    """A frame that maintains minimum size and proper scaling"""
    def __init__(self, master, min_width: int = 200, min_height: int = 100, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.min_width = min_width
        self.min_height = min_height
        
        # Ensure minimum size
        self.pack_propagate(False)
        self.grid_propagate(False)
        
        # Configure grid weights
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Set initial size
        self.configure(width=min_width, height=min_height)
        
    def update_size(self, width: Optional[int] = None, height: Optional[int] = None):
        """Update frame size while maintaining minimums"""
        if width is not None:
            width = max(width, self.min_width)
        if height is not None:
            height = max(height, self.min_height)
        self.configure(width=width, height=height)

class ScrollableFrame(ttk.Frame):
    """Enhanced scrollable frame with smooth scrolling"""
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        # Configure grid weights
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create canvas with proper styling
        self.canvas = tk.Canvas(
            self,
            highlightthickness=0,
            bd=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        # Add vertical scrollbar
        self.vsb = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview
        )
        self.vsb.grid(row=0, column=1, sticky="ns")
        
        # Add horizontal scrollbar
        self.hsb = ttk.Scrollbar(
            self,
            orient="horizontal",
            command=self.canvas.xview
        )
        self.hsb.grid(row=1, column=0, sticky="ew")
        
        # Configure canvas scrolling
        self.canvas.configure(
            yscrollcommand=self.vsb.set,
            xscrollcommand=self.hsb.set
        )
        
        # Create inner frame for content
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self._configure_scroll_region()
        )
        
        # Create window in canvas
        self.canvas_frame = self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw"
        )
        
        # Bind canvas resizing
        self.canvas.bind('<Configure>', self._configure_canvas_window)
        
        # Bind mouse wheel scrolling
        self._bind_mouse_scroll()
        
        # Initially hide scrollbars
        self.vsb.grid_remove()
        self.hsb.grid_remove()
        
    def _configure_scroll_region(self):
        """Update canvas scroll region"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._check_scrollbar_visibility()
        
    def _configure_canvas_window(self, event=None):
        """Update canvas window size"""
        # Get current width and scroll region
        canvas_width = self.canvas.winfo_width()
        scroll_region = self.canvas.bbox("all")
        
        if scroll_region:
            # Update window width to match canvas
            self.canvas.itemconfig(
                self.canvas_frame,
                width=canvas_width if canvas_width > scroll_region[2] else scroll_region[2]
            )
            
        # Check scrollbar visibility
        self._check_scrollbar_visibility()
            
    def _check_scrollbar_visibility(self):
        """Check and update scrollbar visibility"""
        scroll_region = self.canvas.bbox("all")
        if not scroll_region:
            return
            
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Show vertical scrollbar if content is taller than canvas
        if scroll_region[3] > canvas_height:
            self.vsb.grid()
            canvas_width -= self.vsb.winfo_reqwidth()
        else:
            self.vsb.grid_remove()
            
        # Show horizontal scrollbar if content is wider than canvas
        if scroll_region[2] > canvas_width:
            self.hsb.grid()
        else:
            self.hsb.grid_remove()
            
    def _on_mouse_scroll(self, event):
        """Handle mouse wheel scrolling"""
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
            
    def _on_shift_mouse_scroll(self, event):
        """Handle horizontal scrolling"""
        if event.state & 0x1:  # Check if shift is pressed
            if event.num == 4 or event.delta > 0:
                self.canvas.xview_scroll(-1, "units")
            elif event.num == 5 or event.delta < 0:
                self.canvas.xview_scroll(1, "units")
            
    def _bind_mouse_scroll(self):
        """Bind mouse wheel events"""
        # Bind to scrollable frame
        self.scrollable_frame.bind(
            "<Enter>",
            lambda e: self._bind_active_scroll()
        )
        self.scrollable_frame.bind(
            "<Leave>",
            lambda e: self._unbind_active_scroll()
        )
        
        # Bind to canvas
        self.canvas.bind(
            "<Enter>",
            lambda e: self._bind_active_scroll()
        )
        self.canvas.bind(
            "<Leave>",
            lambda e: self._unbind_active_scroll()
        )
        
    def _bind_active_scroll(self):
        """Bind active scrolling events"""
        self.bind_all("<MouseWheel>", self._on_mouse_scroll)
        self.bind_all("<Button-4>", self._on_mouse_scroll)
        self.bind_all("<Button-5>", self._on_mouse_scroll)
        self.bind_all("<Shift-MouseWheel>", self._on_shift_mouse_scroll)
        
    def _unbind_active_scroll(self):
        """Unbind active scrolling events"""
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")
        self.unbind_all("<Shift-MouseWheel>")

def configure_styles():
    """Configure global styles for widgets"""
    style = ttk.Style()
    
    # Configure tab styling
    style.configure(
        'TNotebook',
        background='white',
        padding=TAB_PADDING
    )
    
    style.configure(
        'TNotebook.Tab',
        padding=(TAB_LABEL_PADDING, TAB_LABEL_PADDING),
        background='#f0f0f0',
        foreground='#666666'
    )
    
    style.map('TNotebook.Tab',
        background=[('selected', '#ffffff')],
        foreground=[('selected', '#000000')],
        expand=[('selected', [1, 1, 1, 0])]
    )
    
    # Button styles
    style.configure(
        'TButton',
        padding=(10, 5),
        width=BUTTON_WIDTH
    )
    
    style.configure(
        'Primary.TButton',
        padding=(10, 5),
        width=BUTTON_WIDTH,
        background='#2196F3',
        foreground='white'
    )
    
    style.map('Primary.TButton',
        background=[('active', '#1976D2')],
        foreground=[('active', 'white')]
    )
    
    style.configure(
        'Action.TButton',
        padding=(8, 4),
        width=BUTTON_WIDTH
    )
    
    # Frame styles
    style.configure(
        'Card.TFrame',
        background='white',
        padding=SECTION_PADDING,
        relief='solid',
        borderwidth=1
    )
    
    style.configure(
        'Card.TLabelframe',
        background='white',
        padding=SECTION_PADDING,
        relief='solid',
        borderwidth=1
    )
    
    # Progressbar styles
    style.configure(
        'Timer.Horizontal.TProgressbar',
        thickness=PROGRESSBAR_HEIGHT,
        troughcolor='#f0f0f0',
        background='#2196F3'
    )
    
    style.configure(
        'Progress.Horizontal.TProgressbar',
        thickness=PROGRESSBAR_HEIGHT - 4,
        troughcolor='#f0f0f0',
        background='#4CAF50'
    )
    
    # Treeview styles
    style.configure(
        'History.Treeview',
        rowheight=25,
        background='white',
        fieldbackground='white',
        foreground='black',
        padding=5
    )
    
    style.map('History.Treeview',
        background=[('selected', '#E3F2FD')],
        foreground=[('selected', '#1976D2')]
    )

def create_button(parent: ttk.Frame, text: str, command, style: str = 'TButton', **kwargs) -> ttk.Button:
    """Create a standardized button"""
    return ttk.Button(
        parent,
        text=text,
        command=command,
        style=style,
        **kwargs
    )

def create_section_frame(parent: ttk.Frame, title: str, **kwargs) -> ttk.LabelFrame:
    """Create a standardized section frame"""
    return ttk.LabelFrame(
        parent,
        text=title,
        padding=SECTION_PADDING,
        style="Card.TLabelframe",
        **kwargs
    )