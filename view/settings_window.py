import wx
import webbrowser
from model.Settings import get_settings, Settings
from view.utils.menu_bar import AppMenuBar
from view.utils.navigation_controller import get_navigation_controller


class SettingsWindow(wx.Frame):
    """Window for managing application settings (Singleton pattern)."""
    
    _instance = None  # Class variable to hold singleton instance
    
    def __new__(cls, parent=None, tab_index: int = 0, opened_from_home: bool = False):
        """Ensure only one instance of SettingsWindow exists."""
        if cls._instance is not None and cls._instance:
            # If instance exists, just show it and bring to front
            try:
                nav = get_navigation_controller()
                nav.show_and_raise(cls._instance)
                # Update the tab if needed
                if hasattr(cls._instance, 'notebook'):
                    cls._instance.notebook.SetSelection(tab_index)
                return cls._instance
            except:
                # Instance is dead, create new one
                cls._instance = None
        
        # Create new instance
        instance = super().__new__(cls)
        cls._instance = instance
        return instance
    
    def __init__(self, parent=None, tab_index: int = 0, opened_from_home: bool = False):
        """
        Initialize the settings window.
        
        Args:
            parent: The parent window
            tab_index: The index of the tab to select (0=API Keys, 1=Query Defaults, 2=OpenAI Settings)
            opened_from_home: True if opened from home page (to restore home when closing)
        """
        # Prevent re-initialization of singleton
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        super().__init__(
            parent,
            title="Settings",
            size=(700, 700),
            style=wx.DEFAULT_FRAME_STYLE
        )
        
        self._initialized = True
        self.settings = get_settings()
        self.modified = False
        self.opened_from_home = opened_from_home
        
        # Set window icon
        from view.utils.icon_helper import set_window_icon
        set_window_icon(self)
        
        # Add menu bar
        menu_bar = AppMenuBar(self)
        self.SetMenuBar(menu_bar)
        
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Create notebook for organized settings
        notebook = wx.Notebook(panel)
        
        # API Keys Tab
        api_panel = self.create_api_keys_panel(notebook)
        notebook.AddPage(api_panel, "API Keys")
        
        # Query Defaults Tab
        query_panel = self.create_query_defaults_panel(notebook)
        notebook.AddPage(query_panel, "Query Defaults")
        
        # Search Settings Tab
        search_panel = self.create_search_settings_panel(notebook)
        notebook.AddPage(search_panel, "Search Settings")
        
        # Select the specified tab
        if 0 <= tab_index < notebook.GetPageCount():
            notebook.SetSelection(tab_index)
        
        main_sizer.Add(notebook, 1, wx.ALL | wx.EXPAND, 10)
        
        # Bottom buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.save_btn = wx.Button(panel, label="Save Settings")
        self.save_btn.Bind(wx.EVT_BUTTON, self.on_save)
        button_sizer.Add(self.save_btn, 0, wx.ALL, 5)
        
        self.reset_btn = wx.Button(panel, label="Reset to Defaults")
        self.reset_btn.Bind(wx.EVT_BUTTON, self.on_reset)
        button_sizer.Add(self.reset_btn, 0, wx.ALL, 5)
        
        close_btn = wx.Button(panel, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda evt: self.Close())
        button_sizer.Add(close_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.ALL | wx.CENTER, 10)
        
        panel.SetSizer(main_sizer)
        self.Centre()
        
        # Track changes
        self.Bind(wx.EVT_CLOSE, self.on_close)
    
    def create_api_keys_panel(self, parent):
        """Create the API Keys settings panel."""
        panel = wx.ScrolledWindow(parent)
        panel.SetScrollRate(5, 5)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Store text controls
        self.api_key_fields = {}
        
        # API Keys with help buttons
        api_keys = [
            ("OPENAI_API_KEY", "OpenAI API Key", True),
            ("GOOGLE_API_KEY", "Google API Key", True),
            ("GOOGLE_CSE_CX", "Google Custom Search Engine ID", True),
            ("STACKEXCHANGE_API_KEY", "Stack Exchange API Key", False),
            ("GITHUB_TOKEN", "GitHub Personal Access Token", True)
        ]
        
        for key, label, required in api_keys:
            field_sizer = wx.BoxSizer(wx.VERTICAL)
            
            # Label with required indicator
            label_text = label
            if required:
                label_text += " *"
            key_label = wx.StaticText(panel, label=label_text)
            font = key_label.GetFont()
            font.PointSize += 1
            if required:
                font = font.Bold()
            key_label.SetFont(font)
            field_sizer.Add(key_label, 0, wx.ALL, 5)
            
            # Input and help button row
            input_sizer = wx.BoxSizer(wx.HORIZONTAL)
            
            # Text input (initially showing dots)
            initial_value = self.settings.get(key, "")
            text_ctrl = wx.TextCtrl(panel, value="•" * len(initial_value), size=(450, -1))
            text_ctrl.SetEditable(False)
            # Store actual value and visibility state as attributes
            text_ctrl.actual_value = initial_value
            text_ctrl.is_visible = False
            text_ctrl.api_key_name = key
            text_ctrl.Bind(wx.EVT_TEXT, self.on_api_key_text_changed)
            self.api_key_fields[key] = text_ctrl
            input_sizer.Add(text_ctrl, 1, wx.ALL | wx.EXPAND, 2)
            
            # Show/Hide button
            show_btn = wx.Button(panel, label="Show", size=(60, -1))
            show_btn.Bind(wx.EVT_BUTTON, lambda evt, tc=text_ctrl, btn=show_btn: self.toggle_visibility(tc, btn))
            input_sizer.Add(show_btn, 0, wx.ALL, 2)
            
            # Help button
            help_url = Settings.get_api_key_url(key)
            if help_url:
                help_btn = wx.Button(panel, label="Get Key", size=(80, -1))
                help_btn.Bind(wx.EVT_BUTTON, lambda evt, url=help_url: webbrowser.open(url))
                input_sizer.Add(help_btn, 0, wx.ALL, 2)
            
            field_sizer.Add(input_sizer, 0, wx.ALL | wx.EXPAND, 2)
            
            # Add separator
            field_sizer.Add(wx.StaticLine(panel), 0, wx.ALL | wx.EXPAND, 5)
            
            sizer.Add(field_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        panel.SetSizer(sizer)
        return panel
    
    def create_query_defaults_panel(self, parent):
        """Create the Query Defaults settings panel."""
        panel = wx.ScrolledWindow(parent)
        panel.SetScrollRate(5, 5)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Store controls
        self.query_fields = {}
        
        # Default Model
        model_sizer = wx.BoxSizer(wx.HORIZONTAL)
        model_label = wx.StaticText(panel, label="Default LLM Model:")
        model_sizer.Add(model_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        # Get LLM model choices from LLMProvider
        from model.LLMProvider import LLMProvider
        llm_models = LLMProvider.get_model_choices()
        
        model_ctrl = wx.ComboBox(panel, choices=llm_models, style=wx.CB_READONLY, size=(250, -1))
        
        # Set default model from settings
        default_model = self.settings.get('QUERY_DEFAULT_MODEL', 'gpt-4o')
        if llm_models:
            # Try to find and select the default model
            default_index = 0
            for i, model in enumerate(llm_models):
                if default_model in model:
                    default_index = i
                    break
            model_ctrl.SetSelection(default_index)
        
        model_ctrl.Bind(wx.EVT_COMBOBOX, self.on_field_changed)
        self.query_fields["QUERY_DEFAULT_MODEL"] = model_ctrl
        model_sizer.Add(model_ctrl, 0, wx.ALL, 5)
        
        sizer.Add(model_sizer, 0, wx.ALL, 5)
        
        # System Role/Prompt
        role_label = wx.StaticText(panel, label="System Prompt (Query Forge Role):")
        sizer.Add(role_label, 0, wx.ALL, 5)
        
        role_ctrl = wx.TextCtrl(
            panel,
            value=self.settings.get("QUERY_FORGE_ROLE", ""),
            style=wx.TE_MULTILINE,
            size=(-1, 100)
        )
        role_ctrl.Bind(wx.EVT_TEXT, self.on_field_changed)
        self.query_fields["QUERY_FORGE_ROLE"] = role_ctrl
        sizer.Add(role_ctrl, 0, wx.ALL | wx.EXPAND, 5)
        
        # Temperature
        temp_sizer = wx.BoxSizer(wx.HORIZONTAL)
        temp_label = wx.StaticText(panel, label="Temperature:")
        temp_sizer.Add(temp_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        temp_ctrl = wx.SpinCtrlDouble(
            panel,
            value=str(self.settings.get("QUERY_FORGE_TEMPERATURE", 0.2)),
            min=0.0,
            max=1.0,
            inc=0.1,
            size=(100, -1)
        )
        temp_ctrl.SetDigits(1)
        temp_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_field_changed)
        self.query_fields["QUERY_FORGE_TEMPERATURE"] = temp_ctrl
        temp_sizer.Add(temp_ctrl, 0, wx.ALL, 5)
        
        sizer.Add(temp_sizer, 0, wx.ALL, 5)
        
        # Default numbers
        numbers_grid = wx.FlexGridSizer(rows=3, cols=2, hgap=10, vgap=5)
        
        # Queries number (Google will auto-split 50/50 between docs and gray literature)
        numbers_grid.Add(wx.StaticText(panel, label="Default Queries Number:"), 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        queries_ctrl = wx.SpinCtrl(panel, value=str(self.settings.get("QUERIES_DEFAULT_NUMBER", 10)), min=1, max=100, size=(100, -1))
        queries_ctrl.Bind(wx.EVT_SPINCTRL, self.on_field_changed)
        self.query_fields["QUERIES_DEFAULT_NUMBER"] = queries_ctrl
        numbers_grid.Add(queries_ctrl, 0, wx.EXPAND)
        
        sizer.Add(numbers_grid, 0, wx.ALL, 10)
        
        panel.SetSizer(sizer)
        return panel
    
    def create_search_settings_panel(self, parent):
        """Create the Search Settings panel."""
        panel = wx.ScrolledWindow(parent)
        panel.SetScrollRate(5, 5)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Store controls
        self.search_fields = {}
        
        # Search settings section
        search_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Search Settings")
        settings_grid = wx.FlexGridSizer(rows=3, cols=2, hgap=10, vgap=10)
        
        # Max results per query
        settings_grid.Add(wx.StaticText(panel, label="Max Results Per Query:"), 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        max_query_ctrl = wx.SpinCtrl(panel, value=str(self.settings.get("MAX_RESULTS_PER_QUERY_DEFAULT", 50)), min=1, max=1000, size=(100, -1))
        max_query_ctrl.Bind(wx.EVT_SPINCTRL, self.on_field_changed)
        self.search_fields["MAX_RESULTS_PER_QUERY_DEFAULT"] = max_query_ctrl
        settings_grid.Add(max_query_ctrl, 0, wx.EXPAND)
        
        # Max results per provider
        settings_grid.Add(wx.StaticText(panel, label="Max Results Per Provider:"), 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        max_provider_ctrl = wx.SpinCtrl(panel, value=str(self.settings.get("MAX_RESULTS_PER_PROVIDER_DEFAULT", 100)), min=1, max=1000, size=(100, -1))
        max_provider_ctrl.Bind(wx.EVT_SPINCTRL, self.on_field_changed)
        self.search_fields["MAX_RESULTS_PER_PROVIDER_DEFAULT"] = max_provider_ctrl
        settings_grid.Add(max_provider_ctrl, 0, wx.EXPAND)
        
        # Sleep between requests
        settings_grid.Add(wx.StaticText(panel, label="Sleep Between Requests (sec):"), 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sleep_ctrl = wx.SpinCtrlDouble(panel, value=str(self.settings.get("SLEEP_BETWEEN", 1.0)), min=0.0, max=10.0, inc=0.1, size=(100, -1))
        sleep_ctrl.SetDigits(1)
        sleep_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_field_changed)
        self.search_fields["SLEEP_BETWEEN"] = sleep_ctrl
        settings_grid.Add(sleep_ctrl, 0, wx.EXPAND)
        
        search_box.Add(settings_grid, 0, wx.ALL, 10)
        sizer.Add(search_box, 0, wx.ALL | wx.EXPAND, 10)
        
        # OpenAI Embeddings settings section
        embeddings_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "OpenAI Embeddings Settings (for ML Filtering)")
        embeddings_grid = wx.FlexGridSizer(rows=2, cols=2, hgap=10, vgap=10)
        embeddings_grid.AddGrowableCol(1, 1)
        
        # OpenAI Tier
        embeddings_grid.Add(wx.StaticText(panel, label="OpenAI API Tier:"), 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        
        from model.TierInfo import get_tier_choices, get_choice_from_tier_id, get_tier_id_from_choice
        
        tier_choices = get_tier_choices()
        current_tier_id = self.settings.get("OPENAI_TIER", "free")
        current_tier_choice = get_choice_from_tier_id(current_tier_id)
        
        tier_ctrl = wx.ComboBox(panel, value=current_tier_choice, choices=tier_choices, style=wx.CB_READONLY, size=(400, -1))
        tier_ctrl.Bind(wx.EVT_COMBOBOX, self.on_field_changed)
        self.search_fields["OPENAI_TIER"] = tier_ctrl
        embeddings_grid.Add(tier_ctrl, 0, wx.EXPAND)
        
        # Overhead per input
        embeddings_grid.Add(wx.StaticText(panel, label="Overhead Per Input (tokens):"), 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        overhead_ctrl = wx.SpinCtrl(panel, value=str(self.settings.get("EMBEDDING_OVERHEAD_PER_INPUT", 150)), min=50, max=500, size=(100, -1))
        overhead_ctrl.Bind(wx.EVT_SPINCTRL, self.on_field_changed)
        overhead_ctrl.SetToolTip("Overhead tokens added per input for embeddings API (default: 150)")
        self.search_fields["EMBEDDING_OVERHEAD_PER_INPUT"] = overhead_ctrl
        embeddings_grid.Add(overhead_ctrl, 0, wx.EXPAND)
        
        embeddings_box.Add(embeddings_grid, 0, wx.ALL | wx.EXPAND, 10)
        
        # Add help text
        help_text = wx.StaticText(panel, label=
            "Note: The tier determines rate limits for OpenAI API calls.\n"
            "Safe maximum tokens per request is calculated as 15% of your tier's tokens-per-minute limit.\n"
            "Higher tiers allow for larger batch sizes and faster filtering.")
        help_text.SetForegroundColour(wx.Colour(100, 100, 100))
        help_font = help_text.GetFont()
        help_font.SetPointSize(8)
        help_text.SetFont(help_font)
        embeddings_box.Add(help_text, 0, wx.ALL, 10)
        
        sizer.Add(embeddings_box, 0, wx.ALL | wx.EXPAND, 10)
        
        panel.SetSizer(sizer)
        return panel
    
    def toggle_visibility(self, text_ctrl, button):
        """Toggle password visibility for API key fields."""
        if text_ctrl.is_visible:
            # Hide it - replace with dots
            text_ctrl.actual_value = text_ctrl.GetValue()
            text_ctrl.ChangeValue("•" * len(text_ctrl.actual_value))
            text_ctrl.SetEditable(False)
            text_ctrl.is_visible = False
            button.SetLabel("Show")
        else:
            # Show it - restore actual value
            text_ctrl.ChangeValue(text_ctrl.actual_value)
            text_ctrl.SetEditable(True)
            text_ctrl.is_visible = True
            button.SetLabel("Hide")
    
    def on_api_key_text_changed(self, event):
        """Handle text changes in API key fields."""
        text_ctrl = event.GetEventObject()
        # Only update actual_value when visible (being edited)
        if text_ctrl.is_visible:
            text_ctrl.actual_value = text_ctrl.GetValue()
        # Mark as modified
        self.on_field_changed(event)
    
    def on_field_changed(self, event):
        """Mark settings as modified when any field changes."""
        self.modified = True
        self.save_btn.SetBackgroundColour(wx.Colour(255, 200, 100))
        self.save_btn.SetLabel("Save Settings *")
    
    def on_save(self, event):
        """Save all settings."""
        # Collect all values
        new_settings = {}
        
        # API Keys - use actual_value to get the real value (not dots)
        for key, ctrl in self.api_key_fields.items():
            new_settings[key] = ctrl.actual_value
        
        # Query defaults
        for key, ctrl in self.query_fields.items():
            if isinstance(ctrl, wx.SpinCtrl):
                new_settings[key] = ctrl.GetValue()
            elif isinstance(ctrl, wx.SpinCtrlDouble):
                new_settings[key] = ctrl.GetValue()
            elif isinstance(ctrl, wx.ComboBox):
                new_settings[key] = ctrl.GetStringSelection()
            else:
                new_settings[key] = ctrl.GetValue()
        
        # Search settings
        for key, ctrl in self.search_fields.items():
            if isinstance(ctrl, wx.SpinCtrl):
                new_settings[key] = ctrl.GetValue()
            elif isinstance(ctrl, wx.SpinCtrlDouble):
                new_settings[key] = ctrl.GetValue()
            elif isinstance(ctrl, wx.ComboBox):
                if key == "OPENAI_TIER":
                    # Convert choice to tier ID
                    from model.TierInfo import get_tier_id_from_choice
                    new_settings[key] = get_tier_id_from_choice(ctrl.GetStringSelection())
                else:
                    new_settings[key] = ctrl.GetStringSelection()
            else:
                new_settings[key] = ctrl.GetValue()
        
        # Update and save
        self.settings.update(new_settings)
        if self.settings.save():
            wx.MessageBox("Settings saved successfully!", "Success", wx.OK | wx.ICON_INFORMATION)
            self.modified = False
            self.save_btn.SetBackgroundColour(wx.NullColour)
            self.save_btn.SetLabel("Save Settings")
        else:
            wx.MessageBox("Error saving settings!", "Error", wx.OK | wx.ICON_ERROR)
    
    def on_reset(self, event):
        """Reset all settings to defaults."""
        dlg = wx.MessageDialog(
            self,
            "Are you sure you want to reset all settings to defaults? This cannot be undone.",
            "Confirm Reset",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
        )
        
        if dlg.ShowModal() == wx.ID_YES:
            # Reset to defaults
            self.settings.update(Settings.DEFAULTS.copy())
            self.settings.save()
            
            # Reload UI
            self.Close()
            new_window = SettingsWindow(self.GetParent())
            new_window.Show()
        
        dlg.Destroy()
    
    def on_close(self, event):
        """Handle window close with unsaved changes check."""
        should_close = True
        
        # Clear singleton instance reference
        SettingsWindow._instance = None
        
        if self.modified:
            dlg = wx.MessageDialog(
                self,
                "You have unsaved changes. Save before closing?",
                "Unsaved Changes",
                wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION
            )
            result = dlg.ShowModal()
            dlg.Destroy()
            
            if result == wx.ID_YES:
                self.on_save(None)
            elif result == wx.ID_CANCEL:
                should_close = False
        
        if should_close:
            # Just close settings - parent windows remain open
            # No need to restore home or any other window
            event.Skip()
        # If should_close is False, don't call Skip() to prevent closing


if __name__ == "__main__":
    app = wx.App()
    window = SettingsWindow()
    window.Show()
    app.MainLoop()
