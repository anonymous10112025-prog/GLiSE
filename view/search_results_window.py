"""
Search results display window.
Shows search results grouped by provider in a tabbed interface with tables.
"""

import wx
import wx.grid as grid
import os
import traceback
from typing import Dict, List
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


class SearchResultsWindow(wx.Frame):
    """Window displaying search results grouped by provider."""
    
    def __init__(self, parent, search_results, query_generation=None):
        """
        Initialize the search results window.
        
        Args:
            parent: Parent window
            search_results: Either a List of result dictionaries or Dict mapping provider IDs to lists
            query_generation: Optional QueryGeneration instance
        """
        # Determine title
        if query_generation:
            title = f"Search Results - {query_generation.instance_id}"
        else:
            title = "Search Results"
        
        super().__init__(
            parent,
            title=title,
            size=(1000, 700)
        )
        
        # Make window fullscreen by default
        self.Maximize()
        
        self.query_generation = query_generation
        self.filter_applied = False  # Track if filtering has been applied
        self.current_filter_model = None  # Track which model was used for filtering
        self.storage_instance_id = None  # Track saved instance ID for reloading
        
        # Simple: always work with SearchResults model instance
        self.search_results_model = None  # The actual SearchResults instance
        
        # Set window icon
        from view.utils.icon_helper import set_window_icon
        set_window_icon(self)
        
        self._build_ui(parent, search_results)
    
    @classmethod
    def create_filtered(cls, parent, search_results, query_generation, filter_model_name):
        """
        Create a SearchResultsWindow with filtered results.
        Alternative constructor for filtered results.
        
        Args:
            parent: Parent window
            search_results: Filtered results dictionary
            query_generation: QueryGeneration instance
            filter_model_name: Name of the model used for filtering
        
        Returns:
            SearchResultsWindow instance with filtering state set
        """
        # Create instance using regular constructor
        instance = cls(parent, search_results, query_generation)
        
        # Set filtering state
        instance.filter_applied = True
        instance.current_filter_model = filter_model_name
        
        # Rebuild UI to reflect filtered state
        instance._rebuild_ui()
        
        return instance
    
    def _build_ui(self, parent, search_results):
        """Build the user interface."""
        # Convert list to dict if needed
        if isinstance(search_results, list):
            # Group by provider
            grouped_results = {}
            for result in search_results:
                provider_id = result.get('source', 'unknown')
                if provider_id not in grouped_results:
                    grouped_results[provider_id] = []
                grouped_results[provider_id].append(result)
            self.search_results = grouped_results
        else:
            self.search_results = search_results
        
        # Add menu bar
        menu_bar = AppMenuBar(self)
        self.SetMenuBar(menu_bar)
        
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Create split window for table and details panel
        splitter = wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE)
        
        # Left panel - Summary, Filtering, and Notebook with results tables
        left_panel = wx.Panel(splitter)
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Right panel - Details panel (create BEFORE notebooks so grids can reference it)
        from view.utils.result_details_panel import ResultDetailsPanel
        self.details_panel = ResultDetailsPanel(splitter)
        
        # Generation Summary Section (only if query_generation available)
        if self.query_generation:
            header_box = wx.StaticBoxSizer(wx.VERTICAL, left_panel, "Generation Summary")
            
            summary_grid = wx.FlexGridSizer(rows=3, cols=2, hgap=10, vgap=5)
            
            # Intent
            summary_grid.Add(wx.StaticText(left_panel, label="Intent:"), 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
            
            # Create intent label with truncation
            truncated_intent = self.query_generation.intent[:100] + "..." if len(self.query_generation.intent) > 100 else self.query_generation.intent
            intent_label = wx.StaticText(left_panel, label=truncated_intent)
            
            # Add tooltip with full text
            intent_label.SetToolTip(self.query_generation.intent)
            
            # Add right-click context menu for copying
            def on_intent_right_click(event):
                menu = wx.Menu()
                copy_item = menu.Append(wx.ID_ANY, "Copy Full Intent")
                
                def on_copy(evt):
                    if wx.TheClipboard.Open():
                        wx.TheClipboard.SetData(wx.TextDataObject(self.query_generation.intent))
                        wx.TheClipboard.Close()
                
                left_panel.Bind(wx.EVT_MENU, on_copy, copy_item)
                left_panel.PopupMenu(menu)
                menu.Destroy()
            
            intent_label.Bind(wx.EVT_RIGHT_DOWN, on_intent_right_click)
            
            summary_grid.Add(intent_label, 0, wx.EXPAND)
            
            # Total queries generated
            total_queries = sum(len(queries) for queries in self.query_generation.results.values())
            summary_grid.Add(wx.StaticText(left_panel, label="Queries:"), 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
            summary_grid.Add(wx.StaticText(left_panel, label=str(total_queries)), 0, wx.EXPAND)
            
            # Total results
            total_results = sum(len(results) for results in self.search_results.values())
            summary_grid.Add(wx.StaticText(left_panel, label="Total Results:"), 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
            summary_grid.Add(wx.StaticText(left_panel, label=str(total_results)), 0, wx.EXPAND)
            
            header_box.Add(summary_grid, 0, wx.ALL | wx.EXPAND, 5)
            left_sizer.Add(header_box, 0, wx.ALL | wx.EXPAND, 5)
        else:
            # Simple header without query_generation info
            total_results = sum(len(results) for results in self.search_results.values())
            header_label = wx.StaticText(left_panel, label=f"Total Results: {total_results}")
            header_font = header_label.GetFont()
            header_font = header_font.Bold()
            header_label.SetFont(header_font)
            left_sizer.Add(header_label, 0, wx.ALL, 5)
        
        # ML Filtering Options Section (always show, but indicate if filtered)
        filter_box = wx.StaticBoxSizer(wx.VERTICAL, left_panel, "ML Filtering Options to keep relevant results only")
        
        # Show status if filtering has been applied
        if self.filter_applied:
            status_label = wx.StaticText(left_panel, label=f"✓ Showing only relevant results (filtered with {self.current_filter_model})")
            status_font = status_label.GetFont()
            status_font = status_font.Bold()
            status_label.SetFont(status_font)
            status_label.SetForegroundColour(wx.Colour(0, 128, 0))  # Green color
            filter_box.Add(status_label, 0, wx.ALL | wx.CENTER, 5)
        
        filter_inner_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        filter_label = wx.StaticText(left_panel, label="Filter results with ML model:")
        filter_inner_sizer.Add(filter_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        
        # Radio buttons for filtering options
        self.filter_choice = wx.RadioBox(
            left_panel,
            label="",
            choices=[
                "No filter (show all results)",
                "text-embedding-3-small (faster, lower cost)",
                "text-embedding-3-large (better accuracy, higher cost)"
            ],
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS
        )
        # Set selection based on current filter state
        if self.filter_applied:
            if self.current_filter_model == "text-embedding-3-small":
                self.filter_choice.SetSelection(1)
            elif self.current_filter_model == "text-embedding-3-large":
                self.filter_choice.SetSelection(2)
        else:
            self.filter_choice.SetSelection(0)  # Default to no filter
        
        filter_inner_sizer.Add(self.filter_choice, 1, wx.EXPAND)
        
        # Apply button
        self.apply_filter_btn = wx.Button(left_panel, label="Apply")
        self.apply_filter_btn.Bind(wx.EVT_BUTTON, self.on_apply_filter)
        filter_inner_sizer.Add(self.apply_filter_btn, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 10)
        
        filter_box.Add(filter_inner_sizer, 0, wx.ALL | wx.EXPAND, 5)
        left_sizer.Add(filter_box, 0, wx.ALL | wx.EXPAND, 5)
        
        # Notebook for providers
        notebook = wx.Notebook(left_panel)
        
        # Create a tab for each provider with results
        for provider_id, results in self.search_results.items():
            # Create panel for this provider
            provider_panel = wx.Panel(notebook)
            provider_sizer = wx.BoxSizer(wx.VERTICAL)
            
            # Count label
            count_label = wx.StaticText(provider_panel, label=f"{len(results)} results found")
            count_font = count_label.GetFont()
            count_font = count_font.Bold()
            count_label.SetFont(count_font)
            provider_sizer.Add(count_label, 0, wx.ALL, 5)
            
            # If no results, show a message
            if not results:
                message = f"No {'relevant' if self.filter_applied else ''} results found for this provider."
                
                no_results_label = wx.StaticText(provider_panel, label=message)
                no_results_font = no_results_label.GetFont()
                no_results_font = no_results_font.MakeItalic()
                no_results_label.SetFont(no_results_font)
                no_results_label.SetForegroundColour(wx.Colour(128, 128, 128))  # Gray color
                provider_sizer.Add(no_results_label, 1, wx.ALL | wx.ALIGN_CENTER, 20)
            else:
                # Create grid for results
                results_grid = grid.Grid(provider_panel)
                
                # Bind click event to show details
                results_grid.Bind(grid.EVT_GRID_SELECT_CELL, lambda evt, pid=provider_id, res=results: self.on_cell_selected(evt, pid, res))
                
                # Determine columns based on first result
                sample_result = results[0]
                columns = self._get_columns_for_provider(provider_id, sample_result)
                
                results_grid.CreateGrid(len(results), len(columns))
                
                # Set column headers
                for col_idx, col_name in enumerate(columns):
                    results_grid.SetColLabelValue(col_idx, col_name)
                
                # Fill grid with data
                for row_idx, result in enumerate(results):
                    for col_idx, col_name in enumerate(columns):
                        value = result.get(col_name, "")
                        # Truncate long values
                        if isinstance(value, str) and len(value) > 200:
                            value = value[:200] + "..."
                        results_grid.SetCellValue(row_idx, col_idx, str(value))
                        results_grid.SetReadOnly(row_idx, col_idx)
                
                # Auto-size columns
                results_grid.AutoSizeColumns()
                
                # Set column widths with limits
                for col_idx in range(len(columns)):
                    width = results_grid.GetColSize(col_idx)
                    if width > 300:
                        results_grid.SetColSize(col_idx, 300)
                    elif width < 100:
                        results_grid.SetColSize(col_idx, 100)
                
                provider_sizer.Add(results_grid, 1, wx.ALL | wx.EXPAND, 5)
            
            provider_panel.SetSizer(provider_sizer)
            
            # Get provider name for tab label
            from model.providers import get_provider
            try:
                provider = get_provider(provider_id)
                tab_label = f"{provider.name} ({len(results)})"
            except:
                tab_label = f"{provider_id} ({len(results)})"
            
            notebook.AddPage(provider_panel, tab_label)
        
        left_sizer.Add(notebook, 1, wx.EXPAND)
        left_panel.SetSizer(left_sizer)
        
        # Split the window (60% left, 40% right)
        # details_panel was already created above
        splitter.SplitVertically(left_panel, self.details_panel)
        splitter.SetSashPosition(int(self.GetSize().width * 0.5))
        splitter.SetMinimumPaneSize(200)  # Minimum width for each panel
        
        main_sizer.Add(splitter, 1, wx.ALL | wx.EXPAND, 10)
        
        # Bottom buttons
        bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        save_json_btn = wx.Button(panel, label="Save Results")
        save_json_btn.Bind(wx.EVT_BUTTON, self.on_save_json)
        bottom_sizer.Add(save_json_btn, 0, wx.ALL, 5)
        
        close_btn = wx.Button(panel, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda evt: self.Close())
        bottom_sizer.Add(close_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(bottom_sizer, 0, wx.ALL | wx.CENTER, 10)
        
        panel.SetSizer(main_sizer)
        self.panel = panel  # Store panel for rebuilding
        self.Centre()
        
        # Bind close event to check for unsaved filters
        self.Bind(wx.EVT_CLOSE, self.on_close)
    
    def on_close(self, event):
        """Handle window close event - prompt to save unsaved changes."""
        # Prevent double-handling of close events
        if hasattr(self, '_closing') and self._closing:
            event.Skip()
            return
        
        self._closing = True
        
        if self._get_unsaved_changes():
            dlg = wx.MessageDialog(
                self,
                "You have unsaved changes.\n\nSave before closing?",
                "Unsaved Changes",
                wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION
            )
            result = dlg.ShowModal()
            dlg.Destroy()
            
            if result == wx.ID_YES:
                # Save current state
                self.on_save_json(None)
            elif result == wx.ID_CANCEL:
                self._closing = False  # Reset flag since we're not closing
                event.Veto()  # Don't close
                return
        
        # Proceed with closing - let NavigationController handle it
        event.Skip()
    
    def _rebuild_ui(self):
        """Rebuild the UI to reflect current filter state."""
        if hasattr(self, 'panel') and self.panel:
            self.panel.Destroy()
        self._build_ui(self, self.search_results)
    
    def _get_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes (new filters computed but not saved)."""
        if not self.search_results_model or not self.storage_instance_id:
            # If never saved, there are unsaved changes
            return self.search_results_model is not None
        
        # Check if current model state differs from disk
        from model.SearchResults import SearchResults
        try:
            disk_model = SearchResults.load(self.storage_instance_id, filter_model=None)
            
            # Compare available filters
            current_filters = set(self.search_results_model.get_available_filters())
            disk_filters = set(disk_model.get_available_filters())
            
            return current_filters != disk_filters
        except:
            # If can't load from disk, assume there are unsaved changes
            return True
    
    def _get_columns_for_provider(self, provider_id: str, sample_result: dict) -> List[str]:
        """Determine which columns to display for a provider."""
        # Check if results are filtered (have relevant_score field)
        is_filtered = "relevant_score" in sample_result
        
        # Common columns
        common_cols = ["title", "url", "snippet", "search_query"]
        
        # Provider-specific columns
        provider_cols = {
            "gh_repos": ["title", "url", "snippet", "stargazers_count", "language", "search_query"],
            "gh_issues": ["title", "url", "state", "comments", "search_query"],
            "so": ["title", "url", "score", "is_answered", "search_query"],
            "google": ["title", "url", "snippet", "search_query"],
        }
        
        # Get base columns for this provider
        if provider_id in provider_cols:
            columns = provider_cols[provider_id].copy()
        else:
            # Use common columns plus any extra keys found in the sample
            extra_keys = [k for k in sample_result.keys() 
                         if k not in common_cols and k not in ["source", "relevant", "relevant_proba", "relevant_score", "_original_index", "_filters", "search_intent"]]
            columns = common_cols + extra_keys[:3]  # Limit to avoid too many columns
        
        return columns
    
    def on_show_all_results(self, event):
        """Show all unfiltered results (just change the view)."""
        try:
            # If not filtered, already showing all
            if not self.filter_applied:
                wx.MessageBox("Already showing all results.", "Info", wx.OK | wx.ICON_INFORMATION)
                return
            
            # Simple: just get all results from the model
            if self.search_results_model:
                all_results = self.search_results_model.results
            elif self.storage_instance_id:
                # Load from disk if needed
                from model.SearchResults import SearchResults
                self.search_results_model = SearchResults.load(self.storage_instance_id, filter_model=None)
                all_results = self.search_results_model.results
            else:
                wx.MessageBox("No results available.", "Error", wx.OK | wx.ICON_ERROR)
                return
            
            # Create new window with all results
            new_window = SearchResultsWindow(None, all_results, self.query_generation)
            new_window.storage_instance_id = self.storage_instance_id
            new_window.search_results_model = self.search_results_model  # Share the same model
            
            # Navigate to new window
            nav = get_navigation_controller()
            nav.push(new_window, 'search_results', close_previous=True)
            
        except Exception as e:
            wx.MessageBox(f"Error loading all results: {e}", "Error", wx.OK | wx.ICON_ERROR)
            import traceback
            traceback.print_exc()
    
    def on_apply_filter(self, event):
        """Apply ML filtering based on selected option."""
        # Get selected filter option
        selection = self.filter_choice.GetSelection()
        
        # If "No filter" is selected, show all results
        if selection == 0:
            self.on_show_all_results(event)
            return
        
        # Ensure we have a search_results_model
        if not self.search_results_model:
            # Create one from current results
            from model.SearchResults import SearchResults
            self.search_results_model = SearchResults(
                query_generation_id=self.query_generation.instance_id if self.query_generation else "unknown",
                intent=self.query_generation.intent if self.query_generation else "Search results",
                providers=list(self.search_results.keys()),
                instance_id=self.storage_instance_id
            )
            for provider_id, results in self.search_results.items():
                queries_list = None
                if self.query_generation and provider_id in self.query_generation.results:
                    queries_list = self.query_generation.results[provider_id]
                self.search_results_model.add_results(provider_id, results, queries=queries_list)
        
        # Determine which embedding model to use
        # selection == 1: text-embedding-3-small
        # selection == 2: text-embedding-3-large
        use_large_model = (selection == 2)
        model_name = "text-embedding-3-large" if use_large_model else "text-embedding-3-small"
        
        # Check if filter already computed (saved in model)
        if self.search_results_model.has_filter(model_name):
            # Use already computed filter - much faster! Just show the view directly
            filtered_results = self.search_results_model.get_filtered_results(model_name)
            
            # Show filtered view directly (no pop-up needed)
            new_window = SearchResultsWindow.create_filtered(
                None, 
                filtered_results, 
                self.query_generation,
                model_name
            )
            new_window.storage_instance_id = self.storage_instance_id
            new_window.search_results_model = self.search_results_model  # Share same model
            
            # Navigate to new window
            nav = get_navigation_controller()
            nav.push(new_window, 'search_results', close_previous=True)
            return
        
        # Get the user's original search intent/message
        # This should come from the info.json file or query_generation
        user_intent = None
        if self.query_generation:
            # Use the intent from QueryGeneration (the actual user message)
            user_intent = self.query_generation.intent
        
        # If we still don't have intent, check if results have it embedded
        if not user_intent:
            # Try to get from first result if it has search_intent
            for provider_results in self.search_results.values():
                if provider_results and 'search_intent' in provider_results[0]:
                    user_intent = provider_results[0]['search_intent']
                    break
        
        # If still no intent, ask the user
        if not user_intent:
            intent_dlg = wx.TextEntryDialog(
                self,
                "Enter your search intent/query for filtering:",
                "Search Intent Required",
                ""
            )
            
            if intent_dlg.ShowModal() != wx.ID_OK:
                intent_dlg.Destroy()
                return
            
            user_intent = intent_dlg.GetStringSelection()
            intent_dlg.Destroy()
            
            if not user_intent.strip():
                wx.MessageBox("Search intent is required for filtering.", "Error", wx.OK | wx.ICON_ERROR)
                return
        
        # Calculate total items to filter
        total_items = sum(len(results) for results in self.search_results.values())
        
        # Show progress dialog
        from view.progress_windows.filtering_progress_dialog import FilteringProgressDialog
        progress_dlg = FilteringProgressDialog(self, total_items, model_name)
        progress_dlg.Show()
        
        try:
            # Import provider system to get filtering strategies
            from model.providers import get_provider
            from model.GLProvider import GLProvider
            
            providers_list = GLProvider.get_providers_list()
            
            filtered_results = {}
            all_scored_results = {}  # Store ALL results with scores (relevant + irrelevant)
            total_relevant = 0
            total_irrelevant = 0
            
            # Always filter from the base unfiltered results in the model
            source_results = self.search_results_model.results
            
            # Process each provider
            for provider_id, results in source_results.items():
                # Check for cancellation
                if progress_dlg.is_cancelled():
                    break
                
                if not results:
                    filtered_results[provider_id] = results
                    continue
                
                # Get provider name for display
                provider = providers_list.get(provider_id)
                provider_name = provider.name if provider else provider_id
                
                progress_dlg.set_current_provider(provider_name, len(results))
                
                # Check for cancellation after setting provider
                if progress_dlg.is_cancelled():
                    break
                
                # IMPORTANT: Add original index and search_intent to each result
                results_with_intent = []
                for idx, result in enumerate(results):
                    result_copy = result.copy()
                    result_copy['search_intent'] = user_intent
                    result_copy['_original_index'] = idx  # Keep track of original position
                    results_with_intent.append(result_copy)
                
                # Get the provider and its filtering strategy
                try:
                    provider = get_provider(provider_id)
                    filtering_strategy = provider.get_filtering_strategy()
                    
                    if filtering_strategy is None:
                        # No filtering available for this provider
                        filtered_results[provider_id] = results
                        continue
                    
                    # Use the appropriate filtering method based on model size
                    if use_large_model:
                        relevant, irrelevant = filtering_strategy.filter_large(results_with_intent)
                    else:
                        relevant, irrelevant = filtering_strategy.filter_small(results_with_intent)
                    
                    # IMPORTANT: Save ALL results with scores (relevant + irrelevant)
                    # This preserves all information for future use with different thresholds
                    all_scored_results[provider_id] = relevant + irrelevant
                    
                    # Keep only relevant results for display
                    filtered_results[provider_id] = relevant
                    total_relevant += len(relevant)
                    total_irrelevant += len(irrelevant)
                    
                    # Update progress
                    progress_dlg.update_progress(provider_name, len(relevant), len(results))
                    
                    # Check for cancellation after filtering
                    if progress_dlg.is_cancelled():
                        break
                    
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    progress_dlg.set_error(provider_name, str(e))
                    # Keep original results if filtering fails
                    filtered_results[provider_id] = results
            
            # Check if cancelled
            was_cancelled = progress_dlg.cancelled
            
            # Close progress dialog
            progress_dlg.Close()
            progress_dlg.Destroy()
            
            # If cancelled, show message and don't continue
            if was_cancelled:
                wx.MessageBox(
                    "Filtering was cancelled.\n\nNo changes were made to the results.",
                    "Filtering Cancelled",
                    wx.OK | wx.ICON_INFORMATION
                )
                return
            
            # IMPORTANT: Save filter scores directly to the model using original indices
            for provider_id, scored_results in all_scored_results.items():
                if provider_id in self.search_results_model.results:
                    base_provider_results = self.search_results_model.results[provider_id]
                    
                    # Build index to score mapping from ALL scored results
                    index_to_score = {}
                    for result in scored_results:
                        if '_original_index' in result:
                            # Get the score from relevant_proba or relevant_score
                            score = result.get('relevant_proba', result.get('relevant_score', 0.0))
                            index_to_score[result['_original_index']] = float(score)
                    
                    # Add filter metadata for ALL results with their scores
                    for idx in range(len(base_provider_results)):
                        score = index_to_score.get(idx, 0.0)  # Default to 0.0 if not scored
                        self.search_results_model.add_filter_metadata(provider_id, idx, model_name, score)
            
            # Show summary
            wx.MessageBox(
                f"Filtering complete using {model_name}!\n\n"
                f"Relevant results kept: {total_relevant}\n"
                f"Irrelevant results removed: {total_irrelevant}\n\n"
                f"💡 Filter has been saved to memory. Click 'Save Results' to persist to disk.",
                "Filtering Complete",
                wx.OK | wx.ICON_INFORMATION
            )
            
            # Show filtered view
            new_window = SearchResultsWindow.create_filtered(
                None, 
                filtered_results, 
                self.query_generation,
                model_name
            )
            new_window.storage_instance_id = self.storage_instance_id
            new_window.search_results_model = self.search_results_model  # Share same model
            
            # Navigate to new window
            nav = get_navigation_controller()
            nav.push(new_window, 'search_results', close_previous=True)
            
        except ImportError as e:
            if progress_dlg:
                progress_dlg.Close()
                progress_dlg.Destroy()
            wx.MessageBox(
                f"Could not import filtering modules: {e}\n\n"
                f"Make sure the filtering_by_embeddings.py file is in controller/judgment/",
                "Import Error",
                wx.OK | wx.ICON_ERROR
            )
        except Exception as e:
            if progress_dlg:
                progress_dlg.Close()
                progress_dlg.Destroy()
            wx.MessageBox(f"Error during filtering: {e}", "Error", wx.OK | wx.ICON_ERROR)
            import traceback
            traceback.print_exc()
    
    def on_cell_selected(self, event, provider_id: str, results: list):
        """Handle grid cell selection to show result details."""
        row = event.GetRow()
        
        if 0 <= row < len(results):
            result = results[row]
            self.details_panel.display_result(result)
        
        event.Skip()
    
    def on_save_json(self, event):
        """Save current results - SIMPLE: just save the model to disk."""
        from model.SearchResults import SearchResults
        
        try:
            # If this window was opened from an existing saved folder (or previously saved), auto-save there
            if hasattr(self, '_loaded_storage_parent') and hasattr(self, '_loaded_folder_name'):
                parent_path = self._loaded_storage_parent
                folder_name = self._loaded_folder_name

                # Ensure we have a model to save
                if not self.search_results_model:
                    # Create one from current results
                    if self.query_generation:
                        query_gen_id = self.query_generation.instance_id
                        intent = self.query_generation.intent
                    else:
                        query_gen_id = "unknown"
                        intent = "Loaded search results"
                    self.search_results_model = SearchResults(
                        query_generation_id=query_gen_id,
                        intent=intent,
                        providers=list(self.search_results.keys()),
                        instance_id=self.storage_instance_id
                    )
                    for provider_id, results in self.search_results.items():
                        queries_list = None
                        if self.query_generation and provider_id in self.query_generation.results:
                            queries_list = self.query_generation.results[provider_id]
                        self.search_results_model.add_results(provider_id, results, queries=queries_list)

                # Validate folder name
                is_valid, error_msg = validate_folder_name(folder_name)
                if not is_valid:
                    wx.MessageBox(error_msg, "Invalid Folder Name", wx.OK | wx.ICON_ERROR)
                    return

                # Save without prompting
                try:
                    storage_path = self.search_results_model.save(storage_root=parent_path, folder_name=folder_name)
                    self.storage_instance_id = folder_name
                    available_filters = self.search_results_model.get_available_filters()
                    saved_info = [f"Location: {storage_path}", f"Instance ID: {self.storage_instance_id}"]
                    if available_filters:
                        saved_info.append(f"\n✓ Saved with {len(available_filters)} filter(s):")
                        for fname in available_filters:
                            saved_info.append(f"  • {fname}")
                    else:
                        saved_info.append("\n✓ Saved (no filters applied yet)")

                    wx.MessageBox(
                        f"Search results saved successfully!\n\n" + "\n".join(saved_info),
                        "Success",
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
            default_file = self.storage_instance_id if self.storage_instance_id else "search_results"
            
            dlg = wx.FileDialog(
                self,
                "Save Search Results As",
                defaultDir=default_dir,
                defaultFile=default_file,
                wildcard="Search Results Folder|*",
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
            
            # Ensure we have a search_results_model
            if not self.search_results_model:
                # Create one from current results
                if self.query_generation:
                    query_gen_id = self.query_generation.instance_id
                    intent = self.query_generation.intent
                else:
                    query_gen_id = "unknown"
                    intent = "Loaded search results"
                
                self.search_results_model = SearchResults(
                    query_generation_id=query_gen_id,
                    intent=intent,
                    providers=list(self.search_results.keys()),
                    instance_id=self.storage_instance_id
                )
                
                for provider_id, results in self.search_results.items():
                    queries_list = None
                    if self.query_generation and provider_id in self.query_generation.results:
                        queries_list = self.query_generation.results[provider_id]
                    self.search_results_model.add_results(provider_id, results, queries=queries_list)
            
            # Save using new API (no instance_id mutation)
            storage_path = self.search_results_model.save(storage_root=parent_path, folder_name=folder_name)
            self.storage_instance_id = folder_name
            
            # Show what was saved
            available_filters = self.search_results_model.get_available_filters()
            
            saved_info = [f"Location: {storage_path}"]
            saved_info.append(f"Instance ID: {self.storage_instance_id}")
            
            if available_filters:
                saved_info.append(f"\n✓ Saved with {len(available_filters)} filter(s):")
                for fname in available_filters:
                    saved_info.append(f"  • {fname}")
            else:
                saved_info.append("\n✓ Saved (no filters applied yet)")
            
            wx.MessageBox(
                f"Search results saved successfully!\n\n" + "\n".join(saved_info),
                "Success",
                wx.OK | wx.ICON_INFORMATION
            )
            
        except PermissionError:
            wx.MessageBox("Permission denied. Please choose a different location.", "Error", wx.OK | wx.ICON_ERROR)
        except OSError as e:
            wx.MessageBox(f"Filesystem error: {e}", "Error", wx.OK | wx.ICON_ERROR)
        except Exception as e:
            wx.MessageBox(f"Error saving results: {e}", "Error", wx.OK | wx.ICON_ERROR)
            traceback.print_exc()
