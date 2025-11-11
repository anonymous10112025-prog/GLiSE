import wx


class ProgressDialog(wx.Dialog):
    """Dialog showing progress of query generation across multiple sources."""
    
    def __init__(self, parent, sources_count: int, sources_names: list):
        """
        Initialize the progress dialog.
        
        Args:
            parent: Parent window
            sources_count: Total number of sources
            sources_names: List of source names for display
        """
        super().__init__(
            parent,
            title="Generating Queries",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(500, 300)
        )
        
        self.sources_count = sources_count
        self.sources_names = sources_names
        self.current_source = 0
        self.cancelled = False
        
        # Set window icon
        from view.utils.icon_helper import set_window_icon
        set_window_icon(self)
        
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title_label = wx.StaticText(panel, label="Generating Search Queries...")
        title_font = title_label.GetFont()
        title_font.PointSize += 2
        title_font = title_font.Bold()
        title_label.SetFont(title_font)
        main_sizer.Add(title_label, 0, wx.ALL | wx.CENTER, 10)
        
        # Current source label
        self.current_source_label = wx.StaticText(panel, label="Initializing...")
        main_sizer.Add(self.current_source_label, 0, wx.ALL | wx.LEFT, 5)
        
        # Progress gauge
        self.progress_gauge = wx.Gauge(panel, range=sources_count, style=wx.GA_HORIZONTAL)
        main_sizer.Add(self.progress_gauge, 0, wx.ALL | wx.EXPAND, 10)
        
        # Progress text (X of Y sources)
        self.progress_text = wx.StaticText(panel, label=f"0 of {sources_count} sources completed")
        main_sizer.Add(self.progress_text, 0, wx.ALL | wx.LEFT, 5)
        
        # Details text area (showing recent activity)
        self.details_text = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
            size=(-1, 80)
        )
        self.details_text.SetValue("Ready to start generating queries...\n")
        main_sizer.Add(self.details_text, 1, wx.ALL | wx.EXPAND, 10)
        
        # Cancel button
        self.cancel_btn = wx.Button(panel, label="Cancel")
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        main_sizer.Add(self.cancel_btn, 0, wx.ALL | wx.CENTER, 10)
        
        panel.SetSizer(main_sizer)
        self.Centre()
    
    def update_progress(self, source_id: str, source_name: str, queries_count: int):
        """
        Update progress when a source completes.
        
        Args:
            source_id: Provider ID
            source_name: Display name of the source
            queries_count: Number of queries generated
        """
        # Update counter
        self.current_source += 1
        
        # Update progress gauge
        self.progress_gauge.SetValue(self.current_source)
        
        # Update current source label
        if self.current_source < self.sources_count:
            next_source = self.sources_names[self.current_source] if self.current_source < len(self.sources_names) else "Next source"
            self.current_source_label.SetLabel(f"Processing: {next_source}")
        else:
            self.current_source_label.SetLabel("Completed!")
        
        # Update progress text
        self.progress_text.SetLabel(f"{self.current_source} of {self.sources_count} sources completed")
        
        # Add to details
        self.details_text.AppendText(f"✓ {source_name}: {queries_count} queries generated\n")
        
        # Force UI to process events and redraw
        wx.SafeYield()
        self.Update()
    
    def set_current_source(self, source_name: str):
        """
        Set the current source being processed (before it completes).
        
        Args:
            source_name: Display name of the source
        """
        self.current_source_label.SetLabel(f"Processing: {source_name}")
        self.details_text.AppendText(f"⏳ Starting {source_name}...\n")
        
        # Force UI to process events and redraw
        wx.SafeYield()
        self.Update()
    
    def set_error(self, source_name: str, error_msg: str):
        """
        Display an error for a source.
        
        Args:
            source_name: Display name of the source
            error_msg: Error message
        """
        self.details_text.AppendText(f"✗ {source_name}: ERROR - {error_msg}\n")
        
        # Force UI to process events and redraw
        wx.SafeYield()
        self.Update()
    
    def on_cancel(self, event):
        """Handle cancel button click."""
        self.cancelled = True
        self.cancel_btn.Enable(False)
        self.cancel_btn.SetLabel("Cancelling...")
        self.current_source_label.SetLabel("Cancelling query generation...")
        self.details_text.AppendText("\n⚠️ Cancellation requested by user. Stopping generation...\n")
        
        # Force UI update
        self.Update()
    
    def is_cancelled(self):
        """
        Check if the user has requested cancellation.
        
        Returns:
            True if cancelled, False otherwise
        """
        return self.cancelled
