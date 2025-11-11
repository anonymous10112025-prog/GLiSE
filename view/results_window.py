import wx
import time
import os
import re
from typing import Dict, List
from model.QueryGeneration import QueryGeneration
from model.GLProvider import GLProvider
from model.providers import get_provider
from view.progress_windows.search_progress_dialog import SearchProgressDialog
from view.search_results_window import SearchResultsWindow
from view.utils.menu_bar import AppMenuBar
from view.utils.navigation_controller import get_navigation_controller


def validate_folder_name(name: str) -> tuple:
    """
    Validate folder name for filesystem safety.
    
    Returns:
        (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Folder name cannot be empty"
    
    # Check for invalid characters (Windows + Unix)
    invalid_chars = r'<>:"/\\|?*'
    if any(char in name for char in invalid_chars):
        return False, f"Folder name contains invalid characters: {invalid_chars}"
    
    # Check for reserved names (Windows)
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                     'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 
                     'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
    if name.upper() in reserved_names:
        return False, f"'{name}' is a reserved system name"
    
    # Check for special directory names
    if name in ['.', '..']:
        return False, "Invalid folder name"
    
    # Check for trailing spaces or dots (Windows issue)
    if name != name.rstrip('. '):
        return False, "Folder name cannot end with space or dot"
    
    return True, ""


class ResultsWindow(wx.Frame):
    """Window displaying generated query results grouped by source."""
    
    def __init__(self, parent, query_generation: QueryGeneration):
        """
        Initialize the results window.
        
        Args:
            parent: Parent window
            query_generation: QueryGeneration instance with results
        """
        super().__init__(
            parent,
            title=f"Query Results - {query_generation.instance_id}",
            size=(800, 600)
        )
        
        self.query_generation = query_generation
        
        # Set window icon
        from view.utils.icon_helper import set_window_icon
        set_window_icon(self)
        
        # Add menu bar
        menu_bar = AppMenuBar(self)
        self.SetMenuBar(menu_bar)
        
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Intent section - display complete intent
        intent_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Intent")
        
        # Create intent text control to display the complete text
        intent_text = wx.TextCtrl(
            panel,
            value=query_generation.intent,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP | wx.BORDER_NONE | wx.TE_NO_VSCROLL,
            size=(-1, -1)  # Auto size
        )
        intent_text.SetBackgroundColour(panel.GetBackgroundColour())
        
        # Calculate the needed height based on actual content
        dc = wx.ClientDC(intent_text)
        dc.SetFont(intent_text.GetFont())
        line_height = dc.GetTextExtent("M")[1]
        
        # Count actual lines in the text (accounting for newlines)
        num_lines = max(1, len(query_generation.intent.split('\n')))
        
        # Set minimum height to fit the content tightly
        desired_height = num_lines * line_height + 10  # Add small padding
        intent_text.SetMinSize((-1, desired_height))
        
        # Add right-click context menu for copying
        def on_intent_right_click(event):
            menu = wx.Menu()
            copy_item = menu.Append(wx.ID_ANY, "Copy Intent")
            
            def on_copy(evt):
                if wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(wx.TextDataObject(query_generation.intent))
                    wx.TheClipboard.Close()
            
            panel.Bind(wx.EVT_MENU, on_copy, copy_item)
            panel.PopupMenu(menu)
            menu.Destroy()
        
        intent_text.Bind(wx.EVT_RIGHT_DOWN, on_intent_right_click)
        
        intent_box.Add(intent_text, 0, wx.ALL | wx.EXPAND, 5)
        main_sizer.Add(intent_box, 0, wx.ALL | wx.EXPAND, 10)
        
        # Search Settings Section
        settings_box = wx.StaticBoxSizer(wx.HORIZONTAL, panel, "Search Settings")
        
        from model.Settings import get_settings
        settings = get_settings()
        
        # Max Results Per Query
        settings_box.Add(wx.StaticText(panel, label="Max Results Per Query:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.max_query_ctrl = wx.SpinCtrl(panel, value=str(settings.get("MAX_RESULTS_PER_QUERY_DEFAULT", 50)), 
                                          min=1, max=1000, size=(80, -1))
        settings_box.Add(self.max_query_ctrl, 0, wx.ALL, 5)
        
        settings_box.Add(wx.StaticText(panel, label="   Max Results Per Provider:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.max_provider_ctrl = wx.SpinCtrl(panel, value=str(settings.get("MAX_RESULTS_PER_PROVIDER_DEFAULT", 100)), 
                                             min=1, max=1000, size=(80, -1))
        settings_box.Add(self.max_provider_ctrl, 0, wx.ALL, 5)
        
        # Help text
        help_text = wx.StaticText(panel, label="(These settings control how many results are fetched)")
        help_font = help_text.GetFont()
        help_font = help_font.MakeItalic()
        help_font.SetPointSize(help_font.GetPointSize() - 1)
        help_text.SetFont(help_font)
        help_text.SetForegroundColour(wx.Colour(100, 100, 100))
        settings_box.Add(help_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        
        main_sizer.Add(settings_box, 0, wx.ALL | wx.EXPAND, 10)
        
        # Notebook for sources
        notebook = wx.Notebook(panel)
        
        # Get provider names
        providers = GLProvider.get_providers_list()
        
        # Create a tab for each source
        for source_id, queries in query_generation.results.items():
            # Get provider name
            provider = providers.get(source_id)
            tab_label = provider.name if provider else source_id
            
            # Create panel for this source
            source_panel = wx.Panel(notebook)
            source_sizer = wx.BoxSizer(wx.VERTICAL)
            
            # Count label
            count_label = wx.StaticText(source_panel, label=f"{len(queries)} queries generated")
            count_font = count_label.GetFont()
            count_font = count_font.Bold()
            count_label.SetFont(count_font)
            source_sizer.Add(count_label, 0, wx.ALL, 5)
            
            # List of queries
            queries_list = wx.ListBox(source_panel, choices=queries, style=wx.LB_SINGLE | wx.LB_HSCROLL)
            source_sizer.Add(queries_list, 1, wx.ALL | wx.EXPAND, 5)
            
            source_panel.SetSizer(source_sizer)
            notebook.AddPage(source_panel, tab_label)
        
        main_sizer.Add(notebook, 1, wx.ALL | wx.EXPAND, 10)
        
        # Bottom buttons
        bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        search_btn = wx.Button(panel, label="Search")
        search_btn.Bind(wx.EVT_BUTTON, self.on_search)
        bottom_sizer.Add(search_btn, 0, wx.ALL, 5)
        
        save_info_btn = wx.Button(panel, label="Save to Storage")
        save_info_btn.Bind(wx.EVT_BUTTON, self.on_save)
        bottom_sizer.Add(save_info_btn, 0, wx.ALL, 5)
        
        close_btn = wx.Button(panel, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda evt: self.Close())
        bottom_sizer.Add(close_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(bottom_sizer, 0, wx.ALL | wx.CENTER, 10)
        
        panel.SetSizer(main_sizer)
        self.Centre()
    
    def on_save(self, event):
        """Save the query generation to storage."""
        try:
            # If this window was opened from an existing saved folder, auto-save there
            if hasattr(self, '_loaded_storage_parent') and hasattr(self, '_loaded_folder_name'):
                parent_path = self._loaded_storage_parent
                folder_name = self._loaded_folder_name

                # Validate folder name
                is_valid, error_msg = validate_folder_name(folder_name)
                if not is_valid:
                    wx.MessageBox(error_msg, "Invalid Folder Name", wx.OK | wx.ICON_ERROR)
                    return

                try:
                    storage_path = self.query_generation.save(storage_root=parent_path, folder_name=folder_name)
                    # If save succeeded, show message and return
                    wx.MessageBox(
                        f"Query generation saved successfully!\n\nLocation: {storage_path}",
                        "Saved",
                        wx.OK | wx.ICON_INFORMATION
                    )
                    return
                except PermissionError:
                    wx.MessageBox("Permission denied. Please choose a different location.", "Error", wx.OK | wx.ICON_ERROR)
                    return
                except OSError as e:
                    wx.MessageBox(f"Filesystem error: {e}", "Error", wx.OK | wx.ICON_ERROR)
                    return

            # Use file dialog to choose location and name in one step
            default_dir = os.path.abspath("storage")
            default_file = self.query_generation.instance_id
            
            dlg = wx.FileDialog(
                self,
                "Save Query Generation As",
                defaultDir=default_dir,
                defaultFile=default_file,
                wildcard="Query Generation Folder|*",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
            )
            
            if dlg.ShowModal() != wx.ID_OK:
                dlg.Destroy()
                return
            
            full_path = dlg.GetPath()
            dlg.Destroy()
            
            # Extract parent directory and folder name
            parent_path = os.path.dirname(full_path)
            folder_name = os.path.basename(full_path)
            
            # Validate folder name
            is_valid, error_msg = validate_folder_name(folder_name)
            if not is_valid:
                wx.MessageBox(error_msg, "Invalid Folder Name", wx.OK | wx.ICON_ERROR)
                return
            
            # Check if folder already exists
            target_path = os.path.join(parent_path, folder_name)
            if os.path.exists(target_path):
                dlg = wx.MessageDialog(
                    self,
                    f"Folder '{folder_name}' already exists.\n\nDo you want to overwrite it?",
                    "Confirm Overwrite",
                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
                )
                if dlg.ShowModal() != wx.ID_YES:
                    dlg.Destroy()
                    return
                dlg.Destroy()
            
            # Save using new API (no instance_id mutation)
            self.query_generation.save(storage_root=parent_path, folder_name=folder_name)
            
            # Get final storage path for display
            original_id = self.query_generation.instance_id
            self.query_generation.instance_id = folder_name
            storage_path = self.query_generation.get_storage_path(parent_path)
            self.query_generation.instance_id = original_id
            
            wx.MessageBox(
                f"Query generation saved successfully!\n\nLocation: {storage_path}",
                "Saved",
                wx.OK | wx.ICON_INFORMATION
            )
        except PermissionError:
            wx.MessageBox("Permission denied. Please choose a different location.", "Error", wx.OK | wx.ICON_ERROR)
        except OSError as e:
            wx.MessageBox(f"Filesystem error: {e}", "Error", wx.OK | wx.ICON_ERROR)
        except Exception as e:
            wx.MessageBox(f"Error saving: {e}", "Error", wx.OK | wx.ICON_ERROR)
            import traceback
            traceback.print_exc()
    
    def on_search(self, event):
        """Execute searches for all generated queries."""
        # Count total queries
        total_queries = sum(len(queries) for queries in self.query_generation.results.values())
        
        if total_queries == 0:
            wx.MessageBox("No queries to search!", "Info", wx.OK | wx.ICON_INFORMATION)
            return
        
        # Proceed immediately without showing a confirmation dialog about quota
        # The previous implementation prompted the user with a modal dialog
        # warning about API quota. That dialog has been removed to simplify
        # the user flow and start searches immediately when the button is clicked.
        
        # Create progress dialog
        progress_dlg = SearchProgressDialog(self, total_queries)
        progress_dlg.Show()
        
        # Execute searches
        from model.Settings import get_settings
        settings = get_settings()
        
        search_results = {}
        # Use values from UI controls
        max_results_per_query = self.max_query_ctrl.GetValue()
        max_results_per_provider = self.max_provider_ctrl.GetValue()
        sleep_between = settings.get('SLEEP_BETWEEN', 1.0)
        
        try:
            for provider_id, queries in self.query_generation.results.items():
                # Check for cancellation before processing each provider
                if progress_dlg.is_cancelled():
                    break
                
                search_results[provider_id] = []
                provider_results_count = 0  # Track results per provider
                
                # Get provider instance
                try:
                    provider = get_provider(provider_id)
                except ValueError:
                    progress_dlg.set_error(provider_id, f"Unknown provider: {provider_id}")
                    continue
                
                # Track consecutive errors to detect API key or connection issues
                consecutive_errors = 0
                max_consecutive_errors = 3
                
                # Execute each query
                for query in queries:
                    # Check for cancellation before each query
                    if progress_dlg.is_cancelled():
                        break
                    
                    # Check if we've reached the provider limit
                    if provider_results_count >= max_results_per_provider:
                        break
                    
                    # Stop if too many consecutive errors (likely API key or connection issue)
                    if consecutive_errors >= max_consecutive_errors:
                        error_msg = f"Too many consecutive errors for {provider.name}. Possible API key or connection issue."
                        progress_dlg.set_error(provider_id, error_msg)
                        wx.CallAfter(wx.MessageBox, 
                            f"{error_msg}\n\nPlease check:\n"
                            f"1. Your API key is correctly configured in Settings\n"
                            f"2. Your internet connection is working\n"
                            f"3. The API service is available",
                            "Provider Error",
                            wx.OK | wx.ICON_WARNING)
                        break
                    
                    progress_dlg.set_current_query(query, provider.name)
                    
                    # Check for cancellation right after setting query
                    if progress_dlg.is_cancelled():
                        break
                    
                    try:
                        # Execute search with per-query limit and date range from QueryGeneration
                        results = provider.search(
                            query, 
                            max_results_per_query,
                            from_date=self.query_generation.from_date,
                            to_date=self.query_generation.to_date
                        )
                        
                        # Check for cancellation after search completes
                        if progress_dlg.is_cancelled():
                            break
                        
                        # Reset error counter on success
                        consecutive_errors = 0
                        
                        # Add results up to the provider limit
                        remaining_slots = max_results_per_provider - provider_results_count
                        results_to_add = results[:remaining_slots]
                        search_results[provider_id].extend(results_to_add)
                        provider_results_count += len(results_to_add)
                        
                        # Update progress
                        progress_dlg.update_progress(query, provider.name, len(results))
                        
                        # Check for cancellation after progress update
                        if progress_dlg.is_cancelled():
                            break
                        
                        # Sleep between requests to avoid rate limiting, checking for cancellation
                        sleep_start = time.time()
                        while time.time() - sleep_start < sleep_between:
                            if progress_dlg.is_cancelled():
                                break
                            time.sleep(0.1)
                            wx.GetApp().Yield()
                        
                        # Final check after sleep
                        if progress_dlg.is_cancelled():
                            break
                        
                    except Exception as e:
                        consecutive_errors += 1
                        error_str = str(e).lower()
                        
                        # Detect specific error types
                        if any(keyword in error_str for keyword in ['401', 'unauthorized', 'authentication', 'api key', 'invalid key']):
                            error_msg = f"API Key Error for {provider.name}: {str(e)}"
                            progress_dlg.set_error(query, error_msg)
                            wx.CallAfter(wx.MessageBox,
                                f"API Key Error for {provider.name}!\n\n{str(e)}\n\n"
                                f"Please check your API key in Settings.",
                                "Authentication Error",
                                wx.OK | wx.ICON_ERROR)
                            break  # Stop processing this provider
                        elif any(keyword in error_str for keyword in ['connection', 'timeout', 'network', 'dns']):
                            error_msg = f"Connection Error for {provider.name}: {str(e)}"
                            progress_dlg.set_error(query, error_msg)
                        elif any(keyword in error_str for keyword in ['403', 'forbidden', 'rate limit', 'quota']):
                            error_msg = f"Rate Limit/Quota Error for {provider.name}: {str(e)}"
                            progress_dlg.set_error(query, error_msg)
                            wx.CallAfter(wx.MessageBox,
                                f"Rate Limit or Quota Error for {provider.name}!\n\n{str(e)}\n\n"
                                f"You may need to wait or check your API quota.",
                                "Rate Limit Error",
                                wx.OK | wx.ICON_WARNING)
                            break  # Stop processing this provider
                        else:
                            progress_dlg.set_error(query, str(e))
                        
                        continue
                
                # Deduplicate results for this provider after all queries are done
                if provider_id in search_results and search_results[provider_id]:
                    search_results[provider_id] = provider._dedupe_by_url(search_results[provider_id])
            
            # Check if search was cancelled
            was_cancelled = progress_dlg.cancelled
            
            # Close progress dialog
            progress_dlg.Close()
            progress_dlg.Destroy()
            
            # Check if any results were collected
            total_results = sum(len(results) for results in search_results.values())
            
            # If cancelled, show message and don't open results window
            if was_cancelled:
                wx.MessageBox(
                    "Search Cancelled",
                    "Cancelled",
                    wx.OK | wx.ICON_INFORMATION
                )
                return
            
            # Only continue if not cancelled
            if total_results > 0:
                # Auto-save search results using SearchResults model
                try:
                    from model.SearchResults import SearchResults
                    
                    search_results_model = SearchResults(
                        query_generation_id=self.query_generation.instance_id,
                        intent=self.query_generation.intent,
                        providers=list(search_results.keys())
                    )
                    
                    # Add results for each provider with their queries
                    for provider_id, results in search_results.items():
                        queries_list = self.query_generation.results.get(provider_id, [])
                        search_results_model.add_results(provider_id, results, queries=queries_list)
                    
                    # Save to storage
                    storage_path = search_results_model.save()
                    
                except Exception as e:
                    pass  # Silent fail for auto-save
                
                # Show results window with collected results
                # Use parent=None to prevent auto-destruction when this window closes
                results_window = SearchResultsWindow(None, search_results, self.query_generation)
                
                # Navigate to search results window (keeps this window open in background)
                nav = get_navigation_controller()
                nav.push(results_window, 'search_results', close_previous=False)
            else:
                # No results collected
                wx.MessageBox("No results were found.", "Search Complete", wx.OK | wx.ICON_INFORMATION)
            
        except Exception as e:
            progress_dlg.Close()
            progress_dlg.Destroy()
            wx.MessageBox(f"Error during search execution: {e}", "Error", wx.OK | wx.ICON_ERROR)
