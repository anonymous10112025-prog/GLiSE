"""
Result Details Panel - Side panel for displaying individual search result details.
Shows all fields of a selected result in a scrollable form with proper formatting.
"""

import wx
import wx.html
import webbrowser
from typing import Dict, Optional


class ResultDetailsPanel(wx.Panel):
    """
    Side panel that displays detailed information about a selected search result.
    Handles different field types (text, HTML, URLs) appropriately.
    """
    
    def __init__(self, parent):
        """
        Initialize the details panel.
        
        Args:
            parent: Parent window
        """
        super().__init__(parent)
        
        self.current_result = None
        
        # Create scrolled window for the content
        self.scroll = wx.ScrolledWindow(self)
        self.scroll.SetScrollRate(10, 10)
        
        # Main sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Header
        header_label = wx.StaticText(self, label="Result Details")
        header_font = header_label.GetFont()
        header_font.PointSize += 2
        header_font = header_font.Bold()
        header_label.SetFont(header_font)
        main_sizer.Add(header_label, 0, wx.ALL, 10)
        
        # Separator
        main_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        
        # Scrolled content area
        self.content_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scroll.SetSizer(self.content_sizer)
        main_sizer.Add(self.scroll, 1, wx.EXPAND | wx.ALL, 5)
        
        # Action buttons at bottom
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.copy_all_btn = wx.Button(self, label="Copy All Fields")
        self.copy_all_btn.Bind(wx.EVT_BUTTON, self.on_copy_all)
        self.copy_all_btn.Enable(False)
        button_sizer.Add(self.copy_all_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        self.SetSizer(main_sizer)
        
        # Show initial message
        self._show_empty_message()
    
    def _show_empty_message(self):
        """Show message when no result is selected."""
        self.content_sizer.Clear(True)
        
        msg = wx.StaticText(self.scroll, 
                           label="Select a result from the table\nto view details here.")
        msg.SetForegroundColour(wx.Colour(128, 128, 128))
        
        self.content_sizer.Add(msg, 0, wx.ALL | wx.ALIGN_CENTER, 20)
        self.scroll.Layout()
        self.scroll.FitInside()
    
    def display_result(self, result: Dict):
        """
        Display a search result with all its fields.
        
        Args:
            result: Dictionary containing result data
        """
        if not result:
            self._show_empty_message()
            return
        
        self.current_result = result
        self.copy_all_btn.Enable(True)
        
        # Clear previous content
        self.content_sizer.Clear(True)
        
        # Define field display order and special handling
        html_fields = ['snippet', 'body', 'description', 'html_snippet']
        
        # Display in specific order: source, search_query, url, then rest
        displayed_fields = set()
        
        # 1. Source (first) - Convert provider ID to name
        if 'source' in result:
            source_value = result['source']
            # Try to get provider name from ID
            try:
                from model.providers import get_provider
                provider = get_provider(source_value)
                source_value = provider.name
            except:
                # If provider lookup fails, use the raw value
                pass
            self._add_field('source', source_value)
            displayed_fields.add('source')
        
        # 2. Search Query (second)
        if 'search_query' in result:
            self._add_field('search_query', result['search_query'])
            displayed_fields.add('search_query')
        
        # 3. Title (third)
        if 'title' in result:
            self._add_field('title', result['title'])
            displayed_fields.add('title')
        
        # 4. URL (fourth)
        if 'url' in result:
            self._add_field('url', result['url'])
            displayed_fields.add('url')
        
        # 5. Content fields (snippet, body, description)
        for field in ['snippet', 'body', 'description']:
            if field in result:
                self._add_field(field, result[field], is_html_field=(field in html_fields))
                displayed_fields.add(field)
        
        # 6. Display remaining fields
        for field, value in sorted(result.items()):
            if field not in displayed_fields:
                self._add_field(field, value, is_html_field=(field in html_fields))
        
        self.scroll.Layout()
        self.scroll.FitInside()
    
    def _add_field(self, field_name: str, field_value, is_html_field: bool = False):
        """
        Add a field to the details panel.
        
        Args:
            field_name: Name of the field
            field_value: Value of the field
            is_html_field: Whether this field contains HTML
        """
        # Skip internal/technical fields that should not be displayed
        skip_fields = ['relevant', 'relevant_score', 'relevant_proba', '_original_index', '_filters', 'search_intent']
        if field_name in skip_fields:
            return
        
        if field_value is None or (isinstance(field_value, str) and not field_value.strip()):
            return
        
        # Create field container
        field_box = wx.StaticBoxSizer(wx.VERTICAL, self.scroll, self._format_field_name(field_name))
        
        # Handle different field types
        if field_name == 'url':
            self._add_url_field(field_box, field_value)
        elif is_html_field and self._is_html_content(str(field_value)):
            self._add_html_field(field_box, str(field_value))
        elif len(str(field_value)) > 100:  # Long text
            self._add_long_text_field(field_box, str(field_value))
        else:  # Short text
            self._add_short_text_field(field_box, str(field_value))
        
        self.content_sizer.Add(field_box, 0, wx.EXPAND | wx.ALL, 5)
    
    def _format_field_name(self, field_name: str) -> str:
        """Format field name for display."""
        return field_name.replace('_', ' ').title()
    
    def _is_html_content(self, text: str) -> bool:
        """Check if text contains HTML tags."""
        return '<' in text and '>' in text and any(tag in text.lower() for tag in ['<p>', '<div>', '<span>', '<a>', '<code>', '<pre>'])
    
    def _add_url_field(self, sizer: wx.StaticBoxSizer, url: str):
        """Add URL field with open and copy buttons."""
        url_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # URL text (clickable)
        url_text = wx.adv.HyperlinkCtrl(self.scroll, wx.ID_ANY, label=url, url=url)
        url_sizer.Add(url_text, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        
        # Copy button
        copy_btn = wx.Button(self.scroll, label="Copy", size=(60, -1))
        copy_btn.Bind(wx.EVT_BUTTON, lambda evt: self._copy_to_clipboard(url))
        url_sizer.Add(copy_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        
        # Open button
        open_btn = wx.Button(self.scroll, label="Open", size=(60, -1))
        open_btn.Bind(wx.EVT_BUTTON, lambda evt: webbrowser.open(url))
        url_sizer.Add(open_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        
        sizer.Add(url_sizer, 0, wx.EXPAND | wx.ALL, 5)
    
    def _add_html_field(self, sizer: wx.StaticBoxSizer, html_content: str):
        """Add HTML field with renderer."""
        # Create HTML window
        html_window = wx.html.HtmlWindow(self.scroll, size=(-1, 200), style=wx.html.HW_SCROLLBAR_AUTO)
        
        # Wrap content in basic HTML structure for better rendering
        wrapped_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; font-size: 10pt;">
        {html_content}
        </body>
        </html>
        """
        
        html_window.SetPage(wrapped_html)
        html_window.SetBackgroundColour(wx.Colour(250, 250, 250))
        
        sizer.Add(html_window, 1, wx.EXPAND | wx.ALL, 5)
    
    def _add_long_text_field(self, sizer: wx.StaticBoxSizer, text: str):
        """Add long text field with scrollable read-only text control."""
        text_ctrl = wx.TextCtrl(
            self.scroll,
            value=text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
            size=(-1, 150)
        )
        text_ctrl.SetBackgroundColour(wx.Colour(250, 250, 250))
        
        sizer.Add(text_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        
        # Add copy button
        copy_btn = wx.Button(self.scroll, label="Copy", size=(60, -1))
        copy_btn.Bind(wx.EVT_BUTTON, lambda evt: self._copy_to_clipboard(text))
        sizer.Add(copy_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 2)
    
    def _add_short_text_field(self, sizer: wx.StaticBoxSizer, text: str):
        """Add short text field as static text."""
        text_ctrl = wx.TextCtrl(
            self.scroll,
            value=text,
            style=wx.TE_READONLY | wx.BORDER_NONE,
            size=(-1, -1)
        )
        text_ctrl.SetBackgroundColour(self.GetBackgroundColour())
        
        sizer.Add(text_ctrl, 0, wx.EXPAND | wx.ALL, 5)
    
    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
    
    def on_copy_all(self, event):
        """Copy all fields to clipboard as formatted text."""
        if not self.current_result:
            return
        
        # Format all fields as text
        lines = []
        for field, value in self.current_result.items():
            if value is not None and str(value).strip():
                lines.append(f"{self._format_field_name(field)}: {value}")
        
        text = "\n\n".join(lines)
        self._copy_to_clipboard(text)
        
        # Show feedback
        wx.MessageBox("All fields copied to clipboard!", "Copied", wx.OK | wx.ICON_INFORMATION)
    
    def clear(self):
        """Clear the details panel."""
        self.current_result = None
        self.copy_all_btn.Enable(False)
        self._show_empty_message()
