"""
Reusable menu bar component for all application windows.
"""

import os
import wx
import json
from typing import Optional
from view.utils.navigation_controller import get_navigation_controller


class AppMenuBar(wx.MenuBar):
    """Reusable menu bar for the Grey Literature Tool application."""
    
    def __init__(self, parent_window):
        """
        Initialize the menu bar.
        
        Args:
            parent_window: The parent window that will use this menu bar
        """
        super().__init__()
        self.parent_window = parent_window
        self._create_menus()
    
    def _create_menus(self):
        """Create all menu items."""
        # File menu
        file_menu = wx.Menu()
        
        home_item = file_menu.Append(wx.ID_HOME, "Home\tCtrl+H", "Go to Query Generator")
        self.parent_window.Bind(wx.EVT_MENU, self._on_home, home_item)
        
        file_menu.AppendSeparator()
        
        open_queries_item = file_menu.Append(wx.ID_ANY, "Open Queries...\tCtrl+O", "Open saved queries from JSON file")
        self.parent_window.Bind(wx.EVT_MENU, self._on_open_queries, open_queries_item)
        
        open_results_item = file_menu.Append(wx.ID_ANY, "Open Search Results...\tCtrl+Shift+O", "Open saved search results from JSON file")
        self.parent_window.Bind(wx.EVT_MENU, self._on_open_search_results, open_results_item)
        
        file_menu.AppendSeparator()
        
        close_item = file_menu.Append(wx.ID_CLOSE, "Close Window\tCtrl+W", "Close current window")
        self.parent_window.Bind(wx.EVT_MENU, lambda evt: self.parent_window.Close(), close_item)
        
        exit_all_item = file_menu.Append(wx.ID_EXIT, "Exit All\tCtrl+Q", "Close all windows and exit application")
        self.parent_window.Bind(wx.EVT_MENU, self._on_exit_all, exit_all_item)
        
        self.Append(file_menu, "&File")
        
        # Settings menu
        settings_menu = wx.Menu()
        
        api_keys_item = settings_menu.Append(wx.ID_ANY, "API Keys\tCtrl+K", "Configure API keys for search providers")
        self.parent_window.Bind(wx.EVT_MENU, lambda evt: self._on_open_settings(evt, 0), api_keys_item)
        
        query_defaults_item = settings_menu.Append(wx.ID_ANY, "Query Defaults\tCtrl+D", "Configure default query generation settings")
        self.parent_window.Bind(wx.EVT_MENU, lambda evt: self._on_open_settings(evt, 1), query_defaults_item)
        
        search_settings_item = settings_menu.Append(wx.ID_ANY, "Search Settings\tCtrl+Shift+S", "Configure search execution settings")
        self.parent_window.Bind(wx.EVT_MENU, lambda evt: self._on_open_settings(evt, 2), search_settings_item)
        
        self.Append(settings_menu, "&Settings")
        
        # Help menu
        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, "About", "About this application")
        self.parent_window.Bind(wx.EVT_MENU, self._on_about, about_item)
        self.Append(help_menu, "&Help")
    
    def _on_home(self, event):
        """Navigate to home (Query Generator window)."""
        from view.generate_queries_form_window import PromptWindow
        from view.settings_window import SettingsWindow
        from view.utils.navigation_controller import get_navigation_controller
        
        # Check if current window is already the home window
        if isinstance(self.parent_window, PromptWindow):
            return
        
        # Get navigation controller
        nav = get_navigation_controller()
        
        # Check if home window already exists in stack
        home_win = nav.get_window_by_type('home')
        if home_win:
            # Bring existing home to front
            nav.show_and_raise(home_win)
        else:
            # Create new home window
            home_win = PromptWindow()
            nav.push(home_win, 'home', close_previous=False)
    
    def _on_open_queries(self, event):
        """Open queries from a JSON file."""
        with wx.FileDialog(self.parent_window, "Open Queries File",
                          wildcard="JSON files (*.json)|*.json",
                          style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            
            pathname = fileDialog.GetPath()
            try:
                import os
                
                # Check if file exists
                if not os.path.exists(pathname):
                    wx.MessageBox(f"File not found: {pathname}",
                                "Error", wx.OK | wx.ICON_ERROR)
                    return
                
                with open(pathname, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                
                # Check if it's a valid format
                if not isinstance(data, dict):
                    wx.MessageBox("Invalid queries file format. Expected JSON object.",
                                "Error", wx.OK | wx.ICON_ERROR)
                    return
                
                # Check if empty
                if not data:
                    wx.MessageBox("Queries file is empty.",
                                "Error", wx.OK | wx.ICON_ERROR)
                    return
                
                # Import here to avoid circular imports
                from model.QueryGeneration import QueryGeneration
                from view.results_window import ResultsWindow
                
                # Determine format: check if it has 'results' key (full format) or just provider_id keys (queries-only format)
                if 'results' in data:
                    # Full QueryGeneration format
                    query_gen = QueryGeneration(
                        model=data.get('model', ''),
                        system_prompt=data.get('system_prompt', ''),
                        temperature=data.get('temperature', 0.7),
                        intent=data.get('intent', ''),
                        sources_ids=list(data['results'].keys()),
                        languages=data.get('languages', ['all']),
                        general_n=data.get('general_n', 10)
                    )
                    
                    # Load the results
                    for source_id, queries in data['results'].items():
                        query_gen.add_results(source_id, queries)
                else:
                    # Simple queries-only format (queries.json)
                    # Try to load info.json from same directory if available
                    dir_path = os.path.dirname(pathname)
                    info_path = os.path.join(dir_path, "info.json")
                    
                    if os.path.exists(info_path):
                        # Load metadata from info.json
                        with open(info_path, 'r', encoding='utf-8') as info_file:
                            info_data = json.load(info_file)
                        
                        query_gen = QueryGeneration(
                            model=info_data.get('model', 'Unknown Model'),
                            system_prompt=info_data.get('system_prompt', ''),
                            temperature=info_data.get('temperature', 0.7),
                            intent=info_data.get('intent', ''),
                            sources_ids=info_data.get('sources_ids', list(data.keys())),
                            languages=info_data.get('languages', ['all']),
                            general_n=info_data.get('general_n', 10)
                        )
                        query_gen.instance_id = info_data.get('instance_id', os.path.basename(dir_path))
                    else:
                        # No info.json, create with minimal data
                        query_gen = QueryGeneration(
                            model='Unknown',
                            system_prompt='',
                            temperature=0.7,
                            intent='Loaded from queries file',
                            sources_ids=list(data.keys()),
                            languages=['all'],
                            general_n=10
                        )
                    
                    # Load queries from the simple format
                    for source_id, queries in data.items():
                        query_gen.add_results(source_id, queries)
                
                # Open results window with loaded queries
                from view.utils.navigation_controller import get_navigation_controller
                results_win = ResultsWindow(None, query_gen)

                # Record where this file was opened from so the UI can auto-save
                try:
                    dir_path = os.path.dirname(pathname)
                    parent_dir = os.path.dirname(dir_path)
                    folder_name = os.path.basename(dir_path)
                    # Attach metadata used by the ResultsWindow to auto-save without prompting
                    results_win._loaded_storage_parent = parent_dir
                    results_win._loaded_folder_name = folder_name
                except Exception:
                    # Non-fatal: if we can't determine paths, fall back to prompting on save
                    pass

                nav = get_navigation_controller()
                nav.push(results_win, 'results', close_previous=False)
                
            except json.JSONDecodeError as e:
                wx.MessageBox(f"Invalid JSON format in queries file:\n{str(e)}",
                            "Error", wx.OK | wx.ICON_ERROR)
            except FileNotFoundError as e:
                wx.MessageBox(f"File not found:\n{str(e)}",
                            "Error", wx.OK | wx.ICON_ERROR)
            except KeyError as e:
                wx.MessageBox(f"Missing required field in queries file:\n{str(e)}\n\nThe file may be corrupted or in an old format.",
                            "Error", wx.OK | wx.ICON_ERROR)
            except Exception as e:
                wx.MessageBox(f"Error loading queries file:\n{str(e)}\n\nFile: {pathname}",
                            "Error", wx.OK | wx.ICON_ERROR)
                import traceback
                traceback.print_exc()
    
    def _on_open_search_results(self, event):
        """Open search results from results.json file - SIMPLIFIED."""
        # Load from file
        with wx.FileDialog(self.parent_window, "Open Search Results File (results.json)",
                          wildcard="JSON files (*.json)|*.json",
                          style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            
            pathname = fileDialog.GetPath()
            try:
                # Check if file exists
                if not os.path.exists(pathname):
                    wx.MessageBox(f"File not found: {pathname}",
                                "Error", wx.OK | wx.ICON_ERROR)
                    return
                
                # Get the instance_id from the directory name
                dir_path = os.path.dirname(pathname)
                instance_id = os.path.basename(dir_path)
                
                if not instance_id:
                    wx.MessageBox("Cannot determine instance ID from file path.",
                                "Error", wx.OK | wx.ICON_ERROR)
                    return
                
                # Check if storage_root exists (parent of instance folder)
                storage_root = os.path.dirname(dir_path)
                if not os.path.exists(storage_root):
                    wx.MessageBox(f"Storage directory not found: {storage_root}",
                                "Error", wx.OK | wx.ICON_ERROR)
                    return
                
                # SIMPLE: Use SearchResults.load() to load everything
                from model.SearchResults import SearchResults
                from view.search_results_window import SearchResultsWindow
                from model.QueryGeneration import QueryGeneration
                
                # Load the complete model (includes all results + all filter metadata)
                search_results_model = SearchResults.load(instance_id, storage_root=storage_root, filter_model=None)
                
                # Create a QueryGeneration object for UI display
                query_gen = QueryGeneration(
                    model='',
                    system_prompt='',
                    temperature=0.2,
                    intent=search_results_model.intent,
                    sources_ids=search_results_model.providers,
                    languages=['all'],
                    general_n=10
                )
                query_gen.instance_id = search_results_model.query_generation_id
                query_gen.results = search_results_model.queries
                
                # Show available filters info
                available_filters = search_results_model.get_available_filters()
                if available_filters:
                    filter_info = f"\n\n📊 Available filters: {', '.join(available_filters)}"
                else:
                    filter_info = ""
                
                # Create window with the loaded results
                from view.utils.navigation_controller import get_navigation_controller
                results_win = SearchResultsWindow(None, search_results_model.results, query_gen)
                results_win.storage_instance_id = instance_id
                results_win.search_results_model = search_results_model  # Attach the model

                # Record storage location so Save can auto-write to the same place
                try:
                    # storage_root is the parent of the instance directory
                    results_win._loaded_storage_parent = storage_root
                    results_win._loaded_folder_name = instance_id
                except Exception:
                    pass

                nav = get_navigation_controller()
                nav.push(results_win, 'search_results', close_previous=False)
                
            except json.JSONDecodeError as e:
                wx.MessageBox(f"Invalid JSON format in search results file:\n{str(e)}",
                            "Error", wx.OK | wx.ICON_ERROR)
            except FileNotFoundError as e:
                wx.MessageBox(f"Required file not found:\n{str(e)}\n\nMake sure you're opening results.json from a complete search results folder.",
                            "Error", wx.OK | wx.ICON_ERROR)
            except KeyError as e:
                wx.MessageBox(f"Missing required field in search results:\n{str(e)}\n\nThe file may be corrupted or in an old format.",
                            "Error", wx.OK | wx.ICON_ERROR)
            except Exception as e:
                wx.MessageBox(f"Error loading search results file:\n{str(e)}\n\nFile: {pathname}",
                            "Error", wx.OK | wx.ICON_ERROR)
                import traceback
                traceback.print_exc()
    
    def _on_open_settings(self, event, tab_index: int = 0):
        """
        Open settings window.
        
        Args:
            event: The menu event
            tab_index: The index of the tab to select (0=API Keys, 1=Query Defaults, 2=Search Settings)
        """
        from view.settings_window import SettingsWindow
        from view.generate_queries_form_window import PromptWindow
        
        # Check if current window is already the settings window
        if isinstance(self.parent_window, SettingsWindow):
            # Just switch to the requested tab
            if hasattr(self.parent_window, 'notebook'):
                notebook = None
                for child in self.parent_window.GetChildren():
                    if isinstance(child, wx.Panel):
                        for panel_child in child.GetChildren():
                            if isinstance(panel_child, wx.Notebook):
                                notebook = panel_child
                                break
                if notebook and 0 <= tab_index < notebook.GetPageCount():
                    notebook.SetSelection(tab_index)
            return
        
        # Settings window uses singleton pattern
        # Don't close parent window - just show settings on top
        settings_win = SettingsWindow(None, tab_index=tab_index, opened_from_home=False)
        # Just show it - don't use NavigationController so parent stays open
        settings_win.Show()
    
    def _on_exit_all(self, event):
        """Exit the entire application."""
        nav = get_navigation_controller()
        nav.close_all()
    
    def _on_about(self, event):
        """Show about dialog."""
        info = wx.adv.AboutDialogInfo()
        info.SetName("GLiSE - Grey Literature Search Engine")
        info.SetVersion("1.0.0")
        info.SetDescription("Generate optimized search queries for grey literature research across multiple platforms.")
        info.SetWebSite("https://github.com/anonymous10112025-prog/GLiSE")
        wx.adv.AboutBox(info)
