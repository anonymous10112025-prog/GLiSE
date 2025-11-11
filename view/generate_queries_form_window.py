import wx
import wx.adv
import wx.lib.scrolledpanel

from model.GLProvider import GLProvider
from model.LLMProvider import LLMProvider
from model.QueryGeneration import QueryGeneration
from model.Settings import get_settings
from controller.queries_generate_split import generate_queries
from view.progress_windows.progress_dialog import ProgressDialog
from view.results_window import ResultsWindow
from view.utils.menu_bar import AppMenuBar
from view.utils.navigation_controller import get_navigation_controller

class PromptWindow(wx.Frame):
    def __init__(self, parent=None):
        super().__init__(parent, title="GLiSE", size=(600, 500))
        
        # Set window icon
        from view.utils.icon_helper import set_window_icon
        set_window_icon(self)
        
        # Load settings
        self.settings = get_settings()
        
        # Create menu bar using reusable component
        menu_bar = AppMenuBar(self)
        self.SetMenuBar(menu_bar)
        
        # Track if form has unsaved changes
        self.form_modified = False
        
        # Create a scrolled panel instead of regular panel
        panel = wx.lib.scrolledpanel.ScrolledPanel(self)
        panel.SetupScrolling()
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Description section
        desc_label = wx.StaticText(panel, label="Search intent:")
        main_sizer.Add(desc_label, 0, wx.ALL, 5)
        
        self.description_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE, size=(-1, 100))
        main_sizer.Add(self.description_text, 0, wx.ALL | wx.EXPAND, 5)
        
        # Time Range section
        time_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Time Range")
        
        # Date pickers row
        date_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        from_label = wx.StaticText(panel, label="From:")
        date_sizer.Add(from_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.from_date = wx.adv.DatePickerCtrl(panel, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY)
        date_sizer.Add(self.from_date, 0, wx.ALL, 5)
        
        to_label = wx.StaticText(panel, label="To:")
        date_sizer.Add(to_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.to_date = wx.adv.DatePickerCtrl(panel, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY)
        date_sizer.Add(self.to_date, 0, wx.ALL, 5)
        
        time_box.Add(date_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        main_sizer.Add(time_box, 0, wx.ALL | wx.EXPAND, 5)

        # Sources section
        
        sources_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Sources")
        sources_grid = wx.GridSizer(rows=2, cols=3, hgap=10, vgap=5)
        
        gl_providers_registry = GLProvider.get_providers_list()
        self.source_checkboxes = []
        for provider in gl_providers_registry.values():
            checkbox = wx.CheckBox(panel, label=provider.name)
            self.source_checkboxes.append(checkbox)
            
            # Check if provider has required API keys configured
            is_enabled = self._check_provider_api_keys(provider.id)
            checkbox.Enable(is_enabled)
            if not is_enabled:
                checkbox.SetToolTip(f"API key not configured for {provider.name}. Please configure in Settings.")
            
            sources_grid.Add(checkbox, 0, wx.ALL, 5)
        
        sources_box.Add(sources_grid, 0, wx.ALL | wx.EXPAND, 5)
        
        main_sizer.Add(sources_box, 0, wx.ALL | wx.EXPAND, 5)
        
        # Advanced users toggle
        self.advanced_checkbox = wx.CheckBox(panel, label="For advanced users")
        self.advanced_checkbox.Bind(wx.EVT_CHECKBOX, self.on_toggle_advanced)
        main_sizer.Add(self.advanced_checkbox, 0, wx.ALL, 5)
        
        # LLM Configuration section (Advanced)
        self.llm_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "LLM Configuration")
        
        # LLM Selection
        llm_select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        llm_label = wx.StaticText(panel, label="Select LLM:")
        llm_select_sizer.Add(llm_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        # Get LLM model choices from data.json
        self.llm_models = LLMProvider.get_model_choices()
        self.llm_combobox = wx.ComboBox(panel, choices=self.llm_models, style=wx.CB_READONLY, size=(250, -1))
        
        # Set default model from settings
        default_model = self.settings.get('QUERY_DEFAULT_MODEL', 'gpt-4o')
        if self.llm_models:
            # Try to find and select the default model
            default_index = 0
            for i, model in enumerate(self.llm_models):
                if default_model in model:
                    default_index = i
                    break
            self.llm_combobox.SetSelection(default_index)
        
        llm_select_sizer.Add(self.llm_combobox, 0, wx.ALL, 5)
        
        self.llm_box.Add(llm_select_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # Temperature selector
        temp_sizer = wx.BoxSizer(wx.HORIZONTAL)
        temp_label = wx.StaticText(panel, label="Temperature:")
        temp_sizer.Add(temp_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        # Get default temperature from settings
        default_temp = str(self.settings.get('QUERY_FORGE_TEMPERATURE', 0.7))
        self.temperature_spinner = wx.SpinCtrlDouble(panel, value=default_temp, min=0.0, max=2.0, inc=0.1, size=(100, -1))
        self.temperature_spinner.SetDigits(1)
        temp_sizer.Add(self.temperature_spinner, 0, wx.ALL, 5)
        
        temp_info = wx.StaticText(panel, label="(0.0 = deterministic, 2.0 = creative)")
        temp_sizer.Add(temp_info, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.llm_box.Add(temp_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        main_sizer.Add(self.llm_box, 0, wx.ALL | wx.EXPAND, 5)
        
        # Hide LLM Configuration by default
        self.llm_box.ShowItems(False)
        
        # Parameters section (Advanced)
        self.params_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Parameters")
        
        # Use FlexGridSizer for 2 columns with proper alignment
        params_grid = wx.FlexGridSizer(rows=3, cols=2, vgap=10, hgap=20)
        params_grid.AddGrowableCol(0, 1)
        params_grid.AddGrowableCol(1, 1)
        
        # First row - Language
        language_row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        language_label = wx.StaticText(panel, label="Languages:")
        language_row_sizer.Add(language_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.language_text = wx.TextCtrl(panel, value="all", size=(120, -1))
        self.language_text.SetToolTip("Comma or space separated list (e.g., 'en, fr' or 'all')")
        language_row_sizer.Add(self.language_text, 0, wx.ALIGN_CENTER_VERTICAL)
        params_grid.Add(language_row_sizer, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        
        # Number of Queries
        queries_row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        queries_label = wx.StaticText(panel, label="Number of Queries:")
        queries_row_sizer.Add(queries_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        default_queries_num = str(self.settings.get('QUERIES_DEFAULT_NUMBER', 10))
        self.queries_number_spinner = wx.SpinCtrl(panel, value=default_queries_num, min=1, max=100, size=(80, -1))
        queries_row_sizer.Add(self.queries_number_spinner, 0, wx.ALIGN_CENTER_VERTICAL)
        params_grid.Add(queries_row_sizer, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        
        self.params_box.Add(params_grid, 0, wx.ALL | wx.EXPAND, 10)
        
        main_sizer.Add(self.params_box, 0, wx.ALL | wx.EXPAND, 5)
        
        # Hide Parameters by default
        self.params_box.ShowItems(False)
        
        # Search button
        self.search_button = wx.Button(panel, label="Generate Search Queries")
        self.search_button.Bind(wx.EVT_BUTTON, self.on_generate_queries)
        main_sizer.Add(self.search_button, 0, wx.ALL | wx.CENTER, 10)
        
        panel.SetSizer(main_sizer)
        self.Centre()
    
    def _check_provider_api_keys(self, provider_id: str) -> bool:
        """
        Check if the required API keys are configured for a provider.
        Uses the provider's own are_all_keys_set() method for scalability.
        
        Args:
            provider_id: The provider ID (e.g., "google", "gh_issues", "so")
            
        Returns:
            True if all required keys are configured, False otherwise
        """
        from model.providers import get_provider
        
        try:
            # Get the provider instance and check its keys
            provider = get_provider(provider_id)
            return provider.__class__.are_all_keys_set()
        except Exception:
            # If provider not found or error, default to False
            return False
    
    def on_toggle_advanced(self, event):
        """Toggle visibility of advanced sections (LLM Configuration and Parameters)."""
        is_checked = self.advanced_checkbox.GetValue()
        
        # Show or hide LLM Configuration section
        self.llm_box.ShowItems(is_checked)
        
        # Show or hide Parameters section
        self.params_box.ShowItems(is_checked)
        
        # Force the panel to recalculate its size
        panel = self.GetChildren()[0]  # Get the main panel
        panel.Layout()
        
        # Set appropriate window height based on visibility
        new_height = 720 if is_checked else 500
        self.SetSize((600, new_height))
        
        # Center the window after resizing
        self.Centre()
        
        # Update scrolling area
        panel.SetupScrolling(scrollToTop=False)
        
        # Refresh the display
        self.Refresh()
    
    def on_generate_queries(self, event):
        # Get values
        description = self.description_text.GetValue().strip()
        
        # Validate description
        if not description:
            wx.MessageBox("Please enter a Description.", "Validation Error", wx.OK | wx.ICON_WARNING)
            self.description_text.SetFocus()
            return
        
        # Get system prompt from settings (not from UI anymore)
        system_prompt = self.settings.get('QUERY_FORGE_ROLE', 
                                          'You are a helpful assistant that generates search queries for grey literature research.')
        
        # Validate sources
        sources = []
        sources_ids = []
        for source_checkbox in self.source_checkboxes:
            if source_checkbox.GetValue():
                sources.append(source_checkbox.GetLabel())
                sources_ids.append(GLProvider.get_provider_id_by_name(source_checkbox.GetLabel()))

        if not sources:
            wx.MessageBox("Please select at least one source.", "Validation Error", wx.OK | wx.ICON_WARNING)
            return
        
        # Get LLM configuration
        selected_llm_idx = self.llm_combobox.GetSelection()
        selected_llm_model = self.llm_models[selected_llm_idx] if selected_llm_idx >= 0 and self.llm_models else None
        temperature = self.temperature_spinner.GetValue()
        
        # Get parameter values
        queries_number = self.queries_number_spinner.GetValue()
        
        # Parse languages from text field (comma or space separated)
        languages_text = self.language_text.GetValue().strip()
        if not languages_text:
            languages = ["all"]
        else:
            # Split by comma or space, remove empty strings and strip whitespace
            import re
            languages = [lang.strip() for lang in re.split(r'[,\s]+', languages_text) if lang.strip()]
            if not languages:
                languages = ["all"]
        
        # Create QueryGeneration instance
        query_gen = QueryGeneration(
            model=selected_llm_model,
            system_prompt=system_prompt,
            temperature=temperature,
            intent=description,
            sources_ids=sources_ids,
            languages=languages,
            general_n=queries_number
        )
        
        # Create and show progress dialog
        progress_dlg = ProgressDialog(self, len(sources_ids), sources)
        progress_dlg.Show()
        
        # Force the dialog to render
        progress_dlg.Update()
        progress_dlg.Refresh()
        progress_dlg.Raise()
        
        # Define callbacks
        def on_source_start(source_id, source_name):
            """Called when starting to process a source."""
            progress_dlg.set_current_source(source_name)
        
        def on_source_complete(source_id, source_name, queries):
            """Called when each source completes."""
            query_gen.add_results(source_id, queries)
            progress_dlg.update_progress(source_id, source_name, len(queries))
        
        try:
            # Generate queries with progress tracking
            results = generate_queries(
                model=selected_llm_model,
                system_prompt=system_prompt,
                temperature=temperature,
                intent=description,
                platforms=sources_ids,
                languages=languages,
                general_n=queries_number,
                progress_callback=on_source_complete,
                start_callback=on_source_start,
                cancel_check=lambda: progress_dlg.is_cancelled()
            )
            
            # Check if cancelled before closing dialog
            was_cancelled = progress_dlg.cancelled
            
            # Close progress dialog
            progress_dlg.Close()
            progress_dlg.Destroy()
            
            # Check if any queries were generated
            total_queries = sum(len(queries) for queries in query_gen.results.values())
            
            if total_queries > 0:
                # Show results window with generated queries
                # Use parent=None to prevent auto-destruction when this window closes
                results_win = ResultsWindow(None, query_gen)
                
                # Navigate to results window (keeps this window open in background)
                nav = get_navigation_controller()
                nav.push(results_win, 'results', close_previous=False)
                
                # Show message if generation was cancelled
                if was_cancelled:
                    wx.MessageBox(
                        f"Query generation was cancelled. {total_queries} queries were generated before cancellation.",
                        "Generation Cancelled",
                        wx.OK | wx.ICON_INFORMATION
                    )
            else:
                # No queries generated
                if was_cancelled:
                    wx.MessageBox("Query generation was cancelled. No queries were generated.", "Generation Cancelled", wx.OK | wx.ICON_INFORMATION)
                else:
                    wx.MessageBox("No queries were generated.", "Generation Complete", wx.OK | wx.ICON_INFORMATION)
                    
        except Exception as e:
            progress_dlg.Close()
            progress_dlg.Destroy()
            wx.MessageBox(f"Error generating queries: {e}", "Error", wx.OK | wx.ICON_ERROR)
            import traceback
            traceback.print_exc()
    
    def has_unsaved_changes(self) -> bool:
        """Check if form has unsaved changes."""
        # Check if description is filled but no queries generated yet
        if self.description_text.GetValue().strip() and self.form_modified:
            return True
        return False
