"""
Navigation Controller - Simplified window navigation pattern.

Manages window lifecycle with automatic cleanup, inspired by mobile navigation patterns.
Eliminates the need for manual flags, race conditions, and complex close handlers.
"""

import wx
from typing import Optional, List, Tuple


class NavigationController:
    """
    Manages window navigation with automatic cleanup.
    
    Features:
    - Stack-based navigation (like iOS/Android)
    - Automatic previous window cleanup
    - No manual flags or timing issues
    - Single source of truth for navigation
    - Automatic app exit when stack is empty
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the navigation controller."""
        if self._initialized:
            return
        
        self._initialized = True
        self.stack: List[Tuple[wx.Frame, str]] = []  # [(window, window_type)]
        self.app: Optional[wx.App] = None
    
    def set_app(self, app: wx.App):
        """Set the wx.App instance for clean exit."""
        self.app = app
    
    def push(self, window: wx.Frame, window_type: str, close_previous: bool = True):
        """
        Push a new window onto the navigation stack.
        
        Args:
            window: The window to show
            window_type: Type identifier (e.g., 'home', 'results', 'settings')
            close_previous: If True, closes the previous window (linear navigation)
                          If False, keeps previous window (modal/settings style)
        
        Example:
            nav = get_navigation_controller()
            results_win = ResultsWindow(self, data)
            nav.push(results_win, 'results', close_previous=True)
        """
        # Add to stack FIRST before closing previous
        # This ensures stack is never empty during transition
        self.stack.append((window, window_type))
        
        # Show and bring to front
        self._show_and_raise(window)
        
        # Bind close event to handle removal from stack
        window.Bind(wx.EVT_CLOSE, lambda evt: self._on_window_close(evt, window, window_type))
        
        # Close previous window if linear navigation (AFTER adding new window)
        if close_previous and len(self.stack) > 1:
            # Get the previous window (second to last)
            previous_window, _ = self.stack[-2]
            try:
                # Remove previous window from stack first
                self.stack = [(w, t) for w, t in self.stack if w != previous_window]
                # Then destroy it
                wx.CallAfter(previous_window.Destroy)
            except:
                pass
    
    def _show_and_raise(self, window: wx.Frame):
        """Show a window and bring it to front."""
        if not window:
            return
        
        # Show the window if hidden
        if not window.IsShown():
            window.Show()
        
        # Bring to front
        window.Raise()
        
        # Set focus
        window.SetFocus()
    
    def pop(self):
        """
        Close current window and show previous one (back navigation).
        Useful for implementing back buttons.
        """
        if not self.stack:
            return
        
        # Get and remove current window
        current_window, _ = self.stack.pop()
        
        try:
            current_window.Destroy()
        except:
            pass
        
        # Show previous window if exists
        if self.stack:
            previous_window, _ = self.stack[-1]
            self._show_and_raise(previous_window)
    
    def _on_window_close(self, event, window, window_type):
        """
        Handle window close event.
        Automatically removes window from stack and exits app if no windows remain.
        """
        # Remove from stack
        self.stack = [(w, t) for w, t in self.stack if w != window]
        
        # If no windows left, exit app
        if not self.stack:
            if self.app:
                wx.CallAfter(self.app.ExitMainLoop)
        
        # Continue with normal close
        event.Skip()
    
    def close_all(self):
        """Close all windows and exit application."""
        # Get all windows as a list
        all_windows = [window for window, _ in list(self.stack)]
        
        # Close all windows
        for window in all_windows:
            try:
                window.Destroy()
            except:
                pass
        
        # Clear stack
        self.stack.clear()
        
        # Exit application
        if self.app:
            wx.CallAfter(self.app.ExitMainLoop)
    
    def get_current(self) -> Optional[wx.Frame]:
        """Get the current (top) window in the stack."""
        return self.stack[-1][0] if self.stack else None
    
    def get_window_by_type(self, window_type: str) -> Optional[wx.Frame]:
        """
        Get a window by its type identifier.
        Returns the most recent window of that type.
        """
        for window, wtype in reversed(self.stack):
            if wtype == window_type:
                return window
        return None
    
    def get_count(self) -> int:
        """Get number of windows in the navigation stack."""
        return len(self.stack)
    
    def is_empty(self) -> bool:
        """Check if navigation stack is empty."""
        return len(self.stack) == 0
    
    def show_and_raise(self, window: wx.Frame):
        """
        Utility method to show and raise any window.
        Useful for bringing existing windows to front without navigation.
        """
        self._show_and_raise(window)


# Global function to get the singleton instance
def get_navigation_controller() -> NavigationController:
    """Get the global NavigationController instance."""
    return NavigationController()
