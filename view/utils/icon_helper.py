"""
Helper utility for setting window icons consistently across the application.
"""

import os
import wx


def set_window_icon(window):
    """
    Set the application icon for a window or dialog.
    
    Args:
        window: wx.Frame or wx.Dialog instance
    """
    # Get path to icon.png in project root
    # Current file is in view/utils/, so go up 2 levels to reach project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    view_dir = os.path.dirname(current_dir)  # view/
    project_root = os.path.dirname(view_dir)  # project root
    icon_path = os.path.join(project_root, "icon.png")
    
    if os.path.exists(icon_path):
        try:
            icon = wx.Icon(icon_path, wx.BITMAP_TYPE_PNG)
            window.SetIcon(icon)
        except Exception as e:
            # Silently fail if icon cannot be loaded
            pass
