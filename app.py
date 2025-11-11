"""
GLiSE - Grey Literature Search Engine
Main application entry point
"""

import wx
from view.generate_queries_form_window import PromptWindow
from view.utils.navigation_controller import get_navigation_controller


def main():
    """Main entry point for the GLiSE application."""
    app = wx.App()
    
    # Initialize navigation controller
    nav = get_navigation_controller()
    nav.set_app(app)
    
    # Create and show home window
    window = PromptWindow()
    nav.push(window, 'home', close_previous=False)
    
    app.MainLoop()


if __name__ == "__main__":
    print("Starting GLiSE application...")
    main()