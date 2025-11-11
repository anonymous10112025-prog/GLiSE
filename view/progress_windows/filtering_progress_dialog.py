"""
Filtering progress dialog for ML filtering operations.
"""

import wx


class FilteringProgressDialog(wx.Dialog):
    """Dialog showing progress of filtering operation."""
    
    def __init__(self, parent, total_items: int, model_name: str):
        """
        Initialize the filtering progress dialog.
        
        Args:
            parent: Parent window
            total_items: Total number of items to filter
            model_name: Name of the ML model being used
        """
        super().__init__(
            parent,
            title="Filtering Results",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(500, 300)
        )
        
        self.total_items = total_items
        self.current_item = 0
        self.cancelled = False
        
        # Set window icon
        from view.utils.icon_helper import set_window_icon
        set_window_icon(self)
        
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title_label = wx.StaticText(panel, label=f"Filtering with {model_name}...")
        title_font = title_label.GetFont()
        title_font.PointSize += 2
        title_font = title_font.Bold()
        title_label.SetFont(title_font)
        main_sizer.Add(title_label, 0, wx.ALL | wx.CENTER, 10)
        
        # Current provider label
        self.current_provider_label = wx.StaticText(panel, label="Initializing...")
        main_sizer.Add(self.current_provider_label, 0, wx.ALL | wx.LEFT, 5)
        
        # Progress gauge
        self.progress_gauge = wx.Gauge(panel, range=total_items, style=wx.GA_HORIZONTAL)
        main_sizer.Add(self.progress_gauge, 0, wx.ALL | wx.EXPAND, 10)
        
        # Progress text (X of Y items)
        self.progress_text = wx.StaticText(panel, label=f"0 of {total_items} items filtered")
        main_sizer.Add(self.progress_text, 0, wx.ALL | wx.LEFT, 5)
        
        # Details text area
        self.details_text = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
            size=(-1, 80)
        )
        self.details_text.SetValue("Ready to start filtering...\n")
        main_sizer.Add(self.details_text, 1, wx.ALL | wx.EXPAND, 10)
        
        # Cancel button
        self.cancel_btn = wx.Button(panel, label="Cancel")
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        main_sizer.Add(self.cancel_btn, 0, wx.ALL | wx.CENTER, 10)
        
        panel.SetSizer(main_sizer)
        self.Centre()
    
    def update_progress(self, provider_name: str, filtered_count: int, total_count: int):
        """
        Update progress when a provider's filtering completes.
        
        Args:
            provider_name: Name of the provider
            filtered_count: Number of items marked as relevant
            total_count: Total number of items in this provider
        """
        self.current_item += total_count
        self.progress_gauge.SetValue(min(self.current_item, self.total_items))
        
        # Update labels
        if self.current_item < self.total_items:
            self.current_provider_label.SetLabel(f"Processing next provider...")
        else:
            self.current_provider_label.SetLabel("Completed!")
        
        self.progress_text.SetLabel(f"{self.current_item} of {self.total_items} items filtered")
        
        # Add to details
        detail_msg = f"✓ [{provider_name}] {filtered_count} relevant / {total_count} total\n"
        self.details_text.AppendText(detail_msg)
        
        # Force UI update
        wx.GetApp().Yield()
    
    def set_current_provider(self, provider_name: str, item_count: int):
        """
        Set the current provider being processed.
        
        Args:
            provider_name: Provider name
            item_count: Number of items in this provider
        """
        self.current_provider_label.SetLabel(f"Filtering {provider_name}...")
        self.details_text.AppendText(f"⏳ Processing {provider_name} ({item_count} items)...\n")
        wx.GetApp().Yield()
    
    def set_error(self, provider_name: str, error_msg: str):
        """
        Display an error for a provider.
        
        Args:
            provider_name: Provider that failed
            error_msg: Error message
        """
        self.details_text.AppendText(f"✗ [{provider_name}] ERROR: {error_msg}\n")
        wx.GetApp().Yield()
    
    def on_cancel(self, event):
        """Handle cancel button click."""
        # Set cancelled flag immediately without confirmation dialog
        self.cancelled = True
        self.cancel_btn.Enable(False)
        self.cancel_btn.SetLabel("Cancelling...")
        self.current_provider_label.SetLabel("Cancelling filtering...")
        self.details_text.AppendText("\n⚠️ Cancellation requested by user. Stopping filtering...\n")
    
    def is_cancelled(self):
        """
        Check if the user has requested cancellation.
        
        Returns:
            True if cancelled, False otherwise
        """
        return self.cancelled
