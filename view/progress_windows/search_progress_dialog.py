"""
Search progress dialog for executing queries.
"""

import wx


class SearchProgressDialog(wx.Dialog):
    """Dialog showing progress of search execution."""
    
    def __init__(self, parent, total_queries: int):
        """
        Initialize the search progress dialog.
        
        Args:
            parent: Parent window
            total_queries: Total number of queries to execute
        """
        super().__init__(
            parent,
            title="Executing Searches",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(500, 300)
        )
        
        self.total_queries = total_queries
        self.current_query = 0
        self.cancelled = False
        
        # Set window icon
        from view.utils.icon_helper import set_window_icon
        set_window_icon(self)
        
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title_label = wx.StaticText(panel, label="Searching Grey Literature Sources...")
        title_font = title_label.GetFont()
        title_font.PointSize += 2
        title_font = title_font.Bold()
        title_label.SetFont(title_font)
        main_sizer.Add(title_label, 0, wx.ALL | wx.CENTER, 10)
        
        # Current query label
        self.current_query_label = wx.StaticText(panel, label="Initializing...")
        main_sizer.Add(self.current_query_label, 0, wx.ALL | wx.LEFT, 5)
        
        # Progress gauge
        self.progress_gauge = wx.Gauge(panel, range=total_queries, style=wx.GA_HORIZONTAL)
        main_sizer.Add(self.progress_gauge, 0, wx.ALL | wx.EXPAND, 10)
        
        # Progress text (X of Y queries)
        self.progress_text = wx.StaticText(panel, label=f"0 of {total_queries} queries executed")
        main_sizer.Add(self.progress_text, 0, wx.ALL | wx.LEFT, 5)
        
        # Details text area
        self.details_text = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
            size=(-1, 80)
        )
        self.details_text.SetValue("Ready to start searching...\n")
        main_sizer.Add(self.details_text, 1, wx.ALL | wx.EXPAND, 10)
        
        # Cancel button
        self.cancel_btn = wx.Button(panel, label="Cancel")
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        main_sizer.Add(self.cancel_btn, 0, wx.ALL | wx.CENTER, 10)
        
        panel.SetSizer(main_sizer)
        self.Centre()
    
    def update_progress(self, query: str, source: str, results_count: int):
        """
        Update progress when a query completes.
        
        Args:
            query: The query that was executed
            source: Provider name
            results_count: Number of results found
        """
        self.current_query += 1
        self.progress_gauge.SetValue(self.current_query)
        
        # Update labels
        if self.current_query < self.total_queries:
            self.current_query_label.SetLabel(f"Processing query {self.current_query + 1}...")
        else:
            self.current_query_label.SetLabel("Completed!")
        
        self.progress_text.SetLabel(f"{self.current_query} of {self.total_queries} queries executed")
        
        # Add to details
        detail_msg = f"✓ [{source}] {query[:50]}... → {results_count} results\n"
        self.details_text.AppendText(detail_msg)
        
        # Force UI update
        wx.SafeYield()
    
    def set_current_query(self, query: str, source: str):
        """
        Set the current query being processed.
        
        Args:
            query: Query being executed
            source: Provider name
        """
        self.current_query_label.SetLabel(f"Processing: {query[:50]}...")
        self.details_text.AppendText(f"⏳ [{source}] {query[:50]}...\n")
        wx.SafeYield()
    
    def set_error(self, query: str, error_msg: str):
        """
        Display an error for a query.
        
        Args:
            query: Query that failed
            error_msg: Error message
        """
        self.details_text.AppendText(f"✗ {query[:50]}... ERROR: {error_msg}\n")
        wx.SafeYield()
    
    def on_cancel(self, event):
        """Handle cancel button click."""
        # Set cancelled flag immediately without confirmation dialog
        self.cancelled = True
        self.cancel_btn.Enable(False)
        self.cancel_btn.SetLabel("Cancelling...")
        self.current_query_label.SetLabel("Cancelling search...")
        self.details_text.AppendText("\n⚠️ Cancellation requested by user. Stopping search...\n")
    
    def is_cancelled(self):
        """
        Check if the user has requested cancellation.
        
        Returns:
            True if cancelled, False otherwise
        """
        return self.cancelled
